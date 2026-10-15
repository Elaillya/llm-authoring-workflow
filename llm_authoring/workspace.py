"""Portable source toolkit and private question workspaces have separate roots."""
import os
import re
import shutil
import tempfile
from pathlib import Path
import subprocess
import uuid
from . import VERSION
from .core import Error, NAMES, TYPES, active_question, question_domain, read_json, require, write_json

TOOL_ROOT=Path(__file__).resolve().parents[1]


def locate_workspace(path):
    path=Path(path).absolute()
    for parent in (path,*path.parents):
        marker=parent/'.authoring-workspace.json'
        if marker.is_file():
            require(read_json(marker).get('workflow')=='llm-authoring','工作区类型不匹配')
            return parent
    raise Error('尚未建立出题工作区；先运行 scripts/lab.py workspace-create <新目录>')


def create_task(workspace,task_id,destination=None):
    import re
    workspace=Path(workspace).resolve();tool=Path(read_json(workspace/'.authoring-workspace.json')['toolkit_root'])
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}',task_id),'题目ID不合法')
    root=Path(destination).absolute() if destination else workspace/'tasks'/task_id
    require(not root.exists(),'题目目录已存在，保留原件，请用新ID')
    root.mkdir(parents=True)
    for name in ('AGENTS.md','INPUTS.md','WORKLOG.md','.gitignore'):
        content=(tool/'templates'/name).read_text().replace('{{TASK_ID}}',task_id).replace('{{WORKSPACE_ROOT}}',str(workspace)).replace('{{TOOL_ROOT}}',str(tool))
        (root/name).write_text(content)
    write_json(root/'TASK.json',{'schema_version':1,'workflow':'llm-authoring','task_id':task_id,'response_mode':'official_manual','memory_id':str(uuid.uuid4()),'platform_checks_required':True})
    write_json(root/'REQUEST.json',{'schema_version':1,'selection_schema':2,'domain':None,'domain_confirmed':False,'subdirection':None,'question_type':None,'scenario_generation':'assistant_sourced'})
    for name in ('materials','drafts','evaluations','delivery'):(root/name).mkdir()
    q=read_json(tool/'templates/question.json');q['task_id']=task_id;write_json(root/'drafts/question.json',q)
    # Copy the small Skill so sidebar discovery works without platform-specific symlinks.
    import shutil
    skill=root/'.agents/skills/llm-authoring-workflow';skill.parent.mkdir(parents=True)
    shutil.copytree(tool/'skills/llm-authoring-workflow',skill)
    (root/'TOOLKIT.md').write_text(f'# 工具入口\n\n源码：{tool}\n工作区：{workspace}\n命令：{workspace}/bin/lab\n工具版本：{VERSION}\n')
    subprocess.run(['git','init','-q',str(root)],check=True)
    file=root/(task_id+'.code-workspace')
    write_json(file,workspace_file('.',task_id,workspace))
    return {'task':str(root),'workspace_file':str(file)}


def default_task(workspace):
    workspace=Path(workspace).resolve()
    path=Path(read_json(workspace/'.authoring-workspace.json').get('default_task','task'))
    require(not path.is_absolute() and '..' not in path.parts,'默认题目路径不合法')
    return workspace/path


