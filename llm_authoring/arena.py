"""Receive two real Arena replies through pre-created Markdown slots."""
from pathlib import Path
from .model_prompt import request_matches,validate_prompt_file
import re
from .core import (ARENA_ROLES, ROLES, active_question, hash_json, read_json,
                   read_response, require, response_dir, save_response,
                   validate_markdown, write_json)
from .authoring import check_three


SLOT_TEMPLATE = '---\nmodel_name: 待填写\n---\n待粘贴完整 Markdown 回复\n'


def normalized_name(name):
    return re.sub(r'[^a-z0-9]', '', name.casefold())


def validate_names(root, names):
    normalized = [normalized_name(name) for name in names]
    require(all(normalized), 'Arena 模型名必须包含可识别的完整型号')
    require(len(set(normalized)) == len(normalized), 'Arena 两个模型不能重复')
    fixed = set()
    for role in ROLES:
        meta = read_response(root, role)['meta']
        fixed.update(normalized_name(meta.get(key, '')) for key in ('display_name', 'model', 'returned_model'))
    for name in normalized:
        require('gpt' not in name and 'claude' not in name, 'Arena 模型不能属于 GPT 或 Claude 系列')
        require(name not in fixed and 'seed21turbo' not in name, 'Arena 模型不能与前三个模型相同')


def parse_slot(data):
    text = data.decode('utf-8')
    match = re.fullmatch(r'---\r?\nmodel_name:[ \t]*([^\r\n]+)\r?\n---\r?\n([\s\S]*)', text)
    require(match is not None, '保留文件开头的 model_name 和两条 ---，只填写型号及后面的原始 Markdown')
    name, reply = match.groups()
    name = name.strip()
    require(name and name != '待填写', '请填写 Arena 揭晓的完整模型名称')
    require(reply.strip() and reply.strip() != '待粘贴完整 Markdown 回复', '请粘贴完整 Arena Markdown 回复')
    validate_markdown(reply)
    return name, reply


def prepare_arena(root, evaluation):
    root = Path(root)
    require(check_three(root, evaluation)['three_model_gate'], '先通过三模型出题门槛，再准备 Arena 输入')
    from .platform_checks import final_gate
    final_gate(root,evaluation)
    current = active_question(root)
    directory = root / 'arena-input' / current['revision']
    require(not directory.is_symlink() and directory.resolve().is_relative_to(root.resolve()), 'Arena 输入目录不能为符号链接或逃逸题目目录')
    directory.mkdir(parents=True, exist_ok=True)
    request = {key: current[key] for key in ('revision', 'question_sha256', 'prompt_sha256', 'rubric_sha256')}
    request.update({'schema_version': 1, 'task_id': current['question']['task_id'],
                    'prompt': current['question']['prompt'], 'prompt_policy':'prompt_only', 'source': 'https://arena.ai/search',
                    'capture_instructions': 'Search 联网模式、Battle Mode、新会话；按偏好揭晓型号，两个模型均须合规。',
                    'provenance': '用户提供 Markdown，工具不能独立确认真实页面的模式、会话和随机性；截图由用户单独提交。'})
    manifest = directory / 'request.json'
    if manifest.exists():
        recorded=read_json(manifest)
        require(request_matches(recorded,request), 'Arena 输入绑定已变化，请保留旧文件并使用当前冻结版本')
        request=recorded
    else:
        write_json(manifest, request)
    slots = {}
    for index, role in enumerate(ARENA_ROLES, 4):
        path = directory / f'model-{index}.md'
        require(not path.is_symlink(), 'Arena 填写文件不能为符号链接')
        if not path.exists():
            path.write_text(SLOT_TEMPLATE, encoding='utf-8')
        slots[role] = str(path)
    prompt = directory / 'arena-prompt.md'
    require(not prompt.is_symlink(),'Arena题面不能为符号链接')
    if prompt.exists():validate_prompt_file(prompt,request)
    else:
        require(request.get('prompt_policy')=='prompt_only','旧Arena题面缺失，先恢复原件，不重建旧格式指令')
        prompt.write_bytes(current['question']['prompt'].encode('utf-8'))
    guide = directory / 'README.md'
    if not guide.exists():
        guide.write_text('# 填入 Arena 的两个模型回复\n\n'
                         '原样使用 arena-prompt.md 的题面，不另加格式要求，在 https://arena.ai/search 的 Search + Battle 新会话获取随机回复，揭晓模型名称。'
                         '两个模型不得重复，不得与前三个相同，不得为 GPT/Claude 系列。\n\n'
                         '打开 model-4.md、model-5.md：把 model_name 后的“待填写”替换为实际完整型号；'
                         '把“待粘贴完整 Markdown 回复”替换为对应回复全文，保留开头两条 ---。保存后在侧栏说“已填好两个 Arena 回复，继续排序”。\n\n'
                         '这里只需要两份 Markdown。Arena 截图由你自行向甲方提交。\n', encoding='utf-8')
    return {'stage': 'awaiting_arena_markdown', 'input_files': slots, 'prompt_file': str(prompt),
            'screenshots_required': False, 'next': '填写两份已创建的 Markdown；保存后由助手导入、逐点评估并排序'}


