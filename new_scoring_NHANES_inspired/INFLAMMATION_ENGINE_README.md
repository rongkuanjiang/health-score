> Update 25 September 2026: inflammation now uses the provisional v0.2 fixed-core hs-CRP/WBC domain total. See [current specification](INFLAMMATION_V02_SPEC.md). Earlier marker-only/null-total descriptions below are historical. Nutrition and system stability are unchanged.

> Current integration status (24 September 2026): all five dashboard domains and the shared API 1.0 handoff are implemented. See [integration handoff](INTEGRATION_HANDOFF.md) and [release review](RELEASE_REVIEW.md). Earlier statements below about pending domain/dashboard work or deferred step 5 describe historical checkpoints. Domain rules remain unchanged. Rendered browser acceptance and deployment ownership remain open.

# Inflammation engine — step 2

Update 2026-09-24: **stage 4 dashboard integration is implemented**; see [dashboard usage and verification](DASHBOARD_README.md). The manual panel uses the unchanged engine via `/score/inflammation`, preserving separate context observations and null domain totals. All 126 Python tests and the shared DOM interaction suite passed. Browser visual verification remains outstanding. Earlier progress notes below describe their original checkpoints.

Implemented 2026-09-24 against [the v0.1 specification](INFLAMMATION_V01_SPEC.md). Standard-library Python 3.10+; no deep learning. The numerical rules are unchanged. This engine returns a conditional hs-CRP component and contextual observations, with no comprehensive inflammation total. NHANES descriptive evaluation is complete; clinical validation and dashboard integration remain outstanding.

## Run

From the workspace root in PowerShell:

```powershell
.\.venv\Scripts\python.exe new_scoring_NHANES_inspired\inflammation_score.py new_scoring_NHANES_inspired\example_inflammation_request.json --today 2026-09-24
.\.venv\Scripts\python.exe -m unittest discover -s new_scoring_NHANES_inspired -p test_inflammation_score.py -v
```

Use another working Python 3.10+ executable if the local virtual environment is unavailable. The synthetic example returns **80.0 hs-CRP points**, preserves the cardiovascular-threshold notice and the separate high-WBC laboratory flag, and returns `domain_score: null`. The sample laboratory reference range is illustrative, not a default range for real users.

## Python interface

With this directory on the module search path:

```python
from datetime import date
import json
from pathlib import Path
from inflammation_score import score_inflammation

request = json.loads(Path('example_inflammation_request.json').read_text())
result = score_inflammation(request, today=date(2026, 9, 24))
print(result['components']['hs_crp']['display_score'])
```

`today` defaults to the host's current date; provide it for reproducible evaluation. Input is JSON-shaped data, not arbitrary Python objects. The function does not mutate the request and returns independent copies. Nonfinite numbers are rejected as measurements and represented as strings in returned provenance so output supports `json.dumps(result, allow_nan=False)`.

Malformed request envelopes, unknown marker keys and invalid `today` arguments raise `ValueError`. Malformed individual records remain in `observations` with `errors`; valid other records survive. Unknown optional fields are retained in original provenance but do not change scoring.

## Request contract

| Field | Values and behavior |
|---|---|
| `person.age` | Positive finite numeric age at collection; points at 18+, older-age notice at 85+ |
| `person.pregnancy_status` | `not_pregnant`, `not_applicable`, `pregnant`, `unknown`; first two permit points |
| `context.acute_context` | `absent`, `present`, `unknown`, around collection; only `absent` permits points |
| `context.chronic_inflammatory_condition` | `present`, `absent`, `unknown`; default unknown, notice without point adjustment |
| `context.inflammation_affecting_treatment` | Same as chronic condition; invalid enum values withhold with a reason |
| `observations` | Object keyed by `hs_crp`, `standard_crp`, `unknown_assay_crp`, `wbc`, `absolute_neutrophils`, `absolute_lymphocytes`, `esr`, `other_differential_counts` |
| Each marker entry | One observation object or a list of observations; an empty list means no records |
| `selected_hs_crp_id` | Explicit selection when multiple hs-CRP records exist; one unambiguous record is selected automatically |
| Observation `observation_id` | Nonempty unique string; if omitted, generated as `marker:index` using zero-based list index |
| Observation `value`, `unit`, `qualifier` | CRP in mg/L or mg/dL; qualifier defaults to `=`, supports `<`, `<=`, `>`, `>=`; never parse inequalities from value strings |
| Observation `assay_type` | `hs_crp` required for clinical hs-CRP scoring; no assumption from the marker key alone |
| Research-equivalent assay | `assay_type: research_equivalent_hs_crp`, `assay_equivalence_verified: true` and nonempty `assay_equivalence_provenance` required; trusted importer metadata, not a patient question |
| Observation `report_id`, `specimen_date` | Nonempty ID and valid `YYYY-MM-DD` date, not future, required for hs-CRP points |
| Observation `reliability` | `valid`, `unknown` (default; notice), `unreliable` (withholds); `invalid` accepted as withholding alias |
| Observation `lab_flag` | Preserved verbatim as a laboratory notice even when points are withheld |
| Optional reference range | `lower_limit`, `upper_limit`, `reference_range_applicable: true`, optional `reference_unit` defaulting to observation unit; bounds are in original units |

