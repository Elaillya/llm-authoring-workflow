import argparse
import json
from pathlib import Path
import sys
from . import VERSION
from .core import Error, ROLES, active_question, freeze, read_json, read_response, require, write_json
from .authoring import check_seed,check_three,evaluation_template,export_authoring,self_review_template
from .providers import collect,recover
from .render import render_response
from .workspace import TOOL_ROOT,begin,choose_type,create_task,create_workspace,locate_workspace


def main(argv=None):
    parser=argparse.ArgumentParser(description='第一轮出题：题型选择、三模型验证、自查、截图及交接。')
    parser.add_argument('--version',action='version',version=VERSION)
    parser.add_argument('--workspace',type=Path);parser.add_argument('--task',type=Path)
    subs=parser.add_subparsers(dest='command',required=True)
    w=subs.add_parser('workspace-create');w.add_argument('directory',type=Path)
    n=subs.add_parser('new');n.add_argument('id')
    subs.add_parser('start');subs.add_parser('begin');subs.add_parser('status')
    t=subs.add_parser('choose-type');t.add_argument('type',choices=['分析决策类','开放推荐类','How-to类'])
    f=subs.add_parser('freeze');f.add_argument('question',type=Path)
    c=subs.add_parser('collect');c.add_argument('role',choices=ROLES);c.add_argument('--allow-live',action='store_true');c.add_argument('--retry-reason',default='');c.add_argument('--max-output',type=int);c.add_argument('--seed-evaluation',type=Path)
    r=subs.add_parser('recover');r.add_argument('role',choices=ROLES);r.add_argument('attempt',type=Path)
    s=subs.add_parser('render');s.add_argument('role',choices=ROLES)
    for command in ('evaluation-template','self-review-template','seed-evaluation-template'):
        q=subs.add_parser(command);q.add_argument('output',type=Path)
    ch=subs.add_parser('check');ch.add_argument('evaluation',type=Path)
    sc=subs.add_parser('seed-check');sc.add_argument('evaluation',type=Path)
    e=subs.add_parser('export');e.add_argument('--evaluation',type=Path,required=True);e.add_argument('--self-review',type=Path,required=True);e.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='workspace-create':result=create_workspace(args.directory)
        else:
            workspace=args.workspace.absolute() if args.workspace else locate_workspace(args.task or Path.cwd())
            root=args.task.absolute() if args.task else Path.cwd() if (Path.cwd()/'TASK.json').is_file() else workspace/'task'
            require(locate_workspace(root)==workspace,'题目不属于指定工作区')
            config=workspace/'local/providers.json'
            if args.command=='new':result=create_task(workspace,args.id)
            elif args.command=='start':
                print('请在当前题目的Codex侧栏发送：\n\n按 AGENTS.md 使用 llm-authoring-workflow 开始第一轮出题。先让我选择题型；首次使用时提示填写三个模型配置。计算机科学场景、问题、事实和限制由你生成并核实。完成三模型验证后导出出题交接包。\n');return 0
            elif args.command=='begin':result=begin(root,workspace)
            elif args.command=='choose-type':result=choose_type(root,args.type)
            elif args.command=='freeze':
                require(begin(root,workspace)['ready'],'先选题型并完成三个模型配置，再设计与冻结')
                result=freeze(root,read_json(args.question))
            elif args.command=='collect':
                if args.max_output is not None:require(args.max_output>0,'max-output 必须大于零')
                if args.role!='seed':
                    probe=args.seed_evaluation or root/'evaluations'/('seed-'+active_question(root)['revision']+'.json')
                    require(probe.is_file(),'先完成当前候选的Turbo决定性考点判断，再调用GPT/Claude')
                    require(check_seed(root,read_json(probe))['continue_to_gpt_claude'],'Turbo已达成全部决定性点，先修订候选，暂不调用GPT/Claude')
                result=collect(root,config,args.role,allow_live=args.allow_live,retry_reason=args.retry_reason,max_output=args.max_output)
            elif args.command=='recover':result=recover(root,config,args.role,args.attempt)
            elif args.command=='render':
                runtime=read_json(workspace/'local/runtime.json');result=render_response(root,args.role,runtime['assets'],runtime['browsers'])
            elif args.command in ('evaluation-template','self-review-template','seed-evaluation-template'):
                require(not args.output.exists(),'输出已存在，拒绝覆盖判断或自查')
                value=self_review_template(root) if args.command=='self-review-template' else evaluation_template(root,('seed',) if args.command=='seed-evaluation-template' else ROLES)
                write_json(args.output,value);result={'output':str(args.output)}
            elif args.command=='seed-check':result=check_seed(root,read_json(args.evaluation))
            elif args.command=='check':result=check_three(root,read_json(args.evaluation))
            elif args.command=='export':result=export_authoring(root,read_json(args.evaluation),read_json(args.self_review),args.output)
            elif args.command=='status':
                result=begin(root,workspace)
                if (root/'CURRENT.json').exists():
                    result['revision']=active_question(root)['revision'];result['responses']={}
                    for role in ROLES:
                        try:r=read_response(root,role);result['responses'][role]={'complete':True,'screenshot':r['meta'].get('screenshot_kind','missing')}
                        except Error:result['responses'][role]={'complete':False,'status':'evidence_missing_or_incomplete'}
            else:raise Error('未知命令')
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (Error,OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
        print('错误：'+(str(exc) if isinstance(exc,Error) else type(exc).__name__+'；检查路径、JSON和权限，未显示私有配置。'),file=sys.stderr);return 2


if __name__=='__main__':sys.exit(main())
