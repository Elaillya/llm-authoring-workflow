"""Obvious split-question checks; semantic focus remains an author review."""
from pathlib import Path
import re
import unicodedata
from .core import active_question, require


def focus_signals(prompt):
    # Question marks inside links and inline code are data, not extra questions.
    text=re.sub(r'`[^`\n]*`|https?://[^\s，。；！？]+','',prompt)
    text=unicodedata.normalize('NFKC',text);signals=[]
    if text.count('?')>1:
        signals.append('存在多个问句；将选择、安排及所需依据合成一个核心提问')
    if re.search(r'[,;。?!\n]\s*(?:(?:为什么|为何|理由是什么|原因是什么)(?:呢)?|(?:并|再)?(?:请)?(?:说明|解释)(?:理由|原因))[?。.!]?\s*$',text):
        signals.append('句尾单独追问原因；把原因或依据融入核心问句')
    return signals


def validate_new_prompt(root,prompt):
    # Frozen input contracts remain readable and usable for rubric-only repairs.
    if (Path(root)/'CURRENT.json').is_file() and active_question(root)['question']['prompt']==prompt:return
    issues=focus_signals(prompt)
    require(not issues,'题面须聚焦一个核心问题：'+'；'.join(issues))
