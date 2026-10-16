"""Checked public source index and independently written business mechanism cards."""
from pathlib import Path
from .core import read_json, require
from .domains import canonical_domain,LIFESTYLE

LIBRARY=Path(__file__).resolve().parents[1]/'rules/business-reference.json'


def business_context(branch=None):
    from .selection import menu
    require(branch is None or branch in {item['id'] for item in menu('商科')},'商科子方向不合法')
    data=read_json(LIBRARY)
    cards=[m for m in data['mechanisms'] if branch is None or m['subdirection']==branch]
    ids={sid for m in cards for sid in m['source_ids']}
    return {'mechanisms':cards,'sources':[s for s in data['sources'] if s['id'] in ids],
            'next':'用机制卡定位原始来源，核对适用条件并记录本题设定；索引不是可直接提交的题目或专业验收'}


def validate_business_references(q):
    if q.get('domain')!='商科':return
    data=read_json(LIBRARY);sources={s['id']:s for s in data['sources']};cards={m['id']:m for m in data['mechanisms']}
    selected=q.get('business_mechanisms',[]);refs=q.get('business_references',[])
    require(isinstance(selected,list) and selected and all(i in cards for i in selected),'商科候选须选择参考库中适用于本题的机制卡')
    require(isinstance(refs,list) and refs and all(i in sources for i in refs),'商科候选须记录已查验的资料ID')
    for i in selected:
        card=cards[i]
        require(card['subdirection']==q.get('subdirection'),'机制卡与所选商科子方向不符')
        require(set(card['source_ids'])&set(refs),'机制卡须关联至少一个实际核实的来源')


LIFESTYLE_LIBRARY=Path(__file__).resolve().parents[1]/'rules/lifestyle-reference.json'


def validate_lifestyle_library(data):
    """Check traceability, not the truth or difficulty of a research claim."""
    from .selection import topic_index
    nodes={n['id'] for n in topic_index('生活娱乐')}
    require(isinstance(data,dict) and isinstance(data.get('sources'),list)
            and isinstance(data.get('mechanisms'),list),'生活资料须包含sources与mechanisms列表')
    sources=data['sources'];cards=data['mechanisms']
    for group in (sources,cards):
        require(all(isinstance(x,dict) and isinstance(x.get('id'),str) and x['id'] for x in group),'资料条目须有ID')
        require(len({x['id'] for x in group})==len(group),'生活资料ID重复')
    def text(value):return isinstance(value,str) and bool(value.strip())
    def texts(value):return isinstance(value,list) and bool(value) and all(text(x) for x in value)
    from urllib.parse import urlsplit
    from datetime import date
    for source in sources:
        require(all(text(source.get(k)) for k in ('title','url','organization','source_type','checked_date')),'来源元信息不完整')
        url=urlsplit(source['url'])
        require(url.scheme=='https' and bool(url.netloc) and not url.username and not url.password,'资料来源须为公开HTTPS链接')
        try:date.fromisoformat(source['checked_date'])
        except ValueError:require(False,'来源阅读日期须为ISO日期')
        verification=source.get('verification',{})
        require(isinstance(verification,dict) and verification.get('status')=='read'
                and verification.get('method')=='web_open' and text(verification.get('scope')),'须记录实际打开阅读的来源范围')
        require(texts(source.get('supported_claims')) and texts(source.get('limitations')),'来源须记录支持结论与边界')
    ids={s['id'] for s in sources}
    for card in cards:
        require(all(text(card.get(k)) for k in ('title','decisive_factor','mechanism','difficulty_note')),'机制卡缺少决定因素或机制')
        require(texts(card.get('node_ids')) and set(card['node_ids'])<=nodes,'机制卡包含未知主题')
        require(texts(card.get('source_ids')) and set(card['source_ids'])<=ids,'机制卡包含未知来源')
        for key in ('applicability','boundaries','common_mistakes','point_targets'):
            require(texts(card.get(key)),'机制卡须记录适用条件、边界、误区和独立考点')
        require(isinstance(card.get('scenario_seeds'),list) and card['scenario_seeds'],'机制卡须含构造情境')
        for seed in card['scenario_seeds']:
            require(isinstance(seed,dict) and seed.get('constructed') is True
                    and all(text(seed.get(k)) for k in ('label','situation','goal')),'情境须明确标记为构造场景')
            for key in ('constraints','observable_evidence','question_types'):
                require(texts(seed.get(key)),'情境缺少限制、证据或题型')
            from .core import TYPES
            require(set(seed['question_types'])<=set(TYPES),'情境题型无效')