def rename_task(workspace,root,label):
    """Rename the visible task while preserving frozen IDs and legacy paths."""
    workspace=Path(workspace).resolve();root=Path(root).resolve()
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}',label),'题目名称不合法')
    require(root!=workspace and root.is_relative_to(workspace),'题目不属于工作区')
    task=read_json(root/'TASK.json')
    require(task.get('workflow')=='llm-authoring','题目工作流类型不匹配')
    destination=workspace/'tasks'/label
    require(not destination.exists() and not destination.is_symlink(),'题目目录已存在，拒绝覆盖')
    require(not destination.parent.is_symlink(),'题目父目录不能为符号链接')
    marker=read_json(workspace/'.authoring-workspace.json')
    tool=Path(marker['toolkit_root'])
    content=(tool/'templates/AGENTS.md').read_text().replace('{{TASK_ID}}',label).replace('{{WORKSPACE_ROOT}}',str(workspace)).replace('{{TOOL_ROOT}}',str(tool))
    old_name=task.get('display_id',task['task_id'])+'.code-workspace'
    new_name=label+'.code-workspace'
    old=root/old_name;new=root/new_name
    require(old==new or not (new.exists() or new.is_symlink()),'目标窗口文件已存在，拒绝覆盖')
    window=read_json(old) if old.exists() else workspace_file('.',label,workspace)
    for folder in window.get('folders',[]):
        if (root/folder['path']).resolve()==root:folder['name']=label
    primary=default_task(workspace).resolve()==root
    old_files={}
    for file in workspace.glob('*.code-workspace'):
        old_files[file]=read_json(file)
    backup=Path(tempfile.mkdtemp(prefix='rename-'+label+'-',dir=workspace/'local'))
    originals={p:(p.read_bytes(),p.stat().st_mode&0o777) for p in
               [root/'TASK.json',root/'AGENTS.md',old,workspace/'.authoring-workspace.json',*old_files] if p.exists()}
    for p,(data,mode) in originals.items():
        saved=backup/p.relative_to(workspace);saved.parent.mkdir(parents=True,exist_ok=True)
        saved.write_bytes(data);saved.chmod(mode)
    destination.parent.mkdir(exist_ok=True)
    root.rename(destination)
    try:
        # An old conversation can still access its original cwd through this alias.
        root.symlink_to(os.path.relpath(destination,root.parent),target_is_directory=True)
        task['display_id']=label;write_json(destination/'TASK.json',task)
        if primary:
            marker['default_task']=destination.relative_to(workspace).as_posix()
            write_json(workspace/'.authoring-workspace.json',marker)
        for file,value in old_files.items():
            for folder in value.get('folders',[]):
                if (file.parent/folder['path']).resolve()==destination:
                    folder.update({'name':label,'path':os.path.relpath(destination,file.parent)})
            write_json(file,value)
        if (destination/old_name).exists() and old_name!=new_name:
            (destination/old_name).rename(destination/new_name)
        file=destination/new_name
        write_json(file,window)
        (destination/'AGENTS.md').write_text(content)
    except BaseException:
        # Only these small instruction/identity files are ever written by rename.
        if old_name!=new_name:(destination/new_name).unlink(missing_ok=True)
        for p,(data,mode) in originals.items():
            target=destination/p.relative_to(root) if p.is_relative_to(root) else p
            target.write_bytes(data);target.chmod(mode)
        if root.is_symlink() and root.resolve()==destination:root.unlink()
        destination.rename(root)
        raise
    return {'task':str(destination),'workspace_file':str(file),'display_id':label,
            'frozen_task_id':task['task_id'],'legacy_path':str(root),'instructions_backup':str(backup)}


def workspace_file(folder,label,workspace):
    return {'folders':[{'name':label,'path':folder}], 'extensions':{'recommendations':['openai.chatgpt']},
            'tasks':{'version':'2.0.0','tasks':[{'label':'出题：侧栏开始指令','type':'process','command':str(Path(workspace)/'bin/lab'),
                    'args':['--task','${workspaceFolder}','start'],'problemMatcher':[]}]}}


def workspace_readme(tool):
    return (f'# 出题与五模型排序工作区\n\n打开 Authoring.code-workspace，在Codex侧栏发送“按AGENTS.md开始或接续完整出题流程”。\n'
            '新题先选计算机科学或商科，再选子方向与题型；助手读本地题库并核实自然表达和跨题差异，生成实际场景，不需要模型API配置。Insight灵活组织并突出决定性因素，考点精简背景且独立可判定。\n'
            '同项目质检配置已随工具仓提供，缺少时自动导入；仅在需要时填写自己的Cookie，无需HAR或另找service.json，已有私有配置保留。\n'
            'prompt与Insight后先做平台难度标签检查，通过后再冻结。三模型原文、判断及备注齐备后先确认Seed未全部决定性达成且GPT或Claude至少一个全部达成，再并行质检考点和达成性；GPT/Claude都未达成则保留失败并重选新prompt，不调用后两项质检。正常请求等待至完成；合理不通过返修，错误意见给异议备注。先发Arena链接，再离线处理三项通过的表达建议，优化后免复检；Cookie按需填已有私有文件。\n'
            '发给五模型的文字严格等于冻结prompt，不追加格式要求。冻结后先填写Seed的Markdown；判断其未达成全部决定性点后，再填写GPT和Claude的Markdown。\n'
            'Arena阶段填写工具创建的另两份Markdown；全部模型的官方页面截图由你单独提交。\n'
            '交付为一份纯文本提交信息和五份按模型名称命名的原Markdown；排序用真实名称，备注简洁说明考点差异和原因，不设字数下限。\n'
            f'新题运行 bin/lab new <编号>，每道题打开自己的code-workspace文件。\n\n工具说明：{tool}/README.md\n')


