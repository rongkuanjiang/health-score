"""Independent numerical examples plus point eligibility and selection boundaries."""
import unittest
from copy import deepcopy
from test_system_stability_score import profile, score, marker, calcium


class PointTests(unittest.TestCase):
    def test_anchors_and_both_tails(self):
        for key, pairs in {
            'sodium': [(1,0),(120,0),(125,25),(130,60),(132.5,80),(135,100),(140,100),
                       (145,100),(147.5,80),(150,60),(155,25),(160,0),(1000,0)],
            'potassium': [(0.1,0),(2,0),(2.5,25),(3,60),(3.25,80),(3.5,100),(4,100),
                          (5,100),(5.25,80),(5.5,60),(6,25),(6.5,0),(100,0)]}.items():
            for value, expected in pairs:
                with self.subTest(key=key,value=value):
                    q=profile();q['observations'][key]['value']=value
                    r=score(q)
                    self.assertAlmostEqual(r['marker_scores'][key],expected)
                    self.assertAlmostEqual(r['domain_score'],50+expected/2)

    def test_worked_calculation_and_context_independence(self):
        q=profile();q['observations']['sodium']['value']=132.5;q['observations']['potassium']['value']=5.5
        r=score(q)
        self.assertEqual(r['weighted_contributions'],{'sodium':40,'potassium':30})
        self.assertEqual(r['domain_score'],70);self.assertEqual(r['display_score'],'70.0')
        for key in ('chloride','total_co2'):
            del q['observations'][key];del q['selection']['observation_ids'][key]
        calcium(q).update(value=20,source_flags=['critical_high'])
        r=score(q);self.assertEqual(r['domain_score'],70);self.assertTrue(r['review_required'])

    def test_missing_core_never_renormalizes(self):
        q=profile();del q['observations']['sodium']
        r=score(q);self.assertIsNone(r['domain_score']);self.assertEqual(r['marker_scores']['potassium'],100)
        self.assertEqual(r['coverage']['scored'],1)

    def test_point_gates_preserve_reference_information(self):
        for person in ({},{'age':17,'pregnancy_status':'not_applicable'},
                       {'age':40,'pregnancy_status':'pregnant'},{'age':40,'pregnancy_status':'unknown'},
                       {'age':True,'pregnancy_status':'not_applicable'},None):
            q=profile();q['person']=person;r=score(q)
            self.assertIsNone(r['domain_score']);self.assertTrue(r['score_reasons'])
            self.assertEqual(r['panel_status'],'all_within_reference')

    def test_unusable_points_retain_other_marker(self):
        for change in ({'value':float('nan')},{'value':float('inf')},{'value':0},
                       {'unit':'mg/dL'},{'reference_unit':'mg/dL'}, {'reliability':'unknown'},
                       {'reliability':'unreliable'},{'qualifier':'<'},{'qualifier':'>'},
                       {'reference_marker':'chloride'}, {'specimen_type':'whole_blood'},
                       {'specimen_date':'2026-09-19'}, {'report_id':'other'}, {'specimen_id':'other'}):
            with self.subTest(change=change):
                q=profile();q['observations']['potassium'].update(change);r=score(q)
                self.assertIsNone(r['domain_score']);self.assertEqual(r['marker_scores']['sodium'],100)
        q=profile();q['observations']['potassium']=[q['observations']['potassium'],deepcopy(q['observations']['potassium'])]
        self.assertIsNone(score(q)['domain_score'])

    def test_high_average_keeps_critical_flag_and_unit_parity(self):
        q=profile();q['observations']['potassium'].update(unit='mEq/L',source_flags=['critical_high'])
        r=score(q);self.assertEqual(r['domain_score'],100);self.assertTrue(r['review_required'])
        self.assertEqual(r['panel_status'],'source_critical_flag')
        self.assertIn('source_flag_conflict',marker(r)['notices'])

    def test_unselected_favourable_result_cannot_replace_selected(self):
        q=profile();old=deepcopy(q['observations']['potassium']);old['observation_id']='old'
        q['observations']['potassium']['value']=6
        q['observations']['potassium']=[old,q['observations']['potassium']]
        self.assertEqual(score(q)['domain_score'],62.5)
