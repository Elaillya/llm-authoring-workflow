"""Frozen input contracts for genuine official clients, separate from manual/API evidence."""
from pathlib import Path
import hashlib
import json
import shutil
import tempfile
import os
import re
from .core import ROLES, read_json, write_json, active_question, response_dir, require, hash_json, sha, validate_markdown, validate_image, read_response, now
from .platform_checks import question_gate
from .manual import seed_screen

MODELS={'seed':('doubao-seed-2.1-pro','Seed 2.1 Pro'),
        'gpt':('gpt-5.6-sol','GPT-5.6 sol'),
        'claude':('claude-opus-4-6','Claude Opus 4.6')}


def request(root,role,evaluation=None):
    root=Path(root).resolve()
    task=read_json(root/'TASK.json')
    require(task.get('response_mode')=='official_clients' and role in ROLES,'此入口仅供官方客户端试验题使用')
    current=active_question(root)
    question_gate(root,current['question'])
    screen=seed_screen(root,evaluation) if role!='seed' else None
    if screen is not None:
        from .check_policy import require_choice
        require_choice(root)
    model,name=MODELS[role]
    contract=task.get('model_contract',{}).get(role,{})
    require(contract.get('model')==model and contract.get('display_name')==name and contract.get('effort')=='high',
            '核对本题规定型号和High配置，不能自动替代型号')
    prompt=current['question']['prompt']
    value={'schema_version':1,'source_kind':'official_client_automation','role':role,
           'task_id':task['task_id'],'revision':current['revision'],
           'question_sha256':current['question_sha256'],'prompt_sha256':current['prompt_sha256'],
           'rubric_sha256':current['rubric_sha256'],'prompt':prompt,'prompt_policy':'prompt_only',
           'prompt_bytes_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
           'model':model,'display_name':name,'effort':'high'}
    if screen is not None:
        value.update(seed_evaluation_sha256=hash_json(screen),seed_response_sha256=screen['models']['seed']['response_sha256'])
    return value


def prepare(root,role,evaluation=None):
    root=Path(root).resolve()
    value=request(root,role,evaluation)
    require(not response_dir(root,role).exists(),'已有本题原回复，先沿用证据，不能自动重新采集')
    directory=root/'client-input'/value['prompt_sha256']/role
    require(not directory.is_symlink(),'官方客户端输入目录不能为符号链接')
    manifest=directory/'request.json'
    if manifest.exists():require(read_json(manifest)==value,'客户端输入合同已变化，保留旧记录再核对')
    else:write_json(manifest,value)
    prompt=directory/'prompt.md'
    if prompt.exists():
        require(prompt.is_file() and not prompt.is_symlink() and prompt.read_bytes()==value['prompt'].encode(),
                '客户端发送题面已改变')
    else:prompt.write_bytes(value['prompt'].encode())
    if role!='seed':
        screen=seed_screen(root,evaluation)
        require(hash_json(screen)==value['seed_evaluation_sha256'],'准备期间Seed判断已变化')
        saved=directory/'seed-screen.json'
        if saved.exists():require(read_json(saved)==screen,'先行Seed判断已变化，保留原件核对')
        else:write_json(saved,screen)
    return {'request':str(manifest),'prompt_file':str(prompt),'role':role,'display_name':value['display_name']}


def ordinary(directory,name):
    require(isinstance(name,str) and Path(name).name==name and name not in ('.','..'),'客户端证据文件名不合法')
    file=Path(directory)/name
    require(file.is_file() and not file.is_symlink(),'客户端原始证据缺失或不是普通文件：'+name)
    return file


def captured_question(contract,wrapper):
    q=wrapper.get('question',{})
    require(wrapper.get('question_sha256')==contract.get('question_sha256')==hash_json(q)
            and wrapper.get('rubric_sha256')==contract.get('rubric_sha256')==hash_json(q.get('points'))
            and wrapper.get('prompt_sha256')==contract.get('prompt_sha256')==hash_json(q.get('prompt'))
            and q.get('prompt')==contract.get('prompt') and q.get('task_id')==contract.get('task_id'),
            '采集时的完整冻结标准不匹配，保留原件核对')
    return q


