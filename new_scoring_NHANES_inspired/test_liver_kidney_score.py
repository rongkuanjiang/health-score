"""Organ-stress v0.2 and retained kidney-equation acceptance checks."""
from copy import deepcopy
from datetime import date
import json
import math
import unittest

from liver_kidney_score import ADULT, U25, _PARAMS, _linear, display_score, score_liver_kidney

TODAY = date(2026, 9, 24)


def observation(value, unit):
    return {'value': value, 'unit': unit, 'report_id': 'synthetic-report',
            'specimen_date': '2026-09-01', 'reliability': 'valid'}


def profile(egfr=90, alt=20, alp=30):
    r = {'person': {'age': 40, 'equation_sex': 'male', 'pregnancy_status': 'not_pregnant'},
         'context': {'dialysis': 'no', 'acute_kidney_injury': 'no'},
         'observations': {'egfr': observation(egfr, 'mL/min/1.73m2'),
                          'alt': observation(alt, 'U/L'), 'alp': observation(alp, 'U/L')}}
    r['observations']['egfr']['equation'] = ADULT
    for key in ('alt', 'alp'):
        r['observations'][key].update(lower_limit=5, upper_limit=40, reference_range_applicable=True)
    return r


def calculated(age=40, equation=None):
    r = profile()
    r['person']['age'] = age
    r['observations'].pop('egfr')
    r['observations']['creatinine'] = observation(1, 'mg/dL')
    r['observations']['creatinine'].update(calibration='idms_traceable', assay_method='enzymatic')
    r['observations']['height'] = observation(1.8, 'm')
    if equation:
        r['context']['creatinine_equation'] = equation
    return r


def score(r):
    return score_liver_kidney(r, today=TODAY)


def kidney(r):
    return score(r)['components']['kidney']


def liver(r):
    return score(r)['components']['liver']


def codes(r):
    return [f['code'] for f in r['flags']]


