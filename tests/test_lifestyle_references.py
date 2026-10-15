"""Grounding/scope integrity and local research extension, with synthetic evidence."""
from pathlib import Path
from unittest.mock import patch
import copy,json,unittest
from llm_authoring.core import Error,read_json,write_json
from llm_authoring.references import (LIFESTYLE_LIBRARY,lifestyle_context,lifestyle_library,
    validate_lifestyle_library,validate_lifestyle_references)
from llm_authoring.selection import topic_index,choose_subdirection
from llm_authoring.workspace import choose_domain
from llm_authoring.quality import candidate_check,reserve
from llm_authoring import platform_checks as qa,platform_client as client
import test_diversity as diversity
import test_platform_checks as platform_fixture
from test_arena_ranking import fill_five
from llm_authoring.ranking import export_complete,ranking_template
from llm_authoring.authoring import self_review_template
from llm_authoring.core import freeze,read_response


class LifestyleLibraryTests(unittest.TestCase):
    def test_traceable_unique_sources_cards_and_coverage_counts(self):
        data=lifestyle_library();validate_lifestyle_library(data)
        self.assertGreaterEqual(len(data['sources']),45);self.assertGreaterEqual(len(data['mechanisms']),70)
        self.assertEqual(len({s['url'].rstrip('/') for s in data['sources']}),len(data['sources']))
        self.assertEqual(data['source_count'],len(data['sources']))
        self.assertEqual(data['mechanism_count'],len(data['mechanisms']))
        self.assertEqual(data['scenario_seed_count'],sum(len(m['scenario_seeds']) for m in data['mechanisms']))
        leaves={n['id'] for n in topic_index('生活爱好类') if not n['has_children']}
        covered={n for m in data['mechanisms'] for n in m['node_ids']}
        self.assertEqual(data['directly_covered_leaf_count'],len(covered&leaves))
        self.assertEqual(set(data['uncovered_leaf_ids']),leaves-covered)
        self.assertEqual({s for m in data['mechanisms'] for s in m['source_ids']},{s['id'] for s in data['sources']})
        for m in data['mechanisms']:self.assertEqual(m['acceptance_status'],'unvalidated_scenario_seed')
    def test_pagination_covers_every_card_without_silent_truncation(self):
        result=lifestyle_context(limit=7);ids=[]
        while True:
            self.assertEqual(len(result['mechanism_index']),result['total'])
            self.assertLessEqual(len(result['mechanisms']),7)
            ids.extend(c['id'] for c in result['mechanisms'])
            if result['next_offset'] is None:break
            result=lifestyle_context(limit=7,offset=result['next_offset'])
        self.assertEqual(len(ids),len(set(ids)));self.assertEqual(len(ids),result['total'])
        for args in ({'branch':'madeup'},{'limit':0},{'offset':-1}):
            with self.assertRaises(Error):lifestyle_context(**args)
    def test_specific_game_rules_do_not_leak_to_sibling_sport(self):
        ping=lifestyle_context('life_ball_table_tennis')
        self.assertTrue(ping['mechanisms'])
        badminton=lifestyle_context('life_ball_badminton')
        self.assertEqual(badminton['total'],0);self.assertIn('先研究',badminton['next'])
        self.assertEqual(badminton['coverage']['uncovered_leaf_ids'],['life_ball_badminton'])
        self.assertEqual(ping['coverage']['directly_covered_leaf_ids'],['life_ball_table_tennis'])
        ball=lifestyle_context('life_sports_ball',limit=30)
        self.assertTrue({c['id'] for c in ping['mechanisms']}<={c['id'] for c in ball['mechanisms']})
    def test_missing_unread_or_unknown_evidence_cannot_be_imported(self):
        original=lifestyle_library()
        for mutate in (lambda d:d['sources'][0]['verification'].update(status='search_only'),
                       lambda d:d['mechanisms'][0].update(source_ids=['missing']),
                       lambda d:d['mechanisms'][0].update(node_ids=['missing']),
                       lambda d:d['mechanisms'][0]['scenario_seeds'][0].update(constructed=False)):
            broken=copy.deepcopy(original);mutate(broken)
            with self.assertRaises(Error):validate_lifestyle_library(broken)
    def test_existing_label_overrides_preserved_and_missing_life_label_merged(self):
        old=client.default_config();old['domain_labels']={'计算机科学':'自定义CS','商科':'商科'}
        before=copy.deepcopy(old);value=client.validated_config(old)
        self.assertEqual(old,before);self.assertEqual(value['domain_labels']['计算机科学'],'自定义CS')
        self.assertEqual(value['domain_labels']['生活爱好类'],'生活爱好')
        old['domain_labels']['生活爱好类']='自定义生活';self.assertEqual(client.validated_config(old)['domain_labels']['生活爱好类'],'自定义生活')


