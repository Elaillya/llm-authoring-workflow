"""Domain choices and progressive topic scopes, retaining flat legacy branches."""
from pathlib import Path
from .core import active_question, question_domain, read_json, require, write_json
from .domains import canonical_domain,LIFESTYLE

CATALOG=Path(__file__).resolve().parents[1]/'config/domains.json'


def topic_index(domain):
    domain=canonical_domain(domain)
    result=[]
    def visit(nodes,path,labels):
        for node in nodes:
            item={k:v for k,v in node.items() if k!='children'}
            item.update(path_ids=[*path,node['id']],path_labels=[*labels,node['label']],
                        has_children=bool(node.get('children')))
            result.append(item)
            visit(node.get('children',[]),item['path_ids'],item['path_labels'])
    visit(read_json(CATALOG)['domains'].get(domain,[]),[],[])
    return result


def topic_node(domain,branch):
    return next((item for item in topic_index(domain) if item['id']==branch),None)


def new_question_available(domain,branch):
    """Keep historical IDs readable, but exclude disabled branches and descendants."""
    nodes={node['id']:node for node in topic_index(domain)}
    node=nodes.get(branch)
    return bool(node and all(nodes[item].get('new_questions_enabled',True) is not False
                             for item in node['path_ids']))


def is_frozen_prompt(root,q):
    root=Path(root)
    if not (root/'CURRENT.json').exists():return False
    current=active_question(root)['question']
    return q.get('prompt')==current['prompt'] and q.get('subdirection')==current.get('subdirection')


def menu(domain=None,parent=None):
    domains=read_json(CATALOG)['domains']
    if domain is None:return list(domains)
    nodes=topic_index(domain)
    return [node for node in nodes if new_question_available(domain,node['id']) and (len(node['path_ids'])==1 if parent is None
            else len(node['path_ids'])>1 and node['path_ids'][-2]==parent)]


def domain_tree(domain):
    domain=canonical_domain(domain)
    require(domain in menu(),'先选择有效大方向')
    nodes=[node for node in topic_index(domain) if new_question_available(domain,node['id'])]
    return {'domain':domain,'nodes':len(nodes),'topics':nodes,
            'facets':read_json(CATALOG).get('lifestyle_facets',{}) if domain==LIFESTYLE else {},
            'next':'按层询问，也可直接指定细类；确认当前范围可停止细分，不强制到叶节点'}


def choose_subdirection(root,branch,confirm=False):
    root=Path(root);request=read_json(root/'REQUEST.json')
    require(request.get('selection_schema')==2,'旧题请保留原选择；未冻结新题可先升级选题入口')
    domain=canonical_domain(question_domain(root,request));selected=topic_node(domain,branch)
    require(selected is not None,'先选择大方向，再从该方向菜单选择子方向')
    if (root/'CURRENT.json').exists():
        require(active_question(root)['question'].get('subdirection')==branch,'已冻结题目不能更换子方向，请新建题目')
    require(new_question_available(domain,branch) or ((root/'CURRENT.json').exists() and
            active_question(root)['question'].get('subdirection')==branch),
            '该子方向已停止新出题；请选择其他方向，历史题仍可接续返修')
    confirmed=bool(confirm or not selected['has_children'] or
                   (request.get('subdirection')==branch and request.get('subdirection_confirmed') is True))
    request.update(subdirection=branch,subdirection_path=selected['path_ids'],subdirection_confirmed=confirmed)
    write_json(root/'REQUEST.json',request)
    return {'domain':domain,'subdirection':branch,'confirmed':confirmed,'guidance':selected,
            'next':'选择题型，读取本分支指引和本地题库记忆，再由助手生成场景' if confirmed else
                   '询问下一层方向，或确认停在当前范围由助手细分（--confirm）'}


def selection_status(root,request,domain):
    if request.get('selection_schema')!=2:return {},[]
    frozen=(Path(root)/'CURRENT.json').exists()
    branch=active_question(root)['question'].get('subdirection') if frozen else request.get('subdirection')
    selected=topic_node(domain,branch)
    confirmed=bool(selected and (frozen or (new_question_available(domain,branch) and
                   (not selected['has_children'] or request.get('subdirection_confirmed') is True))))
    missing=['subdirection'] if domain is not None and not confirmed and not frozen else []
    field='domain' if domain is None else 'subdirection' if missing else 'question_type' if not request.get('question_type') else None
    path=[{'id':i,'label':label} for i,label in zip(selected['path_ids'],selected['path_labels'])] if selected else []
    return {'domain_choices':menu(),'subdirection':branch,
            'subdirection_choices':menu(domain,parent=branch) if selected and not confirmed and new_question_available(domain,branch) else menu(domain),
            'selection_path':path,'can_confirm_current_scope':bool(selected and selected['has_children'] and not confirmed and new_question_available(domain,branch)),
            'audience_guidance':selected,'next_question':{'field':field,'ask':'先只询问该字段；已有明确选择直接记录'} if field else None},missing


def validate_selection(root,q):
    request=read_json(Path(root)/'REQUEST.json')
    if request.get('selection_schema')!=2:return
    require(request.get('domain_confirmed') is True and canonical_domain(request.get('domain'))==canonical_domain(q.get('domain')),
            '先询问并确认用户选择的领域，候选题目须与选择一致')
    require(request.get('question_type')==q.get('question_type'),
            '先询问并记录用户选择的题型，候选题目须与选择一致')
    require(canonical_domain(q.get('domain')) in menu(),'新题须选择目录中的大方向')
    branch=request.get('subdirection');selected=topic_node(q['domain'],branch)
    require(selected is not None and q.get('subdirection')==branch,'先记录子方向，并让候选题目与该子方向一致')
    require(new_question_available(q['domain'],branch) or is_frozen_prompt(root,q),
            '该子方向已停止新出题；只允许保留同一冻结prompt的历史返修')
    require(not selected['has_children'] or request.get('subdirection_confirmed') is True,
            '当前范围尚未确认：继续细分或明确确认停在本层')


def upgrade_selection(root):
    root=Path(root)
    require(not (root/'CURRENT.json').exists(),'已冻结旧题继续原流程，不能重解释旧题选择')
    request=read_json(root/'REQUEST.json')
    if request.get('selection_schema')==2:return {'already_upgraded':True}
    request.update(selection_schema=2,domain=None,domain_confirmed=False,subdirection=None)
    write_json(root/'REQUEST.json',request)
    return {'requires_input':['domain','subdirection','question_type']}
