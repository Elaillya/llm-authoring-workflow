"""Read recipe evidence for delivery; never dispatch requests or change workflow gates."""
from pathlib import Path
import hashlib
import shutil
from .core import ROLES, active_question, hash_json, read_json, read_response, require, sha, write_json
from .delivery import attainment_notes
from .text import insight_text

PREFIXES = dict(seed='doubao', gpt='gpt56', claude='claude')
BASE = ['question-input', 'insight-input']
RUBRIC = ['insight-description-input', 'non-decisive-insight-description-input']
SELECTIONS = ['question-type-radio', 'question-domain-select']


def platform_fields(root, evaluation=None, stats=None):
    """Generate the platform payload from frozen material and validated judgments."""
    q = active_question(root)['question']
    values = dict(zip(BASE, (q['prompt'], insight_text(q['insight']))))
    for kind, field in zip(('decisive', 'supporting'), RUBRIC):
        values[field] = '\n'.join(p['id']+'：'+p['criterion'] for p in q['points'] if p['kind'] == kind) or '无'
    selections = dict(zip(SELECTIONS, (q['question_type'].removesuffix('类'), q.get('domain','计算机科学'))))
    if stats is None and evaluation is not None:
        from .authoring import check_three
        checked = check_three(root, evaluation)
        require(checked['three_model_gate'], '平台模型填写前须满足三模型门槛')
        stats = checked['models']
    if stats is not None:
        for role, prefix in PREFIXES.items():
            values[prefix+'-markdown-input'] = read_response(root, role)['text']
            values[prefix+'-achievement-note-input'] = attainment_notes(stats[role])
            selections[prefix+'-achievement-select'] = '达成' if stats[role]['attained'] else '未达成'
    return {'values': values, 'selections': selections}


def _subset(payload, key):
    ids = BASE + (RUBRIC + [p+'-markdown-input' for p in PREFIXES.values()] if key != 'insight' else [])
    selects = SELECTIONS.copy()
    if key == 'attainment':
        ids += [p+'-achievement-note-input' for p in PREFIXES.values()]
        selects += [p+'-achievement-select' for p in PREFIXES.values()]
    return {'values': {k: payload['values'][k].replace('\r\n','\n').replace('\r','\n') for k in ids},
            'selections': {k: payload['selections'][k] for k in selects}}


def capture_source(root, role, package=None):
    item = read_response(root, role)
    target = item['directory']/'capture-source.json'
    if not target.exists():
        return None
    source = read_json(target)
    require(source.get('kind') in ('piweb_auto','piweb_user') and source.get('role') == role
            and source.get('reply_sha256') == item['meta']['reply_sha256'], '采集来源与原回复不符')
    directory = Path(source['directory'])
    for name, digest in source['files'].items():
        require(Path(name).name == name and not (directory/name).is_symlink() and sha(directory/name) == digest,
                '采集来源证据已变化')
    result = read_json(directory/'result.json')
    prompt_hash = hashlib.sha256(active_question(root)['question']['prompt'].encode('utf-8')).hexdigest()
    require(result['replyHash'] == source['reply_sha256'] and result['promptHash'] == prompt_hash == source['prompt_hash'],
            '采集来源题面或原文不符')
    summary = {'kind': source['kind'], 'session_id': result['sessionId'],
               'display_model': result.get('model',{}).get('displayName'),
               'thinking_level': result.get('thinkingLevel'), 'exception_note': result.get('exceptionNote'),
               'reply_sha256': source['reply_sha256']}
    if package:
        destination = Path(package)/'evidence'/role/'capture'
        destination.mkdir(parents=True, exist_ok=True)
        for name in source['files']:
            if name != 'reply.md':
                shutil.copyfile(directory/name, destination/name)
        write_json(destination/'source.json', source)
    return summary


def _records(root):
    directory = Path(root)/'platform-web'
    if not directory.is_dir():
        return
    for p in sorted(directory.rglob('input.json')):
        if any(part.is_symlink() for part in (p, *p.parents)):
            continue
        yield p, read_json(p)


