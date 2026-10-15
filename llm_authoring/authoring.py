"""Three-model screening checkpoints and shared point-level evidence validation."""
from pathlib import Path
import shutil
import tempfile
from .core import (Error, NAMES, ROLES, active_question, read_json, read_response,
                   question_domain, require, sha, validate_image, write_json)
from .delivery import model_files,submission_id,submission_text

COMMON_CHECKS=('realistic_stable_domain_scenario','clear_natural_prompt','no_insight_leak_or_hidden_conditions',
               'insight_key_reasoning_and_conclusion','insight_necessary_decisive_specific_consensual',
               'rubric_specific_atomic_and_supported','insight_and_rubric_distinct','sources_and_assumptions_honest')
TYPE_CHECKS={'分析决策类':'decision_selects_one_allowed_option','开放推荐类':'recommendation_infers_profile_and_limited_candidates',
             'How-to类':'howto_has_executable_mainline_and_order'}


def decisive_points(root):
    return [p for p in active_question(root)['question']['points'] if p['kind']=='decisive']


def evaluation_template(root,roles=ROLES,include_supporting=False):
    current=active_question(root)
    result={'schema_version':1,'phase':'five_model_evaluation' if include_supporting else 'authoring','task_id':current['question']['task_id'],
            'prompt_sha256':current['prompt_sha256'],'rubric_sha256':current['rubric_sha256'],'question_sha256':current['question_sha256'],'reviewer':'','models':{}}
    for role in roles:
        response=read_response(root,role)
        result['models'][role]={'response_sha256':response['meta']['reply_sha256'],
                               'points':{p['id']:{'met':None,'reason':'','quotes':[]} for p in (current['question']['points'] if include_supporting else decisive_points(root))}}
    return result


def validated_models(root,ev,roles=ROLES,include_supporting=False):
    current=active_question(root);points=current['question']['points'] if include_supporting else decisive_points(root)
    phase='five_model_evaluation' if include_supporting else 'authoring'
    require(ev.get('schema_version')==1 and ev.get('phase')==phase and ev.get('task_id')==current['question']['task_id'],'评估不属于当前出题任务')
    require(ev.get('prompt_sha256')==current['prompt_sha256'],'评估题面版本失效，需获取新回复')
    require(ev.get('rubric_sha256')==current['rubric_sha256'],'评估考点版本失效，须对三模型统一重评')
    require(ev.get('question_sha256')==current['question_sha256'],'完整冻结版本失效，重新确认三模型判断；题面未变可复用完整原回复')
    require(isinstance(ev.get('reviewer'),str) and ev['reviewer'].strip(),'填写实际评估责任人')
    require(set(ev.get('models',{}))==set(roles),'当前检查须有完整指定模型，缺回复不能记为未达成')
    stats={};sent_texts=set()
    for role in roles:
        item=read_response(root,role);record=ev['models'][role]
        if role in NAMES:
            require(item['meta'].get('display_name')==NAMES[role],'指定模型名称不匹配')
            from .manual import validate_manual_evidence
            task=read_json(Path(root)/'TASK.json') if (Path(root)/'TASK.json').exists() else {}
            if task.get('response_mode')=='official_manual' or item['meta'].get('source_kind')=='official_manual':
                validate_manual_evidence(root,role,item)
        else:
            from .arena import validate_arena_evidence
            validate_arena_evidence(root,role,item)
        request=item['meta'].get('manual_request') if item['meta'].get('source_kind')=='official_manual' else item['meta'].get('arena_request')
        if request is not None:
            from .model_prompt import prompt_text
            sent_texts.add(prompt_text(request))
        require(record.get('response_sha256')==item['meta']['reply_sha256'],'评估与原文不匹配')
        require(set(record.get('points',{}))=={p['id'] for p in points},'逐项评估全部指定考点；五模型排序也需判断非决定性点')
        judgments=[]
        for point in points:
            judgment=record['points'][point['id']]
            require(type(judgment.get('met')) is bool,'证据不足或未判定，不得写成未达成')
            require(isinstance(judgment.get('reason'),str) and judgment['reason'].strip(),'逐项判断需要具体理由')
            quotes=judgment.get('quotes',[])
            require(isinstance(quotes,list) and all(isinstance(q,str) and q.strip() and q in item['text'] for q in quotes),'引用不是原文的准确子串')
            require(not judgment['met'] or quotes,'满足须有原文引用依据')
            judgments.append({**judgment,'id':point['id'],'kind':point['kind']})
        decisive=[j for j in judgments if j['kind']=='decisive']
        met=sum(j['met'] for j in decisive)
        stats[role]={'name':item['meta']['display_name'],'decisive_met':met,'decisive_total':len(decisive),'attained':met==len(decisive),
                     'total_met':sum(j['met'] for j in judgments),'total_points':len(points),'judgments':judgments}
    require(len(sent_texts)<=1,'模型实际发送文字存在新旧合同差异；保留原件，在独立新题统一采集相同prompt后再评测')
    return stats


