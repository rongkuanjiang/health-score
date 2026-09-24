"""Executable acceptance checks for the provisional specification."""
from copy import deepcopy
from datetime import date, timedelta
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import unittest

from metabolism_score import MARKERS, VERSION, _PARAMS, _curve, display_score, score_metabolism

TODAY = date(2026, 9, 24)


def profile(values=(5, 2, 1, 1.5)):
    return {'snapshot_id': 'synthetic-example',
            'person': {'age': 40, 'pregnancy_status': 'no', 'sex_reference': 'female'},
            'context': {'fasting_status': 'fasting', 'ldl_method': 'direct', 'hba1c_interference': 'no'},
            'observations': {m: {'value': v, 'unit': '%' if m == 'hba1c' else 'mmol/L',
                                'report_id': 'example-report', 'specimen_date': '2026-09-01',
                                'reliability': 'valid'} for m, v in zip(MARKERS, values)}}


def score(request):
    return score_metabolism(request, today=TODAY)


class EngineTests(unittest.TestCase):
    def test_worked_profiles(self):
        for values, expected in [((5, 2, 1, 1.5), 100), ((5.5, 3, 1.7, 1.3), 85.625),
                                 ((6, 3.5, 2.3, 1), 66.25), ((6.5, 5, 5.6, .8), 40),
                                 ((5, 2, 10, 1.5), 88.125)]:
            with self.subTest(values=values):
                r = score(profile(values))
                self.assertEqual(r['score'], expected)
                self.assertEqual(r['status'], 'scored')
                self.assertEqual(r['model_version'], VERSION)
                self.assertEqual(r['coverage'], {'scored': 4, 'required': 4})

    def test_anchors_interpolation_tails_and_bounds(self):
        for marker, params in _PARAMS['curves'].items():
            for nonfasting in ([False, True] if marker == 'triglycerides' else [False]):
                anchors = params['nonfasting_anchors'] if nonfasting else params['anchors']
                for x, y in anchors:
                    self.assertAlmostEqual(_curve(marker, x, nonfasting)[0], y)
                for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
                    self.assertAlmostEqual(_curve(marker, (x0+x1)/2, nonfasting)[0], (y0+y1)/2)
                if marker != 'hdl_c':
                    x, y = anchors[-1]
                    self.assertAlmostEqual(_curve(marker, x + params['above_last_anchor']['interval'], nonfasting)[0], y/2)
                    self.assertAlmostEqual(_curve(marker, x+1e-9, nonfasting)[0], y, places=7)
                xs = [4+i*.02 for i in range(1500)] if marker == 'hba1c' else [0.001+i*.002 for i in range(1249)] if marker == 'hdl_c' else [0.001+i*.02 for i in range(2000)]
                ys = [_curve(marker, x, nonfasting)[0] for x in xs]
                self.assertTrue(all(0 <= y <= 100 for y in ys))
                self.assertTrue(all(a <= b if marker == 'hdl_c' else a >= b for a, b in zip(ys, ys[1:])))
        self.assertEqual(_curve('hdl_c', .25)[0], 2.5)

    def test_unit_equivalence(self):
        original = profile((6.3, 3.7, 2.1, 1.2))
        converted = deepcopy(original)
        factors = {'ldl_c': .02586, 'hdl_c': .02586, 'triglycerides': .01129}
        for m, obs in converted['observations'].items():
            if m == 'hba1c':
                obs.update(value=(obs['value']-2.152)/.09148, unit='mmol/mol')
            else:
                obs.update(value=obs['value']/factors[m], unit='mg/dL')
        a, b = score(original), score(converted)
        self.assertAlmostEqual(a['score'], b['score'])
        for m in MARKERS:
            self.assertAlmostEqual(a['markers'][m]['score'], b['markers'][m]['score'])

    def test_input_validation(self):
        for m in MARKERS:
            for value, expected in [(None, 'missing'), (True, 'invalid_input'), (False, 'invalid_input'),
                                    (0, 'invalid_input'), (-1, 'invalid_input'), ('5', 'invalid_input'),
                                    (float('nan'), 'invalid_input'), (float('inf'), 'invalid_input'),
                                    (10**1000, 'invalid_input'), ('<4', 'censored_result'), ('>10', 'censored_result')]:
                with self.subTest(marker=m, value=str(value)[:30]):
                    p = profile()
                    p['observations'][m]['value'] = value
                    r = score(p)
                    self.assertEqual(r['markers'][m]['status'], expected)
                    self.assertIsNone(r['score'])
                    json.dumps(r, allow_nan=False)
            p = profile()
            p['observations'][m]['unit'] = 'unknown'
            self.assertEqual(score(p)['markers'][m]['status'], 'unsupported_unit')
            p['observations'][m] = 5
            self.assertEqual(score(p)['markers'][m]['status'], 'invalid_input')
            del p['observations'][m]
            r = score(p)
            self.assertEqual(r['coverage']['scored'], 3)
            self.assertIsNone(r['score'])
        p = profile()
        p['observations']['hba1c']['qualifier'] = '<'
        self.assertEqual(score(p)['markers']['hba1c']['status'], 'censored_result')

    def test_coverage_boundaries(self):
        for value, expected in [(3.999, 'below_model_coverage'), (4, 'scored')]:
            p = profile(); p['observations']['hba1c']['value'] = value
            self.assertEqual(score(p)['markers']['hba1c']['status'], expected)
        for value, expected in [(2.499999, 'scored'), (2.5, 'high_hdl_outside_model_coverage')]:
            p = profile(); p['observations']['hdl_c']['value'] = value
            self.assertEqual(score(p)['markers']['hdl_c']['status'], expected)

    def test_pregnancy_gate_suppresses_all_interpretation(self):
        for state, expected in [('yes', 'outside_scope'), ('unknown', 'eligibility_required'), (None, 'eligibility_required'), ('typo', 'eligibility_required')]:
            p = profile((20, 12, 20, .2)); p['person']['pregnancy_status'] = state
            p['optional_observations'] = {'apob': {'value': 2, 'unit': 'g/L'}}
            r = score(p)
            self.assertEqual(r['status'], expected)
            self.assertIsNone(r['score'])
            self.assertFalse(r['flags'])
            self.assertFalse(r['optional_context'])
            for m in r['markers'].values():
                self.assertIsNone(m['score'])
                self.assertFalse(m['flags'])
                self.assertFalse(m['interpretation'])
        p = profile(); del p['person']['pregnancy_status']
        self.assertEqual(score(p)['status'], 'eligibility_required')
        p['person']['pregnancy_status'] = 'not_applicable'
        self.assertEqual(score(p)['score'], 100)

    def test_age_and_sex_unadjusted(self):
        for age in (0.1, 5, 17, 19.999, 20, 50, 84.999, 85, 100):
            for sex in ('male', 'female', 'unknown'):
                p = profile((5.5, 3, 1.7, 1.2)); p['person'].update(age=age, sex_reference=sex)
                self.assertEqual(score(p)['score'], score(profile((5.5, 3, 1.7, 1.2)))['score'])
        p = profile(); p['person']['age'] = 19.999
        self.assertEqual(score(p)['status'], 'scored')
        self.assertEqual(score(p)['coverage']['scored'], 4)
        for age in (None, 0, -1, '40', True, float('inf')):
            p['person']['age'] = age
            self.assertEqual(score(p)['status'], 'eligibility_required')
            self.assertIsNone(score(p)['score'])
        p['person']['age'] = None
        self.assertEqual(score(p)['coverage']['scored'], 4)

    def test_age_extension_notices_and_other_safeguards(self):
        for age, expected in [(12, 'younger_age_extrapolation'), (19.999, 'younger_age_extrapolation'), (20, 'adult_reference'), (84.999, 'adult_reference'), (85, 'older_age_limited_evidence'), (105, 'older_age_limited_evidence')]:
            p = profile((6.5, 5, 5.6, .8)); p['person']['age'] = age
            result = score(p)
            self.assertEqual(result['age_applicability'], expected)
            self.assertEqual(result['score'], 40)
            codes = [f['code'] for f in result['flags']]
            if expected != 'adult_reference':
                self.assertIn(expected, codes)
            if age < 20:
                self.assertNotIn('a1c_diabetes_range', codes)
                self.assertNotIn('hdl_low_reference', codes)
            p['person']['pregnancy_status'] = 'yes'
            self.assertIsNone(score(p)['score'])
            self.assertFalse(score(p)['flags'])
            p['person']['pregnancy_status'] = 'no'
            del p['observations']['triglycerides']
            self.assertIsNone(score(p)['score'])

    def test_unknown_and_nonfasting(self):
        for value, primary, alternative in [(1.7, 80, 86), (2, 70, 80), (1, 100, 100)]:
            p = profile(); p['observations']['triglycerides']['value'] = value
            p['context']['fasting_status'] = 'nonfasting'
            self.assertAlmostEqual(score(p)['markers']['triglycerides']['score'], alternative)
            p['context']['fasting_status'] = 'unknown'
            r = score(p)
            self.assertEqual(r['markers']['triglycerides']['score'], primary)
            self.assertAlmostEqual(r['alternative_nonfasting']['triglycerides'], alternative)
            self.assertIn('tg_fasting_unknown', [f['code'] for f in r['flags']])
            self.assertNotIn('tg_elevated_reference', [f['code'] for f in r['flags']])
        p = profile((5, 2, 2, 1.5)); p['context']['fasting_status'] = 'unknown'
        r = score(p)
        self.assertEqual(r['score'], 96.25)
        self.assertEqual(r['alternative_nonfasting']['metabolism'], 97.5)

    def test_fasting_duration_and_conflicts(self):
        for hours, state in [(0, 'nonfasting'), (7.99, 'nonfasting'), (8, 'fasting'), (23.99, 'fasting')]:
            p = profile(); p['context'].update(fasting_status='unknown', fasting_hours=hours)
            self.assertEqual(score(p)['fasting_status'], state)
        for hours in (4, 24, 30):
            p = profile(); p['context']['fasting_hours'] = hours
            self.assertEqual(score(p)['markers']['triglycerides']['status'], 'fasting_context_conflict')
            p['context']['use_unknown_fasting_on_conflict'] = True
            r = score(p)
            self.assertEqual(r['status'], 'scored')
            self.assertEqual(r['fasting_status'], 'unknown')
            self.assertIn('fasting_conflict_recorded', [f['code'] for f in r['flags']])
        for bad in (True, -1, float('nan'), '8', 10**1000):
            p = profile(); p['context']['fasting_hours'] = bad
            self.assertEqual(score(p)['markers']['triglycerides']['status'], 'invalid_fasting_hours')

    def test_ldl_reliability(self):
        for unit, value in [('mmol/L', 4.516), ('mg/dL', 400)]:
            for method, validity, expected in [('friedewald', 'valid', 'ldl_calculation_unreliable'),
                ('unknown', 'valid', 'ldl_method_required'), ('other_lab_calculated', 'unknown', 'ldl_validity_confirmation_required'),
                ('other_lab_calculated', 'valid', 'scored'), ('direct', 'unknown', 'scored')]:
                p = profile(); p['observations']['triglycerides'].update(value=value, unit=unit)
                p['context']['ldl_method'] = method
                p['observations']['ldl_c']['reliability'] = validity
                self.assertEqual(score(p)['markers']['ldl_c']['status'], expected)
        p = profile((5, 2, 4.515999, 1.5)); p['context']['ldl_method'] = 'friedewald'
        self.assertEqual(score(p)['status'], 'scored')
        del p['observations']['triglycerides']
        r = score(p)
        self.assertEqual(r['markers']['ldl_c']['score'], 100)
        self.assertIn('ldl_reliability_context_incomplete', [f['code'] for f in r['flags']])

    def test_invalid_labs_and_interference_suppress_clinical_flags(self):
        p = profile((9, 6, 12, .3))
        for m in MARKERS:
            q = deepcopy(p); q['observations'][m]['reliability'] = 'invalid'
            r = score(q)['markers'][m]
            self.assertEqual(r['status'], 'laboratory_invalid')
            self.assertFalse(r['flags'])
        p['context']['hba1c_interference'] = 'yes'
        r = score(p)
        self.assertEqual(r['markers']['hba1c']['status'], 'interpretation_interference')
        self.assertFalse(r['markers']['hba1c']['flags'])
        self.assertIsNotNone(r['components']['lipid_health']['score'])
        p['context']['hba1c_interference'] = 'unknown'
        self.assertIsNotNone(score(p)['score'])

    def test_dates_and_report_selection(self):
        p = profile()
        for gap, expected in [(90, 'scored'), (91, 'dates_not_aligned')]:
            p['observations']['hba1c']['specimen_date'] = (date(2026, 9, 1)-timedelta(days=gap)).isoformat()
            r = score(p)
            self.assertEqual(r['status'], expected)
            self.assertEqual(r['snapshot_date'], '2026-09-01')
            self.assertEqual(r['coverage']['scored'], 4)
        p = profile()
        for obs in p['observations'].values(): obs.pop('specimen_date')
        self.assertEqual(score(p)['status'], 'scored')
        self.assertIn('dates_unverified', [f['code'] for f in score(p)['flags']])
        p.pop('snapshot_id')
        self.assertIn('snapshot_selection_required', score(p)['blocking_reasons'])
        for invalid in ('2026-09-25', '2026-02-30', '20260901', True):
            p = profile(); p['observations']['hba1c']['specimen_date'] = invalid
            self.assertIn('hba1c:invalid_specimen_date', score(p)['blocking_reasons'])
        p = profile(); p['observations']['hdl_c']['report_id'] = 'unrelated'
        r = score(p)
        self.assertIsNone(r['score'])
        self.assertIsNone(r['components']['lipid_health']['score'])
        p = profile(); p['observations']['hdl_c']['specimen_date'] = '2026-08-31'
        self.assertIn('lipid_report_dates_conflict', score(p)['blocking_reasons'])

    def test_flags_survive_compensation_and_blocking(self):
        r = score(profile((5, 2, 10, 1.5)))
        self.assertEqual(r['score'], 88.125)
        self.assertIn('tg_very_high', [f['code'] for f in r['flags']])
        self.assertNotIn('tg_markedly_elevated', [f['code'] for f in r['flags']])
        p = profile((6.5, 5, 10, 2.5)); p['context']['ldl_method'] = 'friedewald'
        r = score(p)
        codes = [f['code'] for f in r['flags']]
        for code in ('tg_very_high', 'ldl_markedly_elevated', 'hdl_high_outside_coverage', 'a1c_diabetes_range'):
            self.assertIn(code, codes)
        self.assertIsNone(r['score'])

    def test_optional_context_and_non_hdl(self):
        p = profile()
        p['optional_observations'] = {'apob': {'value': 100, 'unit': 'mg/dL'},
            'bmi': {'value': True, 'unit': 'kg/m²'}, 'glucose': {'value': 90, 'unit': 'mg/dL', 'type': 'random'},
            'total_cholesterol': {'value': 5, 'unit': 'mmol/L', 'report_id': 'example-report'}}
        r = score(p)
        self.assertEqual(r['score'], 100)
        self.assertEqual(r['optional_context']['apob']['normalized_value'], 1)
        self.assertEqual(r['optional_context']['bmi']['status'], 'invalid_input')
        self.assertEqual(r['optional_context']['glucose']['normalized_value'], 90)
        self.assertEqual(r['optional_context']['non_hdl_c']['normalized_value'], 3.5)
        p['optional_observations']['total_cholesterol']['report_id'] = 'unrelated'
        self.assertIsNone(score(p)['optional_context']['non_hdl_c']['normalized_value'])
        p['observations']['hdl_c'] = 5
        self.assertEqual(score(p)['markers']['hdl_c']['status'], 'invalid_input')

    def test_rounding_and_no_mutation(self):
        self.assertEqual(display_score(85.625), '85.6')
        self.assertEqual(display_score(66.25), '66.3')
        self.assertEqual(display_score(.049), '<0.1')
        self.assertEqual(display_score(None), None)
        p = profile(); original = deepcopy(p)
        r = score(p)
        self.assertEqual(p, original)
        r['provenance']['person']['age'] = 99
        self.assertEqual(p, original)

    def test_envelope_validation(self):
        for p in (None, [], {'person': []}, {'observations': None}):
            with self.assertRaises(ValueError): score(p)

    def test_javascript_hba1c_parity(self):
        node = os.environ.get('NODE_EXE') or shutil.which('node')
        if not node:
            self.skipTest('Set NODE_EXE to run parity against the original JavaScript engine')
        values = [3.9, 4, 4.7, 5, 5.25, 5.5, 5.8, 6, 6.5, 7, 8, 9, 10, 12, 14, 30]
        script = "import {scoreHba1c} from './hba1c_score.mjs'; console.log(JSON.stringify(" + json.dumps(values) + '.map(x=>scoreHba1c(x))));'
        completed = subprocess.run([node, '--input-type=module', '-e', script], cwd=Path(__file__).parent, check=True, capture_output=True, text=True)
        for value, expected in zip(values, json.loads(completed.stdout)):
            p = profile(); p['observations']['hba1c']['value'] = value
            actual = score(p)['markers']['hba1c']
            self.assertEqual(actual['status'], expected['status'])
            self.assertEqual(actual['version'], expected['version'])
            self.assertEqual(actual['score'], expected['score'])


if __name__ == '__main__':
    unittest.main()
