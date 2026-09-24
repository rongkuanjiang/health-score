"""Stage 2 acceptance tests; synthetic intervals do not validate clinical use."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import unittest

from system_stability_score import score_system_stability, CORE

ROOT = Path(__file__).parent
TODAY = date(2026, 9, 24)


def profile():
    return json.loads((ROOT / 'example_system_stability_request.json').read_text(encoding='utf-8'))


def score(request):
    return score_system_stability(request, today=TODAY)


def marker(result, key='potassium'):
    return next(r for r in result['observations'] + result['context_observations'] if r['marker'] == key)


def calcium(request, key='total_calcium'):
    raw = deepcopy(request['observations']['potassium'])
    raw.update(observation_id='ca-1', raw_analyte_name=key, value=10, unit='mg/dL',
               lower_limit=8, upper_limit=11, reference_unit='mg/dL')
    request['observations'][key] = raw
    request['selection']['observation_ids'][key] = 'ca-1'
    return raw


class SystemStabilityTests(unittest.TestCase):
    def test_complete_fixture_has_no_points(self):
        result = score(profile())
        self.assertEqual(result['panel_status'], 'all_within_reference')
        self.assertEqual(result['coverage'], {'present_count': 4, 'interpretable_count': 4,
            'expected_count': 4, 'missing_markers': [], 'uninterpretable_markers': []})
        self.assertEqual(result['reasons'], [])
        self.assertIsNone(result['domain_score'])
        for r in result['observations']:
            self.assertIsNone(r['score'])
            self.assertEqual(r['reference_status'], 'within_reference')
            self.assertEqual(r['specimen_age_days'], 4)

    def test_exact_boundaries_and_no_rounding_before_classification(self):
        for value, expected in [(3.5, 'within_reference'), (5, 'within_reference'),
                                (3.49, 'low'), (5.01, 'high'), (4, 'within_reference'),
                                (3.499999999, 'low'), (5.000000001, 'high')]:
            with self.subTest(value=value):
                request = profile()
                request['observations']['potassium']['value'] = value
                result = score(request)
                self.assertEqual(marker(result)['reference_status'], expected)
                self.assertEqual(result['panel_status'], 'all_within_reference' if expected == 'within_reference' else 'outside_reference')

    def test_bounds_and_inclusivity(self):
        for qualifier, value, expected in [('<',3.5,'low'),('<=',3.5,'indeterminate_bound'),
                ('<=',3.49,'low'),('>',5,'high'),('>=',5,'indeterminate_bound'),
                ('>=',5.01,'high'),('<',4,'indeterminate_bound'),('>',4,'indeterminate_bound'),
                ('<',5,'indeterminate_bound'),('>',3.5,'indeterminate_bound')]:
            with self.subTest(qualifier=qualifier, value=value):
                request = profile()
                request['observations']['potassium'].update(value=value, qualifier=qualifier)
                result = score(request)
                self.assertEqual(marker(result)['reference_status'], expected)
                self.assertEqual(marker(result)['qualifier'], qualifier)
                self.assertEqual(result['coverage']['interpretable_count'], 3 if expected == 'indeterminate_bound' else 4)

    def test_missing_and_partial_abnormal_panels(self):
        request = profile()
        del request['observations']['total_co2']
        result = score(request)
        self.assertEqual(result['panel_status'], 'partial')
        self.assertEqual(result['coverage']['missing_markers'], ['total_co2'])
        request['observations'] = {'potassium': request['observations']['potassium']}
        request['observations']['potassium']['value'] = 5.5
        result = score(request)
        self.assertEqual(result['panel_status'], 'outside_reference')
        self.assertEqual(result['coverage']['interpretable_count'], 1)
        self.assertEqual(score({})['panel_status'], 'unavailable')

    def test_unit_conversion_including_independent_reference_units(self):
        request = profile()
        request['observations']['potassium']['unit'] = 'mEq/L'
        self.assertEqual(marker(score(request))['reference_status'], 'within_reference')
        ca = calcium(request)
        result = marker(score(request), 'total_calcium')
        self.assertEqual(result['normalized_value'], 2.495)
        self.assertEqual(result['normalized_lower_limit'], 1.996)
        self.assertEqual(result['normalized_upper_limit'], 2.7445)
        ca.update(value=2.495, unit='mmol/L')
        self.assertEqual(marker(score(request), 'total_calcium')['reference_status'], 'within_reference')
        ca.update(value=1.996)
        self.assertEqual(marker(score(request), 'total_calcium')['reference_status'], 'within_reference')
        ca['unit'] = 'mEq/L'
        self.assertIn('unsupported_unit', marker(score(request), 'total_calcium')['errors'])

    def test_optional_calcium_never_changes_core_summary_or_coverage(self):
        request = profile()
        before = score(request)
        ca = calcium(request)
        ca.update(source_flags=['critical_high'], value=20)
        result = score(request)
        self.assertEqual(result['panel_status'], before['panel_status'])
        self.assertEqual(result['coverage'], before['coverage'])
        self.assertTrue(any(n['code'] == 'source_critical_flag' and n['marker'] == 'total_calcium' for n in result['notices']))

    def test_total_and_ionized_calcium_are_distinct(self):
        request = profile()
        calcium(request)
        ion = calcium(request, 'ionized_calcium')
        ion['observation_id'] = 'ica-1'
        request['selection']['observation_ids']['ionized_calcium'] = 'ica-1'
        ion.update(specimen_type='whole_blood', unit='mmol/L', value=1.2,
                   lower_limit=1.1, upper_limit=1.3, reference_unit='mmol/L')
        result = score(request)
        self.assertEqual(len(result['context_observations']), 2)
        self.assertTrue(all(r['reference_status'] == 'within_reference' for r in result['context_observations']))

    def test_missing_invalid_or_inapplicable_reference(self):
        cases = [{'lower_limit': None}, {'lower_limit': 6}, {'lower_limit': 5},
                 {'lower_limit': 0}, {'reference_unit': 'mg/L'}, {'reference_applicability': 'unknown'},
                 {'reference_provenance': ''}, {'reference_marker': 'sodium'}, {'upper_limit': float('inf')}]
        for change in cases:
            with self.subTest(change=change):
                request = profile()
                request['observations']['potassium'].update(change, source_flags=['high'])
                result = score(request)
                self.assertEqual(marker(result)['reference_status'], 'unavailable')
                self.assertEqual(marker(result)['classification_basis'], 'source_only')
                self.assertEqual(result['panel_status'], 'outside_reference')
                self.assertEqual(result['coverage']['interpretable_count'], 3)

    def test_invalid_measurements_are_json_safe_and_do_not_erase_others(self):
        for value in [None, True, False, -1, 0, '4', float('nan'), float('inf'), -float('inf'), {}, [], 10**400]:
            with self.subTest(value=str(value)[:40]):
                request = profile()
                request['observations']['potassium']['value'] = value
                result = score(request)
                self.assertIn('invalid_value', marker(result)['errors'])
                self.assertEqual(result['coverage']['present_count'], 4)
                self.assertEqual(result['coverage']['interpretable_count'], 3)
                json.dumps(result, allow_nan=False)

    def test_malformed_fields_do_not_crash(self):
        for field in ['unit', 'qualifier', 'reference_unit', 'reliability', 'source_flags',
                      'specimen_type', 'specimen_date', 'report_id', 'reference_applicability',
                      'reference_provenance', 'interference_affects_result', 'observation_id']:
            for value in [None, {}, [], True, 7]:
                if field == 'source_flags' and value == []:
                    continue  # An empty flag list is valid, not malformed.
                with self.subTest(field=field, value=value):
                    request = profile()
                    request['observations']['potassium'][field] = value
                    result = score(request)
                    self.assertNotEqual(result['panel_status'], 'all_within_reference')
                    json.dumps(result, allow_nan=False)

    def test_unreliable_and_interfered_values_retain_flags(self):
        for change in [{'reliability': 'unreliable'}, {'interference_affects_result': True,
                                                       'interference_note': 'Hemolysis affects this potassium result'}]:
            request = profile()
            request['observations']['potassium'].update(change, source_flags=['high'])
            result = score(request)
            self.assertIn('unreliable_result', marker(result)['reasons'])
            self.assertEqual(result['panel_status'], 'outside_reference')
            self.assertEqual(marker(result)['classification_basis'], 'source_only')

    def test_unknown_reliability_allows_comparison_with_notice(self):
        request = profile()
        del request['observations']['potassium']['reliability']
        result = score(request)
        self.assertEqual(result['panel_status'], 'all_within_reference')
        self.assertIn('reliability_unknown', marker(result)['notices'])

    def test_critical_overrides_conflicts_and_invalid_values(self):
        request = profile()
        request['observations']['potassium'].update(value=None, source_flags=['critical_high'])
        request['observations']['sodium']['source_flags'] = ['high']
        result = score(request)
        self.assertEqual(result['panel_status'], 'source_critical_flag')
        self.assertIn('source_flag_conflict', marker(result, 'sodium')['notices'])
        self.assertIn('invalid_value', marker(result)['errors'])
        request['observations']['potassium']['source_flags'] = 'critical_high'
        self.assertEqual(score(request)['panel_status'], 'source_critical_flag')

    def test_conflicting_and_unmapped_flags_block_reassurance(self):
        for flags, expected in [(['high'],'source_flag_conflict'), (['low'],'source_flag_conflict'),
                                (['H'],'partial'), (['high','low'],'source_flag_conflict')]:
            request = profile()
            request['observations']['potassium']['source_flags'] = flags
            result = score(request)
            self.assertEqual(result['panel_status'], expected)
            self.assertEqual(marker(result)['source_flags'], flags)

    def test_source_normal_does_not_count_as_interpretable(self):
        request = profile()
        request['observations']['potassium'].update(lower_limit=None, source_flags=['within_reference'])
        result = score(request)
        self.assertEqual(result['panel_status'], 'partial')
        self.assertEqual(result['coverage']['interpretable_count'], 3)
        self.assertEqual(marker(result)['reference_status'], 'unavailable')

    def test_explicit_selection_required(self):
        request = profile()
        request.pop('selection')
        result = score(request)
        self.assertEqual(result['panel_status'], 'unavailable')
        self.assertEqual(result['coverage']['present_count'], 0)
        self.assertEqual(len(result['observations']), 4)

    def test_unselected_critical_result_is_preserved_but_not_current_summary(self):
        request = profile()
        previous = deepcopy(request['observations']['potassium'])
        previous.update(observation_id='old-k', source_flags=['critical_high'], value=9, specimen_date='2025-09-20')
        request['observations']['potassium'] = [request['observations']['potassium'], previous]
        result = score(request)
        self.assertEqual(result['panel_status'], 'all_within_reference')
        self.assertTrue(any(n['code'] == 'source_critical_flag' and n['selected'] is False for n in result['notices']))

    def test_duplicate_ids_are_ambiguous_not_averaged(self):
        request = profile()
        other = deepcopy(request['observations']['potassium'])
        other['value'] = 6
        other['source_flags'] = ['high']
        request['observations']['potassium'] = [request['observations']['potassium'], other]
        result = score(request)
        self.assertEqual(result['coverage']['interpretable_count'], 3)
        self.assertEqual(result['coverage']['present_count'], 4)
        self.assertEqual(result['panel_status'], 'outside_reference')
        self.assertTrue(all('ambiguous_observation_id' in r['reasons'] for r in result['observations'] if r['marker'] == 'potassium'))

    def test_report_date_and_specimen_mismatches(self):
        for change, reason in [({'report_id': 'other'},'selected_report_mismatch'),
                                ({'specimen_date':'2026-09-19'},'selected_collection_mismatch'),
                                ({'specimen_id':'other'},'selected_specimen_mismatch'),
                                ({'specimen_date':'2026-09-25'},'future_specimen_date')]:
            request = profile()
            request['observations']['potassium'].update(change)
            result = score(request)
            self.assertEqual(result['panel_status'], 'partial')
            self.assertIn(reason, marker(result)['reasons'])

    def test_multiple_specimens_require_selection(self):
        request = profile()
        request['selection'].pop('specimen_id')
        request['observations']['potassium']['specimen_id'] = 'second'
        result = score(request)
        self.assertEqual(result['coverage']['interpretable_count'], 0)
        self.assertIn('specimen_selection_required', result['reasons'])

    def test_missing_specimen_ids_allowed_when_one_report_collection(self):
        request = profile()
        request['selection'].pop('specimen_id')
        for r in request['observations'].values():
            r.pop('specimen_id')
        self.assertEqual(score(request)['panel_status'], 'all_within_reference')

    def test_co2_identity_is_not_blood_gas(self):
        for assay, verified, expected in [('pco2',True,False), ('blood_gas_bicarbonate',True,False),
                ('chemistry_bicarbonate',False,False), ('chemistry_bicarbonate',True,True),
                ('chemistry_total_co2',False,True), (None,False,False)]:
            request = profile()
            request['observations']['total_co2'].update(assay_type=assay, chemistry_alias_verified=verified)
            self.assertEqual(marker(score(request),'total_co2')['reference_status'] == 'within_reference', expected)

    def test_person_context_does_not_apply_adult_defaults(self):
        for person in [{'age':3}, {'age':95}, {'age':30,'pregnancy_status':'pregnant'}, {}]:
            request = profile()
            request['person'] = person
            self.assertEqual(score(request)['panel_status'], 'all_within_reference')
            request['observations']['potassium']['reference_applicability'] = 'unknown'
            self.assertEqual(score(request)['panel_status'], 'partial')

    def test_invalid_envelopes_raise_clear_error(self):
        for request in [[], None, {'observations': []}, {'selection': []},
                        {'selection': {'observation_ids': []}}, {'observations': {1: {}}}, {'extra': object()}]:
            with self.assertRaises(ValueError):
                score(request)

    def test_unknown_marker_and_malformed_record_retained(self):
        request = profile()
        request['observations']['hemoglobin'] = {'value': 13}
        request['observations']['potassium'] = None
        result = score(request)
        self.assertEqual(result['unsupported_observations'][0]['marker'], 'hemoglobin')
        self.assertIn('invalid_observation', marker(result)['errors'])
        self.assertEqual(result['panel_status'], 'partial')

    def test_deterministic_json_and_no_input_or_output_aliasing(self):
        request = profile()
        before = deepcopy(request)
        first, second = score(request), score(request)
        self.assertEqual(request, before)
        self.assertEqual(first, second)
        first['observations'][0]['observation']['value'] = 1
        first['request']['selection']['report_id'] = 'changed'
        self.assertEqual(request, before)
        self.assertEqual(second, score(request))
        json.dumps(second, allow_nan=False)

    def test_cli_example_returns_strict_json(self):
        completed = subprocess.run([sys.executable, str(ROOT / 'system_stability_score.py'),
            str(ROOT / 'example_system_stability_request.json'), '--today', TODAY.isoformat()],
            capture_output=True, text=True, check=True)
        result = json.loads(completed.stdout)
        self.assertEqual(result['panel_status'], 'all_within_reference')
        self.assertIsNone(result['domain_score'])


if __name__ == '__main__':
    unittest.main()
