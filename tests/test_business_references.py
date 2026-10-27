from pathlib import Path
import copy
import json
import unittest
from llm_authoring.core import Error
from llm_authoring.references import LIBRARY,business_context,validate_business_references
from llm_authoring.selection import menu


class ReferenceTests(unittest.TestCase):
    def test_source_index_and_cards_are_bound_and_cover_all_business_branches(self):
        data=json.loads(LIBRARY.read_text());sources={s['id']:s for s in data['sources']}
        self.assertEqual(len(sources),len(data['sources']));self.assertGreaterEqual(len(sources),16)
        self.assertEqual(len({s['url'] for s in sources.values()}),len(sources))
        branches={b['id'] for b in menu('商科')}
        self.assertEqual({m['subdirection'] for m in data['mechanisms']},branches)
        for s in sources.values():
            self.assertTrue(s['url'].startswith('https://'))
            self.assertEqual(s['verified_on'],str(__import__('datetime').date.fromisoformat(s['verified_on'])))
            for key in ('publisher','verification','accessibility','boundaries'):self.assertTrue(s[key])
        for m in data['mechanisms']:
            self.assertTrue(set(m['source_ids'])<=set(sources))
            self.assertTrue(m['assumptions']);self.assertTrue(m['limits'])
            self.assertEqual(m['acceptance_status'],'unvalidated_scenario_seed')
            self.assertTrue(business_context(m['subdirection'])['sources'])
    def test_business_candidate_needs_supported_ids_and_matching_branch(self):
        card=business_context('business_operations')['mechanisms'][0]
        q={'domain':'商科','subdirection':'business_operations','business_mechanisms':[card['id']],
           'business_references':[card['source_ids'][0]]}
        validate_business_references(q)
        for key,value in [('business_mechanisms',[]),('business_references',['not-real']),('subdirection','business_accounting')]:
            broken=copy.deepcopy(q);broken[key]=value
            with self.assertRaises(Error):validate_business_references(broken)
    def test_unknown_branch_does_not_silently_return_an_empty_library(self):
        with self.assertRaises(Error):business_context('made-up')
