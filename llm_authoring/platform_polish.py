"""Offline wording improvements after passed checks and the Arena handoff."""
from pathlib import Path
import copy
import time
import uuid
from .core import ROLES,active_question,hash_json,read_json,require,sha,write_json
from . import platform_checks as qa

REVIEWS=('prompt_unchanged','insight_meaning_unchanged','rubric_meaning_unchanged',
         'model_originals_unchanged','attainment_and_quotes_unchanged')
NOTICE='平台三项通过对应优化前的检查输入；发送Arena填写提示后仅优化说明表达，题面、考点含义、原回复及达成判断保持，优化后未再次调用质检。'


def basis(root,evaluation):
    require(qa.required(root),'表达优化用于启用平台三检查的新题')
    current=active_question(root);checks=qa.final_gate(root,evaluation)
    request,_,_=qa.descriptor(root,'question',q=current['question'])
    checks={'question':qa.latest(root,request),**checks}
    require(all(item['state']=='passed' for item in checks.values()),'仅三项实际通过后可做免复检表达优化；有证据异议不冒充通过')
    require(qa.authoring_evaluation(root,evaluation)[1]['three_model_gate'],'先满足三模型门槛')
    directory=Path(root)/'arena-input'/current['revision']
    require(not directory.is_symlink(),'Arena目录不能为符号链接')
    manifest=read_json(directory/'request.json')
    require(all(manifest.get(key)==current[key] for key in ('revision','question_sha256','prompt_sha256','rubric_sha256')),
            '先按当前版本创建Arena填写文件并向用户发出链接，再进行优化')
    for name in ('model-4.md','model-5.md','arena-prompt.md'):
        require((directory/name).is_file() and not (directory/name).is_symlink(),'保留已发出的Arena填写文件')
    binding={'question_sha256':current['question_sha256'],
             'checks':{stage:{'request_sha256':sha(Path(item['attempt'])/'request.json'),
                              'result_sha256':sha(Path(item['attempt'])/'result.json')} for stage,item in checks.items()}}
    return current,checks,binding


def editable_fields(root,evaluation):
    q=active_question(root)['question'];ev,_=qa.authoring_evaluation(root,evaluation)
    fields={f'insight.{key}':q['insight'][key] for key in ('mechanism','priority','conclusion')}
    fields['author_notes']=q['author_notes']
    fields.update({f'points.{point["id"]}.criterion':point['criterion'] for point in q['points']})
    fields.update({f'reasons.{role}.{point}':item['reason'] for role in ROLES
                   for point,item in ev['models'][role]['points'].items()})
    return fields


def template(root,evaluation):
    _,_,binding=basis(root,evaluation)
    return {'schema_version':1,'phase':'platform_postpass_polish','binding':binding,'reviewer':'',
            'arena_notice':'','reviews':{key:{'passed':False,'reason':''} for key in REVIEWS},'changes':[],
            'instructions':'先在侧栏发出Arena题面及model-4.md/model-5.md链接，记录实际通知；changes填写field、before、after、stage、feedback_quote、reason。仅优化表达，不改专业含义或判定。无需再次调用质检。'}


def validate(root,evaluation,decision):
    _,checks,binding=basis(root,evaluation)
    require(decision.get('schema_version')==1 and decision.get('phase')=='platform_postpass_polish'
            and decision.get('binding')==binding,'优化依据已变化或不属于当前三项通过记录')
    require(isinstance(decision.get('reviewer'),str) and decision['reviewer'].strip(),'记录实际优化者')
    notice=decision.get('arena_notice','')
    require(isinstance(notice,str) and all(name in notice for name in ('model-4.md','model-5.md','arena-prompt.md')),
            '先向用户发送三个Arena文件的填写提示，并记录已发送的实际通知')
    for key in REVIEWS:
        item=decision.get('reviews',{}).get(key,{})
        require(item.get('passed') is True and isinstance(item.get('reason'),str) and item['reason'].strip(),
                '逐项说明优化未改变题面、专业含义、考点、原文、判断和引用：'+key)
    fields=editable_fields(root,evaluation);seen=set();changes=decision.get('changes')
    require(isinstance(changes,list) and changes,'无优化建议时直接继续；有改写需逐项记录')
    for change in changes:
        field=change.get('field');stage=change.get('stage');quote=change.get('feedback_quote')
        require(field in fields and field not in seen,'仅允许指定说明字段的表达优化，不能改题面、分类、判定或引用')
        seen.add(field)
        require(change.get('before')==fields[field],'优化前原文与已验证版本不一致')
        require(isinstance(change.get('after'),str) and change['after'].strip() and change['after']!=fields[field],
                '改写须为实际非空新表达')
        require(stage in checks and isinstance(quote,str) and quote.strip() and quote in checks[stage]['feedback'],
                '建议依据须准确引用当前通过反馈')
        require(isinstance(change.get('reason'),str) and change['reason'].strip(),'逐项写明表达优化与含义保持依据')
    return binding


def apply(root,evaluation,decision):
    with qa.check_lock(root):
        binding=validate(root,evaluation,decision)
        directory=qa.records_directory(root)
        target=directory/f'polish-{binding["question_sha256"]}-{time.time_ns()}-{uuid.uuid4().hex[:8]}.json'
        write_json(target,decision)
    return {'state':'postpass_polished','record':str(target),'changes':len(decision['changes']),
            'platform_requests':0,'notice':NOTICE,'next':'保留已发出Arena文件，等待两份Markdown；最终交付使用优化表达并注明未复检'}


def export(root,evaluation,fields,models,package):
    if not qa.required(root):return None
    current=active_question(root)
    paths=sorted(qa.records_directory(root).glob('polish-'+current['question_sha256']+'-*.json'))
    if not paths:return None
    path=paths[-1];decision=read_json(path);validate(root,evaluation,decision)
    models=copy.deepcopy(models)
    for change in decision['changes']:
        parts=change['field'].split('.');after=change['after']
        if parts[0]=='insight':fields['insight'][parts[1]]=after
        elif parts[0]=='author_notes':fields['author_notes']=after
        elif parts[0]=='points':
            for name in ('decisive_points','supporting_points'):
                if fields[name]=='无':continue
                for point in fields[name]:
                    if point['id']==parts[1]:point['criterion']=after
        else:
            for item in models[parts[1]]['judgments']:
                if item['id']==parts[2]:item['reason']=after
    from .ranking import attainment_notes
    for role in ROLES:fields['models'][role]['attainment_notes']=attainment_notes(models[role])
    destination=Path(package)/'evidence/platform/postpass-polish.json';write_json(destination,decision)
    fields['postpass_polish']={'notice':NOTICE,'evidence_file':destination.relative_to(package).as_posix(),
                              'changes':len(decision['changes']),'record_sha256':hash_json(decision)}
    return fields['postpass_polish']
