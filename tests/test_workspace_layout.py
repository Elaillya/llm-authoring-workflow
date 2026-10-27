"""Flat question folders and legacy discovery; synthetic data only."""
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from llm_authoring.cli import main
from llm_authoring.core import Error, freeze_record, read_json, sha, write_json
from llm_authoring.memory import sync
from llm_authoring.workspace import create_workspace, create_task, default_task, task_roots, update_workspace
from test_core import question


class WorkspaceLayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.ws=Path(self.tmp.name).resolve()/'workspaces'

    def test_first_question_and_following_questions_share_flat_parent(self):
        output=StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(['workspace-create',str(self.ws),'--first-task','1512','--no-platform-checks']),0)
        first=Path(json.loads(output.getvalue())['first_task']['task'])
        self.assertEqual(first,self.ws/'question-1512')
        self.assertEqual(default_task(self.ws),first)
        self.assertFalse(read_json(first/'TASK.json')['platform_checks_required'])
        self.assertFalse((self.ws/'task').exists())
        self.assertFalse((self.ws/'question-001').exists())
        self.assertEqual(Path(create_task(self.ws,'1513')['task']),self.ws/'question-1513')
        self.assertEqual(Path(create_task(self.ws,'question-1514')['task']),self.ws/'question-1514')
        self.assertFalse((self.ws/'tasks').exists())
        with self.assertRaises(Error):create_task(self.ws,'question-1512')

    def test_mixed_legacy_layout_is_synced_updated_and_not_duplicated(self):
        create_workspace(self.ws)
        first=self.ws/'question-001';first.rename(self.ws/'task')
        marker=read_json(self.ws/'.authoring-workspace.json');marker.pop('default_task');write_json(self.ws/'.authoring-workspace.json',marker)
        legacy=Path(create_task(self.ws,'old',destination=self.ws/'tasks/old')['task'])
        flat=Path(create_task(self.ws,'new')['task'])
        roots=[self.ws/'task',legacy,flat]
        for root in roots:
            q=question();q['task_id']=read_json(root/'TASK.json')['task_id'];freeze_record(root,q)
        protected={p:sha(p) for root in roots for p in (root/'revisions/r0001/question.json',root/'TASK.json')}
        self.assertEqual(set(task_roots(self.ws)),set(roots))
        self.assertEqual(default_task(self.ws),self.ws/'task')
        self.assertEqual(sync(self.ws)['imported'],3)
        self.assertEqual(sync(self.ws)['imported'],0)
        self.assertEqual(len(update_workspace(self.ws)['tasks']),3)
        self.assertEqual(protected,{p:sha(p) for p in protected})
        with self.assertRaises(Error):create_task(self.ws,'old')
        with self.assertRaises(Error):create_task(self.ws,'question-old')
        self.assertFalse((self.ws/'question-old').exists())
