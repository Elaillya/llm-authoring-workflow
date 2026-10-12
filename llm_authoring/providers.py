"""JSON and complete Responses SSE clients. Keys stay in private configuration, never evidence."""
import copy
from contextlib import contextmanager
import hashlib
import signal
import threading
import time
import json
import os
from pathlib import Path
import re
import stat
import urllib.error
import urllib.parse
import urllib.request

from .core import Error, NAMES, active_question, now, read_json, require, response_dir, save_response, write_json

FORMAT = ('Formatting re-enabled\n请直接输出完整 Markdown 正文；标题、列表、表格和代码块使用标准 Markdown。'
          '不要把整个回答放入一个 Markdown 代码块。请独立回答用户题目。')
SUFFIXES = {'chat_completions':'/chat/completions', 'responses':'/responses', 'anthropic_messages':'/messages'}


def private_json(path):
    path=Path(path)
    require(path.is_file() and not path.is_symlink(), 'API 配置须为普通私有文件')
    require(stat.S_IMODE(path.stat().st_mode)&0o077==0, 'API 配置权限须为 600（不能允许其他用户读取）')
    return read_json(path)


def load_provider(path, role, *, allow_local=False):
    require(role in NAMES, 'API 仅支持 seed/gpt/claude')
    config=private_json(path)
    require(config.get('schema_version')==1,'API 配置 schema_version 必须为 1')
    provider=copy.deepcopy(config.get('providers',{}).get(role,{}))
    require(provider.get('display_name')==NAMES[role], f'{role} display_name 须为 {NAMES[role]}')
    model=provider.get('model','').strip()
    # Endpoint IDs may be opaque; returned ID is still checked against explicit mappings.
    require(model, f'{role} 未配置实际模型 ID')
    protocol=provider.get('protocol')
    require(protocol in SUFFIXES,'协议须为 chat_completions/responses/anthropic_messages')
    url=urllib.parse.urlsplit(provider.get('base_url','').strip())
    require(url.hostname and not url.username and not url.password and not url.query and not url.fragment,'API 地址不能包含凭据或查询参数')
    require(url.scheme=='https' or (allow_local and url.scheme=='http' and url.hostname in ('127.0.0.1','localhost')), 'API 地址须为 HTTPS')
    prefix=url.path.rstrip('/')
    effective=next((key for key,suffix in SUFFIXES.items() if prefix.endswith(suffix)),protocol)
    if not any(prefix.endswith(s) for s in SUFFIXES.values()):
        prefix+=(('/v1' if not prefix.endswith('/v1') else '')+SUFFIXES[effective])
    endpoint=urllib.parse.urlunsplit((url.scheme,url.netloc,prefix,'',''))
    key=provider.get('api_key','').strip()
    if not key and provider.get('api_key_file'):
        keyfile=Path(provider['api_key_file'])
        if not keyfile.is_absolute(): keyfile=Path(path).parent/keyfile
        require(keyfile.is_file() and not keyfile.is_symlink() and stat.S_IMODE(keyfile.stat().st_mode)&0o077==0,'密钥文件须为普通私有文件')
        key=keyfile.read_text().strip()
    if not key and provider.get('api_key_env'): key=os.environ.get(provider['api_key_env'],'').strip()
    require(key and '\n' not in key and '\r' not in key, f'{role} 缺少有效密钥')
    provider.update({'endpoint':endpoint,'effective_protocol':effective,'model':model,'_key':key})
    return provider


def public_provider(p):
    return {k:p.get(k) for k in ('display_name','model','protocol','effective_protocol','endpoint')}


