import argparse
import json
from pathlib import Path
import sys
from . import VERSION
from .core import ALL_ROLES, Error, ROLES, active_question, freeze, read_json, read_response, require, write_json
from .authoring import check_seed,check_three,evaluation_template,export_authoring,self_review_template
from .providers import collect,recover
from .render import render_response
from .workspace import TOOL_ROOT,begin,choose_domain,choose_type,create_task,create_workspace,default_task,locate_workspace,find_authoring_evaluation,rename_task,update_workspace
from .arena import prepare_arena,import_arena
from .manual import prepare_model,import_model,manual_status
from .ranking import check_five,export_complete,five_evaluation_template,ranking_template,validate_ranking
from .selection import choose_subdirection,upgrade_selection
from .memory import context as memory_context,sync as memory_sync,show as memory_show,transaction,remember,STATUSES
from .quality import candidate_check,review_template,reserve
from .references import business_context
from . import platform_checks as qa
from . import platform_client
from . import platform_polish


def main(argv=None):
    parser=argparse.ArgumentParser(description='完整出题：三模型验证、Arena两份Markdown、五模型考点评估与排序。')
    parser.add_argument('--version',action='version',version=VERSION)
    parser.add_argument('--workspace',type=Path);parser.add_argument('--task',type=Path)
    subs=parser.add_subparsers(dest='command',required=True)
    w=subs.add_parser('workspace-create');w.add_argument('directory',type=Path)
    n=subs.add_parser('new');n.add_argument('id')
    rn=subs.add_parser('rename');rn.add_argument('name')
    subs.add_parser('start');subs.add_parser('begin');subs.add_parser('status');subs.add_parser('workspace-update')
    ai=subs.add_parser('arena-import');ai.add_argument('--evaluation',type=Path)
    t=subs.add_parser('choose-type');t.add_argument('type',choices=['分析决策类','开放推荐类','How-to类'])
    d=subs.add_parser('choose-domain');d.add_argument('domain')
    sd=subs.add_parser('choose-subdirection');sd.add_argument('branch')
    subs.add_parser('selection-upgrade');subs.add_parser('memory-sync')
    mc=subs.add_parser('memory-context');mc.add_argument('--limit',type=int,default=12)
    ms=subs.add_parser('memory-show');ms.add_argument('entry_id')
    mr=subs.add_parser('memory-record');mr.add_argument('question',type=Path);mr.add_argument('--status',choices=STATUSES,required=True);mr.add_argument('--note',required=True)
    dc=subs.add_parser('design-check');dc.add_argument('question',type=Path)
    dr=subs.add_parser('design-review-template');dr.add_argument('output',type=Path);dr.add_argument('--question',type=Path,required=True)
    cr=subs.add_parser('candidate-reserve');cr.add_argument('question',type=Path);cr.add_argument('--review',type=Path)
    br=subs.add_parser('business-references');br.add_argument('--subdirection')
    qs=subs.add_parser('qa-setup');sources=qs.add_mutually_exclusive_group(required=True)
    sources.add_argument('--har',type=Path);sources.add_argument('--config',type=Path);sources.add_argument('--default',dest='use_default',action='store_true')
    qr=subs.add_parser('qa-run');qr.add_argument('stage',choices=[*platform_client.KEYS,'models'])
    qr.add_argument('--question',type=Path);qr.add_argument('--evaluation',type=Path);qr.add_argument('--refresh',action='store_true')
    qst=subs.add_parser('qa-status');qst.add_argument('--evaluation',type=Path)
    qdt=subs.add_parser('qa-disagreement-template');qdt.add_argument('stage',choices=list(platform_client.KEYS));qdt.add_argument('output',type=Path);qdt.add_argument('--evaluation',type=Path);qdt.add_argument('--question',type=Path)
    qd=subs.add_parser('qa-disagree');qd.add_argument('decision',type=Path);qd.add_argument('--evaluation',type=Path);qd.add_argument('--question',type=Path)
    for command in ('qa-polish-template','qa-polish'):
        qp=subs.add_parser(command);qp.add_argument('file',type=Path);qp.add_argument('--evaluation',type=Path,required=True)
    f=subs.add_parser('freeze');f.add_argument('question',type=Path)
    c=subs.add_parser('collect');c.add_argument('role',choices=ROLES);c.add_argument('--allow-live',action='store_true');c.add_argument('--retry-reason',default='');c.add_argument('--max-output',type=int);c.add_argument('--seed-evaluation',type=Path)
    r=subs.add_parser('recover');r.add_argument('role',choices=ROLES);r.add_argument('attempt',type=Path)
    s=subs.add_parser('render');s.add_argument('role',choices=ROLES)
    for command in ('model-prepare','model-import'):
        m=subs.add_parser(command);m.add_argument('role',choices=ROLES);m.add_argument('--seed-evaluation',type=Path)
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
            root=args.task.absolute() if args.task else Path.cwd() if (Path.cwd()/'TASK.json').is_file() else default_task(workspace)
            require(locate_workspace(root)==workspace,'题目不属于指定工作区')
            if args.command=='new':result=create_task(workspace,args.id)
            elif args.command=='rename':result=rename_task(workspace,root,args.name)
            elif args.command=='workspace-update':result=update_workspace(workspace)
            elif args.command=='start':
                print('请在当前题目的Codex侧栏发送：\n\n按 AGENTS.md 使用 llm-authoring-workflow 开始或接续完整出题流程。保留已有题目、三模型原文和判断，按status补齐缺失步骤。新题先问我计算机科学还是商科，再问相应子方向，最后选择题型；设计前读取本地题库，核实自然表达、场景/Insight/考点的实质差异；按Skill的writing.md灵活组织Insight但突出真正决定性因素，考点精简背景且一条判断一件事，提交字段用纯文本、排序备注简洁；五模型发送文字严格等于冻结prompt，不追加格式要求；不调用模型生成API，允许平台质检调用。prompt和Insight后先做难度标签检查，按反馈自主返修，通过后再冻结。按我选定的领域生成并核实场景。冻结候选后先创建Seed的Markdown填写文件；我填好后导入并判断，Seed未达成全部决定性点才创建GPT和Claude文件。三个模型原文、判断及备注齐备后按Skill并行考点和达成性质检，正常请求等待至完成、不设客户端时限；合理不通过自主返修，错误意见登记证据异议，立即告诉我不认同并给可复制备注。门禁满足后先发Arena题面和两份Markdown填写链接，再离线处理三项通过的表达建议，保持题面和判定、优化后不再质检。等我填好后继续五模型考点评估、排序及完整交付；所有模型的官方网页截图由我自行提交。\n');return 0
            elif args.command=='begin':result=begin(root,workspace)
            elif args.command=='choose-type':result=choose_type(root,args.type)
            elif args.command=='choose-domain':result=choose_domain(root,args.domain)
            elif args.command=='choose-subdirection':result=choose_subdirection(root,args.branch)
            elif args.command=='selection-upgrade':result=upgrade_selection(root)
            elif args.command=='memory-sync':result=memory_sync(workspace)
            elif args.command=='memory-context':result=memory_context(root,workspace,args.limit)
            elif args.command=='memory-show':result=memory_show(workspace,args.entry_id)
            elif args.command=='memory-record':
                with transaction(workspace) as connection:
                    result={'entry_id':remember(connection,root,read_json(args.question),args.status,note=args.note),'status':args.status}
            elif args.command=='design-check':result=candidate_check(root,read_json(args.question))
            elif args.command=='design-review-template':
                require(not args.output.exists(),'设计复核文件已存在，保留旧记录；新版请使用新文件名')
                write_json(args.output,review_template(root,read_json(args.question)));result={'output':str(args.output),'next':'助手逐项填写真实比较理由，再candidate-reserve或freeze，不向用户新增确认'}
            elif args.command=='candidate-reserve':result=reserve(root,read_json(args.question),args.review)
            elif args.command=='business-references':result=business_context(args.subdirection)
            elif args.command=='qa-setup':
                config=platform_client.default_config() if args.use_default else platform_client.config_from_har(args.har) if args.har else read_json(args.config)
                result=platform_client.setup(workspace,config)
            elif args.command=='qa-run':
                q=read_json(args.question or root/'drafts/question.json') if args.stage=='question' else None
                evaluation=read_json(args.evaluation) if args.evaluation else None
                result=qa.run_models(root,evaluation,refresh=args.refresh) if args.stage=='models' else qa.run(root,args.stage,q=q,evaluation=evaluation,refresh=args.refresh)
            elif args.command=='qa-status':result=qa.status(root,read_json(args.evaluation) if args.evaluation else None)
            elif args.command=='qa-disagreement-template':
                require(not args.output.exists(),'保留旧异议记录，使用新的文件名')
                q=read_json(args.question or root/'drafts/question.json') if args.stage=='question' else None
                write_json(args.output,qa.disagreement_template(root,args.stage,read_json(args.evaluation) if args.evaluation else None,q=q));result={'output':str(args.output),'next':'助手核对证据，填写理由和表单备注，再qa-disagree；不要求用户审批'}
            elif args.command=='qa-disagree':
                decision=read_json(args.decision)
                q=read_json(args.question or root/'drafts/question.json') if decision.get('stage')=='question' else None
                result=qa.disagree(root,decision,read_json(args.evaluation) if args.evaluation else None,q=q)
            elif args.command=='qa-polish-template':
                require(not args.file.exists(),'保留旧优化记录，使用新文件名')
                write_json(args.file,platform_polish.template(root,read_json(args.evaluation)));result={'output':str(args.file),'next':'先发Arena链接，再填写表达优化与依据；不重复调用平台质检'}
            elif args.command=='qa-polish':result=platform_polish.apply(root,read_json(args.evaluation),read_json(args.file))
            elif args.command=='freeze':
                require(begin(root,workspace)['ready'],'先选大方向、子方向和题型，再设计、查重与冻结')
                result=freeze(root,read_json(args.question))
            elif args.command in ('collect','recover','render'):
                raise Error('当前流程不调用模型API或生成渲染截图；请使用 model-prepare / model-import，官方网页截图由用户单独提交')
            elif args.command=='model-prepare':result=prepare_model(root,args.role,args.seed_evaluation)
            elif args.command=='model-import':result=import_model(root,args.role,args.seed_evaluation)
            elif args.command in ('evaluation-template','self-review-template','seed-evaluation-template'):
                require(not args.output.exists(),'输出已存在，拒绝覆盖判断或自查')
                value=self_review_template(root) if args.command=='self-review-template' else evaluation_template(root,('seed',) if args.command=='seed-evaluation-template' else ROLES)
                write_json(args.output,value);result={'output':str(args.output)}
            elif args.command=='seed-check':result=check_seed(root,read_json(args.evaluation))
            elif args.command=='check':result=check_three(root,read_json(args.evaluation))
            elif args.command=='arena-prepare':result=prepare_arena(root,read_json(args.evaluation))
            elif args.command=='arena-import':result=import_arena(root,read_json(args.evaluation) if args.evaluation else None)
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
                        try:r=read_response(root,role);result['responses'][role]={'complete':True,'display_name':r['meta'].get('display_name'),'screenshot':r['meta'].get('screenshot_kind','user_submits_separately' if role not in ROLES or r['meta'].get('source_kind')=='official_manual' else 'missing')}
                        except Error:result['responses'][role]={'complete':False,'status':'evidence_missing_or_incomplete'}
                    result['authoring_evaluation']=str(path) if (path:=find_authoring_evaluation(root)) else None
                    missing=[role for role,value in result['responses'].items() if not value['complete']]
                    result.update(manual_status(root))
                    if all(result['responses'][role]['complete'] for role in ROLES) and result['authoring_evaluation']:
                        result['stage']='awaiting_arena_markdown' if missing else 'five_model_evaluation_and_ranking'
                        result['next']='三模型门槛已通过；创建或填写 Arena 两份Markdown' if missing else '统一评估五模型全部考点，生成并校验排序，然后导出新的完整提交版'
                    if (root/'arena-input'/result['revision']).exists():
                        result['arena_input_files']=[str(root/'arena-input'/result['revision']/f'model-{index}.md') for index in (4,5)]
                path=find_authoring_evaluation(root)
                platform=qa.status(root,read_json(path) if path else None);result['platform_checks']=platform
                if platform.get('required') and result['ready'] and not platform.get('ready_for_arena'):
                    result['stage']=platform['stage'];result['next']='按状态补齐题目检查；三模型原文、判断及备注齐备后qa-run models并行质检，正常请求等至完成；异议给可复制备注'
            else:raise Error('未知命令')
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (Error,OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
        print('错误：'+(str(exc) if isinstance(exc,Error) else type(exc).__name__+'；检查路径、JSON和权限，未显示私有配置。'),file=sys.stderr);return 2


if __name__=='__main__':sys.exit(main())
