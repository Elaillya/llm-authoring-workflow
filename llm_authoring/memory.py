"""Private, workspace-local question memory; no global memory or model service."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import sqlite3
from .core import Error, hash_json, now, read_json, require, validate_question

STATUSES=('draft','frozen','delivered','rejected','historical')


def task_key(root):
    root=Path(root).resolve();task=read_json(root/'TASK.json')
    return task.get('memory_id') or 'legacy:'+hash_json(str(root))


def database_path(workspace):
    workspace=Path(workspace).resolve();local=workspace/'local'
    require(local.is_dir() and not local.is_symlink(),'本地题库须位于工作区普通local目录')
    path=local/'question-memory.sqlite3'
    for p in (path,Path(str(path)+'-wal'),Path(str(path)+'-shm')):
        require(not p.is_symlink(),'本地题库文件不能为符号链接')
    return path


@contextmanager
def transaction(workspace):
    path=database_path(workspace)
    if not path.exists():
        try:
            fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
        except FileExistsError:pass
    require(path.is_file(),'本地题库须为普通文件');path.chmod(0o600)
    connection=sqlite3.connect(path,timeout=30)
    try:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('BEGIN IMMEDIATE')
        connection.execute('CREATE TABLE IF NOT EXISTS entries (entry_id TEXT PRIMARY KEY, task_key TEXT NOT NULL, question_sha TEXT NOT NULL, question_json TEXT NOT NULL, status TEXT NOT NULL, revision TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, provenance TEXT NOT NULL)')
        connection.execute('CREATE TABLE IF NOT EXISTS events (entry_id TEXT NOT NULL, status TEXT NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL)')
        connection.execute('CREATE TABLE IF NOT EXISTS failure_observations (event_id TEXT PRIMARY KEY, body TEXT NOT NULL, body_sha TEXT NOT NULL, created_at TEXT NOT NULL)')
        connection.execute('CREATE TABLE IF NOT EXISTS failure_reviews (event_id TEXT NOT NULL REFERENCES failure_observations(event_id), body TEXT NOT NULL, body_sha TEXT NOT NULL, created_at TEXT NOT NULL)')
        yield connection
        connection.commit()
    except sqlite3.Error:
        connection.rollback()
        raise Error('本地题库无法读取或写入，请检查占用、权限或损坏；保留原库与题目，不自动清空') from None
    except BaseException:
        connection.rollback();raise
    finally:connection.close()


def records(connection):
    items=[]
    for row in connection.execute('SELECT entry_id,task_key,question_sha,question_json,status,revision,provenance,updated_at FROM entries ORDER BY entry_id'):
        eid,key,qhash,raw,status,revision,source,updated=row;q=json.loads(raw)
        require(hash_json(q)==qhash and eid==hash_json([key,qhash]),'本地题库内容或身份绑定已改变')
        items.append({'entry_id':eid,'task_key':key,'question_sha256':qhash,'question':q,
                      'status':status,'revision':revision,'provenance':source,'updated_at':updated})
    return items


def remember(connection,root,q,status='draft',revision=None,note='',provenance='candidate'):
    require(status in STATUSES,'题库状态不合法');validate_question(q,legacy_domain=True)
    require(q['task_id']==read_json(Path(root)/'TASK.json')['task_id'],'题库候选ID不属于此任务')
    key=task_key(root);qhash=hash_json(q);eid=hash_json([key,qhash]);timestamp=now()
    previous=connection.execute('SELECT status FROM entries WHERE entry_id=?',(eid,)).fetchone()
    connection.execute('INSERT INTO entries VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(entry_id) DO UPDATE SET status=excluded.status,revision=COALESCE(excluded.revision,entries.revision),updated_at=excluded.updated_at',
                       (eid,key,qhash,json.dumps(q,ensure_ascii=False,sort_keys=True),status,revision,timestamp,timestamp,provenance))
    if previous is None or previous[0]!=status or note:
        connection.execute('INSERT INTO events VALUES (?,?,?,?)',(eid,status,note,timestamp))
    return eid


def sync_locked(workspace,connection):
    """Read only real task roots and frozen question records, never replies/configs."""
    workspace=Path(workspace).resolve();roots=[workspace/'task']+sorted((workspace/'tasks').glob('*'))
    imported=0
    for root in roots:
        if root.is_symlink() or not (root/'TASK.json').is_file():continue
        require(root.resolve().is_relative_to(workspace),'题库导入目录逃逸工作区')
        task=read_json(root/'TASK.json');require(task.get('workflow')=='llm-authoring','题库任务类型不符')
        revisions=root/'revisions'
        require(not revisions.is_symlink(),'题库版本目录不能为符号链接')
        if not revisions.is_dir():continue
        for version in sorted(revisions.iterdir()):
            if not re.fullmatch(r'r\d{4}',version.name):continue
            require(version.is_dir() and not version.is_symlink(),'题库冻结版本须为普通目录')
            frozen=read_json(version/'question.json');q=frozen['question'];validate_question(q,legacy_domain=True)
            require(frozen.get('question_sha256')==hash_json(q)
                    and frozen.get('prompt_sha256')==hash_json(q['prompt'])
                    and frozen.get('rubric_sha256')==hash_json(q['points'])
                    and frozen.get('revision')==version.name,'历史冻结记录绑定失效；先核对原件，题库未跳过损坏记录')
            eid=hash_json([task_key(root),hash_json(q)])
            if connection.execute('SELECT 1 FROM entries WHERE entry_id=?',(eid,)).fetchone():continue
            remember(connection,root,q,'historical',version.name,provenance=str(version/'question.json'));imported+=1
    return imported


def sync(workspace):
    with transaction(workspace) as connection:
        imported=sync_locked(workspace,connection);count=len(records(connection))
    return {'database':str(database_path(workspace)),'imported':imported,'entries':count,'scope':'workspace_local_only'}


def snapshot(items,key):
    # Changes within the same question do not invalidate its own review.
    return hash_json(sorted((i['entry_id'],i['question_sha256'],i['status']) for i in items if i['task_key']!=key))


def topic_index(items,key):
    result=[]
    for item in items:
        if item['task_key']==key:continue
        q=item['question'];profile=q.get('design_profile',{})
        result.append({'entry_id':item['entry_id'],'task_id':q['task_id'],'domain':q.get('domain'),
                       'subdirection':q.get('subdirection'),'prompt':q['prompt'],
                       'mechanism':(q['insight'] if isinstance(q['insight'],str) else q['insight']['mechanism'])[:220],
                       'mechanism_tags':profile.get('mechanism_tags',[]),
                       'point_targets':profile.get('point_targets') or [p['criterion'][:120] for p in q['points']],
                       'status':item['status']})
    return result


def context(root,workspace,limit=12):
    require(1<=limit<=50,'题库上下文条数须在1到50之间')
    with transaction(workspace) as connection:
        sync_locked(workspace,connection);items=records(connection)
    from .lessons import failure_context
    learning=failure_context(root,workspace,limit)
    own=task_key(root);others=sorted([i for i in items if i['task_key']!=own],key=lambda i:(i['updated_at'],i['entry_id']))
    # Return text and profiles to allow semantic review beyond lexical matching.
    return {'memory_snapshot_sha256':snapshot(items,own),'entries':len(items),'other_task_entries':len(others),
            'topic_index':topic_index(items,own),
            'recent_questions':others[-limit:],'own_previous_candidates':[i for i in items if i['task_key']==own][-5:],'failure_learning':learning,
            'next':'先看题面、机制、任务目标与考点评分结构，再拟不同场景候选；需要更广上下文时提高limit或design-check全库召回'}


def show(workspace,entry_id):
    with transaction(workspace) as connection:
        sync_locked(workspace,connection)
        item=next((i for i in records(connection) if i['entry_id']==entry_id),None)
    require(item is not None,'题库条目不存在')
    return item