def lifestyle_library(root=None):
    data=read_json(LIFESTYLE_LIBRARY)
    public_counts={'sources':len(data['sources']),'mechanisms':len(data['mechanisms'])}
    if root is not None:
        path=Path(root)/'drafts/lifestyle-supplement.json'
        if path.exists():
            require(path.is_file() and not path.is_symlink(),'生活补充资料须为普通JSON文件')
            extra=read_json(path);validate_lifestyle_library(extra)
            data={**data,'sources':data['sources']+extra['sources'],'mechanisms':data['mechanisms']+extra['mechanisms']}
    validate_lifestyle_library(data)
    data['public_counts']=public_counts
    data['supplement_counts']={k:len(data[k])-v for k,v in public_counts.items()}
    data.update(source_count=len(data['sources']),mechanism_count=len(data['mechanisms']),
                scenario_seed_count=sum(len(c['scenario_seeds']) for c in data['mechanisms']))
    coverage=lifestyle_coverage(data['mechanisms'])
    data.update(directly_covered_leaf_count=len(coverage['directly_covered_leaf_ids']),
                uncovered_leaf_ids=coverage['uncovered_leaf_ids'])
    return data


def lifestyle_coverage(cards,branch=None):
    from .selection import topic_index
    nodes=topic_index('生活娱乐')
    leaves=[n for n in nodes if not n['has_children'] and (branch is None or branch in n['path_ids'])]
    direct_nodes={i for card in cards for i in card['node_ids']}
    direct=[n['id'] for n in leaves if n['id'] in direct_nodes]
    inherited=[n['id'] for n in leaves if n['id'] not in direct_nodes and set(n['path_ids'])&direct_nodes]
    covered=set(direct)|set(inherited)
    return {'leaf_count':len(leaves),'directly_covered_leaf_ids':direct,'inherited_covered_leaf_ids':inherited,
            'uncovered_leaf_ids':[n['id'] for n in leaves if n['id'] not in covered],
            'note':'覆盖仅指存在匹配卡，仍须核对卡片条件与本题证据；不是合格题或模型区分度。'}


def topic_matches(branch,node_ids):
    from .selection import topic_node
    selected=topic_node('生活娱乐',branch)
    if not selected:return False
    for node_id in node_ids:
        node=topic_node('生活娱乐',node_id)
        if node and (branch in node['path_ids'] or node_id in selected['path_ids']):return True
    return False


def lifestyle_context(branch=None,limit=8,offset=0,root=None):
    from .selection import topic_node
    require(branch is None or topic_node('生活娱乐',branch) is not None,'生活子方向不合法')
    require(type(limit) is int and 1<=limit<=30 and type(offset) is int and offset>=0,'分页须limit=1..30且offset>=0')
    data=lifestyle_library(root)
    cards=[m for m in data['mechanisms'] if branch is None or topic_matches(branch,m['node_ids'])]
    page=cards[offset:offset+limit];ids={sid for m in page for sid in m['source_ids']}
    return {'domain':'生活娱乐','scope':topic_node('生活娱乐',branch) if branch else None,
            'total':len(cards),'offset':offset,'next_offset':offset+limit if offset+limit<len(cards) else None,
            'mechanism_index':[{'id':m['id'],'title':m['title'],'node_ids':m['node_ids']} for m in cards],
            'mechanisms':page,'sources':[s for s in data['sources'] if s['id'] in ids],
            'coverage':lifestyle_coverage(cards,branch),'public_counts':data['public_counts'],
            'supplement_counts':data['supplement_counts'],
            'acceptance_status':'unvalidated_scenario_seeds',
            'next':'核实原始资料、边界和本地记忆后设计新场景；无匹配或证据不足时由助手先研究，并按相同结构写drafts/lifestyle-supplement.json；不是要求用户补资料或直接复用题库'}


def validate_lifestyle_references(root,q):
    if canonical_domain(q.get('domain'))!=LIFESTYLE:return
    data=lifestyle_library(root);sources={s['id']:s for s in data['sources']};cards={m['id']:m for m in data['mechanisms']}
    selected=q.get('lifestyle_mechanisms',[]);refs=q.get('lifestyle_references',[])
    require(isinstance(selected,list) and selected and all(isinstance(i,str) and i in cards for i in selected),'生活候选须绑定匹配本题的机制卡')
    require(isinstance(refs,list) and refs and all(isinstance(i,str) and i in sources for i in refs),'生活候选须记录已核验来源ID')
    for i in selected:
        card=cards[i]
        require(topic_matches(q.get('subdirection'),card['node_ids']),'机制卡与所选生活子方向不符')
        require(set(card['source_ids'])<=set(refs),'所选机制卡的关联来源须全部核实并记录')
