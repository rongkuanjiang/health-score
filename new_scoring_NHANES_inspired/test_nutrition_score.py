"""Nutrition stage-2 acceptance tests; these do not establish clinical validity."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import unittest

from nutrition_score import display_score, score_nutrition

ROOT = Path(__file__).parent


def profile(value=40):
    request = json.loads((ROOT / 'example_nutrition_request.json').read_text(encoding='utf-8'))
    request['observations']['vitamin_d']['value'] = value
    request['observations'].pop('b12', None)
    request['observations'].pop('ferritin', None)
    return request


def component(request):
    return score_nutrition(request)['components']['vitamin_d']


def codes(result):
    return [n['code'] for n in result['notices']]


class NutritionTests(unittest.TestCase):
    def test_worked_examples_and_domain_contract(self):
        for value, expected in [(15, 25), (30, 50), (40, 75), (50, 100), (75, 100), (125, 100)]:
            with self.subTest(value=value):
                r = score_nutrition(profile(value))
                c = r['components']['vitamin_d']
                self.assertEqual(c['score'], expected)
                self.assertEqual(c['status'], 'scored')
                self.assertEqual(c['reasons'], [])
                self.assertEqual(r['status'], 'unavailable')
                self.assertIsNone(r['domain_score'])
                self.assertEqual(r['domain_aggregation_status'], 'fixed_core')
                self.assertEqual(r['coverage']['scored_component_count'], 0)
                self.assertEqual(r['coverage']['defined_component_count'], 2)
                self.assertEqual(codes(r), ['limited_nutrition_coverage', 'provisional_points'])

    def test_units_and_upper_edge(self):
        for value, unit, expected in [(20, 'ng/mL', 100), (50, 'ng/mL', 100),
                                      (50.01, 'ng/mL', None), (125.01, 'nmol/L', None)]:
            p = profile(value)
            p['observations']['vitamin_d']['unit'] = unit
            c = component(p)
            self.assertEqual(c['score'], expected)
            if expected is None:
                self.assertIn('above_scoring_range', c['reasons'])
                self.assertIn('above_scoring_range_review', codes(c))
        for x in (1, 15, 29.99, 30, 40, 49.99, 50, 75, 125):
            p = profile(x / 2.5)
            p['observations']['vitamin_d']['unit'] = 'ng/mL'
            self.assertAlmostEqual(component(p)['score'], component(profile(x))['score'])

    def test_continuity_monotonicity_and_no_early_rounding(self):
        previous = -1
        for x in range(1, 126):
            score = component(profile(x))['score']
            self.assertGreaterEqual(score, previous)
            self.assertLessEqual(score, 100)
            previous = score
        for edge in (30, 50):
            self.assertAlmostEqual(component(profile(edge - 1e-8))['score'],
                                   component(profile(edge + 1e-8))['score'], places=6)
        for x, notice in [(29.99, 'below_reference_band'), (30, 'possible_inadequacy_band'),
                          (49.99, 'possible_inadequacy_band'), (50, 'reference_adequacy_band')]:
            self.assertIn(notice, codes(component(profile(x))))
        self.assertEqual(component(profile(49.99))['display_score'], '100.0')
        self.assertEqual(display_score(75.05), '75.1')
        self.assertIsNone(display_score(None))

    def test_bounds_never_score_and_endpoint_notices(self):
        for q, x, expected in [('<', 30, 'below_reference_band'), ('<=', 29.99, 'below_reference_band'),
                                ('<=', 30, 'reference_band_indeterminate_from_bound'),
                                ('<', 50, 'reference_band_indeterminate_from_bound'),
                                ('>=', 50, 'reference_band_indeterminate_from_bound'),
                                ('>', 125, 'above_scoring_range_review'),
                                ('>=', 125, 'reference_band_indeterminate_from_bound'),
                                ('>=', 125.01, 'above_scoring_range_review')]:
            with self.subTest(q=q, x=x):
                p = profile(x)
                p['observations']['vitamin_d']['qualifier'] = q
                r = score_nutrition(p)
                c = r['components']['vitamin_d']
                self.assertIsNone(c['score'])
                self.assertIn('bounded_result', c['reasons'])
                self.assertIn(expected, codes(c))
                self.assertEqual(r['observations'][0]['qualifier'], q)

    def test_no_surrogate_or_optional_marker_weight(self):
        for marker in ('b12', 'ferritin', 'hemoglobin', 'albumin'):
            p = profile(75)
            o = p['observations']['albumin']
            o['observation_id'] = 'context-' + marker
            p['observations'][marker] = o
            if marker != 'albumin':
                del p['observations']['albumin']
            self.assertEqual(component(p)['score'], 100)
            del p['observations']['vitamin_d']
            r = score_nutrition(p)
            self.assertIsNone(r['components']['vitamin_d']['score'])
            self.assertEqual(r['status'], 'unavailable')
            self.assertTrue(r['coverage']['missing'])
            self.assertIn('laboratory_flag', codes(r['observations'][0]))

    def test_invalid_numeric_inputs_and_strict_serialization(self):
        for value in (0, -1, float('nan'), float('inf'), float('-inf'), True, False, '40', None, [], {}, 10**400):
            with self.subTest(value=str(value)[:30]):
                r = score_nutrition(profile(value))
                self.assertIsNone(r['components']['vitamin_d']['score'])
                self.assertIn('invalid_value', r['components']['vitamin_d']['reasons'])
                json.dumps(r, allow_nan=False)
        p = profile(1e308)
        p['observations']['vitamin_d']['unit'] = 'ng/mL'
        r = score_nutrition(p)
        self.assertIn('invalid_normalized_value', r['components']['vitamin_d']['reasons'])
        json.dumps(r, allow_nan=False)

    def test_identity_units_and_qualifier_validation(self):
        for key, value, reason in [('analyte', '1_25_dihydroxyvitamin_d', 'unsupported_analyte'),
                                   ('analyte', 'vitamin_d3', 'unsupported_analyte'),
                                   ('analyte', None, 'unsupported_analyte'),
                                   ('specimen_type', 'urine', 'unsupported_or_unknown_specimen_type'),
                                   ('specimen_type', None, 'unsupported_or_unknown_specimen_type'),
                                   ('unit', 'mg/L', 'unsupported_unit'),
                                   ('unit', [], 'unsupported_unit'),
                                   ('qualifier', '~', 'unsupported_qualifier')]:
            p = profile()
            p['observations']['vitamin_d'][key] = value
            c = component(p)
            self.assertIsNone(c['score'])
            self.assertIn(reason, c['reasons'])
            self.assertNotIn('possible_inadequacy_band', codes(c))

    def test_plasma_is_supported_and_raw_flags_survive_exclusion(self):
        p = profile()
        p['observations']['vitamin_d']['specimen_type'] = 'plasma'
        self.assertEqual(component(p)['score'], 75)
        p['observations']['vitamin_d'].update(specimen_type='urine', lab_flag='Reported flag')
        c = component(p)
        self.assertIsNone(c['score'])
        self.assertIn('laboratory_flag', codes(c))

    def test_selection_is_explicit_and_no_fallback(self):
        p = profile()
        a = p['observations']['vitamin_d']
        b = deepcopy(a)
        b.update(observation_id='second', value=75)
        p['observations']['vitamin_d'] = [a, b]
        self.assertIn('selection_required', component(p)['reasons'])
        p['selected_vitamin_d_id'] = 'second'
        self.assertEqual(component(p)['score'], 100)
        b['value'] = -1
        self.assertIn('invalid_value', component(p)['reasons'])
        self.assertIsNone(component(p)['score'])
        p['selected_vitamin_d_id'] = 'nonexistent'
        self.assertIn('selection_required', component(p)['reasons'])
        p['selected_vitamin_d_id'] = a['observation_id']
        b['observation_id'] = a['observation_id']
        self.assertIn('selection_required', component(p)['reasons'])
        self.assertIn('duplicate_observation_id', score_nutrition(p)['observations'][0]['errors'])

    def test_required_ids_dates_and_explicit_evaluation_date(self):
        for key, reason in [('observation_id', 'observation_id_required'),
                             ('report_id', 'report_id_required'), ('specimen_date', 'specimen_date_required')]:
            p = profile()
            del p['observations']['vitamin_d'][key]
            self.assertIn(reason, component(p)['reasons'])
        for day, reason in [('2026-09-25', 'future_specimen_date'), ('2026-02-30', 'invalid_specimen_date'),
                             ('20260901', 'invalid_specimen_date'), (True, 'invalid_specimen_date')]:
            p = profile()
            p['observations']['vitamin_d']['specimen_date'] = day
            self.assertIn(reason, component(p)['reasons'])
        r = score_nutrition(profile())
        self.assertEqual(r['observations'][0]['specimen_age_days'], 23)
        p = profile()
        del p['evaluation_date']
        self.assertIn('evaluation_date_required', component(p)['reasons'])
        self.assertEqual(score_nutrition(p, today=date(2026, 9, 24))['components']['vitamin_d']['score'], 75)
        for bad in ('2026-02-30', '', 5):
            p['evaluation_date'] = bad
            self.assertIn('invalid_evaluation_date', component(p)['reasons'])
        r = score_nutrition(profile(), today=date(2026, 9, 25))
        self.assertIn('invalid_evaluation_date', r['components']['vitamin_d']['reasons'])

    def test_age_pregnancy_and_reference_notice_gates(self):
        for age, reason in [(17.99, 'pediatric_points_not_defined'), (0, 'invalid_age'),
                            (-1, 'invalid_age'), (True, 'invalid_age'), (float('nan'), 'invalid_age')]:
            p = profile()
            p['person']['age'] = age
            c = component(p)
            self.assertIn(reason, c['reasons'])
            self.assertNotIn('possible_inadequacy_band', codes(c))
        for age in (18, 85, 100):
            p = profile()
            p['person']['age'] = age
            c = component(p)
            self.assertEqual(c['score'], 75)
            self.assertEqual('older_age_limited_evidence' in codes(c), age >= 85)
        for state in ('pregnant', 'unknown', None, 'invalid'):
            p = profile()
            p['person']['pregnancy_status'] = state
            c = component(p)
            self.assertIsNone(c['score'])
            self.assertNotIn('possible_inadequacy_band', codes(c))
            self.assertIn('laboratory_flag', codes(score_nutrition(p)['observations'][1]))

    def test_reliability_and_optional_context(self):
        for state, expected in [('valid', 75), ('unknown', 75), ('unreliable', None), ('bogus', None)]:
            p = profile()
            p['observations']['vitamin_d']['reliability'] = state
            c = component(p)
            self.assertEqual(c['score'], expected)
            if state == 'unknown':
                self.assertIn('reliability_unknown', codes(c))
        for state in ('present', 'absent', 'unknown', [], 'bogus'):
            p = profile()
            p['context'] = {key: state for key in ('vitamin_d_supplementation', 'vitamin_d_treatment', 'relevant_conditions')}
            self.assertEqual(component(p)['score'], 75)

    def test_context_reference_ranges_and_no_cross_specimen_interpretation(self):
        base = profile()
        self.assertEqual(score_nutrition(base)['observations'][1]['reference_status'], 'low')
        for overrides in ({'lower_limit': 60}, {'upper_limit': float('nan')},
                          {'reference_unit': 'g/dL'}, {'reference_range_applicable': False},
                          {'reference_analyte': 'rbc_folate'}, {'reference_specimen_type': 'rbc'},
                          {'qualifier': '<'}, {'reliability': 'unreliable'}):
            p = deepcopy(base)
            p['observations']['albumin'].update(overrides)
            r = score_nutrition(p)
            self.assertEqual(r['components']['vitamin_d']['score'], 75)
            self.assertEqual(r['observations'][1]['reference_status'], 'unavailable')
            self.assertIn('laboratory_flag', codes(r['observations'][1]))
        for context in (None, True, 'bad', {'value': -1}, [{'value': 1}, None]):
            p = profile()
            p['observations']['albumin'] = context
            self.assertEqual(component(p)['score'], 75)

    def test_reason_order_retains_independent_failures(self):
        p = profile(-1)
        p['person']['age'] = 17
        p['person']['pregnancy_status'] = 'unknown'
        p['observations']['vitamin_d'].update(unit='bad', reliability='unreliable')
        del p['observations']['vitamin_d']['report_id']
        self.assertEqual(component(p)['reasons'], ['invalid_value', 'unsupported_unit', 'report_id_required',
                         'pediatric_points_not_defined', 'pregnancy_status_unknown', 'unreliable_result'])

    def test_copy_isolation_and_provenance(self):
        p = profile()
        original = deepcopy(p)
        r = score_nutrition(p)
        self.assertEqual(p, original)
        r['input']['person']['age'] = 1
        r['observations'][0]['observation']['value'] = 1
        r['components']['vitamin_d']['notices'].append({'code': 'test', 'text': 'test'})
        self.assertEqual(p, original)
        self.assertNotIn('test', codes(r['observations'][0]))
        json.dumps(r, allow_nan=False)

    def test_malformed_envelopes(self):
        for p in ([], None, {'person': []}, {'context': None}, {'observations': []},
                  {'observations': {'typo': {}}}, {'extra': object()}):
            with self.assertRaises(ValueError):
                score_nutrition(p)
        with self.assertRaises(ValueError):
            score_nutrition(profile(), today='2026-09-24')
        p = profile()
        p['observations']['vitamin_d'] = None
        self.assertIn('invalid_observation', component(p)['reasons'])

    def test_cli_example(self):
        result = subprocess.run([sys.executable, str(ROOT / 'nutrition_score.py'),
                                 str(ROOT / 'example_nutrition_request.json')], capture_output=True, text=True, check=True)
        r = json.loads(result.stdout)
        self.assertEqual(r['components']['vitamin_d']['display_score'], '75.0')
        self.assertEqual(r['domain_score'], 75)


if __name__ == '__main__':
    unittest.main()
