"""Acceptance checks for inflammation stage 2; no clinical validation implied."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import unittest

from inflammation_score import score_inflammation, display_score

TODAY = date(2026, 9, 24)
ROOT = Path(__file__).parent


def profile(value=2):
    r = json.loads((ROOT / 'example_inflammation_request.json').read_text())
    r['observations']['hs_crp']['value'] = value
    return r


def score(r):
    return score_inflammation(r, today=TODAY)


def component(r):
    return score(r)['components']['hs_crp']


def codes(r):
    return [n['code'] for n in r['notices']]


class InflammationTests(unittest.TestCase):
    def test_worked_examples_and_no_domain_total(self):
        for value, expected in [(0.5,100),(1,100),(1.5,90),(2,80),(3,60),(6.5,40),(10,20)]:
            with self.subTest(value=value):
                r = score(profile(value))
                self.assertEqual(r['components']['hs_crp']['score'], expected)
                self.assertEqual(r['status'], 'component_available')
                self.assertIsNone(r['domain_score'])
                self.assertEqual(r['domain_aggregation_status'], 'limited_marker_coverage')
                self.assertEqual(r['coverage']['missing_requirements'], [])

    def test_monotonicity_continuity_and_upper_boundary(self):
        values = [component(profile(i/100))['score'] for i in range(1, 1001)]
        self.assertTrue(all(a >= b for a,b in zip(values,values[1:])))
        for x in (1,2,3):
            self.assertAlmostEqual(component(profile(x-1e-9))['score'], component(profile(x+1e-9))['score'], places=6)
        r = component(profile(10.0001))
        self.assertIsNone(r['score'])
        self.assertIn('above_scoring_range', r['reasons'])
        self.assertIn('crp_above_10', codes(r))

    def test_unit_parity_and_bounds(self):
        for q, value, expected, reason in [('<',1,100,None),('<=',1,100,None),('<',.5,100,None),
            ('<',2,None,'bounded_result'),('>',3,None,'bounded_result'),('>=',10,None,'bounded_result'),
            ('>',10,None,'above_scoring_range'),('>=',11,None,'above_scoring_range'),
            ('<=',10,None,'bounded_result')]:
            for unit, factor in [('mg/L',1),('mg/dL',.1)]:
                with self.subTest(q=q, value=value, unit=unit):
                    r = profile(value*factor)
                    r['observations']['hs_crp'].update(unit=unit, qualifier=q)
                    c = component(r)
                    self.assertEqual(c['score'], expected)
                    if reason:
                        self.assertIn(reason,c['reasons'])
                    else:
                        self.assertEqual(c['status'],'scored_from_bound')
        r=profile(.2)
        r['observations']['hs_crp']['unit']='mg/dL'
        self.assertEqual(component(r)['score'],80)
        self.assertIn('hs_crp_risk_enhancer',codes(component(r)))

    def test_threshold_notices_respect_bounds_and_exclusions(self):
        for q,x,established in [('<',2,False),('<=',2,False),('>',1,False),('>=',2,True),('=',2,True),('>',10,True)]:
            r=profile(x)
            r['observations']['hs_crp']['qualifier']=q
            r['context']['acute_context']='present'
            c=component(r)
            self.assertIsNone(c['score'])
            self.assertEqual('hs_crp_risk_enhancer' in codes(c),established)
        r=profile(2)
        r['observations']['hs_crp']['qualifier']='<='
        self.assertIn('threshold_indeterminate_from_bound',codes(component(r)))

    def test_no_cbc_or_conventional_crp_fallback(self):
        r=profile(.5)
        hs=r['observations'].pop('hs_crp')
        r['observations']['standard_crp']=hs
        out=score(r)
        self.assertEqual(out['status'],'context_only')
        self.assertIsNone(out['components']['hs_crp']['score'])
        self.assertFalse(out['coverage']['hs_crp_present'])
        r['observations'].pop('standard_crp')
        self.assertEqual(score(r)['status'],'context_only')
        self.assertEqual(score({})['status'],'unavailable')

    def test_assay_and_research_equivalence(self):
        for assay in (None,'standard_crp','unknown','research_equivalent_hs_crp'):
            r=profile()
            r['observations']['hs_crp']['assay_type']=assay
            self.assertIn('unsupported_or_unknown_assay',component(r)['reasons'])
        r=profile()
        r['observations']['hs_crp'].update(assay_type='research_equivalent_hs_crp',
            assay_equivalence_verified=True,assay_equivalence_provenance='Synthetic verified method reference')
        self.assertEqual(component(r)['score'],80)

    def test_age_and_pregnancy_gates(self):
        for age, expected in [(17.99,None),(18,80),(85,80),(.5,None),(0,None),(True,None)]:
            r=profile(); r['person']['age']=age
            self.assertEqual(component(r)['score'],expected)
            if age==85:
                self.assertIn('older_age_limited_evidence',codes(component(r)))
        for state in ('pregnant','unknown',None,'no'):
            r=profile(); r['person']['pregnancy_status']=state
            self.assertIsNone(component(r)['score'])
        r=profile(); r['person']['pregnancy_status']='not_applicable'
        self.assertEqual(component(r)['score'],80)

    def test_collection_context_and_treatment(self):
        for state,reason in [('present','acute_context_present'),('unknown','acute_context_unknown'),(False,'acute_context_unknown')]:
            r=profile(); r['context']['acute_context']=state
            self.assertIn(reason,component(r)['reasons'])
        for field in ('chronic_inflammatory_condition','inflammation_affecting_treatment'):
            for state in ('present','unknown'):
                r=profile(); r['context'][field]=state
                c=component(r)
                self.assertEqual(c['score'],80)
                self.assertIn(field+'_'+state,codes(c))
        r=profile(); r['context'].pop('acute_context')
        self.assertIsNone(component(r)['score'])

    def test_dates_report_and_reliability(self):
        for key,value,reason in [('specimen_date',None,'specimen_date_required'),
            ('specimen_date','2026-09-25','invalid_specimen_date'),('specimen_date','2026-02-30','invalid_specimen_date'),
            ('specimen_date','20260901','invalid_specimen_date'),('report_id',' ','report_id_required'),
            ('reliability','unreliable','unreliable_result')]:
            r=profile(); r['observations']['hs_crp'][key]=value
            self.assertIn(reason,component(r)['reasons'])
        r=profile(); r['observations']['hs_crp']['reliability']='unknown'
        self.assertEqual(component(r)['score'],80)
        self.assertIn('reliability_unknown',codes(component(r)))
        self.assertEqual(score(profile())['observations'][0]['specimen_age_days'],23)

    def test_invalid_values_and_json_serialization(self):
        for value in (0,-1,True,'2',None,[],{},float('nan'),float('inf'),10**500):
            r=profile(value)
            out=score(r)
            self.assertIsNone(out['components']['hs_crp']['score'])
            self.assertIn('invalid_value',out['components']['hs_crp']['reasons'])
            json.dumps(out,allow_nan=False)
        r=profile(1e308); r['observations']['hs_crp']['unit']='mg/dL'
        self.assertIn('invalid_normalized_value',component(r)['reasons'])
        for key,value in [('unit','mmol/L'),('unit',{}),('qualifier','approximately'),('qualifier',[])]:
            r=profile(); r['observations']['hs_crp'][key]=value
            self.assertIsNone(component(r)['score'])

    def test_repeated_observation_selection(self):
        r=profile()
        first=r['observations']['hs_crp']
        second=deepcopy(first); second.update(value=.5, observation_id='second')
        r['observations']['hs_crp']=[first,second]
        self.assertIn('selection_required',component(r)['reasons'])
        r['selected_hs_crp_id']='synthetic-hscrp'
        self.assertEqual(component(r)['score'],80)
        r['selected_hs_crp_id']='second'
        self.assertEqual(component(r)['score'],100)
        second['observation_id']='synthetic-hscrp'
        self.assertIn('duplicate_observation_id',component(r)['reasons'])
        r['observations']['hs_crp']=[first,None]
        r.pop('selected_hs_crp_id')
        self.assertIn('selection_required',component(r)['reasons'])

    def test_cbc_context_units_flags_and_percentages(self):
        for value,unit in [(12,'10^9/L'),(12,'10^3/uL'),(12000,'cells/uL')]:
            r=profile(.5)
            r['observations']['wbc'].update(value=value,unit=unit)
            out=score(r)
            self.assertEqual(out['components']['hs_crp']['score'],100)
            self.assertEqual(out['observations'][1]['normalized_value'],12)
            self.assertIn('laboratory_flag',codes(out['observations'][1]))
        r=profile()
        r['observations']['absolute_neutrophils']={'value':55,'unit':'%'}
        obs=score(r)['observations'][-1]
        self.assertEqual(obs['normalized_unit'],'%')
        self.assertIn('percentage_not_absolute_count',codes(obs))
        self.assertIn('reference_interpretation_unavailable',codes(obs))
        r['observations']['wbc']['reference_range_applicable']=False
        self.assertEqual(score(r)['observations'][1]['reference_status'],'unavailable')

    def test_context_invalidity_does_not_erase_score(self):
        r=profile(); r['observations']['wbc']={'value':-12,'unit':'10^9/L','lab_flag':'Review'}
        out=score(r)
        self.assertEqual(out['components']['hs_crp']['score'],80)
        self.assertIn('invalid_value',out['observations'][1]['errors'])
        self.assertIn('laboratory_flag',codes(out['observations'][1]))

    def test_envelopes_and_malformed_observations(self):
        for r in ([],None,{'person':[]},{'context':None},{'observations':[]},{'observations':{'typo':{}}}):
            with self.assertRaises(ValueError):
                score(r)
        for raw in (None,42,'bad'):
            r=profile(); r['observations']['hs_crp']=raw
            self.assertIn('invalid_observation',component(r)['reasons'])

    def test_immutability_and_rounding(self):
        r=profile(); before=deepcopy(r)
        out=score(r)
        self.assertEqual(r,before)
        out['input']['person']['age']=1
        out['observations'][0]['observation']['value']=100
        self.assertEqual(r,before)
        self.assertEqual(display_score(80.05),'80.1')
        self.assertIsNone(display_score(None))
        self.assertIn('single_measurement_not_persistent_inflammation',codes(component(r)))

    def test_cli_example(self):
        p=subprocess.run([sys.executable,str(ROOT/'inflammation_score.py'),str(ROOT/'example_inflammation_request.json'),
                          '--today','2026-09-24'],capture_output=True,text=True,check=True)
        out=json.loads(p.stdout)
        self.assertEqual(out['components']['hs_crp']['display_score'],'80.0')


if __name__=='__main__':
    unittest.main()
