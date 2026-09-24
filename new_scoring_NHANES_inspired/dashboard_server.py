"""Local-only dashboard adapter. Run: python dashboard_server.py."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from metabolism_score import score_metabolism, _PARAMS, _curve, VERSION
from liver_kidney_score import score_liver_kidney
from nutrition_score import score_nutrition, _curve as nutrition_curve, VERSION as NUTRITION_VERSION
from system_stability_score import score_system_stability
from inflammation_score import score_inflammation, _curve as inflammation_curve, VERSION as INFLAMMATION_VERSION
from health_scorer_api import score_request, loads_request, metadata

ROOT = Path(__file__).with_name('dashboard')
ASSETS = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
          '/style.css': ('style.css', 'text/css'), '/details.js': ('details.js', 'text/javascript'),
          '/domains.js': ('domains.js', 'text/javascript'), '/organ.js': ('organ.js', 'text/javascript')}
SCORERS = {'/score': score_metabolism, '/score/metabolism': score_metabolism,
           '/score/organ-stress': score_liver_kidney, '/score/inflammation': score_inflammation}
ASSETS['/inflammation.js'] = ('inflammation.js', 'text/javascript')
ASSETS['/nutrition.js'] = ('nutrition.js', 'text/javascript')
SCORERS['/score/nutrition'] = score_nutrition
ASSETS['/stability.js'] = ('stability.js', 'text/javascript')
ASSETS['/overview.js'] = ('overview.js', 'text/javascript')
SCORERS['/score/system-stability'] = score_system_stability


def model_explanation():
    """Sample the actual scoring engine so diagrams cannot invent a second model."""
    ranges = {'hba1c': (4, 14), 'ldl_c': (0.01, 11), 'triglycerides': (0.01, 15), 'hdl_c': (0.01, 2.4999)}
    curves = {}
    for marker, (low, high) in ranges.items():
        parameters = _PARAMS['curves'][marker]
        xs = sorted(set([low + (high-low)*i/160 for i in range(161)] + [x for x, _ in parameters['anchors']] + [x for x, _ in parameters.get('nonfasting_anchors', [])]))
        curves[marker] = {**parameters, 'points': [[x, _curve(marker, x)[0]] for x in xs]}
        if marker == 'triglycerides':
            curves[marker]['nonfasting_points'] = [[x, _curve(marker, x, True)[0]] for x in xs]
    return {'model_version': VERSION, 'weights': _PARAMS['effective_weights'], 'curves': curves}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Do not log entered health information.

    def reply(self, status, body, content_type='application/json'):
        if not isinstance(body, bytes):
            body = json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type + '; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

    def do_GET(self):
        if not self.valid_host():
            return self.reply(403, {'error': 'Use localhost or 127.0.0.1.'})
        if self.path == '/api/v1/health':
            return self.reply(200, metadata())
        if self.path == '/api/v1/schema':
            return self.reply(200, Path(__file__).with_name('integration_schema.json').read_bytes())
        if self.path == '/model':
            return self.reply(200, model_explanation())
        if self.path == '/model/nutrition':
            return self.reply(200, {'model_version': NUTRITION_VERSION,
                                   'points': [[i / 2, nutrition_curve(i / 2)] for i in range(1, 251)]})
        if self.path == '/model/inflammation':
            return self.reply(200, {'model_version': INFLAMMATION_VERSION,
                                   'points': [[i / 20, inflammation_curve(i / 20)] for i in range(1, 201)]})
        asset = ASSETS.get(self.path)
        if not asset:
            return self.reply(404, {'error': 'Not found'})
        name, mime = asset
        self.reply(200, (ROOT / name).read_bytes(), mime)

    def do_POST(self):
        origin = self.headers.get('Origin')
        allowed = (None, f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}')
        if not self.valid_host() or origin not in allowed:
            return self.reply(403, {'error': 'Local dashboard requests only.'})
        shared_api = self.path == '/api/v1/score'
        if self.path not in SCORERS and not shared_api:
            return self.reply(404, {'error': 'Not found'})
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.reply(415, {'error': 'Expected application/json'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 65536:
                return self.reply(413, {'error': 'Request must be 1–65536 bytes.'})
            raw = self.rfile.read(length)
            request = loads_request(raw) if shared_api else json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite number')))
            result = score_request(request) if shared_api else SCORERS[self.path](request)
        except (ValueError, UnicodeError, RecursionError, OverflowError):
            return self.reply(400, {'error': 'Invalid scoring request. Check the JSON fields.'})
        self.reply(200, result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Health scorer dashboard: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
