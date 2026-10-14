"""Stage user-provided official-site Markdown behind the Seed-first gate."""
from pathlib import Path
from .core import (Error, NAMES, ROLES, active_question, hash_json, read_json,
                   read_response, require, response_dir, save_response,
                   validate_markdown, write_json)

PLACEHOLDER = '待粘贴完整 Markdown 回复\n'
FORMAT_INSTRUCTION = '请使用 Markdown 格式回复，不要用最外层代码块包裹全文。'


def seed_screen(root, evaluation=None):
    from .authoring import check_seed
    current = active_question(root)
    path = Path(evaluation) if evaluation else Path(root) / 'evaluations' / ('seed-' + current['revision'] + '.json')
    require(path.is_file(), '先导入 Seed 回复并完成当前版本的决定性考点判断，再要求 GPT/Claude')
    value = read_json(path)
    require(check_seed(root, value)['continue_to_gpt_claude'],
            'Seed 已达成全部决定性考点，先修订候选并重新冻结，暂不要求 GPT/Claude 回复')
    return value


def input_directory(root):
    root = Path(root)
    directory = root / 'model-input' / active_question(root)['revision']
    require(not directory.is_symlink() and directory.resolve().is_relative_to(root.resolve()),
            '模型输入目录不能为符号链接或逃逸题目目录')
    return directory


def model_request(root, role, screen=None):
    current = active_question(root)
    request = {key: current[key] for key in ('revision', 'question_sha256', 'prompt_sha256', 'rubric_sha256')}
    request.update({'schema_version': 1, 'task_id': current['question']['task_id'],
                    'role': role, 'display_name': NAMES[role], 'prompt': current['question']['prompt'],
                    'format_instruction': FORMAT_INSTRUCTION,
                    'source_kind': 'official_manual', 'screenshot_submission': 'user_submits_separately'})
    if screen is not None:
        request['seed_evaluation_sha256'] = hash_json(screen)
        request['seed_response_sha256'] = screen['models']['seed']['response_sha256']
    return request


def prompt_text(request):
    return request['prompt'] + '\n\n' + FORMAT_INSTRUCTION + '\n'


def validate_prompt(directory, request):
    prompt = directory / 'prompt.md'
    require(prompt.is_file() and not prompt.is_symlink()
            and prompt.read_text(encoding='utf-8') == prompt_text(request),
            '发送给模型的题面文件已改变或缺失，请恢复冻结题面')
    return prompt


def prepare_model(root, role, evaluation=None):
    require(role in ROLES, '模型角色不合法')
    root = Path(root)
    from .platform_checks import question_gate
    question_gate(root,active_question(root)['question'])
    screen = seed_screen(root, evaluation) if role != 'seed' else None
    if response_dir(root, role).exists():
        item = read_response(root, role)
        validate_model_evidence(root, role, item)
        return {'role': role, 'display_name': NAMES[role], 'already_imported': True,
                'reply_file': str(item['directory'] / 'reply.md'),
                'next': '已有完整原回复，沿用原件并按当前冻结标准评估，无需再次提供'}
    directory = input_directory(root)
    directory.mkdir(parents=True, exist_ok=True)
    request = model_request(root, role, screen)
    manifest = directory / (role + '-request.json')
    if manifest.exists():
        require(read_json(manifest) == request, '填写文件绑定已变化，保留旧文件并使用新的冻结版本')
    else:
        write_json(manifest, request)
    slot = directory / (NAMES[role] + '.md')
    require(not slot.is_symlink(), '模型填写文件不能为符号链接')
    if not slot.exists():
        slot.write_text(PLACEHOLDER, encoding='utf-8')
    prompt = directory / 'prompt.md'
    require(not prompt.is_symlink(), '题面文件不能为符号链接')
    if prompt.exists():
        validate_prompt(directory, request)
    else:
        prompt.write_text(prompt_text(request), encoding='utf-8')
    guide = directory / 'README.md'
    require(not guide.is_symlink(), '模型填写说明不能为符号链接')
    if not guide.exists():
        guide.write_text('# 填入官方网页的完整回答\n\n'
                         '复制 prompt.md 到指定型号的官方页面新会话。GPT/Claude 使用项目要求的中高推理模式。'
                         '如果网页不能确认规定型号，先说明问题，不用相近型号代替。\n\n'
                         '模型文件已经创建：将“待粘贴完整 Markdown 回复”替换为回答原文全文并保存，'
                         '不增加标题、来源声明或外层代码块，不改写或补写回答。'
                         '保存后在 Codex 侧栏说“已填好 Seed 回复，继续”或“已填好 GPT 和 Claude 回复，继续”。\n\n'
                         '先收 Seed；其未达成全部决定性考点后才创建 GPT 和 Claude 的填写文件。'
                         '所有官方网页截图由你另行提交甲方，工作区只接收 Markdown。\n', encoding='utf-8')
    return {'stage': 'awaiting_seed_markdown' if role == 'seed' else 'awaiting_gpt_claude_markdown',
            'role': role, 'display_name': NAMES[role], 'input_file': str(slot),
            'prompt_file': str(prompt), 'screenshots_required': False,
            'next': '在官方页面获得对应型号的完整回答，粘贴到已创建的模型文件并保存'}