def create_workspace(destination,tool=TOOL_ROOT,runtime=None):
    root=Path(destination).absolute();tool=Path(tool).resolve()
    require(not root.exists(),'工作区目录已存在，拒绝覆盖题目或私有配置')
    root.mkdir(parents=True);local=root/'local';local.mkdir(mode=0o700)
    runtime=runtime or {'python':str(tool/'.venv/bin/python'),'browsers':str(tool/'.browsers'),'assets':str(tool/'.assets')}
    write_json(local/'runtime.json',runtime)
    write_json(root/'.authoring-workspace.json',{'schema_version':1,'workflow':'llm-authoring','toolkit_root':str(tool),'version':VERSION})
    (root/'bin').mkdir()
    launcher='#!/usr/bin/env python3\nimport json,os,sys\nfrom pathlib import Path\nroot=Path(__file__).resolve().parents[1]\n'+\
             'runtime=json.loads((root/"local/runtime.json").read_text())\nmarker=json.loads((root/".authoring-workspace.json").read_text())\n'+\
             'exe=Path(runtime["python"])\nif not exe.is_file():\n print("首次使用：请让侧栏运行工具仓 scripts/setup.py，准备依赖环境。",file=sys.stderr);sys.exit(2)\n'+\
             'os.execv(str(exe),[str(exe),str(Path(marker["toolkit_root"])/"scripts/lab.py"),"--workspace",str(root),*sys.argv[1:]])\n'
    (root/'bin/lab').write_text(launcher);(root/'bin/lab').chmod(0o755)
    write_json(root/'Authoring.code-workspace',workspace_file('task','出题与五模型排序',root))
    (root/'README.md').write_text(workspace_readme(tool))
    result=create_task(root,'question-001',root/'task')
    return {'workspace':str(root),'workspace_file':str(root/'Authoring.code-workspace'),'response_mode':'official_manual','first_task':result}


def choose_type(root,question_type):
    require(question_type in TYPES,'题型须是分析决策类、开放推荐类或How-to类')
    file=Path(root)/'REQUEST.json';request=read_json(file)
    if request.get('question_type') and request['question_type']!=question_type:
        require(not (Path(root)/'CURRENT.json').exists(),'已有冻结题目，改题型请新建题目，保留旧题返修来源')
    request['question_type']=question_type;write_json(file,request)
    return {'question_type':question_type,'domain':question_domain(root,request),'next':'按用户选择的领域生成问题、关键事实及限制并核实来源'}


def choose_domain(root,domain):
    require(isinstance(domain,str) and domain.strip(),'请输入非空的专业领域名称')
    domain=domain.strip();root=Path(root)
    file=root/'REQUEST.json';request=read_json(file)
    if request.get('selection_schema')==2 and not (root/'CURRENT.json').is_file():
        from .selection import menu
        require(domain in menu(),'请选择计算机科学或商科')
        if request.get('domain')!=domain:request['subdirection']=None
    if (root/'CURRENT.json').is_file():
        require(domain==question_domain(root,request),'已有冻结题目，改领域请新建题目，保留旧题返修来源')
    request.update({'domain':domain,'domain_confirmed':True});write_json(file,request)
    return {'domain':domain,'next':'从该方向菜单询问子方向，再记录题型；已有选择直接记录，不要求用户提供场景或事实'}


def begin(root,workspace):
    root=Path(root);workspace=Path(workspace)
    request=read_json(root/'REQUEST.json')
    models={role:{'display_name':name,'input':'user_provided_markdown'} for role,name in NAMES.items()}
    needs=[]
    domain=question_domain(root,request)
    if domain is None:needs.append('domain')
    from .selection import selection_status
    selection,missing=selection_status(root,request,domain);needs.extend(missing)
    if request.get('question_type') not in TYPES:needs.append('question_type')
    memory=None
    if request.get('selection_schema')==2 and not needs:
        from .memory import context
        memory=context(root,workspace,6)
    return {'phase':'authoring','domain':domain,'question_type':request.get('question_type'),'question_type_choices':list(TYPES),
            **selection,'memory_context':memory,'models':models,'response_mode':'official_manual','requires_input':needs,'ready':not needs,
            'scenario_owner':'assistant','next':'按next_question先选计算机科学或商科，再选子方向与题型；场景和专业资料由助手生成核实' if needs else
            '已有冻结题目，运行status查看缺失材料并接续，不重跑已完成模型' if (root/'CURRENT.json').exists() else '按已选领域和题型自动生成并核实场景'}


