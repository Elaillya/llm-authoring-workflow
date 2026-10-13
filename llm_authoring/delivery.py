"""Presentation helpers for separate Markdown submission fields and replies."""
import re
from pathlib import Path
from urllib.parse import quote
from .core import ALL_ROLES, hash_json, read_json


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
