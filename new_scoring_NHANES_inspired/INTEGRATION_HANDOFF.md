> Nutrition update, 25 September 2026: [v0.2](NUTRITION_V02_SPEC.md) now provides one provisional B12/ferritin total (50% each), with vitamin D separate and optional. Prior vitamin-D-only/null-total descriptions are historical.

> Update 25 September 2026: inflammation now uses the provisional v0.2 fixed-core hs-CRP/WBC domain total. See [current specification](INFLAMMATION_V02_SPEC.md). Earlier marker-only/null-total descriptions below are historical. Nutrition and system stability are unchanged.

> Current organ-stress model (25 September 2026): v0.2 now combines eGFR (50%), ALT (30%) and ALP (20%) into one domain score. AST and bilirubin are optional context. See [the current specification](ORGAN_STRESS_V02_SPEC.md) for inputs, curves, missing-data rules and Canadian source rationale. The v0.1 descriptions and evaluation results below are historical and do not validate v0.2.

# Health scorer integration handoff

Package **0.1.2**, shared API **1.0**, prepared 24 September 2026. All five domain engines and dashboard panels are included, with a questionnaire, unified five-domain dashboard, inline biomarker sections, calculate-all action and pentagon visualization. Numerical parameters are unchanged. This is a preliminary integration release, not clinical validation or a hosted production service. No overall health score is defined.

## Run the delivered package

Extract `health-scorer-0.1.2.zip`, open a terminal in its `health-scorer` directory, and use Python 3.10+:

```powershell
python dashboard_server.py --port 8765
```

Open http://127.0.0.1:8765. Runtime uses only the Python standard library; no pip install, frontend build, Node runtime, database or deep learning is required. The ZIP contains engines, parameter files, dashboard assets, examples, contracts and acceptance tests. Keep parameter JSON beside its corresponding Python module. `MANIFEST.json` lists SHA-256 hashes of packaged files; the adjacent `.zip.sha256` hashes the archive. Research datasets and patient records are excluded.

For an existing Python backend, put the extracted directory on the module search path and call the module directly:

```python
import json
from health_scorer_api import score_request

with open('integration_examples/worked.request.json', encoding='utf-8') as source:
    request = json.load(source)
response = score_request(request)
metabolism = response['domains']['metabolism']['result']
print(metabolism['display_score'])  # 85.6
```

Or run a reproducible CLI request:

```powershell
python health_scorer_api.py integration_examples/worked.request.json
```

CLI exit codes: 0 for successfully evaluated domains (including withheld points), 1 for one or more domain processing errors, 2 for an invalid envelope. CLI prints the full result, including submitted data. Use `--output result.json` only when intentionally saving that data. The module itself does not persist or log input.

## HTTP interface

| Method and path | Behavior |
|---|---|
| `GET /api/v1/health` | API/package/model versions and preliminary status; no health data |
| `GET /api/v1/schema` | Shared request/response envelope JSON Schema |
| `POST /api/v1/score` | Evaluate one or more domains with an explicit evaluation date |

Example from PowerShell, in the extracted directory:

```powershell
$requestBody = Get-Content -Raw integration_examples/worked.request.json
$response = Invoke-RestMethod -Uri http://127.0.0.1:8765/api/v1/score -Method Post -ContentType application/json -Body $requestBody
$response.domains.metabolism.result.display_score
```

The existing `/score`, `/score/metabolism`, `/score/organ-stress`, `/score/inflammation`, `/score/nutrition` and `/score/system-stability` routes remain dashboard compatibility adapters returning raw engine results. New integrations should use `/api/v1/score` or `score_request`.

HTTP server binds to loopback only. It checks Host and Origin, serves allowlisted assets, disables response caching, has no CORS and accepts JSON bodies up to 65,536 bytes. A separately hosted frontend should call its own backend, which imports `score_request`; it cannot call this demo cross-origin. This standard-library server is for local development, not public hosting.

## Shared request contract

```json
{
  "api_version": "1.0",
  "evaluation_date": "2026-09-24",
  "domains": {
    "metabolism": {}
  }
}
```

The three top-level fields are required; extra top-level fields, duplicate JSON keys, nonfinite values, invalid dates, unknown domain IDs and empty `domains` are rejected. This minimal example intentionally returns missing-data results. Use the bundled worked request for scorable examples.

`evaluation_date` is an explicit YYYY-MM-DD date used by every requested engine. It may be historical for replay; it is not a collection date and never fills missing specimen dates. Any domain-local `evaluation_date` must match it. The wrapper supplies the date to the engines without changing the supplied domain payload. Omitted domains are not calculated or inferred. Each domain receives its own context; there is no implicit copying of pregnancy, age, reliability or report-selection fields between domains.

The JSON Schema validates the shared envelope. **It is not a complete schema for all domain fields.** Domain contracts below define units, eligibility, observations, reference limits, selection, bounds and output meanings. Individual invalid observations usually remain in engine results with reasons; malformed domain envelopes produce a domain processing error.

