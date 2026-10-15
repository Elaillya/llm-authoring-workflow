"""Private configuration and one-shot calls to the observed AIDP check service."""
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
import json
import os
import tempfile
from .core import read_json, require

ENDPOINT='https://aidp.bytedance.com/llm/union/app/invoke'
KEYS={'question':('题目AI质检结论','题目AI质检详情'),
      'criteria':('AI考点质检结论','AI考点质检详情'),
      'attainment':('AI达成性判断结论','AI达成性质检详情')}
COOKIE_PLACEHOLDER='请用已登录AIDP的Cookie完整值替换本行，保存后告诉助手。\n'
DEFAULT_CONFIG=Path(__file__).resolve().parents[1]/'config/aidp-service.json'


def private_directory(workspace):
    base=Path(workspace).resolve()/'local'
    require(base.is_dir() and not base.is_symlink(),'父工作区local须为普通目录')
    directory=base/'aidp'
    require(not directory.is_symlink(),'平台私有目录不能为符号链接')
    directory.mkdir(mode=0o700,exist_ok=True);directory.chmod(0o700)
    for name in ('service.json','cookie.txt'):
        require(not (directory/name).is_symlink(),'平台配置和Cookie不能为符号链接')
    cookie=directory/'cookie.txt'
    if not cookie.exists():
        try:fd=os.open(cookie,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        except FileExistsError:pass
        else:
            with os.fdopen(fd,'w') as stream:stream.write(COOKIE_PLACEHOLDER)
    require(cookie.is_file(),'Cookie须为普通文件');cookie.chmod(0o600)
    return directory


def validated_config(value):
    require(value.get('endpoint')==ENDPOINT,'平台检查只允许固定AIDP HTTPS接口')
    task=value.get('task_id','')
    require(isinstance(task,str) and task.isdigit(),'平台任务ID须为数字字符串')
    plans=value.get('checks',{});require(set(plans)==set(KEYS),'配置须包含三个检查计划')
    checked={}
    for stage,item in plans.items():
        require(isinstance(item.get('plan_id'),str) and item['plan_id'].isdigit()
                and type(item.get('provider')) is int and item['provider']==2,'计划ID或provider不符合已观察的协议')
        checked[stage]={'plan_id':item['plan_id'],'provider':2}
    referer=value.get('referer','https://aidp.bytedance.com/')
    parsed=urlsplit(referer)
    require(parsed.scheme=='https' and parsed.netloc=='aidp.bytedance.com' and not parsed.fragment,'Referer须为同站HTTPS地址')
    # Existing private configs may contain the old numeric limit. Normalize it
    # without changing those files; a healthy check must be allowed to finish.
    agent=value.get('user_agent','Mozilla/5.0')
    require(isinstance(agent,str) and agent and not any(c in agent+referer for c in '\r\n'),'请求头格式不合法')
    domains=value.get('domain_labels',{'计算机科学':'计算机与数理科学','商科':'商科'})
    types=value.get('type_labels',{'分析决策类':'分析决策','开放推荐类':'开放推荐','How-to类':'How-to'})
    require(isinstance(domains,dict) and isinstance(types,dict)
            and all(isinstance(k,str) and isinstance(v,str) and v.strip() for mapping in (domains,types) for k,v in mapping.items()),'平台标签映射须为非空文本')
    return {'schema_version':1,'endpoint':ENDPOINT,'task_id':task,'checks':checked,'referer':referer,
            'timeout_seconds':None,'user_agent':agent,'domain_labels':domains,'type_labels':types}


def config_from_har(path):
    capture=read_json(path);found={};tasks=set();meta={}
    for entry in capture.get('log',{}).get('entries',[]):
        request=entry.get('request',{})
        if request.get('url')!=ENDPOINT or request.get('method')!='POST':continue
        try:
            payload=json.loads(request['postData']['text'])
            result=json.loads(entry['response']['content']['text'])['response']
            if isinstance(result,str):result=json.loads(result)
        except (KeyError,ValueError,TypeError):continue
        headers={h['name'].lower():h['value'] for h in request.get('headers',[])}
        if headers.get('x-aidp-task-id'):tasks.add(headers['x-aidp-task-id'])
        for stage,(key,_) in KEYS.items():
            if not isinstance(result,dict) or key not in result:continue
            plan={'plan_id':payload['plan_id'],'provider':payload['provider']}
            require(stage not in found or found[stage]==plan,'HAR混合不同检查配置，请仅导出当前平台任务')
            found[stage]=plan
            meta={'referer':headers.get('referer','https://aidp.bytedance.com/'),'user_agent':headers.get('user-agent','Mozilla/5.0')}
    require(len(tasks)==1,'HAR须有唯一的平台任务ID请求头')
    return validated_config({'endpoint':ENDPOINT,'task_id':next(iter(tasks)),'checks':found,**meta})


def default_config():
    return validated_config(read_json(DEFAULT_CONFIG))


def setup(workspace,config):
    directory=private_directory(workspace);config=validated_config(config);target=directory/'service.json'
    if not target.exists():
        # Publish a complete file exclusively: concurrent setup must never
        # overwrite a custom configuration or expose partially written JSON.
        fd,name=tempfile.mkstemp(prefix='.service-',dir=directory)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as stream:
                json.dump(config,stream,ensure_ascii=False,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
            try:os.link(name,target)
            except FileExistsError:pass
        finally:Path(name).unlink(missing_ok=True)
    require(validated_config(read_json(target))==config,'已有平台配置，保留原件；确认新任务配置后由助手显式编辑')
    target.chmod(0o600)
    return {'service_file':str(target),'cookie_file':str(directory/'cookie.txt'),
            'next':'需要检查时填写Cookie；账号密码不进入聊天、源码或日志'}


def configuration(root):
    from .workspace import locate_workspace
    workspace=locate_workspace(root);directory=private_directory(workspace);target=directory/'service.json'
    if not target.exists():setup(workspace,default_config())
    return validated_config(read_json(target)),directory/'cookie.txt'


def load_cookie(path):
    path=Path(path);require(path.is_file() and not path.is_symlink(),'Cookie须为普通私有文件')
    require(path.stat().st_mode&0o077==0,'Cookie文件权限须为600')
    cookie=path.read_text(encoding='utf-8-sig').strip()
    require(cookie and cookie!=COOKIE_PLACEHOLDER.strip() and '=' in cookie
            and not any(c in cookie for c in '\r\n'),'请填写或更新Cookie文件：'+str(path))
    if cookie.lower().startswith('cookie:'):cookie=cookie.split(':',1)[1].strip()
    return cookie


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def call(config,payload,cookie):
    """No retries, redirects, save endpoints, or exception strings with secrets."""
    config=validated_config(config)
    headers={'Content-Type':'application/json','Accept':'application/json','agw-js-conv':'str',
             'Origin':'https://aidp.bytedance.com','Referer':config['referer'],'User-Agent':config['user_agent'],
             'x-aidp-task-id':config['task_id'],'Cookie':cookie}
    request=Request(ENDPOINT,data=json.dumps(payload,ensure_ascii=False).encode(),method='POST',headers=headers)
    try:
        try:response=build_opener(NoRedirect()).open(request,timeout=config['timeout_seconds'])
        except HTTPError as error:response=error
        with response:
            raw=response.read(1000001);text=raw[:1000000].decode('utf-8','replace')
            for secret in [cookie]+[p.split('=',1)[1].strip() for p in cookie.split(';') if '=' in p and len(p.split('=',1)[1].strip())>=8]:
                if secret:text=text.replace(secret,'[redacted credential]')
            return {'http_status':response.code,'response_text':text,'truncated':len(raw)>1000000}
    except Exception as error:
        return {'http_status':None,'response_text':'','transport_error':type(error).__name__}
