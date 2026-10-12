#!/usr/bin/env python3
"""Prepare dependencies in this clone only. No model calls or credentials."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import urllib.request
import venv

ROOT=Path(__file__).resolve().parents[1]
FONT_URL='https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf'
FONT_SHA='2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b'


def main():
    parser=argparse.ArgumentParser(description='安装当前工具仓独立Python依赖、Chromium和中文字体。Linux/macOS；Windows请用WSL。')
    parser.parse_args()
    if sys.version_info<(3,10):raise SystemExit('需要Python 3.10或更新版本')
    if sys.platform=='win32':raise SystemExit('当前接口总时限使用POSIX信号；Windows请在WSL内运行。')
    print('Preparing project Python environment...',flush=True)
    venv.EnvBuilder(with_pip=True).create(ROOT/'.venv')
    python=ROOT/'.venv/bin/python'
    subprocess.run([str(python),'-m','pip','install','--index-url','https://pypi.org/simple','-r',str(ROOT/'requirements.lock')],check=True)
    import os
    env={**os.environ,'PLAYWRIGHT_BROWSERS_PATH':str(ROOT/'.browsers')}
    subprocess.run([str(python),'-m','playwright','install','chromium','--only-shell'],env=env,check=True)
    assets=ROOT/'.assets';assets.mkdir(exist_ok=True);font=assets/'NotoSansCJKsc-Regular.otf'
    if not font.is_file() or hashlib.sha256(font.read_bytes()).hexdigest()!=FONT_SHA:
        with urllib.request.urlopen(FONT_URL,timeout=120) as reply:data=reply.read(20*1024*1024)
        if hashlib.sha256(data).hexdigest()!=FONT_SHA:raise SystemExit('字体下载SHA-256不符，未安装')
        temporary=font.with_suffix('.download');temporary.write_bytes(data);temporary.replace(font)
    print('环境准备完成。下一步：创建独立工作区，在侧栏选择题型并填三个模型配置。')


if __name__=='__main__':main()
