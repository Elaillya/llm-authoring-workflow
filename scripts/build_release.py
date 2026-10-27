#!/usr/bin/env python3
"""Build a small GitHub source ZIP from the committed, allowed source files."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ALLOWED_ROOT={'README.md','AGENTS.md','CONTEXT.md','LICENSE','NOTICE.md','.gitignore','requirements.lock'}
ALLOWED_DIR={'llm_authoring','skills','templates','config','rules','scripts','docs','assets','tests'}


def check_json_secrets(value):
    if isinstance(value,dict):
        for k,v in value.items():
            if k.lower() in ('api_key','authorization','password','access_token','refresh_token') and v:
                raise ValueError('发布JSON含非空凭据字段，停止打包')
            check_json_secrets(v)
    elif isinstance(value,list):
        for item in value:check_json_secrets(item)


def main():
    parser=argparse.ArgumentParser(description='将已提交的工具源码打包，排除私有工作区和环境。')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    report=args.output.with_suffix('.manifest.json')
    if args.output.exists() or args.output.is_symlink() or report.exists() or report.is_symlink():raise SystemExit('发布包或清单已存在，拒绝覆盖')
    commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    names=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only','-z','HEAD']).decode().split('\0')
    files={}
    for name in filter(None,names):
        path=Path(name)
        if not (name in ALLOWED_ROOT or path.parts[0] in ALLOWED_DIR):raise SystemExit('发现发布范围外的Git文件：'+name)
        if path.is_absolute() or '..' in path.parts:raise SystemExit('不合法的发布路径')
        data=subprocess.check_output(['git','-C',str(ROOT),'show',f'{commit}:{name}'])
        if path.suffix=='.json':check_json_secrets(json.loads(data))
        if name=='config/providers.example.json':
            for p in json.loads(data)['providers'].values():
                if any(p.get(k) for k in ('base_url','api_key','api_key_file','api_key_env')):raise SystemExit('示例配置须为空服务地址和凭据')
        files[name]=data
    args.output.parent.mkdir(parents=True,exist_ok=True)
    prefix='llm-authoring-workflow/'
    with zipfile.ZipFile(args.output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(files.items()):
            item=zipfile.ZipInfo(prefix+name,date_time=(2026,10,12,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED
            item.external_attr=0o100644<<16;archive.writestr(item,data)
    manifest={'kind':'github_source_release','git_commit':commit,'files':{n:hashlib.sha256(d).hexdigest() for n,d in sorted(files.items())},
              'zip_sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),'note':'仅通用源码/Skill/规则/模板，个人密钥、题目、运行结果、虚拟环境和浏览器不在包内。'}
    report.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'zip':str(args.output),'manifest':str(report),'git_commit':commit,'files':len(files),'bytes':args.output.stat().st_size},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
