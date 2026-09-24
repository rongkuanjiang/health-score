"""Exercise the actual local HTTP boundary, including missing/blocked results."""
from copy import deepcopy
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
import unittest

from dashboard_server import Handler
from metabolism_score import _curve, VERSION
from liver_kidney_score import score_liver_kidney
from system_stability_score import score_system_stability
from nutrition_score import score_nutrition, _curve as nutrition_curve
from inflammation_score import score_inflammation, _curve as inflammation_curve


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.example = json.loads(Path(__file__).with_name('example_metabolism_request.json').read_text())
        cls.organ_example = json.loads(Path(__file__).with_name('example_liver_kidney_request.json').read_text())

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def call(self, method, path, body=None, headers=None):
        conn = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        conn.request(method, path, body, headers or {})
        response = conn.getresponse()
        status, data, content_type = response.status, response.read(), response.getheader('Content-Type')
        conn.close()
        return status, data, content_type

    def score(self, request):
        status, data, _ = self.call('POST', '/score', json.dumps(request), {'Content-Type':'application/json'})
        self.assertEqual(status, 200)
        return json.loads(data)

    def test_assets_and_no_filesystem_exposure(self):
        status, data, content_type = self.call('GET', '/overview.js')
        self.assertEqual(status, 200)
        self.assertIn(b'onboarding-form', data)
        self.assertTrue(content_type.startswith('text/javascript'))
        for path, mime in [('/', 'text/html'), ('/app.js', 'text/javascript'), ('/details.js', 'text/javascript'), ('/domains.js', 'text/javascript'), ('/organ.js', 'text/javascript'), ('/style.css', 'text/css')]:
            status, data, content_type = self.call('GET', path)
            self.assertEqual(status, 200)
            self.assertTrue(data)
            self.assertTrue(content_type.startswith(mime))
        self.assertEqual(self.call('GET', '/../metabolism_score.py')[0], 404)

    def test_worked_example_over_http(self):
        self.assertEqual(self.score(self.example)['display_score'], '85.6')

    def test_stability_route_parity_and_warnings(self):
        fixture = json.loads(Path(__file__).with_name('example_system_stability_request.json').read_text())
        for flag, value in [([], 4), (['high'], 4), (['critical_high'], None), ([], 5.5)]:
            request = deepcopy(fixture)
            request['observations']['potassium'].update(value=value, source_flags=flag)
            status, data, _ = self.call('POST', '/score/system-stability', json.dumps(request), {'Content-Type': 'application/json'})
            self.assertEqual(status, 200)
            result = json.loads(data)
            self.assertEqual(result, score_system_stability(request))
            self.assertIsNone(result['domain_score'])
        self.assertEqual(result['panel_status'], 'outside_reference')

    def test_stability_asset_and_request_restrictions(self):
        self.assertEqual(self.call('GET', '/stability.js')[0], 200)
        self.assertEqual(self.call('POST', '/score/system-stability', '[]', {'Content-Type': 'application/json'})[0], 400)
        self.assertEqual(self.call('POST', '/score/system-stability', None, {'Content-Type': 'application/json', 'Origin': 'https://example.com'})[0], 403)

    def test_nutrition_route_preserves_engine_results(self):
        request = json.loads(Path(__file__).with_name('example_nutrition_request.json').read_text())
        for value, qualifier in [(40, '='), (125, '='), (126, '='), (30, '<'), (50, '>=')]:
            request['observations']['vitamin_d'].update(value=value, qualifier=qualifier)
            status, data, _ = self.call('POST', '/score/nutrition', json.dumps(request), {'Content-Type': 'application/json'})
            self.assertEqual(status, 200)
            result = json.loads(data)
            self.assertEqual(result, score_nutrition(request))
            self.assertIsNone(result['domain_score'])
            self.assertTrue(result['observations'][1]['notices'])
        del request['evaluation_date']
        status, data, _ = self.call('POST', '/score/nutrition', json.dumps(request), {'Content-Type': 'application/json'})
        self.assertEqual(status, 200)
        self.assertIsNone(json.loads(data)['components']['vitamin_d']['score'])
        self.assertEqual(self.call('POST', '/score/nutrition', '[]', {'Content-Type': 'application/json'})[0], 400)
        self.assertEqual(self.call('POST', '/score/nutrition', None, {'Content-Type': 'application/json', 'Origin': 'https://example.com'})[0], 403)

    def test_nutrition_asset_and_engine_curve(self):
        self.assertEqual(self.call('GET', '/nutrition.js')[0], 200)
        status, data, _ = self.call('GET', '/model/nutrition')
        self.assertEqual(status, 200)
        points = json.loads(data)['points']
        self.assertEqual(len(points), 250)
        for x, y in points:
            self.assertGreater(x, 0)
            self.assertLessEqual(x, 125)
            self.assertEqual(y, nutrition_curve(x))

    def test_inflammation_route_and_engine_parity(self):
        request = json.loads(Path(__file__).with_name('example_inflammation_request.json').read_text())
        for value, qualifier in [(2, '='), (12, '='), (1, '<'), (2, '<')]:
            request['observations']['hs_crp'].update(value=value, qualifier=qualifier)
            status, data, _ = self.call('POST', '/score/inflammation', json.dumps(request), {'Content-Type': 'application/json'})
            self.assertEqual(status, 200)
            result = json.loads(data)
            self.assertEqual(result, score_inflammation(request))
            self.assertIsNone(result['domain_score'])
            self.assertTrue(result['observations'][1]['notices'])
        self.assertEqual(self.call('POST', '/score/inflammation', '[]', {'Content-Type': 'application/json'})[0], 400)
        self.assertEqual(self.call('POST', '/score/inflammation', None, {'Content-Type': 'application/json', 'Origin': 'https://example.com'})[0], 403)

    def test_inflammation_asset_and_actual_engine_curve(self):
        self.assertEqual(self.call('GET', '/inflammation.js')[0], 200)
        status, data, _ = self.call('GET', '/model/inflammation')
        self.assertEqual(status, 200)
        points = json.loads(data)['points']
        self.assertEqual(len(points), 200)
        for x, y in points:
            self.assertEqual(y, inflammation_curve(x))

    def organ_score(self, request):
        status, data, _ = self.call('POST', '/score/organ-stress', json.dumps(request), {'Content-Type': 'application/json'})
        self.assertEqual(status, 200)
        result = json.loads(data)
        self.assertEqual(result, score_liver_kidney(request))
        self.assertIsNone(result['domain_score'])
        return result

    def test_organ_example_and_domain_isolation(self):
        result = self.organ_score(self.organ_example)
        self.assertEqual(result['components']['kidney']['display_score'], '87.5')
        self.assertEqual(result['components']['liver']['display_score'], '75.0')
        status, data, _ = self.call('POST', '/score/metabolism', json.dumps(self.example), {'Content-Type': 'application/json'})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data), self.score(self.example))
        self.assertIn('alt_above_upper_limit', [f['code'] for f in result['flags']])

    def test_organ_bounds_missing_metadata_and_eligibility(self):
        request = deepcopy(self.organ_example)
        request['observations']['egfr'].update(value=60, qualifier='>')
        kidney = self.organ_score(request)['components']['kidney']
        self.assertIsNone(kidney['score'])
        self.assertEqual(kidney['score_envelope'], [75, 100])
        request['observations']['egfr'].update(value=90, qualifier='>=')
        self.assertEqual(self.organ_score(request)['components']['kidney']['display_score'], '100.0')
        del request['observations']['ast']
        self.assertIsNone(self.organ_score(request)['components']['liver']['score'])
        del request['observations']['egfr']['specimen_date']
        self.assertIsNone(self.organ_score(request)['components']['kidney']['score'])
        for pregnancy in ('pregnant', 'unknown'):
            request = deepcopy(self.organ_example)
            request['person']['pregnancy_status'] = pregnancy
            self.assertTrue(all(c['score'] is None for c in self.organ_score(request)['components'].values()))

    def test_organ_creatinine_pediatric_and_context(self):
        request = deepcopy(self.organ_example)
        request['context']['kidney_route'] = 'creatinine'
        request['observations']['creatinine'] = {**request['observations'].pop('egfr'), 'value': 88.4, 'unit': 'umol/L', 'calibration': 'idms_traceable'}
        self.assertIsNotNone(self.organ_score(request)['components']['kidney']['score'])
        request['optional_observations'] = {'uacr': {'value': 0, 'unit': 'mg/g', 'lab_flag': 'Synthetic laboratory flag'}}
        result = self.organ_score(request)
        self.assertTrue(result['optional_context']['uacr']['usable_for_display'])
        self.assertIn('Synthetic laboratory flag', [f['text'] for f in result['flags']])
        request['person']['age'] = 16
        request['context']['creatinine_equation'] = 'ckid_u25_creatinine'
        request['observations']['height'] = {'value': 170, 'unit': 'cm'}
        result = self.organ_score(request)
        self.assertIsNotNone(result['components']['kidney']['egfr'])
        self.assertTrue(all(c['score'] is None for c in result['components'].values()))

    def test_organ_invalid_requests_and_origin(self):
        for body in ('[]', '{', '{"observations":null}', '{"person":{"age":NaN}}'):
            self.assertEqual(self.call('POST', '/score/organ-stress', body, {'Content-Type': 'application/json'})[0], 400)
        self.assertEqual(self.call('POST', '/score/organ-stress', None, {'Content-Type': 'application/json', 'Origin': 'https://example.com'})[0], 403)
        self.assertEqual(self.call('POST', '/score/unimplemented', None, {'Content-Type': 'application/json'})[0], 404)

    def test_diagrams_match_engine_and_age_extension_over_http(self):
        status, data, _ = self.call('GET', '/model')
        self.assertEqual(status, 200)
        model = json.loads(data)
        self.assertEqual(model['model_version'], VERSION)
        self.assertEqual(sum(model['weights'].values()), 1)
        for marker, curve in model['curves'].items():
            for x, y in curve['points']:
                self.assertEqual(y, _curve(marker, x)[0])
            for x, y in curve.get('nonfasting_points', []):
                self.assertEqual(y, _curve(marker, x, True)[0])
        for age, notice in [(12, 'younger_age_extrapolation'), (95, 'older_age_limited_evidence')]:
            request = deepcopy(self.example)
            request['person']['age'] = age
            result = self.score(request)
            self.assertEqual(result['display_score'], '85.6')
            self.assertEqual(result['age_applicability'], notice)
            self.assertIn(notice, [flag['code'] for flag in result['flags']])

    def test_missing_and_outside_scope_over_http(self):
        request = deepcopy(self.example)
        del request['observations']['triglycerides']
        result = self.score(request)
        self.assertIsNone(result['score'])
        self.assertEqual(result['coverage']['scored'], 3)
        request['person']['pregnancy_status'] = 'yes'
        self.assertEqual(self.score(request)['status'], 'outside_scope')

    def test_notice_and_sensitivity_survive_http(self):
        request = deepcopy(self.example)
        request['observations']['ldl_c']['value'] = 5.2
        request['context']['fasting_status'] = 'unknown'
        result = self.score(request)
        self.assertIn('ldl_markedly_elevated', [f['code'] for f in result['flags']])
        self.assertIsNotNone(result['alternative_nonfasting']['metabolism'])

    def test_bad_requests_and_cross_origin_rejected(self):
        for data in ('[]', '{', '{"person": null}', '{"person":{"age":NaN}}'):
            self.assertEqual(self.call('POST', '/score', data, {'Content-Type':'application/json'})[0], 400)
        self.assertEqual(self.call('POST', '/score', None, {'Content-Type':'text/plain'})[0], 415)
        self.assertEqual(self.call('POST', '/score', None, {'Content-Type':'application/json', 'Origin':'https://example.com'})[0], 403)
        self.assertEqual(self.call('GET', '/', headers={'Host':'example.com'})[0], 403)


if __name__ == '__main__':
    unittest.main()