def make_payload(p, prompt, *, max_output=None):
    protocol=p['effective_protocol'];options=copy.deepcopy(p.get('request_options',{}))
    require(isinstance(options,dict),'request_options 须为 JSON 对象')
    require(not set(options)&{'model','messages','input','system','instructions','stream','tools','tool_choice','store','n'}, 'request_options 不能覆盖题面、消息、流式或工具')
    require(set(options)<= {'max_tokens','max_completion_tokens','max_output_tokens','temperature','top_p','reasoning','reasoning_effort','thinking','output_config','stop','seed','frequency_penalty','presence_penalty'}, 'request_options 包含未支持参数；认证信息只能放私有配置的专用字段')
    if protocol=='chat_completions':
        if 'max_output_tokens' in options: options['max_completion_tokens']=options.pop('max_output_tokens')
        if 'reasoning' in options:
            reasoning=options.pop('reasoning')
            require(set(reasoning)=={'effort'},'Chat Completions 只能转换 reasoning.effort')
            options['reasoning_effort']=reasoning['effort']
        if max_output is not None:
            options.pop('max_tokens',None);options['max_completion_tokens' if p['model'].startswith('gpt') else 'max_tokens']=max_output
        result={'model':p['model'],'messages':[{'role':'system','content':FORMAT},{'role':'user','content':prompt}],'stream':False,**options}
    elif protocol=='responses':
        if 'max_tokens' in options: options['max_output_tokens']=options.pop('max_tokens')
        if max_output is not None: options['max_output_tokens']=max_output
        result={'model':p['model'],'instructions':FORMAT,'input':[{'role':'user','content':[{'type':'input_text','text':prompt}]}],'stream':True,'store':False,**options}
    else:
        if max_output is not None: options['max_tokens']=max_output
        require(isinstance(options.get('max_tokens'),int) and options['max_tokens']>0,'Claude 需要 max_tokens')
        result={'model':p['model'],'system':FORMAT,'messages':[{'role':'user','content':prompt}],'stream':False,**options}
    # Confirm required high reasoning independently of display names.
    if p['display_name']==NAMES['gpt']:
        effort=options.get('reasoning_effort') if protocol=='chat_completions' else options.get('reasoning',{}).get('effort')
        require(effort in ('medium','high','xhigh'),'GPT 需要中高推理配置')
    if p['display_name']==NAMES['claude']:
        require(options.get('thinking',{}).get('type') in ('adaptive','enabled') and options.get('output_config',{}).get('effort','high') in ('medium','high','max'), 'Claude 需要中高推理配置')
    return result


def parse_response(protocol, data):
    require(isinstance(data,dict) and not data.get('error'),'API 返回错误，不能作为模型未达成')
    if protocol=='chat_completions':
        choices=data.get('choices',[])
        require(len(choices)==1,'必须得到单条回复')
        item=choices[0];message=item.get('message',{})
        require(not message.get('refusal'),'API 拒绝回复，证据不足')
        text=message.get('content','')
        if isinstance(text,list): text=''.join(v.get('text','') for v in text if v.get('type') in ('text','output_text'))
        finish=item.get('finish_reason');complete=finish=='stop' and not message.get('tool_calls')
    elif protocol=='responses':
        parts=[]
        for item in data.get('output',[]):
            if item.get('type')=='message':
                require(item.get('status','completed')=='completed','Responses 消息未完整完成')
                for block in item.get('content',[]):
                    require(block.get('type')!='refusal','API 拒绝回复，证据不足')
                    if block.get('type')=='output_text': parts.append(block['text'])
        text='\n\n'.join(parts);finish=data.get('status');complete=finish=='completed'
    else:
        text='\n\n'.join(block['text'] for block in data.get('content',[]) if block.get('type')=='text')
        finish=data.get('stop_reason');complete=finish in ('end_turn','stop_sequence')
    require(isinstance(text,str) and text.strip(),'API 未返回正文，证据不足')
    return {'text':text,'returned_model':data.get('model',''),'response_id':data.get('id',''),
            'finish_reason':finish,'completion_status':'complete' if complete else 'incomplete','usage':data.get('usage',{})}


def model_matches(returned, expected):
    # Only spelling punctuation/case aliases; version suffixes remain significant.
    normalize=lambda value:re.sub(r'[^a-z0-9]','',str(value).casefold())
    return bool(returned) and any(normalize(returned)==normalize(item) for item in expected)


