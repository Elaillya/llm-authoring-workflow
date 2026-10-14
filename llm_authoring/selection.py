"""Two broad domains and audience-specific branches for new questions."""
from pathlib import Path
from .core import active_question, question_domain, read_json, require, write_json

CATALOG=Path(__file__).resolve().parents[1]/'config/domains.json'


def menu(domain=None):
    domains=read_json(CATALOG)['domains']
    return domains.get(domain,[]) if domain is not None else list(domains)


def choose_subdirection(root,branch):
    root=Path(root);request=read_json(root/'REQUEST.json')
    require(request.get('selection_schema')==2,'旧题请保留原选择；未冻结新题可先升级选题入口')
    domain=question_domain(root,request)
    selected=next((item for item in menu(domain) if item['id']==branch),None) if domain else None
    require(selected is not None,'先选择计算机科学或商科，再从该方向菜单选择子方向')
    if (root/'CURRENT.json').exists():
        require(active_question(root)['question'].get('subdirection')==branch,'已冻结题目不能更换子方向，请新建题目')
    request['subdirection']=branch;write_json(root/'REQUEST.json',request)
    return {'domain':domain,'subdirection':branch,'guidance':selected,'next':'选择题型，读取本分支指引和本地题库记忆，再由助手生成场景'}


def selection_status(root,request,domain):
    if request.get('selection_schema')!=2:
        return {},[]
    frozen=(Path(root)/'CURRENT.json').exists()
    branch=active_question(root)['question'].get('subdirection') if frozen else request.get('subdirection')
    choices=menu(domain) if domain in menu() else []
    selected=next((item for item in choices if item['id']==branch),None)
    missing=[]
    if domain is not None and selected is None and not frozen:missing.append('subdirection')
    field='domain' if domain is None else 'subdirection' if missing else 'question_type' if not request.get('question_type') else None
    return {'domain_choices':menu(),'subdirection':branch,'subdirection_choices':choices,
            'audience_guidance':selected,'next_question':{'field':field,'ask':'先只询问该字段；已有明确选择直接记录'} if field else None},missing


def validate_selection(root,q):
    request=read_json(Path(root)/'REQUEST.json')
    if request.get('selection_schema')!=2:return
    require(request.get('domain_confirmed') is True and request.get('domain')==q.get('domain'),
            '先询问并确认用户选择的领域，候选题目须与选择一致')
    require(request.get('question_type')==q.get('question_type'),
            '先询问并记录用户选择的题型，候选题目须与选择一致')
    require(q.get('domain') in menu(),'新题方向须为计算机科学或商科')
    branch=request.get('subdirection')
    require(branch in {item['id'] for item in menu(q['domain'])} and q.get('subdirection')==branch,
            '先记录子方向，并让候选题目与该子方向一致')


def upgrade_selection(root):
    root=Path(root)
    require(not (root/'CURRENT.json').exists(),'已冻结旧题继续原流程，不能重解释旧题选择')
    request=read_json(root/'REQUEST.json')
    if request.get('selection_schema')==2:return {'already_upgraded':True}
    request.update(selection_schema=2,domain=None,domain_confirmed=False,subdirection=None)
    write_json(root/'REQUEST.json',request)
    return {'requires_input':['domain','subdirection','question_type']}
