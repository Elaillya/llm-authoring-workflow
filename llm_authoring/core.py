"""Frozen question evidence shared by user-supplied and historical replies."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import os
import tempfile
from datetime import datetime, timezone
from .text import valid_insight
from .domains import canonical_domain

ROLES = ('seed', 'gpt', 'claude')
ARENA_ROLES = ('arena_1', 'arena_2')
ALL_ROLES = ROLES + ARENA_ROLES
NAMES = {'seed':'Seed 2.1 Turbo', 'gpt':'GPT-5.6 sol', 'claude':'Claude Opus 4.6'}
TYPES = ('分析决策类', '开放推荐类', 'How-to类')


class Error(ValueError): pass


def require(condition, message):
    if not condition: raise Error(message)


def read_json(path):
    path=Path(path)
    require(path.is_file() and not path.is_symlink(), f'缺少普通文件：{path}')
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    require(not path.is_symlink(), '输出文件不能为符号链接')
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as output:
            output.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n');output.flush();os.fsync(output.fileno())
        os.replace(name,path)
    finally:
        Path(name).unlink(missing_ok=True)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hash_json(value): return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')


def validate_question(q,legacy_domain=False):
    require(q.get('schema_version')==1, '题目 schema_version 必须为 1')
    require(bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}',q.get('task_id',''))), '题目 ID 不合法')
    prompt=q.get('prompt','')
    require(isinstance(prompt,str) and prompt.strip() and len(prompt)<=100, '题目 prompt 必须为非空文本且不超过 100 字符（含标点和空白）')
    require(q.get('question_type') in TYPES, '题目类型必须是分析决策类、开放推荐类或 How-to类')
    if not legacy_domain or 'domain' in q:
        require(isinstance(q.get('domain'),str) and q['domain'].strip(), '题目需要用户选择的专业领域')
    require(valid_insight(q.get('insight')), 'Insight需要非空洞察文本，或完整的旧版机制、优先级和结论对象')
    require(isinstance(q.get('author_notes'),str) and q['author_notes'].strip(), '需要真实来源及出题说明备注')
    points=q.get('points',[])
    require(isinstance(points,list) and any(isinstance(p,dict) and p.get('kind')=='decisive' for p in points), '至少需要一个决定性考点')
    ids=[]
    for p in points:
        require(isinstance(p,dict) and bool(re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,31}',p.get('id',''))), '考点 ID 不合法')
        require(p.get('kind') in ['decisive','supporting'] and isinstance(p.get('criterion'),str) and p['criterion'].strip(), '考点需要明确分类与标准')
        ids.append(p['id'])
    require(len(ids)==len(set(ids)), '考点 ID 重复')


def freeze(root, q):
    root=Path(root);root.mkdir(parents=True,exist_ok=True);validate_question(q)
    request=read_json(root/'REQUEST.json')
    require(request.get('question_type')==q['question_type'],'先询问并记录用户选择的题型，再冻结相同题型的题目')
    if (root/'TASK.json').exists():require(read_json(root/'TASK.json').get('task_id')==q['task_id'],'题目ID与工作区不匹配')
    selected=question_domain(root,request)
    require(selected is not None,'先询问并记录用户选择的领域，再冻结题目')
    require(canonical_domain(q['domain'])==canonical_domain(selected),'题目领域与用户选择不一致；已冻结题目换领域请新建题目')
    from .platform_checks import question_gate
    question_gate(root,q)
    if (root/'CURRENT.json').is_file():
        previous=active_question(root)
        if previous['question_sha256']==hash_json(q):return previous
    if request.get('selection_schema')==2:
        from .quality import reserve
        return reserve(root,q,freeze_writer=lambda:freeze_record(root,q))
    return freeze_record(root,q)


def freeze_record(root,q):
    """Write an already validated candidate; new-policy callers hold the memory lock."""
    root=Path(root)
    revs=root/'revisions';revs.mkdir(exist_ok=True)
    value={'question':q,'prompt_sha256':hash_json(q['prompt']),'rubric_sha256':hash_json(q['points']),
           'question_sha256':hash_json(q)}
    current=root/'CURRENT.json'
    if current.exists():
        previous=active_question(root)
        if previous['question_sha256']==value['question_sha256']: return previous
    index=max([int(p.name[1:]) for p in revs.iterdir() if re.fullmatch(r'r\d{4}',p.name)]+[0])+1
    name=f'r{index:04d}';directory=revs/name
    value.update({'revision':name,'frozen_at':now()})
    staging=Path(tempfile.mkdtemp(prefix='.freeze-'+name+'-',dir=revs))
    try:
        write_json(staging/'question.json',value)
        require(not directory.exists(),'冻结版本已存在，请重新读取当前版本后重试')
        staging.rename(directory)
    finally:
        if staging.exists():shutil.rmtree(staging)
    # If this write fails, retain the complete version as recoverable evidence;
    # sibling tasks can still read it. Never publish an incomplete rNNNN folder.
    write_json(current,{'revision':name})
    return value


def active_question(root):
    root=Path(root);name=read_json(root/'CURRENT.json')['revision']
    require(bool(re.fullmatch(r'r\d{4}',name)), '当前题目版本不合法')
    value=read_json(root/'revisions'/name/'question.json');q=value['question'];validate_question(q,legacy_domain=True)
    require(value['question_sha256']==hash_json(q) and value['prompt_sha256']==hash_json(q['prompt'])
            and value['rubric_sha256']==hash_json(q['points']), '冻结题目被改写；请保留原件并创建新版本')
    return value


def question_domain(root,request=None):
    root=Path(root);request=read_json(root/'REQUEST.json') if request is None else request
    if (root/'CURRENT.json').is_file():
        # Older frozen records could omit this field under the former CS-only contract.
        return active_question(root)['question'].get('domain','计算机科学')
    domain=request.get('domain')
    return domain if request.get('domain_confirmed') is True and isinstance(domain,str) and domain.strip() else None


def response_dir(root,role):
    require(role in ALL_ROLES,'模型角色不合法')
    return Path(root)/'responses'/active_question(root)['prompt_sha256']/role


def validate_markdown(text):
    require(isinstance(text,str) and text.strip(), '模型回复 Markdown 为空')
    from markdown_it import MarkdownIt
    tokens=MarkdownIt('commonmark',{'html':False}).enable('table').parse(text)
    lines=text.splitlines()
    for token in tokens:
        if token.type=='fence':
            last=lines[token.map[1]-1].strip()
            marker=token.markup[0]
            require(bool(re.fullmatch(re.escape(marker)+'{'+str(len(token.markup))+r',}\s*',last)), 'Markdown 存在未闭合代码块，需核是否截断')


def save_response(root, role, text, meta, raw=None):
    validate_markdown(text); current=active_question(root);directory=response_dir(root,role)
    require(not directory.exists(),'当前题面已有该模型的回复或调用记录，保留原件；不要自动重复调用')
    directory.mkdir(parents=True)
    (directory/'reply.md').write_text(text,encoding='utf-8')
    if raw is not None:
        rawname=meta.get('raw_response_file','raw_response.json')
        allowed={'arena_manual':('arena-input.md',),'official_manual':('model-input.md',)}.get(meta.get('source_kind'),('raw_response.json','raw_response.sse'))
        require(rawname in allowed,'原响应文件名不合法')
        (directory/rawname).write_bytes(raw)
    metadata={**meta,'schema_version':1,'role':role,'task_id':current['question']['task_id'],
              'prompt_sha256':current['prompt_sha256'],'rubric_at_capture':current['rubric_sha256'],
              'reply_sha256':sha(directory/'reply.md'),'captured_at':meta.get('captured_at',now())}
    if raw is not None:metadata['raw_response_sha256']=sha(directory/rawname)
    write_json(directory/'metadata.json',metadata)
    return metadata


def read_response(root,role):
    directory=response_dir(root,role)
    require((directory/'metadata.json').is_file(),f'当前题面版本缺少 {role} 的完整回复')
    meta=read_json(directory/'metadata.json');text=(directory/'reply.md').read_bytes().decode('utf-8')
    require(meta['prompt_sha256']==active_question(root)['prompt_sha256'],'回复题面版本不一致')
    require(sha(directory/'reply.md')==meta['reply_sha256'],'模型回复原件已改变')
    if meta.get('source_kind') in ('api','arena_manual','official_manual'):
        rawname=meta.get('raw_response_file','raw_response.json')
        allowed={'arena_manual':('arena-input.md',),'official_manual':('model-input.md',)}.get(meta.get('source_kind'),('raw_response.json','raw_response.sse'))
        require(rawname in allowed,'原响应文件名不合法')
        rawpath=directory/rawname
        require(rawpath.is_file() and not rawpath.is_symlink() and sha(rawpath)==meta.get('raw_response_sha256'),'模型原始响应缺失或已改变')
    require(meta.get('completion_status')=='complete','回复未完整完成，不用于评估')
    validate_markdown(text)
    return {'directory':directory,'meta':meta,'text':text}


def validate_image(path):
    from PIL import Image
    import warnings
    require(Path(path).is_file() and not Path(path).is_symlink(),'截图须为普通文件')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(path,formats=['PNG','JPEG']) as pic:
                width,height=pic.size;pic.verify()
            with Image.open(path,formats=['PNG','JPEG']) as pic:pic.load()
        require(width>=320 and height>=200,'截图尺寸过小，无法检查关键页面信息')
    except (OSError,ValueError,SyntaxError,Image.DecompressionBombWarning,Image.DecompressionBombError):
        raise Error('截图损坏或无法完整解码，不纳入正式证据') from None
    return width,height
