"""User-authorized GPT/Claude replacements; old originals remain recoverable."""
from pathlib import Path
import re,shutil,uuid
from .core import (Error,ROLES,NAMES,active_question,hash_json,now,read_json,read_response,require,
                   response_dir,save_response,sha,validate_markdown,write_json)
from .manual import PLACEHOLDER,input_directory,model_request,seed_screen,validate_manual_evidence
from .model_prompt import prompt_text,validate_prompt_file
from . import lessons
from .memory import task_key


def _directory(root,replacement_id):
    require(isinstance(replacement_id,str) and re.fullmatch(r'r\d{4}-[a-f0-9]{16}',replacement_id),'替换ID不合法')
    path=Path(root)/'model-input'/replacement_id[:5]/'replacements'/replacement_id
    for parent in (path,*path.parents):
        if parent==Path(root):break
        require(not parent.is_symlink(),'替换文件目录不能为符号链接')
    return path


def _approved_failure(root,failure_id):
    from .workspace import locate_workspace
    item=lessons.show(locate_workspace(root),failure_id);event=item['observation']
    require(event['task_key']==task_key(root) and event['kind']=='criteria_quality_failed'
            and item['reviews'] and item['reviews'][-1]['verdict']=='accepted','仅为本题已认可的考点质检失败准备替换')
    require(event['prompt']==active_question(root)['question']['prompt'],'题面已改变，按新题从Seed开始')
    attempt=Path(event['evidence']['attempt'])
    require(not list(attempt.glob('disagreement-*.json')),'该意见已登记异议，不作为认可的修复依据')
    return item


def prepare(root,role,failure_id,*,authorization_note,reason,evaluation=None):
    require(role in ('gpt','claude'),'仅允许用户重新提供GPT或Claude；Seed按原门槛保持')
    require(isinstance(authorization_note,str) and authorization_note.strip(),'先询问用户并取得明确同意，记录原授权语句')
    require(isinstance(reason,str) and reason.strip(),'说明为何仅修订Insight和考点仍不可行，以及待补的考点缺口')
    root=Path(root).resolve();_approved_failure(root,failure_id)
    from .platform_checks import check_lock,question_gate
    with check_lock(root):
        current=active_question(root);question_gate(root,current['question']);screen=seed_screen(root,evaluation)
        for model in ROLES:
            item=validate_manual_evidence(root,model)
            require(prompt_text(item['meta']['manual_request'])==current['question']['prompt'],
                    '现有原回复含不同发送内容，不能与严格prompt的新回复混用')
        old=read_response(root,role)
        for previous in input_directory(root).glob('replacements/*/replacement.json'):
            saved=read_json(previous)
            if saved.get('role')==role and saved.get('failure_id')==failure_id and saved.get('authorization_note')==authorization_note:
                require(False,'这份授权已有替换填写入口，继续该入口；本次结果不合格时先告知用户，不自动重复抽取')
        replacement_id=current['revision']+'-'+uuid.uuid4().hex[:16]
        directory=_directory(root,replacement_id);directory.mkdir(parents=True)
        request=model_request(root,role,screen);request['prompt_file']='prompt.md'
        plan={'schema_version':1,'replacement_id':replacement_id,'role':role,'failure_id':failure_id,
              'question_sha256':current['question_sha256'],'prompt_sha256':current['prompt_sha256'],
              'old_response_sha256':old['meta']['reply_sha256'],'old_metadata_sha256':sha(old['directory']/'metadata.json'),
              'request':request,'authorization_note':authorization_note,'reason':reason,'prepared_at':now()}
        write_json(directory/'replacement.json',plan)
        (directory/'prompt.md').write_bytes(current['question']['prompt'].encode())
        slot=directory/(NAMES[role]+'.md');slot.write_text(PLACEHOLDER)
        (directory/'填写说明.md').write_text('使用所列型号的官方网页新会话和规定的中高推理模式，发送prompt.md全部原文，不加其他要求。将完整Markdown粘贴到模型文件并保存；网页截图自行交甲方。新回复仍可能不达成，原回复和失败记录保留。\n')
        return {'replacement_id':replacement_id,'role':role,'prompt_file':str(directory/'prompt.md'),
                'input_file':str(slot),'current_original_preserved':True,
                'next':'等待用户填入完整原文；导入后重新统一评估三模型，不能假定替换成功或自动继续质检'}


def pending(root):
    """Locate authorized fill-in slots without replacing or rejudging any reply."""
    root=Path(root).resolve()
    if not (root/'CURRENT.json').exists():return []
    current=active_question(root);result=[]
    for manifest in input_directory(root).glob('replacements/*/replacement.json'):
        directory=_directory(root,manifest.parent.name)
        require(manifest.is_file() and not manifest.is_symlink(),'替换计划须为普通文件')
        plan=read_json(manifest);role=plan.get('role')
        if role not in ('gpt','claude') or plan.get('question_sha256')!=current['question_sha256']:continue
        if plan.get('replacement_id')!=directory.name or not plan.get('authorization_note'):continue
        try:
            _approved_failure(root,plan['failure_id']);old=read_response(root,role)
            if old['meta']['reply_sha256']!=plan['old_response_sha256'] or sha(old['directory']/'metadata.json')!=plan['old_metadata_sha256']:continue
        except (Error,OSError,ValueError,KeyError,TypeError):continue
        result.append({'role':role,'replacement_id':directory.name,'failure_id':plan['failure_id'],
                       'prompt_file':str(directory/'prompt.md'),'input_file':str(directory/(NAMES[role]+'.md')),
                       'current_original_preserved':True})
    return result


