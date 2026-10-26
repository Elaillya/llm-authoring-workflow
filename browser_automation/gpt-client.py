#!/usr/bin/env python3
"""Official Codex only. Persist intent before generation, pin model/effort, keep raw proof."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm_authoring.official import prepare,request
from llm_authoring.core import read_json,write_json,hash_json,require,Error

BINARY=Path('/root/.vscode-server/extensions/openai.chatgpt-26.1021.22027-linux-x64/bin/linux-x86_64/codex')
PARENT=Path('/srv/llm-authoring-browser-lab')


def verify_generation(events,rollout,prompt,reply):
    sessions={e.get('thread_id') for e in events if e.get('type')=='thread.started'}
    sessions.discard(None)
    require(len(sessions)==1,'Codex未给出唯一实际会话')
    session=sessions.pop()
    require(any(e.get('type')=='turn.completed' for e in events),'Codex回合未完成')
    require(not any(e.get('type') in ('error','turn.failed') for e in events),'Codex原请求发生错误')
    tool_events=[e for e in events if e.get('type','').startswith('item.')
                 and e.get('item',{}).get('type') not in ('agent_message','reasoning')]
    require(not tool_events,'独立模型回答出现了工具调用，先检查客户端环境')
    finals=[e['item'].get('text') for e in events if e.get('type')=='item.completed'
            and e.get('item',{}).get('type')=='agent_message']
    require(finals and finals[-1]==reply,'Codex原始事件与reply.md正文不一致')
    contexts=[e['payload'] for e in rollout if e.get('type')=='turn_context']
    require(contexts and all(c.get('model')=='gpt-5.6-sol' and c.get('effort')=='high' for c in contexts),
            '实际模型或推理强度不符合本题要求')
    require(all(not c.get('user_instructions') for c in contexts),'检测到额外用户指令，保留原件并核对')
    users=[]
    for item in rollout:
        p=item.get('payload',{})
        if item.get('type')=='response_item' and p.get('type')=='message' and p.get('role')=='user':
            users.append(''.join(c.get('text','') for c in p.get('content',[]) if c.get('type') in ('input_text','text')))
    require(prompt in users and all(v==prompt or v.startswith('<environment_context>') for v in users),
            '原会话含有其他用户内容或题面不一致')
    require(not any('AGENTS.md instructions' in text or '/root/.codex/memories/' in text for text in users),
            '检测到题目外指引或记忆注入')
    require(any(e.get('type')=='session_meta' and e.get('payload',{}).get('id')==session for e in rollout),
            '实际客户端日志与会话ID不一致')
    return {'session_id':session,'actual_model':'gpt-5.6-sol','actual_effort':'high',
            'context_verified':True,'tools_used':False,'exact_prompt_verified':True,
            'official_client_system_environment':True}


def run(root):
    root=Path(root).resolve()
    require(root.is_relative_to(PARENT/'tasks'),'该开发采集器只用于新父工作区')
    item=prepare(root,'gpt')
    manifest=Path(item['request']);contract=read_json(manifest)
    directory=manifest.parent/'run'
    intent=directory/'intent.json'
    if intent.exists():
        value=read_json(intent)
        require(value.get('request_sha256')==hash_json(contract),'已有采集意图与当前题面不一致')
        receipt=directory/'generation.json'
        return read_json(receipt) if receipt.is_file() else {'state':'unconfirmed','next':'核对已有客户端进程与原事件，不重复发送','intent':str(intent)}
    require(BINARY.is_file(),'已验证的官方Codex客户端不在当前路径，先核对安装')
    directory.mkdir(mode=0o700)
    write_json(intent,{'request_sha256':hash_json(contract),'state':'one_generation_no_auto_retry','started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    home=directory/'client-home';home.mkdir(mode=0o700)
    auth=Path('/root/.codex/auth.json')
    require(auth.is_file(),'官方Codex登录尚未配置')
    (home/'auth.json').symlink_to(auth)
    # User previously selected keeping GPT-5.6 sol; acknowledge that native notice only.
    (home/'config.toml').write_text('[notice.model_migrations]\n"gpt-5.6-sol" = "gpt-6-sol"\n')
    empty=Path(tempfile.mkdtemp(prefix='llm-authoring-gpt-clean-',dir='/tmp'))
    env=os.environ.copy();env['CODEX_HOME']=str(home)
    args=[str(BINARY),'--no-daemon','exec','--ignore-user-config','--skip-git-repo-check','-C',str(empty),
          '-m','gpt-5.6-sol','-c','forced_login_method="chatgpt"','-c','model_reasoning_effort="high"',
          '-c','project_doc_max_bytes=0','-c','features.shell_tool=false','-c','features.memories=false',
          '-c','features.apps=false','-c','features.plugins=false','-c','features.remote_plugin=false',
          '-c','web_search="disabled"','-s','read-only','--json','-o',str(directory/'reply.md'),'-']
    write_json(directory/'launch.json',{'argv':args,'cwd':str(empty),'request_sha256':hash_json(contract),'client_home':str(home)})
    with (directory/'events.jsonl').open('wb') as output,(directory/'stderr.log').open('wb') as errors:
        process=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=output,stderr=errors,env=env)
        write_json(directory/'process.json',{'pid':process.pid,'state':'running'})
        process.communicate(input=contract['prompt'].encode())
    require(process.returncode==0,'官方Codex未正常完成，原事件与错误日志已保留，不自动重试')
    require(request(root,'gpt')==contract,'生成期间题目或先行Seed判断已变化，保留原回答后核对')
    events=[json.loads(line) for line in (directory/'events.jsonl').read_text().splitlines() if line.strip()]
    session=next((e.get('thread_id') for e in events if e.get('type')=='thread.started'),None)
    logs=list((home/'sessions').rglob('*'+str(session)+'.jsonl'))
    require(len(logs)==1,'无法找到唯一真实客户端会话日志')
    shutil.copyfile(logs[0],directory/'generation-rollout.jsonl')
    rollout=[json.loads(line) for line in (directory/'generation-rollout.jsonl').read_text().splitlines() if line.strip()]
    proof=verify_generation(events,rollout,contract['prompt'],(directory/'reply.md').read_text())
    result={'schema_version':1,'state':'generated_pending_screenshot','source_kind':'official_client_automation',
            'request_sha256':hash_json(contract),'prompt_bytes_sha256':contract['prompt_bytes_sha256'],
            **proof,'exit_code':process.returncode,'cwd':str(empty),'client_home':str(home),'binary':str(BINARY),
            'reply_sha256':hashlib.sha256((directory/'reply.md').read_bytes()).hexdigest(),
            'rollout_sha256':hashlib.sha256((directory/'generation-rollout.jsonl').read_bytes()).hexdigest(),
            'screenshot_verified':False}
    receipt=directory/'generation.json';write_json(receipt,result)
    registry=PARENT/'local/gpt-sessions'/ (proof['session_id']+'.json')
    require(not registry.exists(),'该原会话已有展示注册，核对后沿用，不覆盖')
    write_json(registry,{'session_id':proof['session_id'],'generation_receipt':str(receipt),
                         'generation_receipt_sha256':hashlib.sha256(receipt.read_bytes()).hexdigest()})
    for file in directory.rglob('*'):
        if file.is_file() and not file.is_symlink():file.chmod(0o600)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--task',type=Path,required=True)
    args=parser.parse_args()
    try:print(json.dumps(run(args.task),ensure_ascii=False,indent=2))
    except (Error,OSError,ValueError,KeyError,StopIteration):
        print('官方GPT采集未完成或待核验；保留已有意图、原事件和日志，不自动重发。',file=sys.stderr);sys.exit(2)
