"""Register captured browser failures without pretending they are API receipts."""
from pathlib import Path
import re
from .core import hash_json, read_json, read_response, require, sha
from .text import insight_text

KIND = 'criteria_web_quality_failed'
FIELDS = ['question-input', 'insight-input', 'insight-description-input',
          'non-decisive-insight-description-input', 'doubao-markdown-input',
          'gpt56-markdown-input', 'claude-markdown-input']
SELECTIONS = ['question-type-radio', 'question-domain-select']


def _file(root, path):
    root = Path(root).resolve()
    path = Path(path).absolute()
    require(all(not p.is_symlink() for p in (path, *path.parents) if p != root),
            '网页证据不能经过符号链接')
    path = path.resolve()
    require(path.is_relative_to(root), '网页证据必须在当前任务目录内')
    require(path.is_file(), '网页证据文件缺失')
    return path


def verify(root, evidence):
    require(read_json(Path(root)/'TASK.json').get('platform_checks_required') is False,
            '网页失败登记仅用于自动化任务')
    for item in evidence['files']:
        require(sha(_file(root, Path(root)/item['path'])) == item['sha256'], '网页失败证据已变化')
    return evidence


def register(root, directory):
    """Read recipe artifacts, bind the old frozen version and current original replies."""
    from . import lessons
    root = Path(root).resolve(); directory = Path(directory).absolute()
    require(read_json(root/'TASK.json').get('platform_checks_required') is False,
            '网页失败登记仅用于自动化任务')
    paths = {name: _file(root, directory/(name+'.json')) for name in
             ('input', 'core-point-intent', 'core-point-dispatch', 'core-point-result')}
    binding, intent, dispatch, result = (read_json(paths[k]) for k in paths)
    require(binding.get('kind') == 'checks' and 'core-point' in binding.get('keys', [])
            and isinstance(binding.get('itemId'), str) and binding['itemId'], '缺少网页检查绑定')
    version = binding.get('version', '')
    require(re.fullmatch(r'r\d{4}', version), '网页冻结版本无效')
    frozen_path = _file(root, root/'revisions'/version/'question.json')
    frozen = read_json(frozen_path); q = frozen['question']
    require(frozen['question_sha256'] == hash_json(q), '冻结题目绑定已变化')
    payload = binding['input']
    require(binding.get('inputHash') == hash_json(payload), '网页输入哈希不匹配')
    values = payload['values']; selections = payload['selections']
    require(all(k in values for k in FIELDS) and all(k in selections for k in SELECTIONS),
            '网页检查输入不完整')
    subset = {'values': {k: values[k] for k in FIELDS},
              'selections': {k: selections[k] for k in SELECTIONS}}
    require(result.get('inputHash') == hash_json(subset), '网页结果与输入不匹配')
    norm = lambda s: s.replace('\r\n', '\n').replace('\r', '\n')
    require(values['question-input'] == q['prompt'] and values['insight-input'] == insight_text(q['insight']),
            '网页题面或Insight与冻结版本不符')
    for kind, field in [('decisive','insight-description-input'), ('supporting','non-decisive-insight-description-input')]:
        expected = '\n'.join(p['id']+'：'+p['criterion'] for p in q['points'] if p['kind'] == kind) or '无'
        require(norm(values[field]) == expected, '网页考点与冻结版本不符')
    require(selections['question-domain-select'] == q['domain'] and
            selections['question-type-radio'] == q['question_type'].removesuffix('类'), '网页领域或题型不符')
    replies = {}
    for role, field in [('seed','doubao'), ('gpt','gpt56'), ('claude','claude')]:
        original = read_response(root, role)
        require(original['meta']['prompt_sha256'] == frozen['prompt_sha256'] and
                norm(values[field+'-markdown-input']) == norm(original['text']), '网页模型原文绑定不符')
        replies[role] = original['meta']['reply_sha256']
    observed = result['observed']; prior = intent['prior']; after = dispatch['after']
    calls = observed.get('calls'); baseline = prior.get('calls')
    linked = type(calls) is int and (type(baseline) is int and calls == baseline+1 or
                                   baseline is None and calls == 1 and after.get('running') is True)
    require(linked and after.get('key') == 'core-point' and after.get('calls') == calls
            and prior.get('key') == 'core-point' and prior.get('running') is False,
            '网页失败缺少本次调用关联')
    require(observed.get('key') == 'core-point' and observed.get('running') is False
            and observed.get('needsRerun') is False and observed.get('observation') == 'result_visible'
            and observed.get('conclusion') == '不通过' and observed.get('resultText'),
            '仅登记已结束且输入有效的网页考点不通过')
    paths['frozen'] = frozen_path
    evidence = {'source': 'platform_web', 'attempt': str(directory), 'version': version,
                'item_id': binding['itemId'], 'reply_sha256': replies,
                'files': [{'path': str(p.relative_to(root)), 'sha256': sha(p)} for p in paths.values()]}
    eid = lessons._save(root, q, KIND, evidence, observed['resultText'])
    return {'event_id': eid, 'kind': KIND, 'source': 'platform_web', 'requires_review': True}
