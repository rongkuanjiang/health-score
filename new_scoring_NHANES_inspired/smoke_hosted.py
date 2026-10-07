"""Check a deployed service with fictional fixtures; never prints bodies or secrets."""
import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from health_scorer_api import score_request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', help='HTTPS origin, e.g. https://your-project.vercel.app')
    parser.add_argument('--api-only', action='store_true')
    args = parser.parse_args()
    base = args.url.rstrip('/')
    parsed = urlsplit(base)
    if (parsed.scheme != 'https' or not parsed.netloc or parsed.path or parsed.query
            or parsed.fragment or parsed.username or parsed.password):
        parser.error('Use an HTTPS origin without a path, credentials or query.')
    headers = {}
    if os.getenv('SCORER_API_KEY'):
        headers['Authorization'] = 'Bearer ' + os.environ['SCORER_API_KEY']
    if os.getenv('VERCEL_AUTOMATION_BYPASS_SECRET'):
        headers['x-vercel-protection-bypass'] = os.environ['VERCEL_AUTOMATION_BYPASS_SECRET']

    def fetch(path, payload=None):
        request_headers = dict(headers)
        raw = None
        if payload is not None:
            raw = json.dumps(payload, allow_nan=False).encode()
            request_headers['Content-Type'] = 'application/json'
        with urlopen(Request(base + path, raw, request_headers), timeout=30) as response:
            assert response.status == 200, path
            assert response.headers.get('Cache-Control') == 'no-store', path
            return response.read()

    try:
        assert json.loads(fetch('/api/v1/health'))['api_version'] == '1.0'
        json.loads(fetch('/api/v1/schema'))
        if not args.api_only:
            assert b'fictional data only' in fetch('/')
            from dashboard_server import ASSETS
            for path in ASSETS:
                assert fetch(path), path
            for path in ('/model', '/model/nutrition', '/model/inflammation'):
                json.loads(fetch(path))
        root = Path(__file__).resolve().parent
        for name in ('worked', 'incomplete', 'age16', 'partial-error'):
            payload = json.loads((root / f'integration_examples/{name}.request.json').read_text())
            assert json.loads(fetch('/api/v1/score', payload)) == score_request(payload), name
    except HTTPError as error:
        raise SystemExit(f'HTTP {error.code}: check deployment mode, allowed hosts, credentials and Vercel protection.') from None
    print('PASS: hosted API and fictional fixture parity' + ('' if args.api_only else ', dashboard assets and models'))


if __name__ == '__main__':
    main()
