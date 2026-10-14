"""Version-bound platform checks, evidence-based disagreement, and Arena gates."""
from pathlib import Path
from contextlib import contextmanager
import copy,json,re,shutil,time,uuid
from .core import Error,ROLES,active_question,hash_json,now,read_json,read_response,require,sha,write_json
from . import platform_client as client


def required(root):
    task=Path(root)/'TASK.json'
    return task.is_file() and read_json(task).get('platform_checks_required') is True


def initial_question(root,q):
    from .selection import validate_selection
    from .core import question_domain,TYPES
    request=read_json(Path(root)/'REQUEST.json');validate_selection(root,q)
    require(q.get('task_id')==read_json(Path(root)/'TASK.json')['task_id'],'平台检查候选不属于当前任务')
    require(q.get('domain')==question_domain(root,request) and q.get('question_type')==request.get('question_type')
            and q.get('question_type') in TYPES,'先选择并记录匹配的领域、子方向及题型')
    require(isinstance(q.get('prompt'),str) and 0<len(q['prompt'].strip()) and len(q['prompt'])<=100,'先形成不超过100字符的题面')
    require(all(isinstance(q.get('insight',{}).get(key),str) and q['insight'][key].strip()
                for key in ('mechanism','priority','conclusion')),'先完成Insight三个字段')


def authoring_evaluation(root,ev):
    from .authoring import check_three
    require(isinstance(ev,dict),'三个模型原文和完整判断齐备后，提供当前evaluation文件')
    value=copy.deepcopy(ev)
    if value.get('phase')=='five_model_evaluation':
        decisive={p['id'] for p in active_question(root)['question']['points'] if p['kind']=='decisive'}
        value['phase']='authoring'
        value['models']={role:{'response_sha256':value['models'][role]['response_sha256'],
            'points':{key:judgment for key,judgment in value['models'][role]['points'].items() if key in decisive}} for role in ROLES}
    return value,check_three(root,value)


def descriptor(root,stage,q=None,evaluation=None):
    require(stage in client.KEYS,'未知平台检查类型')
    config,cookie=client.configuration(root)
    if stage=='question':
        require(q is not None,'题目检查需要候选JSON');initial_question(root,q)
        binding={'task_identity':read_json(Path(root)/'TASK.json').get('memory_id',str(Path(root).resolve()))}
    else:
        current=active_question(root);q=current['question'];evaluation,stats=authoring_evaluation(root,evaluation)
        binding={'task_identity':read_json(Path(root)/'TASK.json').get('memory_id',str(Path(root).resolve())),
                 'question_sha256':current['question_sha256']}
    insight=q['insight'];params={'题目':q['prompt'],'出题说明':f'机制：{insight["mechanism"]}\n\n优先级：{insight["priority"]}\n\n核心结论：{insight["conclusion"]}'}
    if stage=='question':
        require(q['domain'] in config['domain_labels'] and q['question_type'] in config['type_labels'],'核实并配置平台领域/题型标签')
        params.update({'领域':config['domain_labels'][q['domain']],'题目类型':config['type_labels'][q['question_type']]})
    else:
        points=lambda kind:'\n'.join(f'- {p["id"]}：{p["criterion"]}' for p in q['points'] if p['kind']==kind) or '无'
        params['决定性核心考点']=points('decisive')
        if stage=='criteria':params['非决定性核心考点']=points('supporting')
        for role,key in zip(ROLES,('豆包专家回复','GPT回复','Claude回复')):params[key]=read_response(root,role)['text']
        if stage=='attainment':
            from .ranking import attainment_notes
            for role,prefix in zip(ROLES,('豆包专家','GPT','Claude')):
                params[prefix+'是否达成']='已达成' if stats['models'][role]['attained'] else '未达成'
                params[prefix+'达成性备注']=attainment_notes(stats['models'][role])
    params['from_agentic']='true'
    payload={**config['checks'][stage],'params':params}
    binding.update(stage=stage,platform_task_id=config['task_id'],payload_sha256=hash_json(payload))
    return {'stage':stage,'payload':payload,'binding':binding},config,cookie