def web_evidence(root, expected, package=None):
    """Read current dependency-bound results, including old-version question checks."""
    records = list(_records(root))
    attempts = {key: [] for key in ('insight','core-point','attainment')}
    for input_path, binding in records:
        if binding.get('kind') not in ('checks','received-check'):
            continue
        require(binding.get('inputHash') == hash_json(binding['input']), '网页检查输入哈希不符')
        directory = input_path.parent
        for key in binding['keys']:
            if key not in attempts:
                continue
            current_input = _subset(binding['input'], key)
            valid = current_input == _subset(expected, key)
            result_path = directory/(key+'-result.json')
            error_path = directory/(key+'-error.json')
            files = [input_path]
            receipt = read_json(result_path) if result_path.exists() else read_json(error_path) if error_path.exists() else None
            if not receipt:
                intent_path=directory/(key+'-intent.json')
                intent=read_json(intent_path) if intent_path.exists() else {}
                attempts[key].append({'state':'unknown' if valid else 'input_changed', 'item_id':binding['itemId'],
                                      'evidence_directory':str(directory), 'conclusion':None, 'completed_at':'',
                                      'started_at':intent.get('startedAt',''),'prior_calls':intent.get('prior',{}).get('calls')})
                continue
            require(receipt.get('inputHash') == hash_json(current_input), '网页结果输入哈希不符')
            observed = receipt['observed']
            files.append(result_path if result_path.exists() else error_path)
            if binding['kind'] == 'checks':
                intent_path, dispatch_path = directory/(key+'-intent.json'), directory/(key+'-dispatch.json')
                intent, dispatch = read_json(intent_path), read_json(dispatch_path)
                baseline, calls = intent['prior'].get('calls'), observed.get('calls')
                linked = (type(calls) is int and type(baseline) is int and calls == baseline+1 or
                          baseline is None and calls == 1 and dispatch['after'].get('running') is True and dispatch['after'].get('calls') == 1 or
                          baseline is None and calls is None and dispatch['after'].get('running') is True)
                require(linked, '网页结果与派发无法关联')
                files += [intent_path, dispatch_path]
            else:
                require(receipt.get('source') == 'user' and binding.get('userStatement')
                        and receipt.get('association') == 'matched_prior_and_user_statement', '人工网页结果缺少接续关联')
                prior_dir = Path(receipt['priorDirectory'])
                prior_file = prior_dir/(key+'-error.json')
                if not prior_file.exists(): prior_file = prior_dir/(key+'-result.json')
                prior = read_json(prior_file)
                prior_binding = read_json(prior_dir/'input.json')
                require(hash_json(prior) == receipt['priorHash'] and prior_binding['itemId'] == binding['itemId']
                        and _subset(prior_binding['input'],key) == current_input
                        and type(prior['observed'].get('calls')) is int
                        and observed.get('calls') == prior['observed']['calls']+1, '人工网页结果前次记录已变化')
                files += [prior_file, prior_dir/'input.json']
            require(observed.get('running') is False, '网页结果尚在运行')
            conclusion = observed.get('conclusion')
            effective = result_path.exists() and observed.get('observation') == 'result_visible' and conclusion in ('通过','不通过')
            state = ('passed' if conclusion == '通过' else 'failed') if effective else 'service_error' if error_path.exists() else 'unknown'
            if not valid: state = 'input_changed'
            record = {'state':state, 'conclusion':conclusion if effective else None,
                      'item_id':binding['itemId'], 'source':'user' if binding['kind']=='received-check' else 'agent',
                      'calls':observed.get('calls'),
                      'completed_at':receipt.get('completedAt',''), 'evidence_directory':str(directory)}
            for feedback_path, feedback in records:
                if feedback.get('kind') != 'feedback' or feedback.get('key') != key or feedback.get('itemId') != binding['itemId']:
                    continue
                saved_path = feedback_path.parent/'result.json'
                if saved_path.exists() and feedback.get('checkCalls') == observed.get('calls') and feedback.get('resultHash') == hashlib.sha256((observed.get('resultText') or '').encode()).hexdigest():
                    saved = read_json(saved_path)
                    require(saved.get('status') == 'saved' and saved.get('note') == feedback.get('note'), '网页反馈保存记录不符')
                    record['feedback'] = {'label':saved['label'],'note':saved.get('note')}
                    files += [feedback_path,saved_path]
            if package:
                dest = Path(package)/'evidence/platform-web'/key/hashlib.sha256(str(directory).encode()).hexdigest()[:12]
                dest.mkdir(parents=True, exist_ok=True)
                for index, source in enumerate(dict.fromkeys(files)):
                    shutil.copyfile(source,dest/f'{index:02d}-{source.name}')
            attempts[key].append(record)
    if not any(attempts.values()):
        return None
    summary = {}
    for key, history in attempts.items():
        valid = [r for r in history if r['state'] != 'input_changed']
        item_ids = {r['item_id'] for r in valid}
        if len(item_ids) > 1:
            selected = {'state':'unknown','conclusion':None,'reason':'Multiple platform items; inspect target'}
        else:
            selected = max(valid,key=lambda r:r['completed_at']) if valid else {'state':'not_verified','conclusion':None}
            # A later unresolved dispatch must not expose an older successful result as current.
            unresolved=[r for r in valid if r['state']=='unknown']
            if any(not (r.get('started_at') and r['started_at'] < selected.get('completed_at','')
                        and type(r.get('prior_calls')) is int and type(selected.get('calls')) is int
                        and selected['calls'] > r['prior_calls']+1) for r in unresolved):
                selected = {'state':'unknown','conclusion':None,'reason':'Unresolved check attempt exists'}
        summary[key] = {**selected,'history':history}
    return {'source':'platform_web','checks':summary}


