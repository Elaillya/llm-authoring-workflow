"""Five-model point-based ordering and complete submission export."""
from pathlib import Path
import copy
import re
import shutil
import tempfile
from .core import (ALL_ROLES, ARENA_ROLES, ROLES, active_question, hash_json,
                   read_response, require, sha, write_json)
from .authoring import check_three, evaluation_template, export_authoring, validated_models
from .arena import validate_arena_evidence, validate_names
from .delivery import model_files, named_text, reply_link


def five_evaluation_template(root, authoring_evaluation):
    require(check_three(root, authoring_evaluation)['three_model_gate'], '先通过三模型出题门槛')
    for role in ARENA_ROLES:
        validate_arena_evidence(root, role)
    result = evaluation_template(root, ALL_ROLES, include_supporting=True)
    result['reviewer'] = authoring_evaluation['reviewer']
    for role in ROLES:
        for point, judgment in authoring_evaluation['models'][role]['points'].items():
            result['models'][role]['points'][point] = copy.deepcopy(judgment)
    return result


def check_five(root, evaluation):
    stats = validated_models(root, evaluation, ALL_ROLES, include_supporting=True)
    validate_names(root, [stats[role]['name'] for role in ARENA_ROLES])
    require(not stats['seed']['attained'] and (stats['gpt']['attained'] or stats['claude']['attained']), '三模型区分度未通过，保留真实结果后修订')
    # Fifth-phase policy: whole-decisive attainment first; total point count within each tier.
    ordered = sorted(ALL_ROLES, key=lambda role: (stats[role]['attained'], stats[role]['total_met']), reverse=True)
    groups = []
    previous = None
    for role in ordered:
        key = (stats[role]['attained'], stats[role]['total_met'])
        if key != previous:
            groups.append([])
            previous = key
        groups[-1].append(role)
    order = ' > '.join(' = '.join(stats[role]['name'] for role in group) for group in groups)
    return {'phase': 'five_model_evaluation', 'three_model_gate': True, 'models': stats,
            'groups': groups, 'order': order, 'models_in_order': list(ALL_ROLES)}


def attainment_notes(stat):
    return '\n\n'.join(f'{item["id"]}（{"决定性" if item["kind"]=="decisive" else "非决定性"}）：'
                       f'{"满足" if item["met"] else "不满足"}；原因：{item["reason"]}'
                       + ('；原文依据：' + ' / '.join(item['quotes']) if item['quotes'] else '')
                       for item in stat['judgments'])


def ranking_template(root, evaluation):
    current = active_question(root)
    result = check_five(root, evaluation)
    notes = {}
    for role, stat in result['models'].items():
        notes[role] = (f'全部决定性考点{"达成" if stat["attained"] else "未达成"}，决定性点{stat["decisive_met"]}/{stat["decisive_total"]}，'
                       f'全部考点{stat["total_met"]}/{stat["total_points"]}。\n\n' + attainment_notes(stat))
    return {'schema_version': 1, 'phase': 'ranking', 'task_id': current['question']['task_id'],
            'question_sha256': current['question_sha256'], 'evaluation_sha256': hash_json(evaluation),
            'reviewer': evaluation['reviewer'], 'groups': result['groups'], 'order': result['order'],
            'display_names': {role: stat['name'] for role, stat in result['models'].items()},
            'summary': f'排序为{result["order"]}。全部决定性考点达成的模型先于未全部达成的模型；'
                       '同一梯队按全部核心考点满足数比较，满足数相同时并列。以下逐模型列出满足和未满足的具体考点及依据。',
            'models': notes}


def ranking_notes(ranking, names=None):
    names = names or ranking.get('display_names')
    require(isinstance(names, dict) and set(names) == set(ALL_ROLES), '排序备注需要五个模型的实际名称')
    return '总结：' + named_text(ranking['summary'], names) + '\n\n' + '\n\n'.join(
        f'{names[role]}：\n\n{named_text(ranking["models"][role], names)}' for role in ALL_ROLES)


def validate_ranking(root, evaluation, ranking):
    expected = ranking_template(root, evaluation)
    for key in ('schema_version', 'phase', 'task_id', 'question_sha256', 'evaluation_sha256', 'groups'):
        require(ranking.get(key) == expected[key], '排序与当前题目、五模型判断或考点优先级不一致：' + key)
    # Historical records remain usable without rewriting their ordinal order.
    legacy = ' > '.join(' = '.join(f'模型{ALL_ROLES.index(role)+1}' for role in group) for group in expected['groups'])
    require(ranking.get('order') in (expected['order'], legacy), '排序与当前题目、五模型判断或考点优先级不一致：order')
    if 'display_names' in ranking:
        require(ranking['display_names'] == expected['display_names'], '排序中的模型名称与真实原件不一致')
    require(isinstance(ranking.get('reviewer'), str) and ranking['reviewer'].strip(), '排序需记录实际执行者')
    require(isinstance(ranking.get('summary'), str) and ranking['summary'].strip(), '排序理由需要总结')
    require(set(ranking.get('models', {})) == set(ALL_ROLES), '排序理由需覆盖全部五个模型')
    for role in ALL_ROLES:
        require(isinstance(ranking['models'][role], str) and ranking['models'][role].strip(), '每个模型需要具体考点达成性备注')
    require(len(re.sub(r'\s', '', ranking_notes(ranking, expected['display_names']))) >= 500, '排序理由（总结＋逐模型说明）不少于500字')
    return check_five(root, evaluation)


