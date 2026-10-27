"""Presentation helpers for separate Markdown submission fields and replies."""
import re
from pathlib import Path
from urllib.parse import quote
from .core import ALL_ROLES, hash_json, read_json
from .text import insight_text


def join_note_fields(parts):
    """Normalize only author-field boundaries; quoted evidence stays verbatim."""
    text=''
    for part in parts:
        if not part:continue
        if text:
            text=text.rstrip()
            # A completed sentence already separates the next labeled field.
            separator='' if text.endswith(('。','.','！','？','!','?','；',';')) else '；'
            text+=separator
        text+=part
    return text


def attainment_notes(stat, *, kinds=True):
    lines=[]
    for item in stat['judgments']:
        label=item['id']
        if kinds:label+='（'+('决定性' if item['kind']=='decisive' else '非决定性')+'）'
        lines.append(label+'：'+join_note_fields([
            '满足' if item['met'] else '不满足', '原因：'+item['reason'],
            '原文依据：'+' / '.join(item['quotes']) if item['quotes'] else '']))
    return '\n\n'.join(lines)


def model_files(names):
    """Keep readable model names while producing portable, distinct file paths."""
    files = {}
    used = set()
    for role, name in names.items():
        stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).rstrip(' .') or 'model'
        while len(stem.encode('utf-8')) > 180:
            stem = stem[:-1]
        if re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', stem, re.I):
            stem = '_' + stem
        if stem.casefold() in used:
            stem += '-' + hash_json([role, name])[:8]
        used.add(stem.casefold())
        files[role] = 'models/' + stem + '.md'
    return files


def named_text(text, names):
    ordinals = {str(i): role for i, role in enumerate(ALL_ROLES, 1)}
    ordinals.update(dict(zip('一二三四五', ALL_ROLES)))
    pattern = r'模型([1-5])(?!\d)|模型([一二三四五])(?=$|[\s:：、，,。.;；=><＞＜/()（）])'
    return re.sub(pattern, lambda m: names[ordinals[m[1] or m[2]]], text)


def reply_link(model):
    return '[模型回复 Markdown](' + quote(model['reply_file'], safe='/') + ')'


def submission_id(root, fallback):
    task = Path(root) / 'TASK.json'
    return read_json(task).get('display_id', fallback) if task.is_file() else fallback


def submission_text(fields,roles,checkpoint=False):
    """The .md filename is retained; author fields are copyable plain text."""
    lines=['三模型出题检查点' if checkpoint else '完整出题与模型排序提交','']
    def field(title,value):
        lines.extend([title+'：',value,''])
    for key,title in (('task_id','题目编号'),('domain','题目领域'),('prompt','题目 prompt'),('question_type','题目类型')):
        field(title,fields[key])
    field('关键洞察（Insight）',insight_text(fields['insight']))
    for key,title in (('decisive_points','决定性核心考点'),('supporting_points','非决定性核心考点')):
        points=fields[key]
        value='无' if points=='无' else '\n'.join(p['id']+'：'+p['criterion'] for p in points)
        field(title,value)
    for role in roles:
        model=fields['models'][role]
        lines.extend([model['display_name'],''])
        field('模型回复文件',model['reply_file'])
        field('是否达成全部决定性核心考点','是' if model['attained'] else '否')
        field('达成性备注',model['attainment_notes'])
        if model.get('screenshot'):field('历史API渲染截图',model['screenshot'])
    if not checkpoint:
        field('五模型核心考点达成性排序',fields['ranking'])
        field('决定性核心考点的达成性排序说明',fields['ranking_notes'])
    field('出题说明备注',fields['author_notes'])
    if checkpoint:
        field('检查点接续说明','三模型区分度检查通过。此为出题检查点，继续补齐Arena两份Markdown、五模型排序及完整提交。')
    manual=all(fields['models'][role].get('source_kind')=='official_manual' for role in roles if role not in ('arena_1','arena_2'))
    source='前三份回复为用户提供的官方页面Markdown。' if manual else '前三份回复包含历史API原文，历史API渲染图不等于官方网页截图。'
    field('材料来源说明',source+'Arena回复为用户提供的Markdown。工具未独立核验网页型号、会话及Arena模式和随机过程。官方网页截图由用户另行向甲方提交。')
    if fields.get('platform_checks',{}).get('form_notes'):
        field('平台质检异议及表单备注',fields['platform_checks']['form_notes'])
    if fields.get('postpass_polish'):field('平台通过后表达优化说明',fields['postpass_polish']['notice'])
    return '\n'.join(lines).rstrip()+'\n'