| Domain ID | Input/output contract | Main result paths inside `result` |
|---|---|---|
| `metabolism` | [Metabolism](ENGINE_README.md), [age amendment](AGE_EXTENSION_AND_DETAILS.md) | `score`, `display_score`, `markers`, `components`, `flags`, `blocking_reasons`, `coverage` |
| `organ-stress` | [Liver/kidney](LIVER_KIDNEY_ENGINE_README.md) | `domain_score` / `score`, `weights`, `weighted_contributions`, `components`, `flags`, `coverage`; see [v0.2](ORGAN_STRESS_V02_SPEC.md) |
| `inflammation` | [Inflammation](INFLAMMATION_ENGINE_README.md) | `components.hs_crp`, `observations`, `notices`, `coverage`; `domain_score` is null |
| `nutrition` | [Nutrition](NUTRITION_ENGINE_README.md) | `domain_score`, B12/ferritin components, optional `components.vitamin_d`, observations, notices and coverage |
| `system-stability` | [System Stability v0.2](SYSTEM_STABILITY_V02_SPEC.md) | `domain_score`, `marker_scores`, `weights`, `weighted_contributions`, `score_reasons`; fixed sodium/potassium core, with supplemental reference `panel_status` and notices |

Enums intentionally remain domain-specific. For example, metabolism pregnancy uses `no`/`yes`; other point engines use `not_pregnant`/`pregnant`. System Stability reliability uses `not_flagged`, unlike the point engines' `valid`. Do not pass one domain's enums to another or infer a technical assertion from a missing field. Importers must explicitly map their source data to each documented contract. A unified importer is app-specific work.

## Responses and errors

Successful HTTP evaluation returns 200 with `api_version`, `package_version`, all `model_versions`, `evaluation_date`, `processing_status`, `domains`, and a null `overall_score` with `overall_score_status: not_defined`.

Each requested domain contains its `model_version`, `processing_status: ok` and unmodified engine `result`, or `processing_status: error` and `{code: invalid_domain_request, message: ...}`. A bad domain does not discard successful domains. Top-level processing status is `ok` if all evaluations succeed, `partial` if some fail, or `error` if all fail. All three use HTTP 200 for a valid shared envelope. **Processing success never means the result is complete, normal or numerically scorable.** Inspect the engine statuses and reasons.

HTTP errors use `{"error": "human-readable message"}`: 400 invalid shared request/JSON, 403 disallowed Host/Origin, 404 unknown route, 413 body outside the limit, 415 unsupported content type. Clients should branch on HTTP status and domain error code, not message wording. Python envelope errors raise `ContractError`, a `ValueError` subclass. Unexpected engine faults propagate in Python and must be handled by the integrating backend without logging raw health data; the demo server is not a production exception boundary.

## App rendering acceptance rules

1. Show withheld/null points as unavailable, never zero or 100. Zero remains a genuine numeric value. Use engine `display_score` where present, including `<0.1`.
2. Show an eGFR interval as an interval, not an invented exact eGFR or score. Preserve qualifiers.
3. Retain notices at domain, component and observation levels, including optional context and laboratory flags. A reassuring average cannot replace individual findings.
4. Keep coverage beside results. Missing or uninterpretable data is not reassuring evidence or a confidence percentage.
5. Do not label vitamin D points as overall nutrition, hs-CRP points as comprehensive inflammation, or a reference-range summary as a numerical stability score. Do not average domains into an overall score.
6. Preserve age applicability. Metabolism's experimental age-16 output does not authorize pediatric points in the other domains.
7. Clear old results when inputs change and reject late responses for superseded inputs. Display transport and domain processing errors separately from withheld scores.
8. Copy technical laboratory metadata from a report or trusted importer. Leave unknown values unknown; never ask patients to certify assay validity or reference applicability.

`integration_client.mjs` provides an optional JavaScript request helper and null-safe display helper. It returns the full response without stripping notices. It is not a full app UI, and the receiving app must verify the acceptance rules in its own components.

## Synthetic fixtures and checks

`integration_examples/` contains paired requests and expected responses for `worked`, `incomplete`, `age16` and `partial-error`. All use 2026-09-24 for reproducibility. The worked fixture yields metabolism 85.6, kidney 87.5, liver 75.0, hs-CRP 80.0, vitamin D 75.0 and a categorical stability summary. These examples are synthetic; reference limits are illustrative.

```powershell
python -m unittest discover -s . -p 'test_*.py'
node test_integration_client.mjs
```

Python runtime requires no external packages. Node is optional for JavaScript checks; the HbA1c parity test may skip if Node is unavailable. Workspace-only DOM checks use the separate optional jsdom setup described in [dashboard notes](DASHBOARD_README.md). Current evidence and remaining visual review are recorded in [release review](RELEASE_REVIEW.md).

## Deployment and ownership handoff

This delivery is ready for the app team to integrate locally. No external deployment or agreement with that team has been made here.

| Responsibility | Proposed owner / state |
|---|---|
| Engine, parameters, model versions and evidence review | Scoring team; named owner to be confirmed |
| Importer field mappings and app result rendering | Receiving app team; named owner to be confirmed |
| Hosting, TLS, authentication, authorization, operational limits | App backend/platform owner; deployment choice remains open |
| Health-data storage, retention, consent and access policy | App/product owner; follow the app's approved policy |
| Desktop/mobile visual acceptance and app integration sign-off | App/scoring teams; pending rendered review |

For production, embed the Python module behind the app's authenticated backend and use its existing operational controls. The local demo does not implement authentication, accounts, persistence, upload/extraction, wearable connections or monitoring. Avoid exposing the demo server publicly. Pin package and model versions; rerun fixture and rendering checks before upgrading. An API major-version change is required for incompatible envelope changes; scoring-rule changes require their own model version and updated evidence regardless of API version.