def find_authoring_evaluation(root,*,require_gate=True):
    from .authoring import check_three
    root=Path(root)
    if not (root/'CURRENT.json').exists():return None
    current=active_question(root)
    standard=root/'evaluations'/('three-'+current['revision']+'.json')
    candidates=[standard]+sorted((root/'evaluations').glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
    for path in dict.fromkeys(candidates):
        if not path.is_file():continue
        try:
            checked=check_three(root,read_json(path))
            if not require_gate or checked['three_model_gate']:return path
        except (Error,ValueError,TypeError,KeyError,AttributeError,OSError):continue
    return None


def update_workspace(workspace,tool=TOOL_ROOT):
    """Update only sidebar instructions and the toolkit binding; retain task evidence."""
    workspace=Path(workspace).resolve();tool=Path(tool).resolve()
    marker=read_json(workspace/'.authoring-workspace.json')
    require(marker.get('workflow')=='llm-authoring','工作区类型不匹配')
    candidates=[workspace/'task']+sorted((workspace/'tasks').glob('*'))
    tasks=[]
    for root in candidates:
        if root.is_symlink() or not (root/'TASK.json').is_file():continue
        require(not root.is_symlink() and root.resolve().is_relative_to(workspace),'题目路径不能逃逸工作区')
        task=read_json(root/'TASK.json')
        require(task.get('workflow')=='llm-authoring','题目工作流类型不匹配')
        tasks.append((root,task.get('display_id',task['task_id'])))
    require(tasks,'工作区没有可接续的题目')
    backup=Path(tempfile.mkdtemp(prefix='workflow-'+VERSION+'-',dir=workspace/'local'))
    for name in ('.authoring-workspace.json','Authoring.code-workspace','README.md'):
        if (workspace/name).is_file():shutil.copy2(workspace/name,backup/name)
    updated=[]
    for root,task_id in tasks:
        saved=backup/root.relative_to(workspace);saved.mkdir(parents=True,exist_ok=True)
        for name in ('AGENTS.md','TOOLKIT.md','WORKLOG.md','.gitignore'):
            path=root/name
            require(not path.is_symlink(),'接续说明文件不能为符号链接')
            if path.exists():shutil.copy2(path,saved/name)
        skill=root/'.agents/skills/llm-authoring-workflow'
        require(not skill.is_symlink() and skill.resolve().is_relative_to(root.resolve()),'工作区Skill不能为符号链接或逃逸题目目录')
        if skill.exists():shutil.copytree(skill,saved/'skill')
        content=(tool/'templates/AGENTS.md').read_text().replace('{{TASK_ID}}',task_id).replace('{{WORKSPACE_ROOT}}',str(workspace)).replace('{{TOOL_ROOT}}',str(tool))
        (root/'AGENTS.md').write_text(content)
        shutil.copytree(tool/'skills/llm-authoring-workflow',skill,dirs_exist_ok=True)
        (root/'TOOLKIT.md').write_text(f'# 工具入口\n\n源码：{tool}\n工作区：{workspace}\n命令：{workspace}/bin/lab\n工具版本：{VERSION}\n')
        ignore=root/'.gitignore';old_ignore=ignore.read_text() if ignore.exists() else ''
        for entry in ('arena-input/','model-input/'):
            if entry not in old_ignore.splitlines():old_ignore=old_ignore.rstrip()+'\n'+entry+'\n'
        ignore.write_text(old_ignore)
        log=root/'WORKLOG.md';previous=log.read_text() if log.exists() else ''
        banner=f'## 当前工作流：{VERSION} 完整出题与五模型排序'
        if banner not in previous:
            log.write_text(banner+'\n\n已保留原题、三模型原件、判断、截图与旧交付。历史记录中的上下轮分工已由当前流程替代。'
                           '当前仅接收用户提供的Markdown：先Seed判断，再GPT/Claude，再Arena与排序；所有网页截图另行提交。使用新的交付版号。\n\n---\n\n'+previous)
        evaluation=find_authoring_evaluation(root)
        arena=None
        if evaluation:
            from .arena import prepare_arena
            arena=prepare_arena(root,read_json(evaluation))
        updated.append({'task':str(root),'preserved_existing_question':(root/'CURRENT.json').exists(),
                        'authoring_evaluation':str(evaluation) if evaluation else None,'arena':arena})
    marker.update({'toolkit_root':str(tool),'version':VERSION});write_json(workspace/'.authoring-workspace.json',marker)
    (workspace/'README.md').write_text(workspace_readme(tool))
    file=workspace/'Authoring.code-workspace'
    if file.exists():
        value=read_json(file)
        for folder in value.get('folders',[]):
            if folder.get('name')=='第一轮出题':folder['name']='出题与五模型排序'
        write_json(file,value)
    return {'workflow_version':VERSION,'tasks':updated,'instructions_backup':str(backup),
            'preserved':'题型、题面、Insight、考点、三模型结果、自查、旧交付、私有配置与运行环境',
            'next':'打开原工作区，运行status；保留原件，缺少回复时按Seed筛查顺序创建Markdown填写文件，再继续Arena与排序'}
