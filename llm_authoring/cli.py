import argparse
import json
from pathlib import Path
import sys
from . import VERSION
from .core import ALL_ROLES, Error, ROLES, active_question, freeze, read_json, read_response, require, write_json
from .authoring import check_seed,check_three,evaluation_template,export_authoring,self_review_template
from .providers import collect,recover
from .render import render_response
from .workspace import TOOL_ROOT,begin,choose_type,create_task,create_workspace,locate_workspace,find_authoring_evaluation,update_workspace
from .arena import prepare_arena,import_arena
from .ranking import check_five,export_complete,five_evaluation_template,ranking_template,validate_ranking


def main(argv=None):
    parser=argparse.ArgumentParser(description='完整出题：三模型验证、Arena两份Markdown、五模型考点评估与排序。')
    parser.add_argument('--version',action='version',version=VERSION)
    parser.add_argument('--workspace',type=Path);parser.add_argument('--task',type=Path)
    subs=parser.add_subparsers(dest='command',required=True)
    w=subs.add_parser('workspace-create');w.add_argument('directory',type=Path)
    n=subs.add_parser('new');n.add_argument('id')
    subs.add_parser('start');subs.add_parser('begin');subs.add_parser('status');subs.add_parser('workspace-update');subs.add_parser('arena-import')
    t=subs.add_parser('choose-type');t.add_argument('type',choices=['分析决策类','开放推荐类','How-to类'])
    f=subs.add_parser('freeze');f.add_argument('question',type=Path)
    c=subs.add_parser('collect');c.add_argument('role',choices=ROLES);c.add_argument('--allow-live',action='store_true');c.add_argument('--retry-reason',default='');c.add_argument('--max-output',type=int);c.add_argument('--seed-evaluation',type=Path)
    r=subs.add_parser('recover');r.add_argument('role',choices=ROLES);r.add_argument('attempt',type=Path)
    s=subs.add_parser('render');s.add_argument('role',choices=ROLES)
    for command in ('evaluation-template','self-review-template','seed-evaluation-template'):
        q=subs.add_parser(command);q.add_argument('output',type=Path)
    ch=subs.add_parser('check');ch.add_argument('evaluation',type=Path)
    sc=subs.add_parser('seed-check');sc.add_argument('evaluation',type=Path)
    ap=subs.add_parser('arena-prepare');ap.add_argument('--evaluation',type=Path,required=True)
    fe=subs.add_parser('five-evaluation-template');fe.add_argument('output',type=Path);fe.add_argument('--authoring-evaluation',type=Path,required=True)
    for command in ('five-check','rank'):
        fc=subs.add_parser(command);fc.add_argument('evaluation',type=Path)
    rt=subs.add_parser('ranking-template');rt.add_argument('output',type=Path);rt.add_argument('--evaluation',type=Path,required=True)
    rc=subs.add_parser('ranking-check');rc.add_argument('ranking',type=Path);rc.add_argument('--evaluation',type=Path,required=True)
    for command in ('export','checkpoint'):
        e=subs.add_parser(command);e.add_argument('--evaluation',type=Path,required=True);e.add_argument('--self-review',type=Path,required=True);e.add_argument('--output',type=Path,required=True)
        if command=='export':e.add_argument('--ranking',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='workspace-create':result=create_workspace(args.directory)
        else:
            workspace=args.workspace.absolute() if args.workspace else locate_workspace(args.task or Path.cwd())
            root=args.task.absolute() if args.task else Path.cwd() if (Path.cwd()/'TASK.json').is_file() else workspace/'task'
            require(locate_workspace(root)==workspace,'题目不属于指定工作区')
            config=workspace/'local/providers.json'
            if args.command=='new':result=create_task(workspace,args.id)
            elif args.command=='workspace-update':result=update_workspace(workspace)
            elif args.command=='start':
                print('请在当前题目的Codex侧栏发送：\n\n按 AGENTS.md 使用 llm-authoring-workflow 开始或接续完整出题流程。保留已有题目、三模型原文和判断，按status补齐缺失步骤。新题先让我选择题型，首次提示配置三个模型；计算机科学场景由你生成并核实。Arena阶段创建两份Markdown填写文件，等我贴好回复后继续五模型考点评估、排序及完整交付；Arena截图由我自行提交。\n');return 0
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
            elif args.command=='arena-prepare':result=prepare_arena(root,read_json(args.evaluation))
            elif args.command=='arena-import':result=import_arena(root)
            elif args.command=='five-evaluation-template':
                require(not args.output.exists(),'输出已存在，保留原判断')
                write_json(args.output,five_evaluation_template(root,read_json(args.authoring_evaluation)));result={'output':str(args.output)}
            elif args.command in ('five-check','rank'):result=check_five(root,read_json(args.evaluation))
            elif args.command=='ranking-template':
                require(not args.output.exists(),'输出已存在，保留原排序备注')
                write_json(args.output,ranking_template(root,read_json(args.evaluation)));result={'output':str(args.output)}
            elif args.command=='ranking-check':result=validate_ranking(root,read_json(args.evaluation),read_json(args.ranking))
            elif args.command=='checkpoint':result=export_authoring(root,read_json(args.evaluation),read_json(args.self_review),args.output)
            elif args.command=='export':result=export_complete(root,read_json(args.evaluation),read_json(args.self_review),read_json(args.ranking),args.output)
            elif args.command=='status':
                result=begin(root,workspace)
                if (root/'CURRENT.json').exists():
                    result['revision']=active_question(root)['revision'];result['responses']={}
                    for role in ALL_ROLES:
                        try:r=read_response(root,role);result['responses'][role]={'complete':True,'display_name':r['meta'].get('display_name'),'screenshot':r['meta'].get('screenshot_kind','user_submits_separately' if role not in ROLES else 'missing')}
                        except Error:result['responses'][role]={'complete':False,'status':'evidence_missing_or_incomplete'}
                    result['authoring_evaluation']=str(path) if (path:=find_authoring_evaluation(root)) else None
                    missing=[role for role,value in result['responses'].items() if not value['complete']]
                    result['stage']='collect_three' if any(role in ROLES for role in missing) else 'awaiting_arena_markdown' if missing else 'five_model_evaluation_and_ranking'
                    result['next']='保留已有原件，补齐缺失API回复/截图及三模型判断' if result['stage']=='collect_three' else '已保留三模型；准备或填写Arena两份Markdown文件，截图自行提交' if missing else '统一评估五模型全部考点，生成并校验排序，然后导出新的完整提交版'
                    if (root/'arena-input'/result['revision']).exists():
                        result['arena_input_files']=[str(root/'arena-input'/result['revision']/f'model-{index}.md') for index in (4,5)]
            else:raise Error('未知命令')
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (Error,OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
        print('错误：'+(str(exc) if isinstance(exc,Error) else type(exc).__name__+'；检查路径、JSON和权限，未显示私有配置。'),file=sys.stderr);return 2


if __name__=='__main__':sys.exit(main())