def import_reply(root,role,replacement_id,evaluation=None):
    root=Path(root).resolve();require(role in ('gpt','claude'),'仅允许GPT或Claude替换')
    directory=_directory(root,replacement_id);plan=read_json(directory/'replacement.json')
    current=active_question(root)
    require(plan.get('replacement_id')==replacement_id and plan.get('role')==role
            and plan.get('question_sha256')==current['question_sha256']
            and plan.get('prompt_sha256')==current['prompt_sha256'],'替换计划题面或冻结版本已变化，保留原件并重新核对')
    require(isinstance(plan.get('authorization_note'),str) and plan['authorization_note'].strip(),'替换缺少用户明确授权记录')
    _approved_failure(root,plan['failure_id'])
    slot=directory/(NAMES[role]+'.md');require(slot.is_file() and not slot.is_symlink(),'缺少普通模型填写文件')
    raw=slot.read_bytes();reply=raw.decode('utf-8')
    require(reply.strip()!=PLACEHOLDER.strip(),'请先填入用户提供的新回复')
    validate_markdown(reply);validate_prompt_file(directory/'prompt.md',plan['request'])
    require(plan['request'].get('prompt_policy')=='prompt_only' and prompt_text(plan['request'])==current['question']['prompt'],'发送文字须严格等于冻结prompt')
    from .platform_checks import check_lock,question_gate
    with check_lock(root):
        require(active_question(root)['question_sha256']==plan['question_sha256'],'替换期间冻结版本变化，先核对原件')
        question_gate(root,current['question']);screen=seed_screen(root,evaluation)
        expected=model_request(root,role,screen);expected['prompt_file']='prompt.md'
        require(expected==plan['request'],'Seed判断或请求绑定变化，保留填写文件并核对当前版本')
        old=validate_manual_evidence(root,role)
        receipt_path=directory/'receipt.json'
        if receipt_path.exists():
            receipt=read_json(receipt_path)
            require(old['meta'].get('replacement_id')==replacement_id
                    and receipt['new_response_sha256']==old['meta']['reply_sha256']
                    and sha(slot)==old['meta']['raw_response_sha256'],'已导入替换内容发生变化，保留原件')
            return {**receipt,'already_imported':True}
        # Recover a completed replacement whose receipt write was interrupted.
        if old['meta'].get('replacement_id')==replacement_id:
            require(sha(slot)==old['meta']['raw_response_sha256'],'已保存原回复与填写内容不一致')
        else:
            require(old['meta']['reply_sha256']==plan['old_response_sha256']
                    and sha(old['directory']/'metadata.json')==plan['old_metadata_sha256'],'原回复已被另一次替换，不能覆盖新结果')
            require(reply!=old['text'],'新旧回复相同，无需替换或伪造新采集')
            active=old['directory']
            for path in (active,*active.parents):
                if path==root:break
                require(not path.is_symlink(),'原回复及归档目录不能为符号链接')
            archive=active.parent/'.replacements'/replacement_id/'original'
            for path in (archive,*archive.parents):
                if path==root:break
                require(not path.is_symlink(),'原回复及归档目录不能为符号链接')
            require(not archive.exists(),'归档路径已存在，保留原件')
            archive.parent.mkdir(parents=True,exist_ok=True);active.rename(archive)
            try:
                save_response(root,role,reply,{'display_name':NAMES[role],'model':NAMES[role],
                    'returned_model':NAMES[role],'model_identity_check':'user_declared_official_site_model',
                    'source_kind':'official_manual','completion_status':'complete','evidence_status':'user_provided_markdown',
                    'raw_response_file':'model-input.md','manual_request':plan['request'],
                    'manual_request_sha256':hash_json(plan['request']),'screenshot_submission':'user_submits_separately',
                    'replacement_id':replacement_id,'replacement_plan_sha256':hash_json(plan)},raw=raw)
            except BaseException:
                if active.exists():shutil.rmtree(active)
                archive.rename(active);raise
            old=validate_manual_evidence(root,role)
        archive=old['directory'].parent/'.replacements'/replacement_id/'original'
        require(sha(archive/'reply.md')==plan['old_response_sha256']
                and sha(archive/'metadata.json')==plan['old_metadata_sha256'],'旧原回复归档校验失败，先核对原件')
        receipt={'replacement_id':replacement_id,'role':role,'archive':str(archive),
                 'old_response_sha256':plan['old_response_sha256'],'new_response_sha256':old['meta']['reply_sha256'],
                 'user_authorization':plan['authorization_note'],'requires_uniform_reevaluation':True,'imported_at':now()}
        write_json(receipt_path,receipt)
        return receipt