def seed_dispatch_proof(contract,wrapper,screen,seed_text,seed_sha):
    q=captured_question(contract,wrapper)
    require(hash_json(screen)==contract.get('seed_evaluation_sha256')
            and screen.get('schema_version')==1 and screen.get('phase')=='authoring'
            and screen.get('task_id')==contract.get('task_id')
            and all(screen.get(k)==contract.get(k) for k in ('question_sha256','prompt_sha256','rubric_sha256'))
            and isinstance(screen.get('reviewer'),str) and screen['reviewer'].strip()
            and set(screen.get('models',{}))=={'seed'},'先行Seed判断原件绑定不一致')
    record=screen['models']['seed']
    require(record.get('response_sha256')==contract.get('seed_response_sha256')==seed_sha,'先行Seed回复已变化')
    points={p['id'] for p in q['points'] if p['kind']=='decisive'}
    require(points and set(record.get('points',{}))==points,'先行Seed判断没有覆盖采集时的全部决定性考点')
    for item in record['points'].values():
        require(type(item.get('met')) is bool and isinstance(item.get('reason'),str) and item['reason'].strip()
                and isinstance(item.get('quotes'),list) and all(isinstance(v,str) and v.strip() and v in seed_text for v in item['quotes'])
                and (not item['met'] or item['quotes']),'先行Seed判断缺少原文证据')
    require(not all(item['met'] for item in record['points'].values()),'采集时Seed已经全部达成，不能启动GPT/Claude')


