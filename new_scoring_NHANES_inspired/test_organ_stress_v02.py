"""Independent composite, missingness and migration checks for organ stress v0.2."""
from copy import deepcopy
from datetime import timedelta
import unittest

from test_liver_kidney_score import profile, observation, score, TODAY


class OrganStressV02Tests(unittest.TestCase):
    def test_weighted_example_and_contributions(self):
        r = score(profile(75, 80, 20))
        self.assertEqual(r['domain_score'], 86.25)
        self.assertEqual(r['display_score'], '86.3')
        self.assertEqual(r['score'], r['domain_score'])
        self.assertEqual(r['weighted_contributions'], {'egfr': 43.75, 'alt': 22.5, 'alp': 20})
        self.assertEqual(r['coverage']['scored'], 3)
        self.assertTrue(r['review_required'])

    def test_each_missing_marker_withholds_without_renormalization(self):
        for marker in ('egfr', 'alt', 'alp'):
            request = profile()
            del request['observations'][marker]
            r = score(request)
            self.assertIsNone(r['domain_score'])
            self.assertEqual(r['coverage']['scored'], 2)
            self.assertIn(marker, r['coverage']['missing_or_unusable'])
            self.assertEqual(r['weights'], {'egfr': .5, 'alt': .3, 'alp': .2})

    def test_legacy_ast_and_optional_bilirubin_are_context(self):
        request = profile()
        request['observations']['ast'] = dict(observation(800, 'U/L'), lab_flag='high')
        request['optional_observations'] = {'bilirubin': dict(observation(100, 'umol/L'), lab_flag='high')}
        r = score(request)
        self.assertEqual(r['domain_score'], 100)
        self.assertTrue(r['review_required'])
        self.assertEqual(r['optional_context']['ast']['observation']['value'], 800)
        self.assertIn('bilirubin', r['optional_context'])
        request['optional_observations']['alp'] = request['observations'].pop('alp')
        self.assertIsNone(score(request)['domain_score'])

    def test_low_component_remains_visible_next_to_high_average(self):
        r = score(profile(90, 800, 20))
        self.assertEqual(r['domain_score'], 70)
        self.assertEqual(r['marker_scores']['alt'], 0)
        self.assertTrue(r['review_required'])
        self.assertTrue(any(f['code'] == 'alt_above_upper_limit' for f in r['flags']))

    def test_dates_at_limit_beyond_limit_and_missing(self):
        request = profile()
        for marker in ('alt', 'alp'):
            request['observations'][marker]['specimen_date'] = TODAY.isoformat()
        for gap, expected in ((90, 100), (91, None)):
            request['observations']['egfr']['specimen_date'] = (TODAY-timedelta(days=gap)).isoformat()
            self.assertEqual(score(request)['domain_score'], expected)
        request = profile()
        request['context']['same_snapshot_confirmed'] = True
        for marker in ('alt', 'alp'):
            request['observations'][marker].pop('specimen_date')
        r = score(request)
        self.assertEqual(r['components']['liver']['score'], 100)
        self.assertIn('liver_date_required_for_total', r['reasons'])
        self.assertIsNone(r['domain_score'])

    def test_alp_reference_units_bounds_and_unreliability(self):
        for update in ({'reference_unit': 'mg/dL'}, {'qualifier': '>'}, {'reliability': 'invalid'}, {'upper_limit': None}):
            request = profile()
            request['observations']['alp'].update(update)
            self.assertIsNone(score(request)['domain_score'])
        request = profile()
        request['observations']['egfr'].update(value=60, qualifier='>')
        self.assertIsNone(score(request)['domain_score'])
        request['observations']['egfr'].update(value=90, qualifier='>=')
        self.assertEqual(score(request)['domain_score'], 100)

    def test_alp_changes_total_monotonically_and_preserves_input(self):
        request = profile()
        totals = []
        for value in (40, 60, 80, 200, 400, 800):
            request['observations']['alp']['value'] = value
            before = deepcopy(request)
            r = score(request)
            self.assertEqual(request, before)
            totals.append(r['domain_score'])
        self.assertEqual(totals, sorted(totals, reverse=True))
        self.assertEqual(totals[0], 100)
        self.assertEqual(totals[-1], 80)


if __name__ == '__main__':
    unittest.main()