class LiverKidneyTests(unittest.TestCase):
    def test_worked_examples(self):
        for values, expected in [((90, 20, 30), (100, 100)), ((45, 20, 30), (50, 100)),
                                 ((75, 80, 40), (87.5, 85)), ((90, 200, 400), (100, 30)),
                                 ((90, 4, 30), (100, None))]:
            with self.subTest(values=values):
                r = score(profile(*values))
                self.assertEqual(tuple(r['components'][k]['score'] for k in ('kidney', 'liver')), expected)
                self.assertEqual(r['domain_score'], None if expected[1] is None else 0.5 * sum(expected))
                self.assertEqual(r['aggregation_status'], 'insufficient_core_data' if expected[1] is None else 'fixed_weight_complete_core')
        self.assertIn('egfr_below_60', codes(kidney(profile(45))))

    def test_every_anchor_midpoint_continuity_and_plateau(self):
        for anchors in (_PARAMS['kidney']['anchors'], _PARAMS['liver']['upper_limit_ratio_anchors']):
            for x, y in anchors:
                self.assertEqual(_linear(x, anchors), y)
                self.assertAlmostEqual(_linear(x+1e-9, anchors), y, places=6)
            for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
                self.assertAlmostEqual(_linear((x0+x1)/2, anchors), (y0+y1)/2)
            self.assertEqual(_linear(1e8, anchors), anchors[-1][1])
        for egfr, expected in _PARAMS['kidney']['anchors'][1:]:
            self.assertEqual(kidney(profile(egfr))['score'], expected)
        for ratio, expected in _PARAMS['liver']['upper_limit_ratio_anchors']:
            self.assertEqual(liver(profile(90, ratio*40, 20))['markers']['alt']['score'], expected)
        self.assertEqual(liver(profile(90, 5, 40))['score'], 100)
        self.assertEqual(liver(profile(90, 1000, 20))['score'], 40)

    def test_bounds(self):
        for q, value, expected, envelope in [('>', 60, None, [75, 100]), ('>=', 90, 100, [100, 100]),
                                            ('>', 90, 100, [100, 100]), ('<', 45, None, [0, 50]),
                                            ('<=', 60, None, [0, 75]), ('>=', 45, None, [50, 100])]:
            with self.subTest(q=q, value=value):
                r = profile(value)
                r['observations']['egfr']['qualifier'] = q
                k = kidney(r)
                self.assertIsNone(k['egfr'])
                self.assertEqual(k['score'], expected)
                self.assertEqual(k['score_envelope'], envelope)
                self.assertEqual(k['egfr_bound']['qualifier'], q)
                if expected is not None:
                    self.assertEqual(k['status'], 'scored_from_bound')
        for q, value, low60, low15 in [('<', 60, True, False), ('<=', 60, False, False),
                                       ('<', 15, True, True), ('<=', 15, True, False), ('>', 10, False, False)]:
            r = profile(value)
            r['observations']['egfr']['qualifier'] = q
            self.assertEqual('egfr_below_60' in codes(kidney(r)), low60)
            self.assertEqual('egfr_below_15' in codes(kidney(r)), low15)

    def test_units_and_equation_reference_values(self):
        r = calculated()
        # Independently evaluated from the specification using .NET Math.Pow.
        self.assertAlmostEqual(kidney(r)['egfr'], 97.5751105709322)
        r['person']['equation_sex'] = 'female'
        self.assertAlmostEqual(kidney(r)['egfr'], 73.0375507831979)
        baseline = kidney(r)['egfr']
        for unit in ('µmol/L', 'μmol/L', 'umol/L'):
            r['observations']['creatinine'].update(value=88.4, unit=unit)
            self.assertAlmostEqual(kidney(r)['egfr'], baseline)
        r = profile()
        r['observations']['egfr']['unit'] = 'mL/min/1.73m²'
        r['observations']['alt']['unit'] = 'IU/L'
        self.assertEqual(score(r)['status'], 'scored')

    def test_u25_examples_and_height_conversion(self):
        r = calculated(18, U25)
        self.assertAlmostEqual(kidney(r)['egfr'], 91.44)
        self.assertEqual(kidney(r)['score'], 100)
        r = calculated(12)
        r['observations']['height']['value'] = 1.5
        r['observations']['creatinine']['value'] = 0.6
        self.assertAlmostEqual(kidney(r)['egfr'], 97.5)
        self.assertIsNone(kidney(r)['score'])
        self.assertIsNone(liver(r)['markers']['alt']['score'])
        r['observations']['height'].update(value=150, unit='cm')
        self.assertAlmostEqual(kidney(r)['egfr'], 97.5)

    def test_equation_age_boundaries(self):
        for age in (0.999, 1, 11.999, 12, 17.999, 18, 25, 25.001):
            r = calculated(age, U25)
            k = kidney(r)
            self.assertEqual(k['egfr'] is not None, 1 <= age <= 25)
            self.assertEqual(k['score'] is not None, 18 <= age <= 25)
        for sex, base, pre, adolescent, adult in [('male', 39, 1.008, 1.045, 50.8), ('female', 36.1, 1.008, 1.023, 41.4)]:
            for age in (1, 11.999, 12, 17.999, 18, 25):
                r = calculated(age, U25)
                r['person']['equation_sex'] = sex
                expected_k = adult if age >= 18 else base * (pre if age < 12 else adolescent)**(age-12)
                self.assertAlmostEqual(kidney(r)['egfr'], expected_k*1.8)
        self.assertEqual(kidney(calculated(18))['equation'], ADULT)
        self.assertIsNone(kidney(calculated(17.999, ADULT))['egfr'])
        r = profile()
        r['person']['age'] = 12
        self.assertIn('equation_age_outside_scope', kidney(r)['reasons'])
        r['observations']['egfr']['equation'] = U25
        self.assertEqual(kidney(r)['egfr'], 90)
        r['observations']['egfr']['qualifier'] = '>'
        self.assertIsNone(kidney(r)['score_envelope'])

    def test_calculation_prerequisites(self):
        for field, value, reason in [('calibration', 'unknown', 'calibration_unknown'),
                                     ('calibration', 'research_calibrated', 'calibration_provenance_required'),
                                     ('qualifier', '>', 'censored_creatinine_not_supported')]:
            r = calculated()
            r['observations']['creatinine'][field] = value
            self.assertIn(reason, kidney(r)['reasons'])
            self.assertIsNone(kidney(r)['egfr'])
        r = calculated()
        r['observations']['creatinine'].update(calibration='research_calibrated', calibration_provenance='Synthetic adapter; correction recorded here')
        self.assertIsNotNone(kidney(r)['egfr'])
        r['person']['equation_sex'] = 'unknown'
        self.assertIn('equation_sex_required', kidney(r)['reasons'])
        r = calculated(12)
        r['observations'].pop('height')
        self.assertIn('height_required', kidney(r)['reasons'])
        r = calculated(18, U25)
        r['observations']['creatinine'].pop('assay_method')
        self.assertIn('enzymatic_assay_not_confirmed', codes(kidney(r)))

    def test_no_silent_fallback_and_explicit_route(self):
        r = calculated()
        r['observations']['egfr'] = profile()['observations']['egfr']
        for update in ({'equation': 'unknown'}, {'value': -1}, {'value': 60, 'qualifier': '>'}):
            p = deepcopy(r)
            p['observations']['egfr'].update(update)
            self.assertIsNone(kidney(p)['score'])
            self.assertEqual(kidney(p)['route'], 'reported')
            p['context']['kidney_route'] = 'creatinine'
            self.assertIsNotNone(kidney(p)['score'])
            self.assertIn('egfr', score(p)['provenance']['observations'])
        r['context']['kidney_route'] = 'other'
        self.assertIn('unsupported_kidney_route', kidney(r)['reasons'])

    def test_pregnancy_and_age_gates(self):
        for pregnancy in ('pregnant', 'unknown', None, True):
            r = profile()
            r['person']['pregnancy_status'] = pregnancy
            self.assertEqual(score(r)['status'], 'unavailable')
        for age in (0, -1, True, '40', None, math.nan, math.inf, 10**400):
            r = profile()
            r['person']['age'] = age
            self.assertEqual(score(r)['status'], 'unavailable')
            json.dumps(score(r), allow_nan=False)
        r = profile()
        r['person']['age'] = 85
        self.assertIn('older_age_limited_evidence', codes(score(r)))
        self.assertEqual(score(r)['status'], 'scored')

    def test_dialysis_aki_independent_liver_and_unknowns(self):
        for field in ('dialysis', 'acute_kidney_injury'):
            for r in (profile(), calculated()):
                r['context'][field] = 'yes'
                k = kidney(r)
                self.assertIsNone(k['score'])
                self.assertIsNone(k['egfr'])
                self.assertEqual(liver(r)['score'], 100)
                self.assertIn(field+'_outside_scope', k['reasons'])
            r = profile()
            r['context'].pop(field)
            self.assertIn(field+'_unknown', codes(kidney(r)))
            r['context'][field] = False
            self.assertIn('invalid_'+field+'_status', kidney(r)['reasons'])

    def test_reference_metadata_and_censored_enzymes(self):
        for update, reason in [({'lower_limit': None}, 'invalid_or_missing_reference_limits'),
                               ({'lower_limit': -1}, 'invalid_or_missing_reference_limits'),
                               ({'lower_limit': 40}, 'invalid_or_missing_reference_limits'),
                               ({'upper_limit': math.inf}, 'invalid_or_missing_reference_limits'),
                               ({'lower_limit': True}, 'invalid_or_missing_reference_limits'),
                               ({'reference_range_applicable': 'yes'}, 'reference_range_applicability_required'),
                               ({'qualifier': '>'}, 'censored_result_not_supported'),
                               ({'value': 4}, 'below_reference_range_not_scored')]:
            r = profile()
            r['observations']['alt'].update(update)
            self.assertIn(reason, liver(r)['markers']['alt']['reasons'])
            self.assertIsNone(liver(r)['score'])
            self.assertEqual(kidney(r)['score'], 100)

    def test_snapshots_and_dates(self):
        r = profile()
        r['observations']['alp']['report_id'] = 'different'
        self.assertIn('report_id_mismatch', liver(r)['reasons'])
        r = profile()
        r['observations']['alp']['specimen_date'] = '2026-09-02'
        r['context']['same_snapshot_confirmed'] = True
        self.assertIn('specimen_date_mismatch', liver(r)['reasons'])
        for stamp in ('bad', '2026-02-30', '2026-09-25', True, '20260901'):
            r = profile()
            for key in ('egfr', 'alt'):
                r['observations'][key]['specimen_date'] = stamp
            self.assertEqual(score(r)['status'], 'partial')
            self.assertIsNone(score(r)['domain_score'])
        r = profile()
        r['observations']['alp'].pop('specimen_date')
        self.assertIn('same_snapshot_confirmation_required', liver(r)['reasons'])
        r['context']['same_snapshot_confirmed'] = True
        self.assertEqual(liver(r)['score'], 100)
        r['observations']['alp']['report_id'] = ''
        self.assertIsNone(liver(r)['score'])
        r = profile()
        r['observations']['egfr']['specimen_date'] = '2000-01-01'
        self.assertIsNotNone(kidney(r)['score'])
        self.assertEqual(kidney(r)['markers']['egfr']['specimen_age_days'], (TODAY-date(2000, 1, 1)).days)

    def test_missing_and_invalid_observations(self):
        for raw in (None, [], '90', {}, {'value': 90}):
            r = profile()
            r['observations']['egfr'] = raw
            self.assertIsNone(kidney(r)['score'])
            json.dumps(score(r), allow_nan=False)
        for value in (0, -1, True, '90', math.nan, math.inf, -math.inf, 10**400):
            for key in ('egfr', 'alt'):
                r = profile()
                r['observations'][key]['value'] = value
                component = kidney(r) if key == 'egfr' else liver(r)
                self.assertIsNone(component['score'])
                json.dumps(score(r), allow_nan=False)
        for key in ('egfr', 'alt'):
            r = profile()
            r['observations'][key]['unit'] = 'mL/min'
            self.assertEqual(score(r)['status'], 'partial')
        r = profile()
        r['observations'].pop('alp')
        self.assertEqual(liver(r)['coverage']['available'], 1)
        self.assertEqual(liver(r)['markers']['alt']['score'], 100)
        self.assertEqual(score({})['status'], 'unavailable')

    def test_reliability_and_context_flags_survive(self):
        r = profile()
        r['optional_observations'] = {'uacr': dict(observation(100, 'mg/g'), lab_flag='high')}
        output = score(r)
        self.assertEqual(output['status'], 'scored')
        self.assertIn('laboratory_flag', codes(output))
        self.assertIn('laboratory_flag', codes(output['components']['kidney']))
        self.assertNotIn('uacr_missing_or_unusable', codes(output))
        r['observations']['egfr']['reliability'] = 'invalid'
        self.assertIsNone(kidney(r)['score'])
        r['observations']['egfr'].pop('reliability')
        self.assertIn('reliability_unknown', codes(kidney(r)))
        self.assertEqual(kidney(r)['score'], 100)
        r['optional_observations']['uacr']['value'] = None
        self.assertIn('uacr_missing_or_unusable', codes(kidney(r)))
        r['context']['previous_egfr_equation'] = U25
        self.assertIn('equation_route_changed', codes(kidney(r)))

    def test_context_zero_missing_units_and_no_point_effect(self):
        r = profile()
        r['optional_observations'] = {'uacr': observation(0, 'mg/g')}
        self.assertTrue(score(r)['optional_context']['uacr']['usable_for_display'])
        self.assertEqual(kidney(r)['score'], 100)
        r['optional_observations']['uacr'].pop('unit')
        self.assertFalse(score(r)['optional_context']['uacr']['usable_for_display'])
        self.assertEqual(kidney(r)['score'], 100)

    def test_computed_nonfinite_or_underflow(self):
        r = calculated(1e308)
        self.assertIn('invalid_computed_egfr', kidney(r)['reasons'])
        r = calculated(18, U25)
        r['observations']['creatinine']['value'] = 5e-324
        self.assertIsNone(kidney(r)['score'])
        json.dumps(score(r), allow_nan=False)

    def test_immutability_serialization_and_envelope_validation(self):
        r = profile()
        before = deepcopy(r)
        result = score(r)
        self.assertEqual(r, before)
        result['provenance']['person']['age'] = 100
        result['components']['liver']['markers']['alt']['observation']['value'] = 9
        self.assertEqual(r, before)
        json.dumps(result, allow_nan=False)
        for bad in ([], None, {'person': []}, {'context': None}, {'observations': []}, {'optional_observations': 3}):
            with self.assertRaises(ValueError):
                score(bad)
        self.assertEqual(display_score(87.55), '87.6')
        self.assertEqual(display_score(0), '0.0')
        self.assertEqual(display_score(0.001), '<0.1')


if __name__ == '__main__':
    unittest.main()
