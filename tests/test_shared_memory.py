"""Synthetic cross-parent memory sharing; no platform, model, or real library."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import copy
import unittest
from llm_authoring import lessons
from llm_authoring.core import Error, freeze, read_json, sha, write_json
from llm_authoring.memory import context, database_path, remember, sync, transaction
from llm_authoring.quality import candidate_check, reserve
from llm_authoring.workspace import create_workspace, choose_domain, choose_type
from llm_authoring.selection import choose_subdirection
import test_diversity as diversity


class SharedMemoryTests(unittest.TestCase):
    candidate=diversity.DiversityTests.candidate

    def setUp(self):
        import tempfile
        self.temp=tempfile.TemporaryDirectory();self.ws=Path(self.temp.name)/'one'
        self.peer=Path(self.temp.name)/'two'
        for ws in (self.ws,self.peer):
            create_workspace(ws);root=ws/'task'
            task=read_json(root/'TASK.json');task.pop('platform_checks_required',None)
            write_json(root/'TASK.json',task)
            choose_domain(root,'计算机科学');choose_subdirection(root,'cs_courses');choose_type(root,'分析决策类')
            (root/'drafts/sources.md').write_text('合成测试依据，无真实模型或平台调用。')
        self.a=self.ws/'task';self.b=self.peer/'task'
        with transaction(self.ws):pass
        self.config={'schema_version':1,'owner_workspace':str(self.ws),'members':[str(self.ws),str(self.peer)]}

    def tearDown(self):self.temp.cleanup()

    def share(self):
        for ws in (self.ws,self.peer):
            marker=read_json(ws/'.authoring-workspace.json');marker['shared_memory_required']=True
            write_json(ws/'.authoring-workspace.json',marker)
            write_json(ws/'local/shared-memory.json',self.config)

    def test_isolation_remains_default(self):
        with transaction(self.ws) as db:remember(db,self.a,self.candidate(self.a))
        self.assertEqual(context(self.b,self.peer)['entries'],0)
        self.assertNotEqual(database_path(self.ws),database_path(self.peer))
        self.assertEqual(context(self.a,self.ws)['scope'],'workspace_local_only')

    def test_both_parents_read_and_write_one_library(self):
        self.share()
        self.assertEqual(database_path(self.ws),database_path(self.peer))
        for ws,root,variant,expected in ((self.ws,self.a,0,1),(self.peer,self.b,1,2)):
            with transaction(ws) as db:remember(db,root,self.candidate(root,variant),'rejected')
            for member,task in ((self.ws,self.a),(self.peer,self.b)):
                result=context(task,member)
                self.assertEqual(result['entries'],expected)
                self.assertEqual(result['scope'],'shared_workspace_group')
                self.assertEqual(result['database'],str(database_path(self.ws)))
        self.assertFalse((self.peer/'local/question-memory.sqlite3').exists())
        self.assertTrue(candidate_check(self.b,{**self.candidate(self.a),'task_id':'question-001'})['hard_duplicates'])

    def test_frozen_sync_reads_all_members_once_without_rewriting_question(self):
        request=read_json(self.b/'REQUEST.json');request.pop('selection_schema')
        write_json(self.b/'REQUEST.json',request)
        from test_core import question
        q=question();q['task_id']=read_json(self.b/'TASK.json')['task_id'];freeze(self.b,q)
        file=self.b/'revisions/r0001/question.json';before=sha(file)
        self.share()
        self.assertEqual(sync(self.ws)['imported'],1)
        self.assertEqual(sync(self.peer)['imported'],0)
        self.assertEqual(context(self.a,self.ws)['entries'],1)
        self.assertEqual(sha(file),before)

    def test_shared_failures_keep_review_and_dispute_semantics_in_both_directions(self):
        self.share()
        for root,other,ws in ((self.a,self.b,self.peer),(self.b,self.a,self.ws)):
            # Synthetic evidence fixture; public review/context still verify hashes.
            eid=lessons._save(root,self.candidate(root),'seed_all_attained',{'synthetic':True},'合成原文：边界已经给出。')
            pending=lessons.failure_context(other,ws)
            self.assertIn(eid,[p['event_id'] for p in pending['pending_reviews']])
            review=lessons.review_template(ws,eid)
            review.update(verdict='accepted',reviewer='synthetic-author',cause='合成原因',prevention='核对边界',
                          applicability='仅此合成情况',evidence_quotes=['边界已经给出'])
            self.assertEqual(lessons.review(ws,review)['shared_with'],'shared_workspace_group')
            self.assertEqual(lessons.failure_context(other,ws)['accepted_count'],1)
            review.update(verdict='disputed',cause='合成异议，不能作为可靠规律')
            lessons.review(ws,review)
            self.assertEqual(lessons.failure_context(root,self.ws)['accepted_count'],0)
            self.assertEqual(len(lessons.show(ws,eid)['reviews']),2)
        self.assertEqual(lessons.failure_context(self.a,self.ws)['observed_count'],2)

    def test_new_peer_record_invalidates_review_but_preserves_frozen_version(self):
        self.share();a=self.candidate(self.a);b=self.candidate(self.b,1)
        diversity.accept(self.b,b);diversity.accept(self.a,a);freeze(self.a,a)
        protected={p:sha(p) for p in (self.a/'CURRENT.json',self.a/'revisions/r0001/question.json')}
        with self.assertRaisesRegex(Error,'复核.*过期'):freeze(self.b,b)
        self.assertFalse((self.b/'CURRENT.json').exists())
        diversity.accept(self.b,b);freeze(self.b,b)
        self.assertEqual(protected,{p:sha(p) for p in protected})

    def test_concurrent_reservations_across_parents_share_one_lock_and_snapshot(self):
        self.share();a=self.candidate(self.a);b=self.candidate(self.b,1)
        diversity.accept(self.a,a);diversity.accept(self.b,b)
        def call(pair):
            root,q=pair
            try:reserve(root,q);return 'ok'
            except Error as error:
                self.assertIn('过期',str(error));return 'stale'
        with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(call,[(self.a,a),(self.b,b)]))
        self.assertEqual(sorted(result),['ok','stale'])

    def test_incomplete_or_mismatched_configuration_fails_closed(self):
        self.share();before=sha(database_path(self.ws))
        file=self.peer/'local/shared-memory.json';file.unlink()
        with self.assertRaisesRegex(Error,'配置缺失'):context(self.a,self.ws)
        with self.assertRaisesRegex(Error,'配置缺失'):context(self.b,self.peer)
        changed=copy.deepcopy(self.config);changed['owner_workspace']=str(self.peer);write_json(file,changed)
        with self.assertRaisesRegex(Error,'配置不一致'):context(self.b,self.peer)
        self.assertFalse((self.peer/'local/question-memory.sqlite3').exists())
        self.assertEqual(sha(self.ws/'local/question-memory.sqlite3'),before)

    def test_missing_owner_database_does_not_create_empty_replacement(self):
        self.share();file=database_path(self.ws);file.unlink()
        for ws in (self.ws,self.peer):
            with self.assertRaisesRegex(Error,'主库缺失'):
                with transaction(ws):pass
        self.assertFalse(file.exists());self.assertFalse((self.peer/'local/question-memory.sqlite3').exists())

    def test_partial_activation_fails_closed_before_any_shared_write(self):
        self.share();marker=read_json(self.peer/'.authoring-workspace.json')
        marker.pop('shared_memory_required');write_json(self.peer/'.authoring-workspace.json',marker)
        with self.assertRaisesRegex(Error,'持久标记'):
            with transaction(self.ws):pass
        self.assertFalse((self.peer/'local/question-memory.sqlite3').exists())

    def test_symlink_config_member_database_and_sidecar_are_rejected(self):
        self.share();config=self.peer/'local/shared-memory.json';saved=config.with_suffix('.saved')
        config.rename(saved);config.symlink_to(saved)
        with self.assertRaisesRegex(Error,'配置缺失'):database_path(self.ws)
        config.unlink();saved.rename(config)
        alias=self.peer.parent/'alias';alias.symlink_to(self.peer,target_is_directory=True)
        invalid={**self.config,'members':[str(self.ws),str(alias)]}
        write_json(self.ws/'local/shared-memory.json',invalid)
        with self.assertRaisesRegex(Error,'规范目录'):database_path(self.ws)
        self.share();file=database_path(self.ws);saved=file.with_suffix('.saved');file.rename(saved);file.symlink_to(saved)
        with self.assertRaisesRegex(Error,'主库缺失'):database_path(self.peer)
        file.unlink();saved.rename(file)
        sidecar=Path(str(file)+'-wal');sidecar.symlink_to(saved)
        with self.assertRaisesRegex(Error,'符号链接'):database_path(self.peer)

    def test_invalid_members_and_unregistered_workspace_cannot_join(self):
        for members in ([str(self.ws),'relative'],[str(self.ws),str(self.ws)],[],None):
            write_json(self.ws/'local/shared-memory.json',{**self.config,'members':members})
            with self.assertRaises(Error):database_path(self.ws)
        self.share();other=self.ws.parent/'third';create_workspace(other)
        write_json(other/'local/shared-memory.json',self.config)
        with self.assertRaisesRegex(Error,'不在成员'):database_path(other)
        self.assertFalse((other/'local/question-memory.sqlite3').exists())
