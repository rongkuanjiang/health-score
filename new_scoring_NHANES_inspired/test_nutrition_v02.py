"""Independent examples for the provisional fixed-core Nutrition model."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from nutrition_score import score_nutrition


def profile():
    return json.loads(Path(__file__).with_name('example_nutrition_request.json').read_text())


class NutritionV02Tests(unittest.TestCase):
    def test_worked_example_and_optional_independence(self):
        p = profile()
        original = deepcopy(p)
        r = score_nutrition(p)
        self.assertEqual(r['components']['b12']['score'], 50)
        self.assertEqual(r['components']['ferritin']['score'], 100)
        self.assertEqual(r['domain_score'], 75)
        self.assertEqual(r['display_score'], '75.0')
        self.assertEqual(p, original)
        p['observations'].pop('vitamin_d')
        p['observations']['albumin']['value'] = 1
        self.assertEqual(score_nutrition(p)['domain_score'], 75)
        self.assertTrue(any(n['code'] == 'laboratory_flag' for o in r['observations'] for n in o['notices']))

    def test_anchors_and_plateaus(self):
        for marker, examples in {'b12': [(75,25),(150,50),(185,65),(220,80),(260,90),(300,100),(600,100)], 'ferritin': [(7.5,20),(15,40),(22.5,57.5),(30,75),(65,87.5),(100,100),(300,100)]}.items():
            for value, expected in examples:
                p = profile(); p['observations'][marker]['value'] = value
                self.assertAlmostEqual(score_nutrition(p)['components'][marker]['score'], expected)
            p['observations'][marker]['value'] += 0.001
            self.assertIsNone(score_nutrition(p)['domain_score'])

    def test_units_and_reference_unit_consistency(self):
        p = profile(); o = p['observations']['b12']
        for key in ('value','lower_limit','upper_limit'): o[key] /= 0.738
        o['unit'] = 'pg/mL'
        p['observations']['ferritin']['unit'] = 'ng/mL'
        self.assertAlmostEqual(score_nutrition(p)['domain_score'],75)
        o['reference_unit'] = 'pmol/L'
        self.assertIsNone(score_nutrition(p)['domain_score'])

    def test_missing_invalid_and_bound_results(self):
        for marker in ('b12','ferritin'):
            p=profile(); del p['observations'][marker]
            self.assertIsNone(score_nutrition(p)['domain_score'])
            for field, values in {'value':[0,-1,True,float('nan'),float('inf')], 'qualifier':['<','<=','>','>='], 'unit':['wrong'], 'analyte':['wrong'], 'specimen_type':['whole_blood'], 'reliability':['unreliable'], 'reference_range_applicable':[False], 'upper_limit':[None], 'specimen_date':['2027-01-01','bad']}.items():
                for value in values:
                    p=profile();p['observations'][marker][field]=value
                    with self.subTest(marker=marker,field=field,value=value):
                        r=score_nutrition(p)
                        self.assertIsNone(r['domain_score'])
                        json.dumps(r,allow_nan=False)
            p=profile();p['observations'][marker]=None
            self.assertIsNone(score_nutrition(p)['domain_score'])

    def test_eligibility_selection_and_collection(self):
        for age,pregnancy in [(16,'not_pregnant'),(40,'pregnant'),(40,'unknown'),(None,'not_pregnant')]:
            p=profile();p['person'].update(age=age,pregnancy_status=pregnancy)
            self.assertIsNone(score_nutrition(p)['domain_score'])
        for field,value in [('specimen_date','2026-09-02'),('report_id','other'),('specimen_type','plasma')]:
            p=profile();p['observations']['b12'][field]=value
            self.assertIn('core_collection_mismatch',score_nutrition(p)['reasons'])
        p=profile();first=p['observations']['b12'];second=deepcopy(first);second.update(observation_id='second',value=400)
        p['observations']['b12']=[first,second]
        self.assertIsNone(score_nutrition(p)['domain_score'])
        p['selected_observation_ids']={'b12':first['observation_id']}
        self.assertEqual(score_nutrition(p)['domain_score'],75)
        second['observation_id']=first['observation_id']
        self.assertIsNone(score_nutrition(p)['domain_score'])

    def test_confounders_and_unknown_context(self):
        for key in ('iron_confounders','recent_iron_treatment_or_transfusion'):
            p=profile();p['context'][key]='present'
            self.assertIsNone(score_nutrition(p)['domain_score'])
            p['context'][key]='unknown'
            r=score_nutrition(p)
            self.assertEqual(r['domain_score'],75)
            self.assertIn(key+'_unknown',[n['code'] for n in r['components']['ferritin']['notices']])


if __name__ == '__main__':
    unittest.main()
