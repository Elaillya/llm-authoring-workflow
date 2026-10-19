"""Evidence-bound failure observations and reviewed lessons in the memory scope."""
from pathlib import Path
import json
from .core import active_question,hash_json,now,read_json,require
from .memory import task_key,transaction
from .memory_scope import lesson_scope
from .text import insight_text

VERDICTS=('accepted','disputed','unresolved')


def _workspace(root):
    from .workspace import locate_workspace
    return locate_workspace(root)


def _save(root,q,kind,evidence,text):
    observation={'schema_version':1,'task_key':task_key(root),'task_id':q['task_id'],
                 'domain':q.get('domain'),'subdirection':q.get('subdirection'),
                 'question_sha256':hash_json(q),'prompt':q['prompt'],
                 'mechanism':insight_text(q['insight'],labels=False),
                 'kind':kind,'evidence':evidence,'evidence_text':text}
    eid=hash_json([observation['task_key'],kind,evidence])
    with transaction(_workspace(root)) as db:
        db.execute('INSERT OR IGNORE INTO failure_observations VALUES (?,?,?,?)',
                   (eid,json.dumps(observation,ensure_ascii=False),hash_json(observation),now()))
    return eid


def observe_gate(root,evaluation):
    from .authoring import check_seed,check_three
    checked=check_seed(root,evaluation) if set(evaluation.get('models',{}))=={'seed'} else check_three(root,evaluation)
    models=checked['models'];kinds=[]
    if models['seed']['attained']:kinds.append('seed_all_attained')
    if 'gpt' in models and not models['gpt']['attained'] and not models['claude']['attained']:
        kinds.append('gpt_claude_both_missed')
    if not kinds:return []
    evidence={'evaluation_sha256':hash_json(evaluation),'models':{
        role:{k:item[k] for k in ('name','decisive_met','decisive_total','attained')} for role,item in models.items()},
        'missing_points':{role:[j['id'] for j in item['judgments'] if j['kind']=='decisive' and not j['met']] for role,item in models.items()}}
    text='；'.join(f'{item["name"]}：决定性考点{item["decisive_met"]}/{item["decisive_total"]}' for item in models.values())
    return [_save(root,active_question(root)['question'],kind,evidence,text) for kind in kinds]


def observe_platform(root,stage,result,q=None):
    if result.get('state') not in ('failed','disputed'):return None
    from .platform_checks import verified_record
    directory=Path(result['attempt']);request,record=verified_record(directory,stage)
    require(record['parsed']['state']=='failed','仅记录实际内容不通过，服务错误另行保留')
    q=q if stage=='question' else active_question(root)['question']
    require(q is not None and request['payload']['params']['题目']==q['prompt']
            and request['payload']['params']['出题说明']==insight_text(q['insight']),'失败观察与原检查输入不一致')
    evidence={'attempt':str(directory),'request_sha256':hash_json(request),
              'result_sha256':hash_json(record),'stage':stage}
    return _save(root,q,stage+'_quality_failed',evidence,record['parsed']['feedback'])


def _observation(db,eid):
    row=db.execute('SELECT body,body_sha FROM failure_observations WHERE event_id=?',(eid,)).fetchone()
    require(row is not None,'失败观察不存在')
    value=json.loads(row[0]);require(hash_json(value)==row[1] and hash_json([value['task_key'],value['kind'],value['evidence']])==eid,'失败观察内容绑定已改变')
    return value


def _reviews(db,eid):
    result=[]
    for raw,digest in db.execute('SELECT body,body_sha FROM failure_reviews WHERE event_id=? ORDER BY rowid',(eid,)):
        value=json.loads(raw);require(hash_json(value)==digest,'失败复核内容绑定已改变');result.append(value)
    return result


def show(workspace,eid):
    with transaction(workspace) as db:return {'event_id':eid,'observation':_observation(db,eid),'reviews':_reviews(db,eid)}


def review_template(workspace,eid):
    item=show(workspace,eid)
    return {'schema_version':1,'event_id':eid,'observation_sha256':hash_json(item['observation']),'observation':item['observation'],
            'verdict':None,'reviewer':'','cause':'','prevention':'','applicability':'','evidence_quotes':[]}