def decode_raw(protocol,raw,raw_format='json'):
    if raw_format=='json':return json.loads(raw)
    require(protocol=='responses' and raw_format=='sse','不支持该流式协议')
    completed=None;data_lines=[]
    def consume(lines):
        if not lines:return None
        value='\n'.join(lines)
        if value=='[DONE]':return None
        event=json.loads(value)
        require(event.get('type') not in ('error','response.failed','response.incomplete'),'流式响应失败或不完整，不能作为考点失败')
        return event.get('response') if event.get('type')=='response.completed' else None
    for line in raw.decode('utf-8').splitlines()+['']:
        if line.startswith('data:'):data_lines.append(line[5:].lstrip())
        elif not line:
            result=consume(data_lines)
            if result is not None:completed=result
            data_lines=[]
    require(completed is not None,'流式响应缺少完整 completed 事件，保留原流但不补写或评分')
    return completed


def capture_raw(root,p,role,raw,options,captured_at=None,raw_format='json'):
    parsed=parse_response(p['effective_protocol'],decode_raw(p['effective_protocol'],raw,raw_format))
    expected=p.get('expected_response_models',[]) or [p['model']]
    require(model_matches(parsed['returned_model'],expected),'实际返回模型与配置不匹配：已保留响应，待核对模型映射；不会替换指定模型')
    require(parsed['completion_status']=='complete','回复截断或未完成：已保留原响应，不判为考点失败，不自动补写')
    meta={**public_provider(p),**{k:v for k,v in parsed.items() if k!='text'},'request_options':options,
          'source_kind':'api','evidence_status':'pending_screenshot','model_identity_check':'returned_model_matches_configured_id_allowing_punctuation',
          'raw_response_sha256':__import__('hashlib').sha256(raw).hexdigest(),'raw_response_format':raw_format,
          'raw_response_file':'raw_response.sse' if raw_format=='sse' else 'raw_response.json'}
    if captured_at: meta['captured_at']=captured_at
    save_response(root,role,parsed['text'],meta,raw)
    return {'role':role,'display_name':p['display_name'],'returned_model':parsed['returned_model'],'completion_status':'complete','reply':str(response_dir(root,role)/'reply.md')}


def recover(root,config_path,role,attempt):
    """Recover already-paid raw response; never sends an HTTP request."""
    p=load_provider(config_path,role);current=active_question(root)
    record=Path(attempt).resolve();expected=(Path(root)/'attempts'/current['prompt_sha256']/role).resolve()
    require(record.parent==expected and re.fullmatch(r'a\d{4}\.json',record.name),'仅能回收当前角色和题面的调用记录')
    state=read_json(record)
    require(state['prompt_sha256']==current['prompt_sha256'] and state['provider']['model']==p['model']
            and state['provider']['effective_protocol']==p['effective_protocol'],'调用模型或题面与配置不符')
    raw_format=state.get('raw_response_format','json')
    rawpath=record.with_suffix('.raw.sse' if raw_format=='sse' else '.raw.json');require(rawpath.is_file() and not rawpath.is_symlink(),'尚无完整落盘的 API 原响应')
    raw=rawpath.read_bytes();require(p['_key'].encode() not in raw,'原响应包含凭据，禁止导入')
    if state.get('raw_response_sha256'):
        from .core import sha
        require(sha(rawpath)==state['raw_response_sha256'],'原响应已被改写')
    result=capture_raw(root,p,role,raw,state.get('request_options',{}),state.get('ended_at',state['started_at']),raw_format)
    state.update({'status':'recovered','recovered_at':now()});write_json(record,state)
    return result



