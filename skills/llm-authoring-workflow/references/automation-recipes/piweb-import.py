"""Import a verified pi-web archive through existing lab preparation/import gates.

Run with the repository Python runtime; no network, new model call or new lab command.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from llm_authoring.core import NAMES, active_question, read_json, require, validate_markdown
from llm_authoring.manual import PLACEHOLDER, prepare_model, import_model


def digest(data):
    return hashlib.sha256(data).hexdigest()


def import_archive(root, directory, replacement_id=None):
    root, directory = Path(root).resolve(), Path(directory).resolve()
    require(read_json(root/'TASK.json').get('platform_checks_required') is False,
            'pi-web 导入仅用于显式自动化任务')
    result = read_json(directory/'result.json')
    intent = read_json(directory/'create-intent.json')
    receipt = read_json(directory/'create-receipt.json')
    current = active_question(root)
    role = result.get('role')
    require(role in ('seed', 'gpt', 'claude') and role == intent.get('role'), '采集角色不一致')
    require(result.get('version') == intent.get('version') == current['revision'], '采集版本不是当前冻结版本')
    prompt = current['question']['prompt'].encode('utf-8')
    require(result.get('promptHash') == intent.get('promptHash') == digest(prompt), '采集题面与当前冻结题面不一致')
    raw = (directory/'reply.md').read_bytes()
    snapshot = (directory/'session.json').read_bytes()
    require(digest(raw) == result.get('replyHash') and digest(snapshot) == result.get('sessionHash'), '采集归档哈希不符')
    require(result.get('sessionId') == receipt.get('sessionId') and result.get('stopReason') == 'stop', '采集会话或结束状态不符')
    text = raw.decode('utf-8')
    validate_markdown(text)
    # These functions retain all existing Seed/choice/version/evidence gates.
    if replacement_id:
        from llm_authoring import replacement
        require(role in ('gpt','claude'), '补取仅用于GPT/Claude')
        replacement_dir = replacement._directory(root, replacement_id)
        plan = read_json(replacement_dir/'replacement.json')
        require(plan.get('role') == role and plan.get('question_sha256') == current['question_sha256'], '补取入口与角色或冻结版本不符')
        replacement._authorize_plan(root, plan)
        prepared = {'input_file': str(replacement_dir/(NAMES[role]+'.md')),
                    'prompt_file': str(replacement_dir/'prompt.md')}
    else:
        prepared = prepare_model(root, role)
    if prepared.get('already_imported'):
        require(Path(prepared['reply_file']).read_bytes() == raw, '已有不同有效回复，须按明确授权的替换流程处理')
        return {'status': 'already_imported', 'role': role, 'reply_file': prepared['reply_file']}
    slot = Path(prepared['input_file'])
    require(Path(prepared['prompt_file']).read_bytes() == prompt, '准备文件的题面不一致')
    old = slot.read_bytes()
    placeholder = old in (PLACEHOLDER.encode('utf-8'), PLACEHOLDER.replace('\n', '\r\n').encode('utf-8'))
    require(placeholder or old == raw, '填写文件已有不同内容，保留原件并核对')
    if old != raw:
        # Atomic replacement prevents a crash from leaving a truncated answer slot.
        from llm_authoring.filesystem import temporary_file
        fd, temp = temporary_file(slot.parent, '.piweb-')
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            require(slot.read_bytes() == old and active_question(root)['revision'] == current['revision'], '写入前目标已变化')
            os.replace(temp, slot)
        finally:
            Path(temp).unlink(missing_ok=True)
    imported = replacement.import_reply(root, role, replacement_id) if replacement_id else import_model(root, role)
    return {'status': 'imported', 'role': role, 'result': imported}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--replacement-id')
    args = parser.parse_args()
    try:
        print(json.dumps(import_archive(args.workspace, args.attempt, args.replacement_id), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({'status': 'needs_attention', 'reason': str(exc)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
