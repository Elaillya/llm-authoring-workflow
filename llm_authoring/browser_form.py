"""Prepare exact, evidence-validated model fields for the bound native form.

Preparation is local only. It never uploads, calls a model/check, or submits.
"""
from pathlib import Path
from .core import ROLES, active_question, hash_json, read_json, read_response, require, sha, write_json
from .authoring import validated_models
from .browser_checks import binding
from .manual import seed_screen
from .platform_checks import question_gate
from .ranking import attainment_notes

PLATFORM_KEYS = {'seed': 'doubao', 'gpt': 'gpt56', 'claude': 'claude'}


def fields(root, role, evaluation):
    root = Path(root).resolve()
    task = read_json(root / 'TASK.json')
    require(task.get('response_mode') == 'official_clients'
            and task.get('platform_check_mode') == 'browser', '仅供独立官方客户端浏览器题目')
    require(role in ROLES, '未知前三模型角色')
    current = active_question(root)
    question_gate(root, current['question'])
    require(isinstance(evaluation, dict) and isinstance(evaluation.get('models'), dict), '先完成当前原文的考点判断')
    roles = tuple(evaluation['models'])
    require(role in roles and set(roles) <= set(ROLES), '只接受指定前三模型的同版判断')
    stats = validated_models(root, evaluation, roles)
    if role == 'seed':
        require(not stats[role]['attained'], 'Seed全部达成的淘汰稿不填入后续模型阶段')
    else:
        seed_screen(root)
        from .check_policy import require_choice
        require_choice(root)
    item = read_response(root, role)
    prefix = PLATFORM_KEYS[role]
    text_fields = {prefix + '-markdown-input': item['text'],
                   prefix + '-achievement-note-input': attainment_notes(stats[role])}
    shots = []
    evidence = item['directory'] / 'client-evidence'
    capture = read_json(evidence / 'capture.json')
    for frame in capture['frames']:
        file = evidence / frame['filename']
        # validated_models already checks original client evidence and every PNG.
        shots.append({'file': str(file), 'sha256': sha(file)})
    return {'schema_version': 1, 'task_root': str(root), 'binding': binding(root),
            'revision': current['revision'], 'question_sha256': current['question_sha256'],
            'prompt_sha256': current['prompt_sha256'], 'rubric_sha256': current['rubric_sha256'],
            'role': role, 'model_name': item['meta']['display_name'], 'platform_key': prefix,
            'expected_selection': {'domain': current['question']['domain'],
                                   'type': {'开放推荐类':'openRecommendation','分析决策类':'analysisDecision',
                                            'How-to类':'howTo'}[current['question']['question_type']]},
            'expected_base': {'question-input': current['question']['prompt'],
                              'insight-input': current['question']['insight'],
                              **{key: '\n'.join(p['id'] + '：' + p['criterion']
                                                for p in current['question']['points'] if p['kind'] == kind) or '无'
                                 for key, kind in [('insight-description-input', 'decisive'),
                                                   ('non-decisive-insight-description-input', 'supporting')]}},
            'text_fields': text_fields,
            'selection': {'field': prefix + '-achievement-select',
                          'label': '已达成' if stats[role]['attained'] else '未达成'},
            'screenshots': shots, 'evaluation': evaluation, 'submitted': False}


def prepare(root, role, evaluation):
    value = fields(root, role, evaluation)
    directory = Path(root).resolve() / 'browser' / 'model-fields' / hash_json(value)
    require(not directory.is_symlink(), '模型填表目录不能为符号链接')
    spec = directory / 'spec.json'
    if spec.exists():
        require(read_json(spec) == value, '已有模型填表输入已被修改')
    else:
        write_json(spec, value)
    return {'spec': str(spec), 'role': role, 'screenshots': len(value['screenshots']),
            'next': '真实网页精确回读后填入；上传及阶段确认另行核验，不自动提交'}


def validate_spec(file):
    file = Path(file)
    require(file.is_file() and not file.is_symlink() and not file.parent.is_symlink(), '填表输入须为普通文件')
    value = read_json(file)
    require(hash_json(value) == file.parent.name, '填表输入哈希已改变')
    expected_path = Path(value['task_root']) / 'browser' / 'model-fields' / file.parent.name / 'spec.json'
    require(file.resolve() == expected_path.resolve(), '填表输入不属于本题目录')
    require(fields(value['task_root'], value['role'], value['evaluation']) == value,
            '冻结题、回复、考点判断或截图已变化，旧填表输入失效')
    return value