class LifestyleCandidateTests(unittest.TestCase):
    setUp=diversity.DiversityTests.setUp
    tearDown=diversity.DiversityTests.tearDown
    candidate=diversity.DiversityTests.candidate
    def life(self):
        choose_domain(self.a,'生活爱好类');choose_subdirection(self.a,'life_garden_indoor')
        card=next(c for c in lifestyle_library()['mechanisms'] if c['id']=='LH-C-M01')
        q=self.candidate(self.a);q.update(domain='生活爱好类',subdirection='life_garden_indoor',
          prompt='两盆绿植叶子都垂了，一盆土干盆轻，另一盆托盘有水。我该一起补水吗？',
          insight=card['decisive_factor'],lifestyle_mechanisms=[card['id']],lifestyle_references=card['source_ids'])
        return q
    def test_grounding_required_and_wrong_topic_or_source_rejected(self):
        q=self.life();validate_lifestyle_references(self.a,q)
        for key,value in [('lifestyle_mechanisms',[]),('lifestyle_references',[]),('subdirection','life_games_board')]:
            broken=copy.deepcopy(q);broken[key]=value
            with self.assertRaises(Error):validate_lifestyle_references(self.a,broken)
    def test_source_hashes_stale_review_without_changing_other_domain_report(self):
        q=self.candidate(self.a);old=candidate_check(self.a,q)
        self.assertNotIn('lifestyle_library_sha256',old)
        q=self.life();review=diversity.accept(self.a,q)
        self.assertIn('lifestyle_library_sha256',review['report'])
        library=read_json(LIFESTYLE_LIBRARY)
        extra={'sources':[copy.deepcopy(library['sources'][0])],
               'mechanisms':[copy.deepcopy(library['mechanisms'][0])]}
        extra['sources'][0]['id']='LH-LOCAL-S01';extra['mechanisms'][0].update(id='LH-LOCAL-M01',source_ids=['LH-LOCAL-S01'])
        write_json(self.a/'drafts/lifestyle-supplement.json',extra)
        with self.assertRaisesRegex(Error,'过期'):reserve(self.a,q)
    def test_assistant_can_ground_uncovered_leaf_with_private_supplement(self):
        q=self.life();choose_subdirection(self.a,'life_ball_badminton');q['subdirection']='life_ball_badminton'
        data=lifestyle_library();source=copy.deepcopy(data['sources'][0]);source['id']='LH-LOCAL-S01'
        card=copy.deepcopy(data['mechanisms'][0]);card.update(id='LH-LOCAL-M01',node_ids=['life_ball_badminton'],source_ids=[source['id']])
        # Deliberately synthetic structural fixture; no real badminton claim.
        source['verification']['scope']='合成测试占位：不作为真实羽毛球来源或验收。'
        write_json(self.a/'drafts/lifestyle-supplement.json',{'sources':[source],'mechanisms':[card]})
        q.update(lifestyle_mechanisms=[card['id']],lifestyle_references=[source['id']])
        validate_lifestyle_references(self.a,q)
        result=lifestyle_context('life_ball_badminton',root=self.a)
        self.assertEqual(result['total'],1);self.assertEqual(result['coverage']['uncovered_leaf_ids'],[])
        self.assertEqual(result['supplement_counts'],{'sources':1,'mechanisms':1})
        combined=lifestyle_library(self.a)
        self.assertEqual(combined['source_count'],len(data['sources'])+1)
        self.assertEqual(combined['directly_covered_leaf_count'],data['directly_covered_leaf_count']+1)
        self.assertEqual(lifestyle_context('life_ball_badminton')['total'],0)
        duplicate=copy.deepcopy(data['mechanisms'][0]);duplicate['source_ids']=[source['id']]
        write_json(self.a/'drafts/lifestyle-supplement.json',{'sources':[source],'mechanisms':[duplicate]})
        with self.assertRaisesRegex(Error,'重复'):lifestyle_library(self.a)


class LifestyleFlowTests(unittest.TestCase):
    candidate=diversity.DiversityTests.candidate
    setUp=platform_fixture.PlatformTests.setUp
    tearDown=platform_fixture.PlatformTests.tearDown
    run_check=platform_fixture.PlatformTests.run_check
    fill=platform_fixture.PlatformTests.fill
    seed=platform_fixture.PlatformTests.seed
    three=platform_fixture.PlatformTests.three
    def test_life_selection_through_mocked_checks_and_five_original_md(self):
        choose_domain(self.root,'生活爱好类');choose_subdirection(self.root,'life_garden_indoor')
        card=next(c for c in lifestyle_library()['mechanisms'] if c['id']=='LH-C-M01')
        self.q.update(domain='生活爱好类',subdirection='life_garden_indoor',lifestyle_mechanisms=[card['id']],
                      lifestyle_references=card['source_ids'],insight=card['decisive_factor'])
        value,send=self.run_check('question',q=self.q)
        self.assertEqual(send.call_args.args[1]['params']['领域'],'生活爱好')
        diversity.accept(self.root,self.q);freeze(self.root,self.q)
        ev=self.three()
        for stage in ('criteria','attainment'):
            value,send=self.run_check(stage,ev=ev);self.assertTrue(value['accepted'])
        five=fill_five(self.root,ev);review=self_review_template(self.root);review['reviewer']='synthetic-test'
        for c in review['checks'].values():c.update(passed=True,reason='合成流程检查，不是实际生活题评测。')
        out=self.root/'delivery/v001';export_complete(self.root,five,review,ranking_template(self.root,five),out)
        self.assertEqual(len(list((out/'models').glob('*.md'))),5)
        for role,item in read_json(out/'fields.json')['models'].items():
            self.assertEqual((out/item['reply_file']).read_bytes(),(read_response(self.root,role)['directory']/'reply.md').read_bytes())
        # New domain does not weaken the post-model quality gate, even refresh.
        for role in ('gpt','claude'):
            for j in ev['models'][role]['points'].values():j.update(met=False,quotes=[])
        with patch('llm_authoring.platform_client.call') as send:
            with self.assertRaisesRegex(Error,'不合格'):qa.run_models(self.root,ev,refresh=True)
            send.assert_not_called()