def submission_markdown(fields):
    q = fields
    lines = ['# 完整出题与模型排序提交', '\n## 题目编号\n', q['task_id'], '\n## 题目 prompt\n', q['prompt'], '\n## 题目类型\n', q['question_type'],
             '\n## 关键洞察（Insight）\n', f'机制：{q["insight"]["mechanism"]}\n\n优先级：{q["insight"]["priority"]}\n\n核心结论：{q["insight"]["conclusion"]}']
    for field, title in [('decisive_points', '决定性核心考点'), ('supporting_points', '非决定性核心考点')]:
        lines.append('\n## ' + title + '\n')
        lines.extend(['无'] if q[field] == '无' else [f'- {p["id"]}：{p["criterion"]}' for p in q[field]])
    for role in ALL_ROLES:
        model = fields['models'][role]
        lines.extend([f'\n## {model["display_name"]}\n', reply_link(model),
                      '\n### 是否达成全部决定性核心考点\n', '是' if model['attained'] else '否',
                      '\n### 达成性备注\n', model['attainment_notes']])
        if model.get('screenshot'):
            lines.append(f'\n截图：[完整API渲染截图]({model["screenshot"]})')
        else:
            lines.append('\nArena 截图由用户另行向甲方提交。')
    lines.extend(['\n## 五模型核心考点达成性排序\n', fields['ranking'], '\n## 排序理由备注\n', fields['ranking_notes'],
                  '\n## 出题说明备注\n', fields['author_notes'], '\n## 材料来源说明\n',
                  '前三份回复为保存的API原文；两份Arena回复为用户提供的Markdown，工具未独立核验Arena页面、模式和随机过程。'])
    return '\n'.join(lines) + '\n'


def export_complete(root, evaluation, review, ranking, output):
    result = validate_ranking(root, evaluation, ranking)
    output = Path(output).absolute()
    require(not output.exists(), '提交目录已存在，拒绝覆盖；请使用新的交付版号')
    for name in ('responses', 'revisions', 'attempts', 'arena-input', 'evaluations', 'drafts'):
        require(not output.resolve().is_relative_to((Path(root) / name).resolve()), '提交不能写入原件、考点、输入或评估目录')
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.complete-export-', dir=output.parent))
    try:
        # Reuse the unchanged three-response screenshot and API-evidence checks.
        authoring = copy.deepcopy(evaluation)
        authoring['phase'] = 'authoring'
        decisive = {p['id'] for p in active_question(root)['question']['points'] if p['kind'] == 'decisive'}
        authoring['models'] = {role: {'response_sha256': evaluation['models'][role]['response_sha256'],
                                     'points': {key: value for key, value in evaluation['models'][role]['points'].items() if key in decisive}}
                              for role in ROLES}
        package = staging / 'package'
        export_authoring(root, authoring, review, package)
        from .core import read_json
        fields = read_json(package / 'fields.json')
        names = {role: stat['name'] for role, stat in result['models'].items()}
        paths = model_files(names)
        fields.update({'phase': 'complete', 'ranking': result['order'], 'ranking_groups': result['groups'],
                       'models_in_order': list(ALL_ROLES), 'ranking_notes': ranking_notes(ranking, names)})
        for index, role in enumerate(ALL_ROLES, 1):
            item = read_response(root, role)
            stat = result['models'][role]
            if role in ARENA_ROLES:
                validate_arena_evidence(root, role, item)
                shutil.copyfile(item['directory'] / 'reply.md', package / paths[role])
                evidence = package / 'evidence' / role
                evidence.mkdir()
                for name in ('metadata.json', 'arena-input.md'):
                    shutil.copyfile(item['directory'] / name, evidence / name)
                fields['models'][role] = {'ordinal': index, 'display_name': item['meta']['display_name'],
                                         'requested_model': item['meta']['model'], 'returned_model': item['meta']['returned_model'],
                                         'reply_markdown': item['text'], 'screenshot': None,
                                         'source_kind': 'arena_manual', 'screenshot_submission': 'user_submits_separately'}
            fields['models'][role].update({'attained': stat['attained'], 'attainment_notes': attainment_notes(stat),
                                         'reply_file': paths[role], 'decisive_met': stat['decisive_met'], 'total_met': stat['total_met']})
        (package / '提交信息.md').write_text(submission_markdown(fields), encoding='utf-8')
        write_json(package / 'fields.json', fields)
        write_json(package / 'authoring-evaluation.json', authoring)
        write_json(package / 'evaluation.json', evaluation)
        write_json(package / 'ranking.json', ranking)
        from . import VERSION
        current = active_question(root)
        write_json(package / 'handoff.json', {'schema_version': 1, 'kind': 'llm_complete_submission', 'workflow_version': VERSION,
                   'task_id': current['question']['task_id'], 'question_sha256': current['question_sha256'],
                   'submission_id': fields['task_id'],
                   'prompt_sha256': current['prompt_sha256'], 'rubric_sha256': current['rubric_sha256'],
                   'models_in_order': list(ALL_ROLES), 'three_model_gate': True, 'ranking': result['order'],
                   'next_workflow': 'platform_submission', 'arena_screenshots': 'user_submits_separately',
                   'next_action': '完整出题与五模型排序材料已生成，用户提交甲方；Arena截图由用户单独提供。'})
        (package / 'manifest.json').unlink()
        write_json(package / 'manifest.json', {'schema_version': 1, 'phase': 'complete',
                   'files': {p.relative_to(package).as_posix(): sha(p) for p in package.rglob('*') if p.is_file()}})
        require(not output.exists(), '提交期间目标被其他写入者占用')
        package.rename(output)
    finally:
        shutil.rmtree(staging)
    return {'phase': 'complete', 'output': str(output), 'markdown': str(output / '提交信息.md'), 'ranking': result['order'],
            'model_markdown': {role: str(output/path) for role, path in paths.items()},
            'models': 5, 'arena_screenshots_required': False}
