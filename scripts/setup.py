#!/usr/bin/env python3
"""Prepare local Python dependencies; no credentials, browsers, or model calls."""
from pathlib import Path
import subprocess
import sys
import venv
import os

ROOT=Path(__file__).resolve().parents[1]


def prepare(root=ROOT):
    if sys.version_info<(3,10):raise SystemExit('需要Python 3.10或更新版本')
    root=Path(root)
    python=root/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    print('Preparing project Python environment...',flush=True)
    if not python.is_file():venv.EnvBuilder(with_pip=True).create(root/'.venv')
    env={**os.environ,'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'}
    probe='import importlib.metadata as m,pathlib,sys; req=pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines(); assert all(m.version(n)==v for n,v in (r.split("==") for r in req if r.strip() and not r.startswith("#")))'
    checked=subprocess.run([str(python),'-X','utf8','-c',probe,str(root/'requirements.lock')],env=env,capture_output=True)
    if checked.returncode:
        subprocess.run([str(python),'-X','utf8','-m','pip','install','--index-url','https://pypi.org/simple','-r',str(root/'requirements.lock')],env=env,check=True)
    print('环境准备完成。下一步：创建独立工作区，在侧栏选择领域和题型；模型回答手动填入预创建的Markdown，无需API配置。')
    return python


def main():prepare()


if __name__=='__main__':main()