def import_arena(root,evaluation=None):
    root = Path(root)
    current = active_question(root)
    directory = root / 'arena-input' / current['revision']
    request = read_json(directory / 'request.json')
    require(request.get('schema_version') == 1 and request.get('task_id') == current['question']['task_id'], 'Arena 输入不属于当前题目')
    for key in ('revision', 'question_sha256', 'prompt_sha256', 'rubric_sha256'):
        require(request.get(key) == current[key], 'Arena 输入绑定已过期，请按当前冻结题目准备新输入文件')
    require(request.get('prompt')==current['question']['prompt'],'Arena请求题面与冻结prompt不一致')
    validate_prompt_file(directory/'arena-prompt.md',request)
    from .platform_checks import final_gate,required
    if required(root):
        require(evaluation is not None,'Arena导入需要显式提供当前三模型判断 --evaluation')
        require(check_three(root,evaluation)['three_model_gate'],'Arena导入前重新确认当前三模型门槛')
        final_gate(root,evaluation)
    records = []
    for index, role in enumerate(ARENA_ROLES, 4):
        path = directory / f'model-{index}.md'
        require(path.is_file() and not path.is_symlink(), 'Arena 填写文件缺失或不是普通文件')
        raw = path.read_bytes()
        name, reply = parse_slot(raw)
        records.append((role, name, reply, raw))
    validate_names(root, [record[1] for record in records])
    # Check every slot before storing either reply; filled slots are never overwritten.
    for role, name, reply, raw in records:
        if response_dir(root, role).exists():
            existing = read_response(root, role)
            validate_arena_evidence(root, role, existing)
            require(existing['text'] == reply and existing['meta']['display_name'] == name
                    and (existing['directory'] / 'arena-input.md').read_bytes() == raw,
                    '已有 Arena 原件与填入内容不同，保留原件；确需换样本请建立新题面版本')
    imported = {}
    for role, name, reply, raw in records:
        if not response_dir(root, role).exists():
            save_response(root, role, reply,
                          {'display_name': name, 'model': name, 'returned_model': name,
                           'source_kind': 'arena_manual', 'completion_status': 'complete',
                           'evidence_status': 'user_provided_markdown', 'raw_response_file': 'arena-input.md',
                           'arena_request': request, 'arena_request_sha256': hash_json(request),
                           'screenshot_submission': 'user_submits_separately'}, raw=raw)
        imported[role] = {'display_name': name, 'complete': True, 'screenshots_required': False}
    return {'stage': 'five_model_evaluation', 'models': imported}


def validate_arena_evidence(root, role, item=None):
    require(role in ARENA_ROLES, 'Arena 角色不合法')
    item = item or read_response(root, role)
    meta = item['meta']
    require(meta.get('source_kind') == 'arena_manual' and meta.get('evidence_status') == 'user_provided_markdown', '缺少用户提供的 Arena Markdown 原件')
    name, reply = parse_slot((item['directory'] / 'arena-input.md').read_bytes())
    require(name == meta.get('display_name') and reply == item['text'], 'Arena 型号或正文与保存的输入原件不一致')
    request = meta.get('arena_request', {})
    require(hash_json(request) == meta.get('arena_request_sha256')
            and request.get('prompt_sha256') == active_question(root)['prompt_sha256']
            and hash_json(request.get('prompt')) == request.get('prompt_sha256')
            and request.get('task_id') == active_question(root)['question']['task_id'], 'Arena 原件题面绑定失效')
    validate_names(root, [name])
    return item
