"""Explicit per-task choice for the two post-model platform checks."""
from pathlib import Path
import re,time,uuid
from .core import Error,now,hash_json,read_json,require,write_json
from .memory import task_key

CHOICES=('required','skipped')
ASK='是否进行考点质检和达成性质检？选择需要则按原流程并行检查，选择不需要则本题后续跳过这两项；题目难度与标签检查和三模型达成性要求保持。'


def current(root):
    root=Path(root)
    if not (root/'TASK.json').is_file():return {'choice':'legacy','configured':True}
    task=read_json(root/'TASK.json')
    if task.get('platform_checks_required') is not True:return {'choice':'legacy','configured':True}
    pointer=task.get('model_checks_choice')
    if pointer is None:return {'choice':None,'configured':False,'ask':ASK}
    require(isinstance(pointer,dict) and isinstance(pointer.get('record'),str)
            and re.fullmatch(r'model-check-choice-\d+-[a-f0-9]{8}\.json',pointer['record']),'后两项质检选择记录不合法')
    directory=root/'platform-checks';require(not directory.is_symlink(),'质检选择目录不能为符号链接')
    file=directory/pointer['record'];value=read_json(file)
    require(hash_json(value)==pointer.get('sha256') and value.get('schema_version')==1
            and value.get('phase')=='model_checks_choice' and value.get('task_key')==task_key(root)
            and value.get('choice') in CHOICES and isinstance(value.get('user_note'),str)
            and value['user_note'].strip(),'后两项质检选择绑定已改变，先核对用户实际答复')
    return {'choice':value['choice'],'configured':True,'record':str(file),'decision_sha256':hash_json(value)}


def require_choice(root):
    result=current(root)
    require(result['configured'],'先询问用户是否进行考点质检和达成性质检，收到明确答复后用choose-model-checks记录；不能自行决定')
    return result


def choose(root,choice,user_note):
    require(choice in CHOICES,'请选择required（需要）或skipped（不需要）')
    require(isinstance(user_note,str) and user_note.strip(),'记录用户本次明确答复，不能把没有回复当作同意')
    root=Path(root).resolve()
    from .platform_checks import check_lock
    with check_lock(root):
        previous=current(root);require(previous['choice']!='legacy','旧合同未启用平台质检，不修改其质检策略')
        if previous['choice']==choice and read_json(previous['record'])['user_note']==user_note:return previous
        value={'schema_version':1,'phase':'model_checks_choice','task_key':task_key(root),
               'choice':choice,'user_note':user_note,'decided_at':now()}
        name=f'model-check-choice-{time.time_ns()}-{uuid.uuid4().hex[:8]}.json'
        write_json(root/'platform-checks'/name,value)
        task=read_json(root/'TASK.json');task['model_checks_choice']={'record':name,'sha256':hash_json(value)}
        write_json(root/'TASK.json',task)
    return current(root)


def prompt(root):
    """Ask at the Seed-to-GPT/Claude transition, including resumed tasks."""
    policy=current(root)
    if policy['configured'] or not (Path(root)/'CURRENT.json').is_file():return None
    from .manual import seed_screen
    try:seed_screen(root)
    except (Error,OSError,ValueError,KeyError,TypeError):return None
    return {'field':'model_checks_choice','ask':ASK,'choices':['需要','不需要']}


def skipped(root,stage):
    policy=require_choice(root);require(policy['choice']=='skipped','未选择跳过后两项质检')
    require(stage in ('criteria','attainment'),'仅考点与达成性质检可跳过')
    return {'state':'skipped_by_user','accepted':False,'required':False,'stage':stage,
            'server_conclusion':None,'feedback':'用户明确选择不执行，本项未请求平台，不代表质检通过。',
            'choice_record':policy['record'],'choice_sha256':policy['decision_sha256']}