def verified_bundle(directory,contract,role,reply_path=None):
    directory=Path(directory)
    generation=read_json(ordinary(directory,'generation.json'))
    capture=read_json(ordinary(directory,'capture.json'))
    review=read_json(ordinary(directory,'verification.json'))
    original=Path(reply_path) if reply_path is not None else ordinary(directory,'reply.md')
    require(original.is_file() and not original.is_symlink(),'客户端回复原件缺失或不是普通文件')
    raw=original.read_bytes();text=raw.decode('utf-8');validate_markdown(text)
    from markdown_it import MarkdownIt
    def text_tokens(tokens):
        for token in tokens:
            require(token.type not in ('image','html_inline','html_block'),'原回复包含富媒体或HTML，保留原文但不能作为可复制的纯Markdown交付')
            if token.type=='link_open':
                href=token.attrGet('href') or ''
                require(not href.startswith(('sandbox:','file:')),'原回复含附件，保留原件后核对格式限制')
            if token.children:text_tokens(token.children)
    text_tokens(MarkdownIt('commonmark',{'html':True}).enable('table').parse(text))
    model,name=MODELS[role]
    require(generation.get('request_sha256')==hash_json(contract)
            and generation.get('prompt_bytes_sha256')==contract['prompt_bytes_sha256']
            and generation.get('actual_model')==model and generation.get('reply_sha256')==hashlib.sha256(raw).hexdigest(),
            '客户端生成原件与题面、型号或正文不一致')
    require(generation.get('rich_media_detected') is not True,'官方页面回复含富媒体，原文保留，不能把缺失媒体的复制文本当完整交付')
    session=generation.get('session_id')
    require(isinstance(session,str) and session,'缺少实际生成会话ID')
    files={'generation.json','capture.json','verification.json'}
    if role=='gpt':
        import importlib.util
        file=Path(__file__).resolve().parents[1]/'browser_automation/gpt-client.py'
        spec=importlib.util.spec_from_file_location('bound_official_gpt',file)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        events=[json.loads(line) for line in ordinary(directory,'events.jsonl').read_text().splitlines() if line.strip()]
        rollout_file=ordinary(directory,'generation-rollout.jsonl')
        require(sha(rollout_file)==generation.get('rollout_sha256'),'GPT实际日志已改变')
        rollout=[json.loads(line) for line in rollout_file.read_text().splitlines() if line.strip()]
        proof=module.verify_generation(events,rollout,contract['prompt'],text)
        require(proof['session_id']==session and generation.get('exit_code')==0,'GPT生成会话或退出状态不匹配')
        files.update(('events.jsonl','generation-rollout.jsonl'))
    elif role=='claude':
        native_file=ordinary(directory,'native-stdout.json')
        native=json.loads(native_file.read_text(encoding='utf-8-sig'))
        usage=native.get('modelUsage',{}).get(model,{})
        require(sha(native_file)==generation.get('native_stdout_sha256') and generation.get('exit_code')==0
                and native.get('is_error') is False and native.get('session_id')==session
                and native.get('result')==text and usage.get('canonicalModel')==model
                and generation.get('tools_disabled') is True and usage.get('webSearchRequests',0)==0,
                'Claude实际结果、会话或禁用工具证据不完整')
        files.add('native-stdout.json')
    else:
        original_file=ordinary(directory,'official-copy.json')
        original=read_json(original_file)
        verified_input=read_json(ordinary(directory,'input-verified.json'))
        send_intent=read_json(ordinary(directory,'send-intent.json'))
        clicked=read_json(ordinary(directory,'send-click.json'))
        conversation=read_json(ordinary(directory,'conversation.json'))
        selected=verified_input.get('model','')
        require(sha(original_file)==generation.get('official_copy_sha256')
                and original.get('source')=='official_reply_copy_action' and original.get('captured')==text
                and original.get('session_id')==session
                and original.get('previous_clipboard_read') is False
                and generation.get('input_verified_before_send') is True
                and generation.get('actual_effort')=='high'
                and verified_input.get('input_verified') is True
                and verified_input.get('prompt_readback')==contract['prompt']
                and verified_input.get('prompt_bytes_sha256')==contract['prompt_bytes_sha256']
                and verified_input.get('request_sha256')==send_intent.get('request_sha256')==conversation.get('request_sha256')==hash_json(contract)
                and clicked.get('clicked') is True and clicked.get('prompt_readback')==contract['prompt']
                and clicked.get('request_sha256')==hash_json(contract) and clicked.get('model')==selected
                and conversation.get('session_id')==session and '2.1 Pro' in selected
                and '高' in (line.strip() for line in selected.splitlines()), '豆包官方复制原文或实际输入证据缺失')
        files.update(('official-copy.json','input-verified.json','send-intent.json','send-click.json','conversation.json'))
    expected_source='real_official_webpage' if role=='seed' else 'real_official_client_console_window'
    require(capture.get('request_sha256')==hash_json(contract) and capture.get('generation_sha256')==hash_json(generation)
            and capture.get('session_id')==session and capture.get('source')==expected_source,
            '真实截图未绑定同一次模型回答')
    frames=capture.get('frames',[])
    require(isinstance(frames,list) and frames,'尚未取得真实界面截图')
    for frame in frames:
        image=ordinary(directory,frame.get('filename'))
        require(image.suffix.lower() in ('.png','.jpg','.jpeg') and sha(image)==frame.get('sha256')
                and frame.get('source')==expected_source and frame.get('session_id')==session,'真实截图原件已改变或会话不一致')
        validate_image(image);files.add(frame['filename'])
    require(review.get('capture_sha256')==hash_json(capture)
            and isinstance(review.get('reviewer'),str) and review['reviewer'].strip()
            and all(review.get(k) is True for k in ('model_and_effort_visible','prompt_matches','complete_reply_covered'))
            and review.get('actual_model')==model and review.get('actual_effort')=='high'
            and isinstance(review.get('ending_quote'),str) and review['ending_quote'].strip()
            and review['ending_quote'] in text,
            '先查看全部真实截图，核对实际型号、High、同一题面和完整原回复，再记录验证')
    return {'files':files,'raw':raw,'text':text,'generation':generation,'capture':capture,'review':review}