def import_model(root, role, evaluation=None):
    require(role in ROLES, '模型角色不合法')
    root = Path(root)
    from .platform_checks import question_gate
    question_gate(root,active_question(root)['question'])
    screen = seed_screen(root, evaluation) if role != 'seed' else None
    directory = input_directory(root)
    request = read_json(directory / (role + '-request.json'))
    require(request == model_request(root, role, screen), '模型输入绑定已过期或与当前 Seed 判断不一致')
    validate_prompt(directory, request)
    slot = directory / (NAMES[role] + '.md')
    require(slot.is_file() and not slot.is_symlink(), '缺少工具创建的模型填写文件')
    raw = slot.read_bytes()
    reply = raw.decode('utf-8')
    require(reply.strip() != PLACEHOLDER.strip(), '请把占位文字替换为对应模型的完整 Markdown 回复')
    validate_markdown(reply)
    if response_dir(root, role).exists():
        item = validate_manual_evidence(root, role)
        require(item['text'] == reply and (item['directory'] / 'model-input.md').read_bytes() == raw,
                '填入内容与已保存原件不同，保留原件；题面改变请建立新冻结版本')
    else:
        save_response(root, role, reply,
                      {'display_name': NAMES[role], 'model': NAMES[role], 'returned_model': NAMES[role],
                       'model_identity_check': 'user_declared_official_site_model',
                       'source_kind': 'official_manual', 'completion_status': 'complete',
                       'evidence_status': 'user_provided_markdown', 'raw_response_file': 'model-input.md',
                       'manual_request': request, 'manual_request_sha256': hash_json(request),
                       'screenshot_submission': 'user_submits_separately'}, raw=raw)
    return {'role': role, 'display_name': NAMES[role], 'complete': True, 'screenshots_required': False,
            'next': '按冻结标准逐项判断 Seed 决定性考点' if role == 'seed' else '三份原文齐备后统一完成三模型决定性考点判断'}


def validate_manual_evidence(root, role, item=None):
    require(role in ROLES, '模型角色不合法')
    item = item or read_response(root, role)
    meta = item['meta']
    require(meta.get('source_kind') == 'official_manual'
            and meta.get('evidence_status') == 'user_provided_markdown', '需要用户提供的官方页面 Markdown 原件')
    raw = (item['directory'] / 'model-input.md').read_bytes()
    require(raw.decode('utf-8') == item['text'] and meta.get('display_name') == NAMES[role],
            '模型名称或正文与用户填写的原件不一致')
    request = meta.get('manual_request', {})
    current = active_question(root)
    require(hash_json(request) == meta.get('manual_request_sha256')
            and request.get('prompt_sha256') == current['prompt_sha256']
            and hash_json(request.get('prompt')) == request.get('prompt_sha256')
            and request.get('task_id') == current['question']['task_id']
            and request.get('role') == role and request.get('display_name') == NAMES[role],
            '用户提供的原件与题目或指定模型绑定失效')
    if role != 'seed':
        require(request.get('seed_evaluation_sha256')
                and request.get('seed_response_sha256') == read_response(root, 'seed')['meta']['reply_sha256'],
                'GPT/Claude 缺少先行 Seed 判断及原回复绑定')
    return item


def validate_model_evidence(root, role, item=None):
    item = item or read_response(root, role)
    task = read_json(Path(root) / 'TASK.json') if (Path(root) / 'TASK.json').exists() else {}
    if task.get('response_mode') == 'official_manual' or item['meta'].get('source_kind') == 'official_manual':
        validate_manual_evidence(root, role, item)
        return None
    # Historical API originals can still be exported without making new calls.
    from .authoring import validate_api_evidence
    return validate_api_evidence(item, role)


def manual_status(root):
    root = Path(root)
    complete = {}
    for role in ROLES:
        try:
            item = read_response(root, role)
            if item['meta'].get('source_kind') == 'official_manual':
                validate_manual_evidence(root, role, item)
            complete[role] = True
        except (Error, OSError, ValueError, KeyError, TypeError):
            complete[role] = False
    directory = input_directory(root)
    result = {'model_input_files': {role: str(directory / (NAMES[role] + '.md'))
                                 for role in ROLES if (directory / (NAMES[role] + '.md')).is_file()}}
    if not complete['seed']:
        result.update(stage='awaiting_seed_markdown', next='先创建 Seed 填写文件，等待用户提供完整原回复，再导入和判断')
    elif not all(complete.values()):
        try:
            seed_screen(root)
            result.update(stage='awaiting_gpt_claude_markdown', next='Seed 未达成全部决定性点；创建并等待 GPT 和 Claude 的完整 Markdown')
        except Error as exc:
            result.update(stage='seed_evaluation', next=str(exc))
    else:
        result.update(stage='three_model_evaluation', next='原回复齐备；判断三模型决定性考点，通过门槛后进入 Arena')
    return result