def records_directory(root):
    base=Path(root).resolve();directory=base/'platform-checks'
    require(not directory.is_symlink(),'平台检查目录不能为符号链接')
    directory.mkdir(mode=0o700,exist_ok=True);directory.chmod(0o700)
    return directory


@contextmanager
def check_lock(root):
    lock=records_directory(root)/'.running'
    try:lock.mkdir()
    except FileExistsError:raise Error('当前题目已有平台检查或异议登记运行；先查看原尝试，不能重复发送')
    try:yield
    finally:lock.rmdir()


def parse_response(stage,transport):
    result={'state':'service_error','server_conclusion':None,'feedback':''}
    if transport.get('http_status') in (401,403):return {**result,'state':'needs_cookie'}
    if transport.get('http_status')!=200 or transport.get('truncated') or transport.get('transport_error'):return result
    try:
        outer=json.loads(transport['response_text']);base=outer['BaseResp']['StatusCode']
        if type(base) is not int or base!=0:return result
        inner=outer['response'];inner=json.loads(inner) if isinstance(inner,str) else inner
        conclusion,details=client.KEYS[stage];decision=inner[conclusion];feedback=inner[details]
        if decision not in ('通过','不通过') or not isinstance(feedback,str) or not feedback.strip():return {**result,'state':'needs_review'}
        return {'state':'passed' if decision=='通过' else 'failed','server_conclusion':decision,'feedback':feedback}
    except (KeyError,ValueError,TypeError):return {**result,'state':'needs_review'}


def verified_record(directory,stage):
    request=read_json(directory/'request.json');record=read_json(directory/'result.json')
    require(record['request_sha256']==hash_json(request) and record['binding']==request['binding']
            and record['response_sha256']==hash_json(record['transport'])
            and record['parsed']==parse_response(stage,record['transport']),'平台检查记录绑定被改写，请核对原件')
    return request,record


def latest(root,request):
    base=records_directory(root);stage=request['stage'];matches=[]
    for path in sorted(base.glob(stage+'-*')):
        require(path.is_dir() and not path.is_symlink(),'检查记录须为普通目录')
        if not (path/'result.json').is_file():
            if (path/'intent.json').is_file() and read_json(path/'request.json')==request:
                raise Error('存在同输入的未完成平台调用，结果未知；先核对该尝试与平台状态，保留原件，不得自动重发：'+str(path))
            continue
        saved,record=verified_record(path,stage)
        if saved==request:matches.append((path,record))
    if not matches:return None
    path,record=matches[-1];result={**record['parsed'],'attempt':str(path),'accepted':record['parsed']['state']=='passed'}
    disagreements=sorted(path.glob('disagreement-*.json'))
    if disagreements:
        decision=read_json(disagreements[-1]);validate_disagreement(request,record,decision)
        notes=path/'表单备注.md'
        require(notes.is_file() and not notes.is_symlink() and notes.read_text()==disagreement_notes(decision),'异议表单备注缺失或被改写')
        result.update(state='disputed',accepted=True,disagreement=decision,notes_file=str(path/'表单备注.md'))
    return result


def question_gate(root,q):
    if not required(root):return None
    request,_,_=descriptor(root,'question',q=q);result=latest(root,request)
    require(result and result['state']=='passed','先执行qa-run question，按反馈修订题面/Insight后检查通过，再冻结与收Seed')
    return result


def stage_gate(root,stage,evaluation):
    q=active_question(root)['question'];question_gate(root,q)
    request,_,_=descriptor(root,stage,evaluation=evaluation);result=latest(root,request)
    require(result and result['accepted'],'平台'+stage+'检查未完成、未通过或已过期；修订复检，或为有证据的错误结论登记异议')
    return result