def import_result(root,role):
    root=Path(root).resolve();current=active_question(root)
    require(read_json(root/'TASK.json').get('response_mode')=='official_clients' and role in ROLES,'仅用于官方客户端题目')
    inputs=root/'client-input'/current['prompt_sha256']/role
    contract=read_json(inputs/'request.json')
    expected=request(root,role)
    # Scoring standards can be revised after capture; the original user input cannot.
    stable=set(expected)-{'question_sha256','rubric_sha256','revision','seed_evaluation_sha256'}
    require({k:contract.get(k) for k in stable}=={k:expected.get(k) for k in stable},'原客户端输入不属于当前题面或Seed原件')
    require((inputs/'prompt.md').read_bytes()==contract['prompt'].encode(),'客户端题面原件已改变')
    bundle=verified_bundle(inputs/'run',contract,role)
    target=response_dir(root,role)
    require(not (root/'responses').is_symlink() and not target.parent.is_symlink(),'官方原回复目录不能为符号链接')
    if target.exists():
        item=validate_evidence(root,role)
        require(item['text']==bundle['text'],'已有不同原回复，保留原件，不自动替换')
        return {'role':role,'complete':True,'already_imported':True}
    target.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.'+role+'-official-',dir=target.parent))
    try:
        (stage/'reply.md').write_bytes(bundle['raw'])
        (stage/'client-original.md').write_bytes(bundle['raw'])
        evidence=stage/'client-evidence';evidence.mkdir(mode=0o700)
        for name in bundle['files']:shutil.copyfile(inputs/'run'/name,evidence/name)
        write_json(evidence/'request.json',contract)
        require(re.fullmatch(r'r\d{4}',contract.get('revision','')),'采集版本不合法')
        capture_question=read_json(root/'revisions'/contract['revision']/'question.json')
        captured_question(contract,capture_question)
        write_json(evidence/'question-at-capture.json',capture_question)
        if role!='seed':
            screen=read_json(inputs/'seed-screen.json')
            seed=read_response(root,'seed')
            seed_dispatch_proof(contract,capture_question,screen,seed['text'],seed['meta']['reply_sha256'])
            write_json(evidence/'seed-screen.json',screen)
        manifest={file.name:sha(file) for file in evidence.iterdir()}
        metadata={'schema_version':1,'source_kind':'official_client_automation','evidence_status':'verified_official_client',
                  'role':role,'display_name':MODELS[role][1],'model':MODELS[role][0],'returned_model':MODELS[role][0],
                  'actual_effort':'high','completion_status':'complete','screenshot_kind':'official_client_capture',
                  'task_id':current['question']['task_id'],'prompt_sha256':current['prompt_sha256'],
                  'rubric_at_capture':contract['rubric_sha256'],'reply_sha256':sha(stage/'reply.md'),
                  'raw_response_file':'client-original.md','raw_response_sha256':sha(stage/'client-original.md'),
                  'client_request':contract,'client_request_sha256':hash_json(contract),
                  'client_evidence_files':manifest,'client_evidence_sha256':hash_json(manifest),'captured_at':now()}
        write_json(stage/'metadata.json',metadata)
        validate_evidence(root,role,{'directory':stage,'meta':metadata,'text':bundle['text']})
        require(not target.exists(),'原回复已由另一操作导入，保留两个原件再核对')
        os.rename(stage,target)
    except BaseException:
        # Retain a complete staged bundle for reconciliation instead of overwriting evidence.
        raise
    return {'role':role,'complete':True,'reply_file':str(target/'reply.md'),'actual_model':MODELS[role][0],
            'actual_effort':'high','real_screenshots':len(bundle['capture']['frames'])}


