"""Acceptance tests at the shared boundary, with actual HTTP and engine comparisons."""
from copy import deepcopy
from datetime import date
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
import unittest

from dashboard_server import Handler
from health_scorer_api import ContractError, SCORERS, loads_request, score_request

ROOT = Path(__file__).resolve().parent
NAMES = {'metabolism': 'metabolism', 'organ-stress': 'liver_kidney', 'inflammation': 'inflammation',
         'nutrition': 'nutrition', 'system-stability': 'system_stability'}


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.request = {'api_version': '1.0', 'evaluation_date': '2026-09-24', 'domains': {
            domain: json.loads((ROOT / f'example_{name}_request.json').read_text()) for domain, name in NAMES.items()}}

    def test_complete_engine_parity_and_no_input_mutation(self):
        before = deepcopy(self.request)
        result = score_request(self.request)
        self.assertEqual(result['processing_status'], 'ok')
        self.assertIsNone(result['overall_score'])
        for domain, (scorer, _) in SCORERS.items():
            self.assertEqual(result['domains'][domain]['result'], scorer(before['domains'][domain], today=date(2026, 9, 24)))
        self.assertEqual(self.request, before)
        self.assertEqual(result['domains']['metabolism']['result']['display_score'], '85.6')

    def test_missing_is_successfully_evaluated_not_fabricated_points(self):
        self.request['domains'] = {domain: {} for domain in SCORERS}
        result = score_request(self.request)
        self.assertEqual(result['processing_status'], 'ok')
        for domain, item in result['domains'].items():
            self.assertIsNone(item['result']['score' if domain == 'metabolism' else 'domain_score'])

    def test_subset_and_domain_error_isolation(self):
        self.request['domains'] = {'metabolism': self.request['domains']['metabolism'], 'nutrition': []}
        result = score_request(self.request)
        self.assertEqual(result['processing_status'], 'partial')
        self.assertEqual(result['domains']['metabolism']['result']['display_score'], '85.6')
        self.assertNotIn('result', result['domains']['nutrition'])
        self.assertEqual(set(result['domains']), {'metabolism', 'nutrition'})
        self.request['domains'] = {'nutrition': []}
        self.assertEqual(score_request(self.request)['processing_status'], 'error')

    def test_conflicting_dates_are_not_silently_overwritten(self):
        self.request['domains']['nutrition']['evaluation_date'] = '2026-09-25'
        self.assertEqual(score_request(self.request)['domains']['nutrition']['processing_status'], 'error')

    def test_envelope_rejections(self):
        for request in [[], {}, {**self.request, 'api_version': '2.0'}, {**self.request, 'evaluation_date': '20260924'},
                        {**self.request, 'evaluation_date': None}, {**self.request, 'domains': {}},
                        {**self.request, 'domains': {'typo': {}}}, {**self.request, 'extra': True},
                        {**self.request, 'domains': {'metabolism': {'person': {'age': float('nan')}}}}]:
            with self.subTest(request=request), self.assertRaises(ContractError):
                score_request(request)
        for raw in ['{"a":1,"a":2}', '{"a":NaN}']:
            with self.assertRaises(ValueError):
                loads_request(raw)

    def test_age_policy_and_warning_preservation(self):
        for raw in self.request['domains'].values():
            raw.setdefault('person', {})['age'] = 16
        result = score_request(self.request)
        metabolism = result['domains']['metabolism']['result']
        self.assertEqual(metabolism['age_applicability'], 'younger_age_extrapolation')
        self.assertTrue(metabolism['flags'])
        self.assertIsNone(result['domains']['inflammation']['result']['components']['hs_crp']['score'])
        self.assertIsNone(result['domains']['nutrition']['result']['components']['vitamin_d']['score'])

    def test_actual_http_contract_and_restrictions(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def call(method, path, raw=None, headers=None):
            conn = HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            try:
                conn.request(method, path, raw, headers or {})
                response = conn.getresponse()
                return response.status, json.loads(response.read())
            finally:
                conn.close()
        try:
            headers = {'Content-Type': 'application/json'}
            status, result = call('POST', '/api/v1/score', json.dumps(self.request), headers)
            self.assertEqual(status, 200)
            self.assertEqual(result, score_request(self.request))
            self.assertEqual(call('GET', '/api/v1/health')[1]['api_version'], '1.0')
            self.assertIn('$defs', call('GET', '/api/v1/schema')[1])
            self.assertEqual(call('POST', '/api/v1/score', '{}', headers)[0], 400)
            self.assertEqual(call('POST', '/api/v1/score', '{"a":1,"a":2}', headers)[0], 400)
            self.assertEqual(call('POST', '/api/v1/score', None, {**headers, 'Origin': 'https://example.com'})[0], 403)
            self.assertEqual(call('POST', '/api/v1/score', None, {'Content-Type': 'text/plain'})[0], 415)
            self.assertEqual(call('POST', '/api/v2/score', None, headers)[0], 404)
            # The server rejects an oversized declared length before reading a body.
            # Do not race its early close with a 64-KiB send (Windows may reset it).
            self.assertEqual(call('POST', '/api/v1/score', None, {**headers, 'Content-Length': '65537'})[0], 413)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
