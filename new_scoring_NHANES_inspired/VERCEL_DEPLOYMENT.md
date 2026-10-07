# Deploy the dashboard and scoring API to Vercel

This prepares the existing five-domain model for hosting. It does not change scoring
rules or establish clinical validation. The initial deployment is an integration demo
using fictional data. No company deployment has been performed yet.

## Company project settings

1. Import the `rongkuanjiang/health-score` GitHub repository into the company Vercel team
   after these changes have been pushed. Create a separate project for the scorer.
2. Set **Root Directory** to `new_scoring_NHANES_inspired` (not the repository root).
3. Set **Framework Preset** to **Other**. Leave build/install commands at their defaults;
   no frontend build or third-party Python dependencies are needed. The checked-in
   `vercel.json` sets Output Directory to `public` (intentionally empty); dashboard
   assets are served by the Python function, not exposed as unprotected static files.
4. Add `SCORER_MODE=demo` to the desired environment. Keep company deployment protection
   enabled for the initial fictional-data review. The mode itself does not authenticate
   viewers; without platform protection anyone with the URL can use demo routes.
5. Add the project's stable alias/custom domain to `SCORER_ALLOWED_HOSTS`, for example
   `health-score.vercel.app,score.company.example` (hostnames only). Deployment, branch
   and production URLs from Vercel's system environment variables are also accepted.
6. Deploy. The function uses Python 3.13 via `.python-version`. Open the deployment URL,
   complete onboarding and try the full fictional example. All five domains should load.

Changes to environment variables require a new deployment. Do not add keys to Git or
paste credentials into chat. Missing/invalid mode returns 503; unknown host returns 403.
There is no database setup and no need to run `python dashboard_server.py` on Vercel.

## How it is wired

`vercel.json` routes requests to `api/index.py`, which exports Vercel's supported
`BaseHTTPRequestHandler` entrypoint. `hosted_dashboard.py` applies the hosted access
policy, then reuses `dashboard_server.Handler` and the existing scoring engines.
Dashboard assets and API calls share one HTTPS origin. Existing relative URLs work
without changing frontend code or adding CORS. Only allowlisted assets/routes are served.
The local `python dashboard_server.py` workflow remains loopback-only.

The root repository's legacy requirements are intentionally outside this Vercel root.
Do not deploy the legacy scorer or the whole research workspace as the application.

## App embedding

- A native WebView can navigate to the full dashboard HTTPS URL. Initial Vercel
  authentication may require browser login; validate that flow with the app team.
- For an HTML iframe inside AI Doctor, set `SCORER_FRAME_ANCESTORS` to its exact HTTPS
  parent origin, e.g. `https://doctor.company.example`. Multiple origins are comma-separated.
  Blank blocks framing; wildcards and HTTP origins are rejected. Every ancestor in nested
  frames must be allowed. This does not grant cross-origin API access.
- Navigate to the HTTPS page; do not copy the HTML into a local app file. Its assets and
  scoring requests need the deployed origin. Platform protection can still block embedding.
- Demo entries clear on reload. Bloodwork is transmitted to the hosted Python service;
  wearable entries remain in the page. Application code does not persist submissions or
  log request bodies. Hosting access logs/retention must be reviewed separately.

## Backend API integration

For the app team's own interface, use a separate deployment/project configured with
`SCORER_MODE=api` and `SCORER_API_KEY` containing a randomly generated secret of at least
32 characters. The app backend sends `Authorization: Bearer <secret>` on every request.
All requests are refused if the key is missing/short. Only these routes are available:

- `GET /api/v1/health`
- `GET /api/v1/schema`
- `POST /api/v1/score`

The existing [input/output contract](INTEGRATION_HANDOFF.md) and
`integration_examples/*.request.json` are unchanged. Keep the key on their backend;
never put it in browser code or the mobile app. API mode intentionally does not serve
the dashboard. A production embedded dashboard needs the app team's user-session
authentication design; do not make demo mode public as a substitute for it.

Before real health data is accepted, the company must configure app authentication,
platform access/rate controls and review hosting region, logs and data handling. A bearer
key identifies the calling backend, not individual users. This deployment has no patient
accounts, record storage or device integration.

## Validation and handoff

From this directory, run:

```sh
python -m unittest discover -s . -p "test_*.py"
python smoke_hosted.py https://YOUR-DEPLOYMENT.vercel.app
```

For API mode add `--api-only` and set `SCORER_API_KEY` in the local environment. If the
deployment uses Vercel protection, the smoke script also accepts the company-provided
`VERCEL_AUTOMATION_BYPASS_SECRET` through the environment. It never prints credentials or
response bodies and sends only the checked-in fictional fixtures.

Optional DOM interaction tests use `test_dashboard_ui.cjs`, `PYTHON_EXE` and `jsdom` as
described in the dashboard notes. Set `DASHBOARD_TRANSPORT=hosted` to run those same
interactions against the Vercel handler locally. These tests do not render a browser.

After deployment, test desktop/mobile rendering and the actual app WebView/iframe. Check
all five domains, incomplete inputs, reload behavior and connection errors. Give the app
team the stable URL, selected access mode and API contract. Local tests cannot verify
Vercel's packaging/routing, company access settings or the app's embedding behavior.

References: [Vercel Python functions](https://vercel.com/docs/functions/runtimes/python/api-directory),
[Python runtime and versions](https://vercel.com/docs/functions/runtimes/python),
[rewrites](https://vercel.com/docs/routing/rewrites).
