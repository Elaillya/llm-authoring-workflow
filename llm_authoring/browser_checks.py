"""Import input-bound checks observed on the real platform page; never call its API."""
from pathlib import Path
import json
from .core import Error, read_json, write_json, require, hash_json, now, active_question
from . import platform_checks as qa


def binding(root):
    value = read_json(Path(root) / 'browser' / 'binding.json')
    require(all(isinstance(value.get(k), str) and value[k].isdigit()
                for k in ('task_id', 'item_id', 'template_id'))
            and value.get('template_type') == '1000', '先核对平台题目ID及模板绑定')
    return {k: value[k] for k in ('task_id', 'item_id', 'template_id', 'template_type')}


def descriptions(root, stages, q=None, evaluation=None):
    require(read_json(Path(root) / 'TASK.json').get('platform_check_mode') == 'browser',
            '此命令仅用于独立浏览器试验工作区')
    require(stages and set(stages) <= {'question', 'criteria', 'attainment'}
            and len(set(stages)) == len(stages), '未知或重复的网页质检类型')
    if any(s != 'question' for s in stages):
        _, stats = qa.authoring_evaluation(root, evaluation)
        require(stats['three_model_gate'], qa.THREE_MODEL_REJECTION)
        from .check_policy import require_choice
        require(require_choice(root)['choice'] == 'required', '本题未启用后两项质检')
        qa.question_gate(root, active_question(root)['question'])
    return {s: qa.descriptor(root, s, q=q, evaluation=evaluation)[0] for s in stages}


def retryable(result, stage):
    if result['state'] in ('service_error', 'needs_cookie'):
        return True
    if result['state'] != 'needs_review':
        return False
    _, record = qa.verified_record(Path(result['attempt']), stage)
    try:
        outer = json.loads(record['transport']['response_text'])
        return outer.get('BaseResp', {}).get('StatusCode') == 0 and outer.get('response') in ('', None)
    except (ValueError, TypeError, AttributeError):
        return False


def prepare(root, stages, q=None, evaluation=None, retry_reason=None):
    root = Path(root).resolve()
    with qa.check_lock(root):
        records = descriptions(root, stages, q, evaluation)
        previous = {s: qa.latest(root, request) for s, request in records.items()}
        cached = {s: result for s, result in previous.items()
                  if result and result['state'] in ('passed', 'failed', 'disputed')}
        pending = {s: request for s, request in records.items() if s not in cached}
        if retry_reason is not None:
            require(isinstance(retry_reason, str) and retry_reason.strip(), '重试须说明已确认的执行错误')
            require(pending, '已有有效专业结果，不能对相同输入重跑')
            for stage in pending:
                require(previous[stage] is not None, '先导入原请求的完整完成回执；未知或在途请求不能重试')
                require(retryable(previous[stage], stage), '原结果须人工核对，不能自动重试')
        elif any(previous[s] for s in pending):
            raise Error('已有同输入的执行异常记录；核对原件后用 --retry-reason 明确重试，未知结果不得重发')
        if not pending:
            return {'cached': cached, 'new_checks': 0}
        spec = {'schema_version': 1, 'binding': binding(root),
                'expected': {s: v['payload'] for s, v in pending.items()},
                'records': pending}
        if retry_reason is not None:
            spec['retry'] = {'reason': retry_reason.strip(), 'prior_results': {
                s: {'attempt': previous[s]['attempt'],
                    'record_sha256': hash_json(read_json(Path(previous[s]['attempt']) / 'result.json'))}
                for s in pending}}
        base = root / 'browser-checks'
        require(not base.is_symlink(), '网页质检目录不能为符号链接')
        if retry_reason is not None:
            # A different human-readable reason must not create a second call
            # from the same failed receipt while its first retry is unresolved.
            for saved in sorted(base.glob('*/spec.json')):
                require(saved.is_file() and not saved.is_symlink() and not saved.parent.is_symlink(),
                        '网页质检输入须为普通文件')
                old = read_json(saved)
                require(hash_json(old) == saved.parent.name, '已有网页质检输入被改写')
                if all(old.get(k) == spec[k] for k in ('binding', 'expected', 'records')) \
                        and old.get('retry', {}).get('prior_results') == spec['retry']['prior_results']:
                    return {'cached': cached, 'spec': str(saved),
                            'journal': str(saved.parent / 'journal'), 'existing_attempt': True,
                            'new_checks': 0,
                            'next': '同一错误回执后的尝试已准备或已发出；核对、等待或导入原尝试，不再点击新请求'}
        directory = base / hash_json(spec)
        require(not directory.is_symlink(), '网页质检输入目录不能为符号链接')
        file = directory / 'spec.json'
        if file.exists():
            require(read_json(file) == spec, '网页质检输入被改写，保留原件核对')
        else:
            write_json(file, spec)
        return {'cached': cached, 'spec': str(file), 'journal': str(directory / 'journal'),
                'new_checks': len(pending),
                'next': '通过真实页面按钮执行并观察原请求；未知结果先核对，不重复发送'}


