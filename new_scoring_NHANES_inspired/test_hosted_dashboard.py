"""Actual HTTP checks against the entrypoint loaded by Vercel."""
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
from threading import Thread
import unittest
from unittest.mock import patch

from dashboard_server import ASSETS
from health_scorer_api import score_request

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('vercel_entrypoint', ROOT / 'api/index.py')
entrypoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entrypoint)


class HostedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), entrypoint.handler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.environment = patch.dict(os.environ, {
            'SCORER_MODE': 'demo', 'VERCEL_URL': 'preview.vercel.app',
            'VERCEL_BRANCH_URL': '', 'VERCEL_PROJECT_PRODUCTION_URL': '',
            'SCORER_ALLOWED_HOSTS': 'score.example.com', 'SCORER_FRAME_ANCESTORS': '',
            'SCORER_API_KEY': ''})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def call(self, method='GET', path='/', body=None, headers=None):
        conn = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        supplied = {'Host': 'preview.vercel.app', **(headers or {})}
        conn.request(method, path, body, supplied)
        response = conn.getresponse()
        result = response.status, response.read(), dict(response.getheaders())
        conn.close()
        return result

    def test_assets_and_queries(self):
        for path, (_, mime) in ASSETS.items():
            status, body, headers = self.call(path=path + '?v=1')
            self.assertEqual(status, 200, path)
            self.assertTrue(body)
            self.assertTrue(headers['Content-Type'].startswith(mime))
            self.assertEqual(headers['Cache-Control'], 'no-store')
        html = self.call()[1]
        self.assertIn(b'fictional data only', html)
        self.assertNotIn(b'local scoring process', html)

    def test_default_closed_and_custom_alias(self):
        self.assertEqual(self.call(headers={'Host': 'score.example.com'})[0], 200)
        os.environ['SCORER_MODE'] = ''
        self.assertEqual(self.call()[0], 503)

    def test_hosts_origins_and_forwarded_spoofing(self):
        for headers in [
            {'Host': 'evil.example', 'X-Forwarded-Host': 'preview.vercel.app'},
            {'Origin': 'https://evil.example'}, {'Origin': 'null'},
            {'Origin': 'http://preview.vercel.app'},
        ]:
            self.assertEqual(self.call(headers=headers)[0], 403)
        self.assertEqual(self.call(headers={'Origin': 'https://preview.vercel.app'})[0], 200)

    def test_shared_api_parity(self):
        for name in ('worked', 'incomplete', 'age16', 'partial-error'):
            payload = json.loads((ROOT / f'integration_examples/{name}.request.json').read_text())
            status, body, _ = self.call('POST', '/api/v1/score', json.dumps(payload),
                                       {'Content-Type': 'application/json', 'Origin': 'https://preview.vercel.app'})
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body), score_request(payload))

    def test_dashboard_domain_routes(self):
        from dashboard_server import SCORERS
        from health_scorer_api import SCORERS as shared
        payload = json.loads((ROOT / 'integration_examples/worked.request.json').read_text())
        for domain, request in payload['domains'].items():
            route = '/score/' + domain
            self.assertIn(route, SCORERS)
            status, body, _ = self.call('POST', route, json.dumps(request), {'Content-Type': 'application/json'})
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body), shared[domain][0](request))

    def test_api_token_and_route_isolation(self):
        os.environ['SCORER_MODE'] = 'api'
        self.assertEqual(self.call()[0], 503)
        os.environ['SCORER_API_KEY'] = 'x' * 40
        for token in ('', 'Bearer wrong', 'Bearer ' + 'é' * 40):
            self.assertEqual(self.call(path='/api/v1/health', headers={'Authorization': token})[0], 401)
        headers = {'Authorization': 'Bearer ' + 'x' * 40}
        self.assertEqual(self.call(path='/api/v1/health', headers=headers)[0], 200)
        self.assertEqual(self.call(headers=headers)[0], 404)
        self.assertEqual(self.call(path='/app.js', headers=headers)[0], 404)
        payload = (ROOT / 'integration_examples/incomplete.request.json').read_bytes()
        self.assertEqual(self.call('POST', '/api/v1/score', payload,
                                  {**headers, 'Content-Type': 'application/json'})[0], 200)

    def test_embedding_policy(self):
        self.assertIn("frame-ancestors 'none'", self.call()[2]['Content-Security-Policy'])
        os.environ['SCORER_FRAME_ANCESTORS'] = 'https://doctor.example.com'
        self.assertIn('frame-ancestors https://doctor.example.com;', self.call()[2]['Content-Security-Policy'])
        # Permission to frame the page is not permission to call its API cross-origin.
        self.assertEqual(self.call(headers={'Origin': 'https://doctor.example.com'})[0], 403)
        for value in ('*', 'https://doctor.example.com/route', 'https://x; script-src *', 'http://doctor.example.com'):
            os.environ['SCORER_FRAME_ANCESTORS'] = value
            self.assertEqual(self.call()[0], 503)

    def test_invalid_body_and_content_type(self):
        for body, headers, expected in [
            ('{}', {}, 415), ('{', {'Content-Type': 'application/json'}, 400),
            ('x' * 65537, {'Content-Type': 'application/json'}, 413),
            ('{"api_version": "1.0", "api_version": "1.0"}', {'Content-Type': 'application/json'}, 400),
        ]:
            self.assertEqual(self.call('POST', '/api/v1/score', body, headers)[0], expected)

    def test_source_files_not_served(self):
        for path in ('/.env', '/health_scorer_api.py', '/dashboard/index.html', '/vercel.json', '/../dashboard_server.py'):
            self.assertEqual(self.call(path=path)[0], 404)

    def test_head_and_schema(self):
        status, body, headers = self.call('HEAD')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'')
        self.assertGreater(int(headers['Content-Length']), 0)
        self.assertEqual(self.call(path='/api/v1/schema')[1], (ROOT / 'integration_schema.json').read_bytes())


if __name__ == '__main__':
    unittest.main()