def source_text(models):
    lines = []
    for role, model in models.items():
        capture = model.get('capture_source')
        kind = capture['kind'] if capture else model.get('source_kind')
        label = {'piweb_auto':'由agent经pi-web采集并归档', 'piweb_user':'由用户获取，agent接收已有pi-web会话',
                 'official_manual':'用户提供的官方页面Markdown，型号与会话未独立核验',
                 'arena_manual':'用户提供的Arena Markdown，未独立核验模式和随机过程',
                 'api':'历史API原文，渲染图不等于官方网页截图'}.get(kind,'来源尚未独立核实')
        lines.append(model['display_name']+'：'+label+'。')
        if capture and capture.get('exception_note'): lines.append('接收差异说明：'+capture['exception_note'])
    return '\n'.join(lines)


def screenshot_evidence(root):
    """Report each separate fact; filenames or files alone never prove upload/review."""
    records = list(_records(root))
    result = {}
    for role, prefix in PREFIXES.items():
        reply_hash = read_response(root,role)['meta']['reply_sha256']
        candidates = []
        for binding_path in (Path(root)/'platform-web').rglob('archive-binding.json'):
            binding = read_json(binding_path)
            if binding.get('role') != role or binding.get('replyHash') != reply_hash:
                continue
            receipt_path = binding_path.parent/'screenshot.json'
            if not receipt_path.exists(): continue
            receipt = read_json(receipt_path)
            require(receipt.get('replyHash') == reply_hash and sha(receipt['imageFile']) == receipt['sha256'], '截图证据已变化')
            reviewed = False
            review_path = binding_path.parent/'visual-review.json'
            if review_path.exists():
                review = read_json(review_path)
                require(review.get('imageSha256') == receipt['sha256'] and review.get('replyHash') == reply_hash, '截图目视记录与成图不符')
                reviewed = review.get('reviewed') is True and bool(review.get('note','').strip())
            uploaded = False
            for upload_path, upload in records:
                if upload.get('kind') != 'upload' or upload.get('prefix') != prefix or upload.get('sha256') != receipt['sha256']:
                    continue
                done_path = upload_path.parent/'result.json'
                if done_path.exists():
                    done = read_json(done_path)
                    require(done.get('sha256') == receipt['sha256'], '上传回执与截图不符')
                    uploaded = done.get('status') == 'uploaded' and bool(done.get('savedAt'))
            candidates.append({'generated':True,'visual_reviewed':bool(reviewed),'uploaded_saved':uploaded,
                               'sha256':receipt['sha256']})
        if candidates:
            selected = max(candidates,key=lambda x:(x['uploaded_saved'],x['visual_reviewed']))
            selected['description'] = '已生成；'+('已记录目视核验' if selected['visual_reviewed'] else '目视核验尚未记录')+'；'+('已上传并保存' if selected['uploaded_saved'] else '未核验到上传并保存证据')
        else:
            selected = {'generated':False,'visual_reviewed':False,'uploaded_saved':False,'description':'未核验到当前回复对应的完整截图证据'}
        result[role] = selected
    return result


def web_notes(evidence):
    names = {'insight':'题目难度与标签','core-point':'考点','attainment':'达成性'}
    labels = {'passed':'通过','failed':'不通过','service_error':'服务异常，无有效结论',
              'unknown':'结果或关联未知','input_changed':'输入已变，仅作历史','not_verified':'未核验到当前有效结果'}
    lines = []
    for key, result in evidence['checks'].items():
        lines.append(names[key]+'：'+labels[result['state']]+'。')
        feedback = result.get('feedback',{})
        if feedback.get('note'): lines.append('已保存备注：'+feedback['note'])
    return '\n'.join(lines)
