"""Local recall plus accountable semantic review, without model API calls."""
from difflib import SequenceMatcher
from pathlib import Path
import re
import unicodedata
from .core import hash_json, read_json, require, sha, validate_question
from .memory import records, remember, snapshot, sync_locked, task_key, topic_index, transaction
from .references import LIBRARY, LIFESTYLE_LIBRARY, validate_business_references, validate_lifestyle_references
from .selection import validate_selection
from .text import insight_text

CHECKS=('natural_prompt','distinct_scenario','distinct_insight','distinct_points','source_grounding')
PROFILE_TEXT=('scenario','goal')
PROFILE_LISTS=('constraints','mechanism_tags','point_targets','reasoning_path')
AXES={'scenario','goal','constraints','mechanism','scoring_targets','reasoning_path'}


def normalized(text):
    text=unicodedata.normalize('NFKC',text).casefold()
    text=re.sub(r'\d+(?:\.\d+)?','num',text)
    return ''.join(re.findall(r'[a-z0-9\u4e00-\u9fff]',text))


def text_similarity(a,b):
    a=normalized(a);b=normalized(b)
    if not a or not b:return 0.0
    grams=lambda t:{t[i:i+3] for i in range(max(1,len(t)-2))}
    x,y=grams(a),grams(b)
    return round(max(SequenceMatcher(None,a,b,autojunk=False).ratio(),len(x&y)/len(x|y)),4)


def jaccard(a,b):
    x={normalized(i) for i in a};y={normalized(i) for i in b}
    return len(x&y)/len(x|y) if x or y else 0.0


def naturalness_signals(q):
    prompt=q['prompt'];signals=[]
    for phrase in ('随着数字化转型','在当前复杂背景下','可落地、可量化、可复制','请从多个维度','构建动态平衡','系统性地全面分析'):
        if phrase in prompt:signals.append({'kind':'template_language','text':phrase})
    if re.search(r'请从[^。？?]{0,35}(?:三个|多个|各个)维度',prompt):signals.append({'kind':'essay_instruction','text':'按维度组织长论述的指令'})
    if prompt.count('；')>=3:signals.append({'kind':'compressed_conditions','text':'复核是否把自然问题压成了条件串'})
    if q.get('subdirection')=='cs_daily':
        jargon=[word for word in ('线性一致性','MVCC','共识协议','幂等键','读写屏障') if word.casefold() in prompt.casefold()]
        if jargon:signals.append({'kind':'audience_mismatch','text':'普通人场景需解释这些术语：'+','.join(jargon)})
    return signals


def validate_profile(q):
    profile=q.get('design_profile',{})
    for key in PROFILE_TEXT:
        require(isinstance(profile.get(key),str) and profile[key].strip(),'候选画像缺少 '+key)
    for key in PROFILE_LISTS:
        values=profile.get(key)
        require(isinstance(values,list) and values and all(isinstance(v,str) and v.strip() for v in values),
                '候选画像需要非空列表 '+key)


def report_locked(root,q,items):
    key=task_key(root);neighbors=[];hard=[]
    insight=lambda value:insight_text(value['insight'],labels=False)
    points=lambda value:'\n'.join(p['criterion'] for p in value['points'])
    for record in items:
        if record['task_key']==key:continue
        other=record['question'];left=q.get('design_profile',{});right=other.get('design_profile',{})
        profile=max(jaccard(left.get('mechanism_tags',[]),right.get('mechanism_tags',[])),
                    jaccard(left.get('point_targets',[]),right.get('point_targets',[])),
                    jaccard(left.get('reasoning_path',[]),right.get('reasoning_path',[])))
        scores={'prompt':text_similarity(q['prompt'],other['prompt']),
                'insight':text_similarity(insight(q),insight(other)),
                'points':text_similarity(points(q),points(other)),'profile':round(profile,4)}
        duplicate=[]
        for field,a,b,minimum in [('prompt',q['prompt'],other['prompt'],1),
                                  ('insight',insight(q),insight(other),30),('points',points(q),points(other),18)]:
            if normalized(a)==normalized(b) and len(normalized(a))>=minimum:duplicate.append(field)
        if duplicate:hard.append({'entry_id':record['entry_id'],'fields':duplicate})
        if max(scores.values())>=0.35:
            neighbors.append({**record,'scores':scores,'risk':'high' if max(scores.values())>=0.8 else 'review'})
    neighbors.sort(key=lambda r:(bool([h for h in hard if h['entry_id']==r['entry_id']]),max(r['scores'].values())),reverse=True)
    # Every high-similarity match needs a concrete comparison. Only the extra
    # lower-risk recall list has a display budget; it cannot hide high risks.
    high=[item for item in neighbors if item['risk']=='high']
    ordinary=[item for item in neighbors if item['risk']!='high']
    neighbors=high+ordinary[:max(0,8-len(high))]
    notes=Path(root)/'drafts/sources.md'
    require(notes.is_file() and not notes.is_symlink() and notes.read_text().strip(),'先保存本题来源、设定和边界到drafts/sources.md')
    report={'schema_version':1,'question_sha256':hash_json(q),'source_notes_sha256':sha(notes),
            'business_library_sha256':sha(LIBRARY) if q.get('domain')=='商科' else None,
            'memory_snapshot_sha256':snapshot(items,key),'naturalness_signals':naturalness_signals(q),
            'neighbors':neighbors,'hard_duplicates':hard,'topic_index':topic_index(items,key),
            'comparison_scope':'all_other_task_versions_in_this_workspace',
            'limits':'本地分数仅召回近似文本和标签；作者必须结合原题语义比较场景、机制和评分要求，不能据低分声称语义绝不重复'}
    from .domains import canonical_domain,LIFESTYLE
    if canonical_domain(q.get('domain'))==LIFESTYLE:
        report['lifestyle_library_sha256']=sha(LIFESTYLE_LIBRARY)
        supplement=Path(root)/'drafts/lifestyle-supplement.json'
        report['lifestyle_supplement_sha256']=sha(supplement) if supplement.exists() else None
    return report