def validate_evidence(root,role,item=None):
    item=item or read_response(root,role)
    meta=item['meta'];directory=item['directory'];current=active_question(root)
    require(meta.get('source_kind')=='official_client_automation' and meta.get('evidence_status')=='verified_official_client'
            and meta.get('display_name')==MODELS[role][1] and meta.get('returned_model')==MODELS[role][0],
            '本题需要官方客户端原文及真实截图，不能使用手工声明或API渲染证据')
    contract=meta.get('client_request',{})
    require(hash_json(contract)==meta.get('client_request_sha256')
            and contract.get('prompt_sha256')==current['prompt_sha256']
            and contract.get('prompt')==current['question']['prompt']
            and contract.get('task_id')==current['question']['task_id'] and contract.get('role')==role
            and contract.get('model')==MODELS[role][0] and contract.get('effort')=='high'
            and contract.get('prompt_policy')=='prompt_only' and 'format_instruction' not in contract,
            '官方客户端证据的题面绑定已变化')
    manifest=meta.get('client_evidence_files',{})
    require(manifest and hash_json(manifest)==meta.get('client_evidence_sha256'),'客户端证据索引已改变')
    evidence=directory/'client-evidence'
    require(evidence.is_dir() and not evidence.is_symlink(),'客户端原证据目录缺失')
    for name,checksum in manifest.items():require(sha(ordinary(evidence,name))==checksum,'客户端原证据已改变')
    require(read_json(evidence/'request.json')==contract,'客户端输入合同副本不一致')
    capture_question=read_json(evidence/'question-at-capture.json')
    captured_question(contract,capture_question)
    verified_bundle(evidence,contract,role,reply_path=ordinary(directory,'reply.md'))
    generation=read_json(evidence/'generation.json')
    require(generation.get('reply_sha256')==meta.get('reply_sha256')
            and ordinary(directory,'client-original.md').read_bytes()==item['text'].encode(), '官方原文与评分正文不一致')
    if role!='seed':
        seed=read_response(root,'seed')
        seed_dispatch_proof(contract,capture_question,read_json(evidence/'seed-screen.json'),seed['text'],seed['meta']['reply_sha256'])
    return item


def status(root):
    complete={}
    for role in ROLES:
        try:validate_evidence(root,role);complete[role]=True
        except (OSError,ValueError,KeyError,TypeError):complete[role]=False
    if not complete['seed']:
        stage='seed_official_client_collection';next_step='准备并运行Seed官方页面采集，核验完整原文及真实截图后导入'
    elif not all(complete.values()):
        try:
            seed_screen(root)
            stage='gpt_claude_official_client_collection';next_step='按已验证客户端采集GPT/Claude，保存完整原文和High真实截图'
        except ValueError as error:stage='seed_evaluation';next_step=str(error)
    else:stage='three_model_evaluation';next_step='同版统一判断三模型，门槛通过后并行网页质检'
    return {'stage':stage,'model_input_files':{},'official_client_complete':complete,'next':next_step}


def review_template(root,role):
    root=Path(root).resolve();current=active_question(root)
    require(role in ROLES and read_json(root/'TASK.json').get('response_mode')=='official_clients','仅审核本题规定的官方客户端截图')
    directory=root/'client-input'/current['prompt_sha256']/role/'run'
    capture=read_json(directory/'capture.json')
    contract=read_json(directory.parent/'request.json')
    require(capture.get('request_sha256')==hash_json(contract) and contract.get('prompt_sha256')==current['prompt_sha256'],
            '待审核截图不属于当前题面')
    file=directory/'verification.json'
    if not file.exists():
        write_json(file,{'capture_sha256':hash_json(capture),'reviewer':'',
                         'model_and_effort_visible':None,'prompt_matches':None,'complete_reply_covered':None,
                         'actual_model':None,'actual_effort':None,'ending_quote':''})
    return {'verification_file':str(file),'screenshots':[str(ordinary(directory,item['filename'])) for item in capture['frames']],
            'required_model':MODELS[role][0],'required_effort':'high',
            'next':'助手逐张查看真实截图，对照原回复末尾及跨页覆盖后填写；未核验不能置true。'}
