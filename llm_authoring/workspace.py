"""Portable source toolkit and private question workspaces have separate roots."""
import os
from pathlib import Path
import subprocess
from . import VERSION
from .core import Error, NAMES, TYPES, read_json, require, write_json
from .providers import load_provider, make_payload

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
    write_json(root/'TASK.json',{'schema_version':1,'workflow':'llm-authoring','task_id':task_id})
    write_json(root/'REQUEST.json',{'schema_version':1,'domain':'计算机科学','question_type':None,'scenario_generation':'assistant_sourced'})
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


def workspace_file(folder,label,workspace):
    return {'folders':[{'name':label,'path':folder}], 'extensions':{'recommendations':['openai.chatgpt']},
            'tasks':{'version':'2.0.0','tasks':[{'label':'出题：侧栏开始指令','type':'process','command':str(Path(workspace)/'bin/lab'),
                    'args':['--task','${workspaceFolder}','start'],'problemMatcher':[]}]}}


def create_workspace(destination,tool=TOOL_ROOT,runtime=None):
    root=Path(destination).absolute();tool=Path(tool).resolve()
    require(not root.exists(),'工作区目录已存在，拒绝覆盖题目或私有配置')
    root.mkdir(parents=True);local=root/'local';local.mkdir(mode=0o700)
    config=local/'providers.json'
    with config.open('x',encoding='utf-8') as f:
        os.chmod(config,0o600);f.write((tool/'config/providers.example.json').read_text())
    runtime=runtime or {'python':str(tool/'.venv/bin/python'),'browsers':str(tool/'.browsers'),'assets':str(tool/'.assets')}
    write_json(local/'runtime.json',runtime)
    write_json(root/'.authoring-workspace.json',{'schema_version':1,'workflow':'llm-authoring','toolkit_root':str(tool),'version':VERSION})
    (root/'bin').mkdir()
    launcher='#!/usr/bin/env python3\nimport json,os,sys\nfrom pathlib import Path\nroot=Path(__file__).resolve().parents[1]\n'+\
             'runtime=json.loads((root/"local/runtime.json").read_text())\nmarker=json.loads((root/".authoring-workspace.json").read_text())\n'+\
             'exe=Path(runtime["python"])\nif not exe.is_file():\n print("首次使用：请让侧栏运行工具仓 scripts/setup.py，准备依赖环境。",file=sys.stderr);sys.exit(2)\n'+\
             'os.execv(str(exe),[str(exe),str(Path(marker["toolkit_root"])/"scripts/lab.py"),"--workspace",str(root),*sys.argv[1:]])\n'
    (root/'bin/lab').write_text(launcher);(root/'bin/lab').chmod(0o755)
    write_json(root/'Authoring.code-workspace',workspace_file('task','第一轮出题',root))
    (root/'README.md').write_text(f'# 第一轮出题工作区\n\n打开 Authoring.code-workspace，在Codex侧栏发送“按AGENTS.md开始第一轮出题”。\n首次使用请填写 local/providers.json。题目类型每次由你选择，计算机科学场景由助手生成。\n\n工具说明：{tool}/README.md\n')
    result=create_task(root,'question-001',root/'task')
    return {'workspace':str(root),'workspace_file':str(root/'Authoring.code-workspace'),'providers_file':str(config),'first_task':result}


def choose_type(root,question_type):
    require(question_type in TYPES,'题型须是分析决策类、开放推荐类或How-to类')
    file=Path(root)/'REQUEST.json';request=read_json(file)
    if request.get('question_type') and request['question_type']!=question_type:
        require(not (Path(root)/'CURRENT.json').exists(),'已有冻结题目，改题型请新建题目，保留旧题返修来源')
    request['question_type']=question_type;write_json(file,request)
    return {'question_type':question_type,'domain':'计算机科学','next':'由助手生成问题、关键事实及限制并核实来源'}


def begin(root,workspace):
    root=Path(root);workspace=Path(workspace)
    request=read_json(root/'REQUEST.json');config=workspace/'local/providers.json';models={}
    for role in NAMES:
        try:
            provider=load_provider(config,role);make_payload(provider,'配置检查，不发送')
            models[role]={'display_name':NAMES[role],'configuration':'ready'}
        except (Error,ValueError,TypeError,KeyError,AttributeError,OSError):models[role]={'display_name':NAMES[role],'configuration':'needs_configuration'}
    needs=[]
    if request.get('question_type') not in TYPES:needs.append('question_type')
    if any(m['configuration']!='ready' for m in models.values()):needs.append('model_configuration')
    return {'phase':'authoring','domain':'计算机科学','question_type':request.get('question_type'),'question_type_choices':list(TYPES),
            'models':models,'configuration_file':str(config),'requires_input':needs,'ready':not needs,
            'scenario_owner':'assistant','next':'先询问题型并提示缺失模型配置，其他场景内容由助手生成' if needs else '按已选题型自动生成并核实计算机科学场景'}