def read_completed_events(directory, spec):
    file = directory / 'journal' / 'events.jsonl'
    require(file.is_file() and not file.is_symlink(), '缺少真实浏览器网络事件记录')
    text = file.read_text()
    require(text.endswith('\n'), '事件尾部不完整，保留原件后核对')
    previous = None
    states = {}
    for number, line in enumerate(text.splitlines(), 1):
        row = json.loads(line)
        checksum = row.pop('sha256')
        require(row.get('sequence') == number and row.get('previous_sha256') == previous
                and hash_json(row) == checksum, '浏览器事件链已被改写')
        previous = checksum
        kind = row.get('type')
        if number == 1:
            require(kind == 'init' and row.get('spec_sha256') == hash_json(spec), '网页质检事件不属于当前输入')
            states = {s: {'state': 'not_started'} for s in spec['expected']}
            continue
        stage = row.get('stage')
        require(stage in states, '浏览器事件的质检类型不匹配')
        value = states[stage]
        if kind == 'intent':
            require(value['state'] == 'not_started', '存在重复质检意图')
            value['state'] = 'awaiting_network'
        elif kind == 'request':
            require(value['state'] == 'awaiting_network' and row.get('request_id')
                    and row.get('input_sha256') == hash_json(spec['expected'][stage]), '浏览器实际请求与题目输入不匹配')
            value.update(state='running', request_id=row['request_id'])
        elif kind=='unmatched_request':
            require(value['state']=='awaiting_network' and row.get('request_id')
                    and hash_json(row.get('observed_input'))==row.get('input_sha256'),'不同输入的观察记录不完整')
            value.update(state='running_unverified',request_id=row['request_id'])
        elif kind == 'response':
            require(value['state'] in ('running','running_unverified') and row.get('request_id') == value.get('request_id')
                    and type(row.get('http_status')) is int, '浏览器响应绑定不匹配')
            value['http_status'] = row['http_status']
        elif kind == 'complete':
            require(value['state'] in ('running','running_unverified') and row.get('request_id') == value.get('request_id')
                    and 'http_status' in value and isinstance(row.get('body'), str), '浏览器质检完成证据不完整')
            value.update(state='unconfirmed' if value['state']=='running_unverified' else 'complete', response_text=row['body'])
        elif kind in ('uncertain', 'network_failed'):
            require(value['state'] in ('awaiting_network', 'running','running_unverified'), '质检异常状态不匹配')
            value['state'] = 'unconfirmed'
        else:
            raise Error('未知的浏览器质检事件')
    return states


def import_results(root, directory, q=None, evaluation=None):
    root = Path(root).resolve()
    directory = Path(directory).absolute()
    spec = read_json(directory / 'spec.json')
    expected_directory = root / 'browser-checks' / hash_json(spec)
    require(directory == expected_directory and directory.resolve() == directory
            and spec.get('binding') == binding(root), '网页质检记录不属于当前题目')
    with qa.check_lock(root):
        current = descriptions(root, tuple(spec['records']), q, evaluation)
        require(current == spec['records'] and spec['expected'] == {s: r['payload'] for s, r in current.items()},
                '题目、Insight、考点或模型判断已变化，旧网页结果不适用')
        states = read_completed_events(directory, spec)
        require(all(v['state']=='complete' for v in states.values()),
                '网页质检尚未取得全部完整网络结果，先核对页面，不自动重发')
        results = {}
        for stage, value in states.items():
            transport = {'http_status': value['http_status'], 'response_text': value['response_text'],
                         'truncated': False, 'source': 'browser_network',
                         'platform_binding': spec['binding'], 'network_request_id': value['request_id']}
            request = current[stage]
            record = {'schema_version': 1, 'binding': request['binding'], 'request_sha256': hash_json(request),
                      'response_sha256': hash_json(transport), 'transport': transport,
                      'parsed': qa.parse_response(stage, transport), 'completed_at': now()}
            base = qa.records_directory(root)
            prefix = stage + '-browser-' + hash_json(request)
            attempts = sorted(base.glob(prefix + '*'))
            matching = []
            for saved in attempts:
                require(saved.is_dir() and not saved.is_symlink(), '网页检查原件须为普通目录')
                old_request, old = qa.verified_record(saved, stage)
                require(old_request == request, '网页检查原件的输入已变化')
                if old['transport'] == transport:
                    matching.append(saved)
            if not matching:
                # Monotonic suffix preserves latest() ordering and legacy receipts.
                sequences = [int(p.name[len(prefix)+1:].split('-')[0])
                             for p in attempts if p.name.startswith(prefix+'-')]
                number = max(sequences, default=0) + 1
                attempt = base / (prefix + '-' + str(number).zfill(6))
                require(not attempt.exists(), '网页检查尝试已存在，保留原件后重读')
                write_json(attempt / 'request.json', request)
                write_json(attempt / 'result.json', record)
            results[stage] = qa.latest(root, request)
        from .lessons import observe_platform
        for stage,result in results.items():observe_platform(root,stage,result,q)
        return results