def final_gate(root,evaluation):
    if not required(root):return {}
    return {stage:stage_gate(root,stage,evaluation) for stage in ('criteria','attainment')}


def run(root,stage,q=None,evaluation=None,refresh=False):
    root=Path(root).resolve()
    if stage!='question':
        question_gate(root,active_question(root)['question'])
        if stage=='attainment':stage_gate(root,'criteria',evaluation)
    request,config,cookie_path=descriptor(root,stage,q=q,evaluation=evaluation)
    previous=latest(root,request)
    if previous and not refresh and previous['state'] in ('passed','failed','disputed'):
        return {**previous,'cached':True,'next':'复用同版结果；不通过时先据专业依据修改，不对相同内容盲目重发'}
    cookie=client.load_cookie(cookie_path)
    base=records_directory(root)
    with check_lock(root):
        # A second writer may have finished after the first cache lookup.
        previous=latest(root,request)
        if previous and not refresh and previous['state'] in ('passed','failed','disputed'):
            return {**previous,'cached':True,'next':'复用同版结果，不重复发送'}
        directory=base/f'{stage}-{time.time_ns()}-{uuid.uuid4().hex[:8]}';directory.mkdir(mode=0o700)
        write_json(directory/'request.json',request)
        write_json(directory/'intent.json',{'started_at':now(),'state':'one_attempt_no_retry','request_sha256':hash_json(request),'timeout_seconds':config['timeout_seconds']})
        transport=client.call(config,request['payload'],cookie)
        record={'schema_version':1,'binding':request['binding'],'request_sha256':hash_json(request),
                'response_sha256':hash_json(transport),'transport':transport,'parsed':parse_response(stage,transport),'completed_at':now()}
        write_json(directory/'result.json',record)
    result=latest(root,request)
    result.update(cached=False,cookie_file=str(cookie_path),next=('请填写/更新Cookie后继续，不把登录问题记为题目不合格' if result['state']=='needs_cookie'
                  else '按原始反馈修订后复检；疑似错误意见先核对证据并登记异议' if not result['accepted'] else '继续下一阶段'))
    return result


def disagreement_template(root,stage,evaluation):
    require(stage in ('criteria','attainment'),'异议仅用于收齐三模型后的两项内容质检')
    request,_,_=descriptor(root,stage,evaluation=evaluation);result=latest(root,request)
    require(result and result['state']=='failed','只对当前实际不通过的内容检查登记异议，服务错误或旧结果不能绕过')
    _,record=verified_record(Path(result['attempt']),stage)
    return {'schema_version':1,'phase':'platform_disagreement','stage':stage,'binding':request['binding'],
            'response_sha256':record['response_sha256'],'reviewer':'','reason':'',
            'evidence':[{'source':'feedback','quote':''},{'source':'input','field':'','quote':''}],
            'form_notes':'','notification':'向用户明确说明不认同该不通过结论，并给出表单备注；不新增用户审批'}


def validate_disagreement(request,record,decision):
    require(request['stage'] in ('criteria','attainment') and record['parsed']['state']=='failed'
            and decision.get('schema_version')==1 and decision.get('phase')=='platform_disagreement'
            and decision.get('stage')==request['stage'] and decision.get('binding')==request['binding']
            and decision.get('response_sha256')==record['response_sha256'],'异议不属于当前失败返回或输入已变化')
    for key in ('reviewer','reason','form_notes'):
        require(isinstance(decision.get(key),str) and decision[key].strip(),'异议需要实际执行者、证据理由及可复制表单备注')
    evidence=decision.get('evidence',[]);sources=set()
    require(isinstance(evidence,list) and len(evidence)>=2,'异议须同时引用质检反馈及实际输入/模型原文')
    for item in evidence:
        quote=item.get('quote');source=item.get('source');sources.add(source)
        target=record['parsed']['feedback'] if source=='feedback' else request['payload']['params'].get(item.get('field','')) if source=='input' else None
        require(isinstance(quote,str) and quote.strip() and isinstance(target,str) and quote in target,'异议引用须是本次反馈或输入的准确原文')
    require({'feedback','input'}<=sources,'异议须比较本次反馈与输入，不能只写不同意')