@contextmanager
def request_deadline(seconds):
    """A total deadline, independent of gateway SSE heartbeats (Linux sidebar CLI)."""
    require(hasattr(signal,'setitimer') and threading.current_thread() is threading.main_thread(),
            '有界 API 调用须在支持 setitimer 的主线程运行；未发送请求')
    old_handler=signal.getsignal(signal.SIGALRM)
    old_timer=signal.getitimer(signal.ITIMER_REAL)
    started=time.monotonic()
    def expired(*args): raise TimeoutError('request_total_deadline')
    signal.signal(signal.SIGALRM,expired)
    signal.setitimer(signal.ITIMER_REAL,min(seconds,old_timer[0]) if old_timer[0]>0 else seconds)
    try: yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,old_handler)
        if old_timer[0]>0:
            signal.setitimer(signal.ITIMER_REAL,max(0.000001,old_timer[0]-(time.monotonic()-started)),old_timer[1])


def read_api_body(reply,rawpath,key,raw_format,state,save_state):
    """Preserve received bytes; a Responses terminal event ends the read without EOF."""
    raw=bytearray();pending=bytearray();started=time.monotonic()
    read=getattr(reply,'read1',reply.read)
    while True:
        chunk=read(8192 if hasattr(reply,'read1') else 50*1024*1024+1)
        if not chunk: break
        raw.extend(chunk)
        require(len(raw)<=50*1024*1024,'API 正文过大，未纳入正式证据')
        if key.encode() in raw:
            rawpath.unlink(missing_ok=True)
            raise Error('API 意外返回凭据，已拒绝保存')
        with rawpath.open('ab') as output: output.write(chunk)
        state['bytes_received']=len(raw)
        state.setdefault('first_body_seconds',round(time.monotonic()-started,3))
        terminal=None
        if raw_format=='sse':
            pending.extend(chunk)
            # Normalizing the pending buffer also handles CR/LF split across chunks.
            pending=bytearray(pending.replace(b'\r\n',b'\n'))
            while b'\n\n' in pending:
                frame,remainder=pending.split(b'\n\n',1);pending=bytearray(remainder)
                lines=[line[5:].lstrip() for line in frame.splitlines() if line.startswith(b'data:')]
                if not lines or b'\n'.join(lines)==b'[DONE]':continue
                try: event=json.loads(b'\n'.join(lines))
                except (ValueError,UnicodeDecodeError):continue
                if not isinstance(event,dict):continue
                kind=event.get('type')
                state['last_event_type']=kind
                if kind in ('response.completed','response.failed','response.incomplete','error'):
                    terminal=kind;break
        save_state()
        if terminal:
            state['terminal_event_type']=terminal
            break
        if not hasattr(reply,'read1') and raw_format=='json':break
    return bytes(raw)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): raise Error('拒绝自动重定向含密钥的 API 请求；请核对端点')


