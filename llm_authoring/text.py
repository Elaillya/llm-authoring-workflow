"""Plain author fields; model originals and evidence are never transformed."""
INSIGHT_LABELS=(('mechanism','机制'),('priority','优先级'),('conclusion','核心结论'))


def valid_insight(value):
    if isinstance(value,str):return bool(value.strip())
    return isinstance(value,dict) and all(isinstance(value.get(key),str) and value[key].strip()
                                         for key,_ in INSIGHT_LABELS)


def insight_text(value,labels=True):
    if isinstance(value,str):return value
    return '\n\n'.join((label+'：' if labels else '')+value[key] for key,label in INSIGHT_LABELS)
