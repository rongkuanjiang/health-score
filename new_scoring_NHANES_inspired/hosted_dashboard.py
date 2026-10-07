"""Hosted transport policy. No model changes, database, or request-body logging."""
import hmac
import os
import re
from urllib.parse import urlsplit

from dashboard_server import Handler


def configured_hosts():
    values = [os.getenv(name, '') for name in
              ('VERCEL_URL', 'VERCEL_BRANCH_URL', 'VERCEL_PROJECT_PRODUCTION_URL')]
    values += os.getenv('SCORER_ALLOWED_HOSTS', '').split(',')
    return {value.strip().lower() for value in values
            if re.fullmatch(r'[a-zA-Z0-9.-]+(?::[0-9]+)?', value.strip())}


def configured_frames():
    origins = os.getenv('SCORER_FRAME_ANCESTORS', '').split(',')
    accepted = []
    for origin in origins:
        origin = origin.strip()
        if not origin:
            continue
        parsed = urlsplit(origin)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
                or parsed.password or parsed.path or parsed.query or parsed.fragment
                or not re.fullmatch(r'https://[a-zA-Z0-9.-]+(?::[0-9]+)?', origin)):
            raise ValueError('Frame ancestors must be exact HTTPS origins.')
        accepted.append(origin)
    return ' '.join(accepted) if accepted else "'none'"


class HostedHandler(Handler):
    def valid_host(self):
        # Never trust client-supplied X-Forwarded-Host to authorize a hostname.
        hosts = self.headers.get_all('Host', [])
        return len(hosts) == 1 and hosts[0].lower() in configured_hosts()

    def valid_origin(self):
        origins = self.headers.get_all('Origin', [])
        return not origins or (len(origins) == 1 and
                               origins[0] == 'https://' + self.headers.get('Host', '').lower())

    def authorize(self):
        self.path = urlsplit(self.path).path  # Accept cache-busting query strings.
        try:
            self.frame_ancestors = configured_frames()
        except ValueError:
            self.reply(503, {'error': 'Invalid embedding configuration.'})
            return False
        if not self.valid_host() or not self.valid_origin():
            self.reply(403, {'error': 'Request host or origin is not allowed.'})
            return False
        mode = os.getenv('SCORER_MODE', '')
        if mode == 'demo':
            return True  # Explicit fictional-data preview; protect in Vercel settings.
        if mode != 'api' or len(os.getenv('SCORER_API_KEY', '')) < 32:
            self.reply(503, {'error': 'Set SCORER_MODE to demo or configure authenticated api mode.'})
            return False
        supplied = self.headers.get('Authorization', '').encode('utf-8')
        expected = ('Bearer ' + os.environ['SCORER_API_KEY']).encode('utf-8')
        if not hmac.compare_digest(supplied, expected):
            self.reply(401, {'error': 'A valid backend bearer token is required.'})
            return False
        if self.path not in ('/api/v1/health', '/api/v1/schema', '/api/v1/score'):
            self.reply(404, {'error': 'Only the versioned API is enabled in api mode.'})
            return False
        return True

    def reply(self, status, body, content_type='application/json'):
        if content_type == 'text/html' and isinstance(body, bytes):
            body = body.replace(b'<body>', b'<body><p role="note">Hosted integration demo: use fictional data only.</p>')
            body = body.replace(b'Entries stay in this browser session and the local scoring process.',
                                b'Bloodwork is sent to the hosted scoring service. This application does not save entries; reloading clears the page.')
        return super().reply(status, body, content_type)

    def do_GET(self):
        if self.authorize():
            super().do_GET()

    def do_POST(self):
        if self.authorize():
            super().do_POST()

    def do_HEAD(self):
        self.do_GET()
