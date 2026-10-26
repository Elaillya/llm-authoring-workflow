#!/usr/bin/env python3
"""Display one verified local Codex session. No user prompt or new generation."""
from pathlib import Path
import hashlib,json,os,re,sys

PARENT=Path('/srv/llm-authoring-browser-lab')
BINARY='/root/.vscode-server/extensions/openai.chatgpt-26.1021.22027-linux-x64/bin/linux-x86_64/codex'

def main(session):
    if not re.fullmatch(r'[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}',session):raise ValueError('Invalid session UUID')
    registry=PARENT/'local/gpt-sessions'/(session+'.json')
    if not registry.is_file() or registry.is_symlink() or registry.stat().st_mode&0o077:raise ValueError('Private session registry required')
    binding=json.loads(registry.read_text());receipt=Path(binding['generation_receipt'])
    if receipt.is_symlink() or not receipt.resolve().is_relative_to(PARENT/'tasks'):raise ValueError('Unexpected source record')
    if hashlib.sha256(receipt.read_bytes()).hexdigest()!=binding['generation_receipt_sha256']:raise ValueError('Source record changed')
    proof=json.loads(receipt.read_text())
    if proof.get('session_id')!=session or proof.get('actual_model')!='gpt-5.6-sol' or proof.get('actual_effort')!='high' or proof.get('context_verified') is not True:raise ValueError('Original model evidence mismatch')
    home=Path(proof['client_home']);cwd=Path(proof['cwd'])
    if not home.resolve().is_relative_to(receipt.parent) or not cwd.name.startswith('llm-authoring-gpt-clean-') or cwd.parent!=Path('/tmp') or any(cwd.iterdir()):raise ValueError('Client isolation changed')
    env=os.environ.copy();env['CODEX_HOME']=str(home)
    args=[BINARY,'--no-daemon','resume',session,'-C',str(cwd),'-m','gpt-5.6-sol',
          '-c','model_reasoning_effort="high"','-c','project_doc_max_bytes=0','-c','features.shell_tool=false',
          '-c','features.memories=false','-c','web_search="disabled"','-s','read-only','--no-alt-screen']
    os.execve(BINARY,args,env)

if __name__=='__main__':
    try:
        if len(sys.argv)!=2:raise ValueError('One session UUID required')
        main(sys.argv[1])
    except (OSError,ValueError,KeyError):
        print('原GPT会话展示绑定未通过，未发送任何新问题。',file=sys.stderr);sys.exit(2)