def review(workspace,decision):
    require(decision.get('schema_version')==1 and decision.get('verdict') in VERDICTS,'复核须明确认可、有异议或未确认')
    eid=decision.get('event_id');require(isinstance(eid,str),'复核缺少失败ID')
    with transaction(workspace) as db:
        observation=_observation(db,eid)
        require(decision.get('observation_sha256')==hash_json(observation) and decision.get('observation',observation)==observation,'复核失败证据已变化')
        for key in ('reviewer','cause'):
            require(isinstance(decision.get(key),str) and decision[key].strip(),'复核需要实际责任人和具体原因')
        if decision['verdict']=='accepted':
            for key in ('prevention','applicability'):
                require(isinstance(decision.get(key),str) and decision[key].strip(),'认可经验须写可执行改进及适用边界')
            quotes=decision.get('evidence_quotes',[])
            require(isinstance(quotes,list) and quotes and all(isinstance(q,str) and q.strip() and q in observation['evidence_text'] for q in quotes),'经验依据须引用原始观察或反馈')
        value={k:decision.get(k) for k in ('schema_version','event_id','observation_sha256','verdict','reviewer','cause','prevention','applicability','evidence_quotes')}
        previous=_reviews(db,eid)
        if not previous or previous[-1]!=value:
            db.execute('INSERT INTO failure_reviews VALUES (?,?,?,?)',(eid,json.dumps(value,ensure_ascii=False),hash_json(value),now()))
    return {'event_id':eid,'verdict':value['verdict'],'shared_with':lesson_scope(workspace)}


def mark_disputed(root,stage,result,decision,q=None):
    eid=observe_platform(root,stage,result,q)
    value=review_template(_workspace(root),eid)
    value.update(verdict='disputed',reviewer=decision['reviewer'],cause=decision['reason'])
    return review(_workspace(root),value)


def failure_context(root,workspace,limit=12):
    require(type(limit) is int and 1<=limit<=50,'失败经验条数须在1到50之间')
    request=read_json(Path(root)/'REQUEST.json');own=task_key(root);accepted=[];pending=[];total=0
    with transaction(workspace) as db:
        for (eid,) in db.execute('SELECT event_id FROM failure_observations ORDER BY rowid'):
            event=_observation(db,eid);reviews=_reviews(db,eid);total+=1
            if reviews and reviews[-1]['verdict']=='accepted':
                # A later evidence disagreement must not remain a trusted lesson,
                # even if a prior process stopped before its review write.
                attempt=event['evidence'].get('attempt')
                if attempt and list(Path(attempt).glob('disagreement-*.json')):continue
                accepted.append({'event_id':eid,'task_id':event['task_id'],'domain':event['domain'],
                    'subdirection':event['subdirection'],'kind':event['kind'],
                    **{k:reviews[-1][k] for k in ('cause','prevention','applicability')}})
            elif not reviews or reviews[-1]['verdict']=='unresolved':
                pending.append({'event_id':eid,'task_id':event['task_id'],'kind':event['kind'],
                    'evidence_summary':event['evidence_text'][:300],'own_task':event['task_key']==own})
    accepted.sort(key=lambda i:(i['domain']==request.get('domain'),i['subdirection']==request.get('subdirection')))
    pending.sort(key=lambda i:i['own_task'])
    return {'scope':lesson_scope(workspace),'observed_count':total,'accepted_count':len(accepted),
            'pending_count':len(pending),'accepted_lessons':accepted[-limit:],'pending_reviews':pending[-limit:],
            'next':'设计前读认可经验并核对适用范围；待复核观察先failure-review，错误意见和服务故障不作为可靠出题规律'}


def repair_route(root):
    """Preserve the accepted-criteria repair branch when a revision loses its gate."""
    root=Path(root)
    if not (root/'CURRENT.json').exists():return None
    q=active_question(root)['question'];key=task_key(root);candidates=[]
    with transaction(_workspace(root)) as db:
        for (eid,) in db.execute('SELECT event_id FROM failure_observations ORDER BY rowid'):
            event=_observation(db,eid)
            if event['task_key']!=key or event['kind']!='criteria_quality_failed' or event['prompt']!=q['prompt']:continue
            reviews=_reviews(db,eid)
            if reviews and reviews[-1]['verdict']=='accepted' and not list(Path(event['evidence']['attempt']).glob('disagreement-*.json')):
                candidates.append(eid)
    if not candidates:return None
    return {'failure_id':candidates[-1],'stage':'criteria_repair_decision',
            'next':'当前同题面已有认可的考点质检失败。先按独立专业依据修复Insight/考点、统一重评；若仍不能满足三模型门槛，询问用户是否重新提供GPT或Claude完整回复。未获同意不替换；拒绝、不可行或替换仍失败时再改prompt，从Seed开始。门槛未通过不调用后两项质检。'}
