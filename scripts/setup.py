#!/usr/bin/env python3
"""Prepare local Python dependencies; no credentials, browsers, or model calls."""
from pathlib import Path
import subprocess
import sys
import venv

ROOT=Path(__file__).resolve().parents[1]


def main():
    if sys.version_info<(3,10):raise SystemExit('需要Python 3.10或更新版本')
    if sys.platform=='win32':raise SystemExit('Windows请在WSL内运行。')
    print('Preparing project Python environment...',flush=True)
    venv.EnvBuilder(with_pip=True).create(ROOT/'.venv')
    python=ROOT/'.venv/bin/python'
    subprocess.run([str(python),'-m','pip','install','--index-url','https://pypi.org/simple','-r',str(ROOT/'requirements.lock')],check=True)
    print('环境准备完成。下一步：创建独立工作区，在侧栏选择领域和题型；模型回答手动填入预创建的Markdown，无需API配置。')


if __name__=='__main__':main()