def check_seed(root,ev):
    stats=validated_models(root,ev,('seed',))
    return {'phase':'authoring','screen':'seed_first','models':stats,'continue_to_gpt_claude':not stats['seed']['attained']}


def check_three(root,ev):
    stats=validated_models(root,ev)
    return {'phase':'authoring','models':stats,'three_model_gate':not stats['seed']['attained'] and (stats['gpt']['attained'] or stats['claude']['attained'])}


def self_review_template(root):
    current=active_question(root)
    ids=COMMON_CHECKS+(TYPE_CHECKS[current['question']['question_type']],)
    sources=Path(root)/'drafts/sources.md'
    require(sources.is_file() and not sources.is_symlink() and sources.read_text().strip(),'先保存专业依据、场景设定和适用边界到drafts/sources.md')
    return {'schema_version':1,'phase':'authoring_self_review','question_sha256':current['question_sha256'],'source_notes_sha256':sha(sources),'reviewer':'',
            'checks':{key:{'passed':None,'reason':''} for key in ids}}


def validate_self_review(root,review):
    expected=self_review_template(root)
    require(review.get('schema_version')==1 and review.get('phase')==expected['phase'] and review.get('question_sha256')==expected['question_sha256'],'自查版本失效，按当前题面、Insight和考点重新自查')
    require(review.get('source_notes_sha256')==expected['source_notes_sha256'],'专业依据笔记已改变，按新依据更新自查')
    require(isinstance(review.get('reviewer'),str) and review['reviewer'].strip(),'自查需记录实际执行者，AI自查不能冒充独立专家质检')
    checks=dict(review.get('checks',{}))
    if 'insight_mechanism_priority_conclusion' in checks and 'insight_key_reasoning_and_conclusion' not in checks:
        checks['insight_key_reasoning_and_conclusion']=checks.pop('insight_mechanism_priority_conclusion')
    if 'realistic_stable_cs_scenario' in checks and 'realistic_stable_domain_scenario' not in checks:
        require(question_domain(root)=='计算机科学','旧CS自查字段仅适用于计算机科学旧题；请按所选领域重新自查')
        checks['realistic_stable_domain_scenario']=checks.pop('realistic_stable_cs_scenario')
    require(set(checks)==set(expected['checks']),'自查须覆盖全部通用及本题型要求')
    for item in checks.values():
        require(item.get('passed') is True and isinstance(item.get('reason'),str) and item['reason'].strip(),'自查未通过或无具体理由，先修订再交接')


def validate_api_evidence(item,role):
    m=item['meta'];d=item['directory']
    require(m.get('source_kind')=='api' and m.get('evidence_status')=='verified' and m.get('screenshot_kind')=='api_rendered','须有完整API原文及来源清楚的截图')
    require(m.get('returned_model') and m.get('model_identity_check','').startswith('returned_model_matches_configured'),'缺少已核对的实际返回模型ID')
    options=m.get('request_options',{})
    if role=='gpt':require(options.get('reasoning',{}).get('effort',options.get('reasoning_effort')) in ('medium','high','xhigh'),'GPT采集记录缺中高推理模式')
    if role=='claude':require(options.get('thinking',{}).get('type') in ('adaptive','enabled') and options.get('output_config',{}).get('effort','high') in ('medium','high','max'),'Claude采集记录缺中高推理模式')
    filename=m.get('screenshot','');require(filename and Path(filename).name==filename,'截图文件名不合法')
    picture=d/filename
    require(picture.is_file() and not picture.is_symlink() and sha(picture)==m.get('screenshot_sha256'),'截图缺失或被改写')
    validate_image(picture)
    manifest=read_json(d/'render-manifest.json')
    require(manifest.get('full_page') is True and manifest.get('reply_sha256')==m['reply_sha256']
            and manifest.get('png_sha256')==m['screenshot_sha256'],'截图未绑定完整原文')
    return picture