Duplicate observation IDs block selection. An explicit selection must match exactly one hs-CRP record. No fallback to a more favorable or more complete result occurs. Context dates can differ and are displayed independently; they do not enter the hs-CRP curve.

CBC absolute-count units are `10^9/L`, `10^3/uL` and `cells/uL`; the last is divided by 1000. Differential percentages are supported as `%`, retained as percentages, and never converted into absolute counts. ESR supports `mm/h`. Reference comparisons require exact values and applicable limits in matching units; otherwise supplied laboratory flags remain, without invented ranges. Zero context counts are allowed; exact zero CRP is not.

This engine accepts documented research-equivalence metadata but does not verify laboratory methods itself. It does not automatically recognize or convert NHANES detection-limit fill values. That verification and censored-value mapping belong to the stage-3 research adapter.

## Output and integration rules

- `components.hs_crp` has `score`, `display_score` (one-decimal string), `status`, ordered `reasons`, `notices` and `observation_id`. Status is `scored`, `scored_from_bound` or `unavailable`.
- `domain_score` is always null, with `domain_aggregation_status: limited_marker_coverage`. Do not relabel the component as a comprehensive inflammation score.
- Global `status` is `component_available`, `context_only` or `unavailable`. `context_only` means a numerically valid observation exists, even if its metadata or eligibility prevents points; inspect record errors and metadata before interpretation.
- `observations` preserves every record, normalized values/units, qualifier, specimen age, `errors`, `metadata_reasons`, `reference_status` and notices. These include **unselected records and CBC flags**; consuming only the component would lose useful context.
- `coverage` distinguishes hs-CRP presence from scoring usability and lists missing requirements and supplied context marker names. A listed marker is not automatically valid; check its observation errors. Coverage is not a confidence percentage.
- Top-level `notices` explain limited coverage and provisional points. Render these alongside component and observation notices. Withheld scores are null, never zero.

For example, changing the example's hs-CRP to 12 mg/L yields no points and retains the above-10 notice. Removing hs-CRP leaves WBC visible with `context_only`. Setting acute context to unknown withholds points rather than inventing an illness-free collection state.

## Verification and remaining work

On 2026-09-24, **16 inflammation acceptance tests passed**. Checks include worked examples, curve continuity/monotonicity, unit parity, bounded results, selection, age/pregnancy/context gates, invalid values, overflow, serialization, independent copies, retained flags and the CLI example.

The full Python suite passed **72 tests with no skips**, including metabolism, liver/kidney, research-adapter tests, existing dashboard HTTP checks and HbA1c JavaScript parity. These are implementation checks, not evidence of clinical validity. No browser test or NHANES inflammation evaluation is claimed.

Update 2026-09-24: [stage 3 descriptive behavior evaluation](nhanes_inventory/inflammation_v01_evaluation.md) is complete, with reproducible Python/Node scripts, raw-row exports, source snapshots and eight adapter tests. Full-engine results remain withheld because required collection context is unavailable; numerical diagnostics are explicitly separate. The inflammation HTTP route and dashboard panel remain stage 4; the shared integration package remains deferred until the domains are ready.

Stage-3 verification: all **80 tests** across inflammation, metabolism, liver/kidney, their evaluation adapters and the existing dashboard passed, including JavaScript parity, with no skips. The broader workspace discovery run executed 124 tests and had one failure in separately developed System Stability: `test_malformed_fields_do_not_crash`, `source_flags=[]` subcase (expected a status other than `all_within_reference`). No System Stability files were changed by this work. The cohort audit passed all eight invariants; the exporter also reconciles the complete CRP counts with the CDC codebook.