def disagree(root,decision,evaluation):
    with check_lock(root):return record_disagreement(root,decision,evaluation)


def record_disagreement(root,decision,evaluation):
    stage=decision.get('stage');request,_,_=descriptor(root,stage,evaluation=evaluation);result=latest(root,request)
    require(result and result['state']=='failed','先核实当前失败的质检记录')
    path=Path(result['attempt']);_,record=verified_record(path,stage);validate_disagreement(request,record,decision)
    target=path/('disagreement-'+uuid.uuid4().hex+'.json')
    notes=path/'表单备注.md'
    require(not notes.exists() and not notes.is_symlink(),'保留已有异议备注，不能覆盖')
    try:
        with notes.open('x',encoding='utf-8') as output:output.write(disagreement_notes(decision))
        write_json(target,decision)
    except BaseException:
        notes.unlink(missing_ok=True);raise
    return {'state':'disputed','server_conclusion':'不通过','accepted_with_evidence':True,'notes_file':str(notes),
            'message':'不认同该不通过结论：'+decision['reason'],'form_notes':decision['form_notes'],
            'placement':'优先填平台质检异议或返修说明栏；若只能追加到模型达成性备注，更新该输入后须重新检查并重新绑定异议',
            'next':'向用户说明异议和如何填写备注；平台原始不通过保留，以有证据异议继续'}


def disagreement_notes(decision):
    return '# 平台质检异议\n\n不认同该不通过结论。\n\n'+decision['reason']+'\n\n## 建议填写到表单的备注\n\n'+decision['form_notes']+'\n'


def status(root,evaluation=None):
    if not required(root):return {'required':False,'stage':'legacy_contract'}
    q=active_question(root)['question'] if (Path(root)/'CURRENT.json').exists() else read_json(Path(root)/'drafts/question.json')
    try:initial_question(root,q)
    except Error:return {'required':True,'stage':'draft_prompt_insight','ready_for_arena':False}
    try:
        request,_,cookie=descriptor(root,'question',q=q);question=latest(root,request)
        checks={'question':question or {'state':'pending','accepted':False}}
        if evaluation is not None:
            for stage in ('criteria','attainment'):
                request,_,_=descriptor(root,stage,evaluation=evaluation);checks[stage]=latest(root,request) or {'state':'pending','accepted':False}
        ready=all(checks.get(stage,{}).get('accepted') for stage in client.KEYS)
        if ready:ready=authoring_evaluation(root,evaluation)[1]['three_model_gate']
        return {'required':True,'checks':checks,'ready_for_arena':bool(ready),'cookie_file':str(cookie),
                'stage':'platform_checks_ready' if ready else 'platform_checks_pending'}
    except Error as error:return {'required':True,'stage':'platform_checks_pending','ready_for_arena':False,'reason':str(error)}


def export_evidence(root,evaluation,package):
    if not required(root):return None
    checks=final_gate(root,evaluation);q=active_question(root)['question']
    request,_,_=descriptor(root,'question',q=q);checks={'question':latest(root,request),**checks}
    notes=[];summary={}
    for stage,result in checks.items():
        destination=Path(package)/'evidence/platform'/stage;destination.mkdir(parents=True)
        source=Path(result['attempt'])
        for name in ('request.json','result.json'):
            shutil.copyfile(source/name,destination/name)
        summary[stage]={'state':result['state'],'server_conclusion':result['server_conclusion']}
        if result.get('disagreement'):
            write_json(destination/'disagreement.json',result['disagreement'])
            notes.append(result['disagreement']['form_notes'])
    return {'checks':summary,'form_notes':'\n\n'.join(notes)}