def export_authoring(root,ev,review,output):
    result=check_three(root,ev)
    require(result['three_model_gate'],'三模型区分度未通过，保留真实负结果，不能作为完成题目交接')
    from .platform_checks import final_gate,export_evidence
    final_gate(root,ev)
    validate_self_review(root,review)
    current=active_question(root);q=current['question'];output=Path(output).absolute()
    require(not output.exists(),'交接目录已存在，拒绝覆盖')
    for protected in ('responses','revisions','attempts','model-input','arena-input','evaluations','drafts','platform-checks'):
        require(not output.resolve().is_relative_to((Path(root)/protected).resolve()),'交接不能写入原始证据或冻结目录')
    validated=[(role,read_response(root,role)) for role in ROLES]
    from .manual import validate_model_evidence
    pictures={role:validate_model_evidence(root,role,item) for role,item in validated}
    fields={'phase':'authoring','task_id':submission_id(root,q['task_id']),'domain':question_domain(root),'prompt':q['prompt'],'question_type':q['question_type'],
            'insight':q['insight'],'author_notes':q['author_notes'],
            'decisive_points':[p for p in q['points'] if p['kind']=='decisive'],
            'supporting_points':[p for p in q['points'] if p['kind']=='supporting'] or '无','models':{}}
    output.parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='.authoring-export-',dir=output.parent))
    try:
        (staging/'models').mkdir();(staging/'evidence').mkdir()
        if any(pictures.values()):(staging/'screenshots').mkdir()
        paths=model_files({role:item['meta']['display_name'] for role,item in validated})
        for index,(role,item) in enumerate(validated,1):
            m=item['meta'];stat=result['models'][role];pic=pictures[role]
            shutil.copyfile(item['directory']/'reply.md',staging/paths[role])
            if pic:shutil.copyfile(pic,staging/'screenshots'/f'{role}.png')
            evidence=staging/'evidence'/role;evidence.mkdir()
            evidence_files=('metadata.json',m.get('raw_response_file','raw_response.json'))+(('render-manifest.json',) if pic else ())
            for name in evidence_files:
                shutil.copyfile(item['directory']/name,evidence/name)
            notes='\n\n'.join(f'{j["id"]}：{"满足" if j["met"] else "不满足"}；原因：{j["reason"]}'+('；原文依据：'+' / '.join(j['quotes']) if j['quotes'] else '') for j in stat['judgments'])
            fields['models'][role]={'ordinal':index,'display_name':m['display_name'],'requested_model':m['model'],'returned_model':m['returned_model'],
                                   'reply_markdown':item['text'],'reply_file':paths[role],'attained':stat['attained'],'attainment_notes':notes,
                                   'screenshot':f'screenshots/{role}.png' if pic else None,'source_kind':m['source_kind'],
                                   'screenshot_submission':'historical_api_render' if pic else 'user_submits_separately'}
        platform=export_evidence(root,ev,staging)
        if platform:
            fields['platform_checks']=platform
        (staging/'提交信息.md').write_text(submission_text(fields,ROLES,checkpoint=True),encoding='utf-8')
        write_json(staging/'question.json',current);write_json(staging/'fields.json',fields)
        shutil.copyfile(Path(root)/'drafts/sources.md',staging/'evidence/sources.md')
        write_json(staging/'evaluation.json',ev);write_json(staging/'author-self-review.json',review)
        from . import VERSION
        handoff={'schema_version':1,'kind':'llm_authoring_handoff','workflow_version':VERSION,'task_id':q['task_id'],
                 'question_sha256':current['question_sha256'],'prompt_sha256':current['prompt_sha256'],'rubric_sha256':current['rubric_sha256'],
                 'models_in_order':list(ROLES),'three_model_gate':True,'next_workflow':'arena_and_ranking',
                 'submission_id':fields['task_id'],
                 'next_inputs':['question.json','evidence/sources.md','evaluation.json','models/','evidence/'],
                 'next_action':'保留本检查点，准备Arena两份Markdown填入文件，完成五模型全部考点评估、排序及最终提交。'}
        write_json(staging/'handoff.json',handoff)
        write_json(staging/'manifest.json',{'schema_version':1,'phase':'authoring','files':{p.relative_to(staging).as_posix():sha(p) for p in staging.rglob('*') if p.is_file()}})
        require(not output.exists(),'交接发布期间目标被其他写入者占用')
        staging.rename(output)
    except BaseException:
        shutil.rmtree(staging);raise
    return {'phase':'authoring','output':str(output),'markdown':str(output/'提交信息.md'),
            'model_markdown':{role:str(output/path) for role,path in paths.items()},'handoff':str(output/'handoff.json')}
