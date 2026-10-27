"""Synthetic automatic resampling, preserving each previous original."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch
from llm_authoring import replacement
from llm_authoring.authoring import evaluation_template, check_three
from llm_authoring.core import Error, freeze, read_json, read_response, write_json
from llm_authoring.manual import prepare_model, import_model
import test_piweb_import as fixture

bridge=fixture.bridge


class AutomationRetryTests(unittest.TestCase):
    def setUp(self):
        fixture.PiWebImportTests.setUp(self)
        bridge.import_archive(self.root, self.directory)
        self.seed_evaluation()
        for role in ('gpt', 'claude'):
            slot = Path(prepare_model(self.root, role)['input_file'])
            slot.write_bytes(('# Original '+role+'\r\n\r\nSynthetic complete answer.\n').encode())
            import_model(self.root, role)
        self.ev = self.negative()

    def negative(self, roles=('seed', 'gpt', 'claude')):
        ev = evaluation_template(self.root, roles); ev['reviewer'] = 'synthetic'
        for model in ev['models'].values():
            for point in model['points'].values():
                point.update(met=False, reason='Synthetic missing decisive evidence.', quotes=[])
        return ev

    def seed_evaluation(self):
        current = read_json(self.root/'CURRENT.json')['revision']
        write_json(self.root/'evaluations'/('seed-'+current+'.json'), self.negative(('seed',)))

    def prepare(self, role='gpt', ev=None):
        return replacement.prepare(self.root, role, authorization_note='User authorizes one GPT/Claude retry per content version.',
                                   reason='Current three-model gate failed.', gate_evaluation=ev or self.ev)

    def test_prepare_both_then_replace_exactly_once_and_preserve_old_bytes(self):
        plans = {role:self.prepare(role) for role in ('gpt','claude')}
        protected = read_response(self.root,'seed')['meta']
        for role, plan in plans.items():
            old = read_response(self.root,role)
            before = {p.name:p.read_bytes() for p in old['directory'].iterdir()}
            raw = ('# Retry '+role+'\r\n\r\nNew complete answer.\n').encode()
            Path(plan['input_file']).write_bytes(raw)
            receipt = replacement.import_reply(self.root,role,plan['replacement_id'])
            self.assertEqual((read_response(self.root,role)['directory']/'reply.md').read_bytes(),raw)
            self.assertEqual({p.name:p.read_bytes() for p in Path(receipt['archive']).iterdir()},before)
            self.assertTrue(replacement.import_reply(self.root,role,plan['replacement_id'])['already_imported'])
            resumed = self.prepare(role)
            self.assertEqual(resumed['replacement_id'],plan['replacement_id'])
            self.assertTrue(resumed['already_imported'])
        self.assertEqual(read_response(self.root,'seed')['meta'],protected)
        with self.assertRaisesRegex(Error,'原文'): check_three(self.root,self.ev)
        self.assertEqual(len(list((self.root/'model-input').glob('r*/replacements/*/replacement.json'))),2)

    def test_resume_pending_and_comment_changes_do_not_grant_another_retry(self):
        first=self.prepare();self.assertEqual(self.prepare()['replacement_id'],first['replacement_id'])
        self.assertEqual(replacement.pending(self.root)[0]['replacement_id'],first['replacement_id'])
        changed=copy.deepcopy(self.ev);changed['reviewer']='another reviewer'
        self.assertEqual(self.prepare(ev=changed)['replacement_id'],first['replacement_id'])
        q=copy.deepcopy(self.q);q['author_notes']+=' Metadata only.';freeze(self.root,q);self.seed_evaluation()
        with self.assertRaisesRegex(Error,'额度已使用'): self.prepare(ev=self.negative())

    def test_interrupted_preparation_recovers_same_slot_and_cli_reuses_it(self):
        plan=self.prepare();Path(plan['prompt_file']).unlink();Path(plan['input_file']).unlink()
        resumed=self.prepare();self.assertEqual(resumed['replacement_id'],plan['replacement_id'])
        self.assertEqual(Path(resumed['prompt_file']).read_bytes(),self.q['prompt'].encode())
        from llm_authoring.cli import main
        from contextlib import redirect_stdout
        from io import StringIO
        import json
        evaluation=self.root/'evaluations'/'negative.json';write_json(evaluation,self.ev)
        output=StringIO()
        with redirect_stdout(output):
            code=main(['--task',str(self.root),'model-replace-prepare','gpt','--retry-evaluation',str(evaluation),
                       '--authorization-note','User authorized this policy.','--reason','Current gate failed.'])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(output.getvalue())['replacement_id'],plan['replacement_id'])

    def test_rubric_and_insight_changes_restore_allowance_but_old_plan_cannot_import(self):
        first=self.prepare()
        for field in ('points','insight','prompt'):
            q=copy.deepcopy(self.q)
            if field=='points': q['points'][0]['criterion']+=' Explicit boundary.'
            elif field=='insight': q['insight']['mechanism']+=' New mechanism.'
            else: q['prompt']='上线前应优先核对哪些验收依据？'
            freeze(self.root,q)
            if field=='prompt':
                # A changed prompt needs three new originals, not a retry of old answers.
                with self.assertRaises(Error): self.prepare(ev=self.ev)
                break
            self.seed_evaluation();fresh=self.prepare(ev=self.negative())
            self.assertNotEqual(fresh['replacement_id'],first['replacement_id'])
            with self.assertRaisesRegex(Error,'版本'): replacement.import_reply(self.root,'gpt',first['replacement_id'])
            self.q=q

    def test_manual_gate_success_and_incomplete_evaluation_cannot_resample(self):
        successful=copy.deepcopy(self.ev)
        for point in successful['models']['gpt']['points'].values(): point.update(met=True,quotes=['Synthetic complete answer.'])
        with self.assertRaisesRegex(Error,'门槛'): self.prepare(ev=successful)
        incomplete=copy.deepcopy(self.ev);incomplete['models'].pop('claude')
        with self.assertRaises(Error): self.prepare(ev=incomplete)
        task=read_json(self.root/'TASK.json');task['platform_checks_required']=True;write_json(self.root/'TASK.json',task)
        with patch('llm_authoring.platform_checks.question_gate'):
            with self.assertRaisesRegex(Error,'自动化'): self.prepare()

    def test_explicit_failure_replacement_retains_its_existing_authorization_contract(self):
        with patch.object(replacement,'_approved_failure',return_value={}):
            plan=replacement.prepare(self.root,'claude','accepted-failure',authorization_note='Specific replacement consent.',reason='Professional repair still insufficient.')
            with self.assertRaisesRegex(Error,'已有替换填写入口'):
                replacement.prepare(self.root,'claude','accepted-failure',authorization_note='Specific replacement consent.',reason='Same consent.')
            Path(plan['input_file']).write_bytes(b'# Specifically authorized replacement\n\nComplete original.\n')
            self.assertTrue(replacement.import_reply(self.root,'claude',plan['replacement_id'])['requires_uniform_reevaluation'])
        self.assertNotIn('retry_key',read_json(Path(plan['input_file']).parent/'replacement.json'))

    def test_bridge_imports_authorized_retry_without_overwriting_original_input_slot(self):
        plan=self.prepare('gpt')
        self.result['role']='gpt'
        for name in ('result.json','create-intent.json'):write_json(self.directory/name,self.result)
        original_input=Path(prepare_model(self.root,'gpt')['reply_file']).read_bytes()
        bridge.import_archive(self.root,self.directory,plan['replacement_id'])
        self.assertEqual((read_response(self.root,'gpt')['directory']/'reply.md').read_bytes(),self.raw)
        self.assertEqual((Path(prepare_model(self.root,'gpt')['reply_file']).parent.parent/'.replacements'/plan['replacement_id']/'original'/'reply.md').read_bytes(),original_input)
        bridge.import_archive(self.root,self.directory,plan['replacement_id'])
