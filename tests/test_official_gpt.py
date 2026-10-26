import copy
import importlib.util
from pathlib import Path
import unittest
from llm_authoring.core import Error

file=Path(__file__).resolve().parents[1]/'browser_automation/gpt-client.py'
spec=importlib.util.spec_from_file_location('official_gpt_client',file)
gpt=importlib.util.module_from_spec(spec);spec.loader.exec_module(gpt)


class OfficialGptProofTests(unittest.TestCase):
    def setUp(self):
        self.events=[{'type':'thread.started','thread_id':'session'},
                     {'type':'item.completed','item':{'type':'agent_message','text':'原始合成回复。'}},
                     {'type':'turn.completed'}]
        self.rollout=[{'type':'session_meta','payload':{'id':'session'}},
                      {'type':'turn_context','payload':{'model':'gpt-5.6-sol','effort':'high','user_instructions':None}},
                      {'type':'response_item','payload':{'type':'message','role':'user','content':[{'type':'input_text','text':'合成题？'}]}}]

    def check(self,events=None,rollout=None,reply='原始合成回复。'):
        return gpt.verify_generation(events or self.events,rollout or self.rollout,'合成题？',reply)

    def test_actual_context_and_original_reply_match(self):
        self.assertTrue(self.check()['context_verified'])

    def test_wrong_model_or_effort_is_rejected(self):
        for change in ({'model':'another-model'},{'effort':'low'}):
            value=copy.deepcopy(self.rollout);value[1]['payload'].update(change)
            with self.assertRaises(Error):self.check(rollout=value)

    def test_incomplete_or_tool_using_response_is_not_evidence(self):
        with self.assertRaises(Error):self.check(events=self.events[:-1])
        with self.assertRaises(Error):self.check(events=self.events+[{'type':'item.completed','item':{'type':'command_execution'}}])

    def test_other_user_context_and_extra_instructions_are_rejected(self):
        extra=copy.deepcopy(self.rollout[-1]);extra['payload']['content'][0]['text']='额外的Insight或历史上下文'
        with self.assertRaises(Error):self.check(rollout=self.rollout+[extra])
        value=copy.deepcopy(self.rollout);value[1]['payload']['user_instructions']='读取本题考点'
        with self.assertRaises(Error):self.check(rollout=value)

    def test_changed_reply_or_wrong_session_is_rejected(self):
        with self.assertRaises(Error):self.check(reply='另一个回答')
        value=copy.deepcopy(self.rollout);value[0]['payload']['id']='another-session'
        with self.assertRaises(Error):self.check(rollout=value)


if __name__=='__main__':unittest.main()
