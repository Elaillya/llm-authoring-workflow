"""Checked public source index and independently written business mechanism cards."""
from pathlib import Path
from .core import read_json, require

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