def collect(root, config_path, role, *, allow_live=False, retry_reason='', max_output=None, allow_local=False):
    require(allow_live,'真实 API 调用需要 --allow-live；不会自动收费重试')
    p=load_provider(config_path,role,allow_local=allow_local);current=active_question(root)
    payload=make_payload(p,current['question']['prompt'],max_output=max_output)
    total_timeout=p.get('total_timeout_seconds',1200)
    idle_timeout=p.get('idle_timeout_seconds',180)
    require(isinstance(total_timeout,(int,float)) and not isinstance(total_timeout,bool) and 0<total_timeout<=3600,
            'total_timeout_seconds 须为 0 到 3600 秒之间的数字')
    require(isinstance(idle_timeout,(int,float)) and not isinstance(idle_timeout,bool) and 0<idle_timeout<=600,
            'idle_timeout_seconds 须为 0 到 600 秒之间的数字')
    require(not response_dir(root,role).exists(),'该题面已有回复；禁止覆盖或自动重复调用')
    attempts=Path(root)/'attempts'/current['prompt_sha256']/role;attempts.mkdir(parents=True,exist_ok=True)
    old=sorted(p for p in attempts.glob('a*.json') if re.fullmatch(r'a\d{4}\.json',p.name))
    if old:
        require(retry_reason.strip(),'存在调用记录（可能已扣费）；先核对结果，再带 --retry-reason 明确重试理由')
        require(read_json(old[-1]).get('status')!='in_flight','之前调用状态未知；先回收已落盘的原响应，不能自动重复扣费')
    index=max([int(p.stem[1:]) for p in old]+[0])+1
    raw_format='sse' if payload.get('stream') else 'json'
    record=attempts/f'a{index:04d}.json';rawpath=record.with_suffix('.raw.sse' if raw_format=='sse' else '.raw.json')
    options={k:v for k,v in payload.items() if k not in ('messages','input','instructions','system','model','stream')}
    state={'provider':public_provider(p),'prompt_sha256':current['prompt_sha256'],'started_at':now(),'status':'in_flight','retry_reason':retry_reason,'request_options':options,'raw_response_format':raw_format}
    with record.open('x',encoding='utf-8') as f: json.dump(state,f,ensure_ascii=False,indent=2)
    headers={'Content-Type':'application/json','Accept':'text/event-stream' if raw_format=='sse' else 'application/json','User-Agent':'llm-workflow/0.1'}
    if p['effective_protocol']=='anthropic_messages': headers.update({'x-api-key':p['_key'],'Authorization':'Bearer '+p['_key'],'anthropic-version':'2023-06-01'})
    else: headers['Authorization']='Bearer '+p['_key']
    req=urllib.request.Request(p['endpoint'],json.dumps(payload,ensure_ascii=False).encode(),headers,method='POST')
    started=time.monotonic()
    state.update({'total_timeout_seconds':total_timeout,'idle_timeout_seconds':idle_timeout,'transport_phase':'connect'})
    try:
        with request_deadline(total_timeout):
            with urllib.request.build_opener(NoRedirect()).open(req,timeout=min(idle_timeout,total_timeout)) as reply:
                state.update({'transport_phase':'body','first_response_seconds':round(time.monotonic()-started,3)})
                raw=read_api_body(reply,rawpath,p['_key'],raw_format,state,lambda:write_json(record,state))
        state['raw_response_sha256']=__import__('hashlib').sha256(raw).hexdigest()
        result=capture_raw(root,p,role,raw,options,raw_format=raw_format)
        state['status']='complete'
        return result
    except urllib.error.HTTPError as e:
        state.update({'status':'http_error','http_status':e.code})
        diagnostic=''
        try:
            body=json.loads(e.read(100000));error=body.get('error',{})
            if isinstance(error,dict):diagnostic=str(error.get('message',''))[:1000]
            elif isinstance(error,str):diagnostic=error[:1000]
            diagnostic=diagnostic.replace(p['_key'],'[REDACTED]')
            diagnostic=re.sub(r'(?i)(?:bearer\s+\S+|(?:sk|sess|key)-[A-Za-z0-9_-]+)','[REDACTED]',diagnostic)
        except (ValueError,AttributeError,OSError):pass
        if diagnostic:state['error_message']=diagnostic
        raise Error(f'{role} HTTP {e.code}；'+(diagnostic+'；' if diagnostic else '')+'已记录失败，不自动重试') from None
    except (urllib.error.URLError,TimeoutError,OSError) as e:
        state.update({'status':'transport_error','error_type':type(e).__name__})
        if isinstance(e,TimeoutError):state['timeout_kind']='total' if str(e)=='request_total_deadline' else 'socket'
        raise Error(f'{role} 连接失败（{type(e).__name__}），不会自动重试；请检查网络和调用记录') from None
    except (Error,ValueError,KeyError,TypeError) as e:
        state.update({'status':'invalid_response','error_type':type(e).__name__})
        if isinstance(e,Error): raise
        raise Error(f'{role} 响应结构不符；保留原响应待检查，不作为考点失败') from None
    finally:
        state['ended_at']=now();state['elapsed_seconds']=round(time.monotonic()-started,3)
        if rawpath.is_file():state['raw_response_sha256']=hashlib.sha256(rawpath.read_bytes()).hexdigest()
        write_json(record,state)