def prepare_candidate(root,q):
    validate_question(q);validate_selection(root,q);validate_profile(q);validate_business_references(q);validate_lifestyle_references(root,q)
    require(read_json(Path(root)/'TASK.json')['task_id']==q['task_id'],'候选题目ID不属于本任务')


def candidate_check(root,q):
    from .workspace import locate_workspace
    prepare_candidate(root,q);workspace=locate_workspace(root)
    with transaction(workspace) as connection:
        sync_locked(workspace,connection)
        return report_locked(root,q,records(connection))


def review_template(root,q):
    report=candidate_check(root,q)
    return {'schema_version':1,'phase':'design_review','question_sha256':hash_json(q),
            'report_sha256':hash_json(report),'report':report,'reviewer':'',
            'checks':{key:{'passed':None,'reason':''} for key in CHECKS},
            'semantic_screen':{'screened_entry_ids':[],'additional_similar_ids':[],'reason':''},
            'comparisons':{n['entry_id']:{'decision':None,'reason':'','difference_axes':[]} for n in report['neighbors']}}


def validate_review(q,review,report):
    require(review.get('schema_version')==1 and review.get('phase')=='design_review'
            and review.get('question_sha256')==hash_json(q) and review.get('report_sha256')==hash_json(report)
            and review.get('report')==report,'设计复核已过期：候选、来源或其他题记忆变化，按最新召回重新比较')
    require(not report['hard_duplicates'],'存在跨题完全或归一化重复的题面、Insight或整组考点；换实质选题后重新复核')
    require(isinstance(review.get('reviewer'),str) and review['reviewer'].strip(),'记录实际设计复核执行者；由助手完成，不向用户新增审批')
    checks=review.get('checks',{})
    require(set(checks)==set(CHECKS),'设计复核须覆盖自然表达、场景、Insight、考点及资料适用性')
    for value in checks.values():
        require(value.get('passed') is True and isinstance(value.get('reason'),str) and value['reason'].strip(),
                '设计复核未通过或缺少具体理由，先修改候选')
    semantic=review.get('semantic_screen',{});all_ids={n['entry_id'] for n in report['topic_index']}
    screened=semantic.get('screened_entry_ids',[]);extra=semantic.get('additional_similar_ids',[])
    require(isinstance(screened,list) and set(screened)==all_ids and isinstance(extra,list) and set(extra)<=all_ids
            and isinstance(semantic.get('reason'),str) and semantic['reason'].strip(),
            '须先阅读全库机制索引并记录语义筛查；低文本分数不证明没有相似题')
    comparisons=review.get('comparisons',{})
    expected={n['entry_id'] for n in report['neighbors']}|set(extra)
    require(set(comparisons)==expected,'逐条比较召回和语义筛查发现的既有候选，不能漏看高相似题')
    compared={n['entry_id']:n for n in report['neighbors']}
    for eid in extra:
        if eid not in compared:compared[eid]={'entry_id':eid,'risk':'high'}
    for n in compared.values():
        item=comparisons[n['entry_id']]
        require(item.get('decision')=='distinct' and isinstance(item.get('reason'),str) and item['reason'].strip(),
                '与已有题的实质区别未确认，先改题，不能只换措辞')
        axes=item.get('difference_axes',[])
        require(isinstance(axes,list) and set(axes)<=AXES,'记录区别维度：场景、目标、约束、机制、评分目标或推理路径')
        if n['risk']=='high':
            require(len(set(axes))>=2 and set(axes)&{'goal','constraints','mechanism','scoring_targets'},
                    '高相似候选须说明至少两个有依据的实质区别，至少涉及目标、约束、机制或评分要求之一')


def reserve(root,q,review_path=None,freeze_writer=None):
    from .workspace import locate_workspace
    prepare_candidate(root,q);workspace=locate_workspace(root)
    review=read_json(review_path or Path(root)/'drafts/design-review.json')
    with transaction(workspace) as connection:
        sync_locked(workspace,connection);items=records(connection);report=report_locked(root,q,items)
        validate_review(q,review,report)
        # Reserve before writing the frozen record. Other windows see this transaction
        # only after commit and must refresh any review based on the old snapshot.
        eid=hash_json([task_key(root),hash_json(q)])
        previous=next((item for item in items if item['entry_id']==eid),None)
        status=previous['status'] if previous and previous['status'] in ('frozen','delivered','historical') else 'draft'
        if previous is None or previous['status']!=status:remember(connection,root,q,status)
        result=freeze_writer() if freeze_writer else None
        if result:
            remember(connection,root,q,'frozen',result['revision'])
        return result or {'entry_id':eid,'status':status,'memory_snapshot_sha256':report['memory_snapshot_sha256']}
