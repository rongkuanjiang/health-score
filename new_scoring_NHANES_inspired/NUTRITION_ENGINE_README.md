> Current integration status (24 September 2026): all five dashboard domains and the shared API 1.0 handoff are implemented. See [integration handoff](INTEGRATION_HANDOFF.md) and [release review](RELEASE_REVIEW.md). Earlier statements below about pending domain/dashboard work or deferred step 5 describe historical checkpoints. Domain rules remain unchanged. Rendered browser acceptance and deployment ownership remain open.

# Nutrition engine — step 2

Implemented 2026-09-24 against [the v0.1 specification](NUTRITION_V01_SPEC.md), using [versioned parameters](nutrition_v01_parameters.json). Standard-library Python 3.10+; no additional packages or deep learning. The experimental vitamin D curve is unchanged. This engine supplies no overall nutrition total. [Stage 3 behavior evaluation](nhanes_inventory/nutrition_v01_evaluation.md) is complete; stage 4 dashboard integration is implemented with visual verification outstanding; see [dashboard notes](DASHBOARD_README.md).

## Run

From the workspace root in PowerShell:

```powershell
.\.venv\Scripts\python.exe new_scoring_NHANES_inspired\nutrition_score.py new_scoring_NHANES_inspired\example_nutrition_request.json
.\.venv\Scripts\python.exe -m unittest discover -s new_scoring_NHANES_inspired -p test_nutrition_score.py -v
```

Use another working Python 3.10+ installation if needed. The [synthetic example](example_nutrition_request.json) returns **75.0 vitamin D points**, a possible-inadequacy reference notice, a separate low-albumin laboratory flag, and `domain_score: null`. The sample albumin limits are illustrative, not defaults.

## Python interface

With this directory on the Python module search path:

```python
import json
from pathlib import Path
from nutrition_score import score_nutrition

request = json.loads(Path('example_nutrition_request.json').read_text())
result = score_nutrition(request)
print(result['components']['vitamin_d']['display_score'])  # '75.0'
```

Supply `evaluation_date` in the request or explicitly pass `today=datetime.date(...)`. The CLI also accepts `--today YYYY-MM-DD`. There is no implicit host-date default: absent dates withhold points; conflicting explicit dates return `invalid_evaluation_date`. This implements the specification's explicit-evaluation-date requirement and makes retrospective checks reproducible.

Input must be JSON-shaped data. The function does not mutate it, and output copies are independent. Nonfinite input numbers are rejected as measurements and represented as strings in returned provenance, permitting `json.dumps(result, allow_nan=False)`. Invalid envelopes, unknown marker keys, unsupported Python object types and invalid `today` argument types raise `ValueError`. Invalid individual observations are retained with reasons and do not erase valid other observations.

## Request contract

| Field | Behavior |
|---|---|
| `person.age` | Positive finite numeric age at collection; points at 18+, older-age notice at 85+ |
| `person.pregnancy_status` | `not_pregnant` or `not_applicable` permits points; other/missing values withhold |
| `evaluation_date` | Required valid `YYYY-MM-DD` unless explicit Python/CLI date supplied |
| `observations` | Object keyed by `vitamin_d` or a context marker listed in the parameters |
| Each marker entry | One object or a list of objects; empty list means absent |
| `selected_vitamin_d_id` | Required when multiple vitamin D records exist; sole record may be selected automatically |
| Observation `observation_id`, `report_id` | Nonempty strings required for points; observation IDs must be unique |
| Observation `specimen_date` | Required `YYYY-MM-DD`, no later than evaluation date |
| Vitamin D `analyte` | Exactly `total_25_hydroxyvitamin_d`; never inferred solely from marker key |
| Vitamin D `specimen_type` | `serum` or `plasma` required; unknown/other type withholds |
| Vitamin D `value`, `unit` | Finite positive number, in `nmol/L` or `ng/mL`; no numeric strings |
| `qualifier` | Defaults to `=`; `<`, `<=`, `>`, `>=` retained but never scored |
| `reliability` | `valid`, `unknown` (default, notice), `unreliable` (withhold); `invalid` is a withholding alias; unrecognized values withhold |
| `lab_flag` | Preserved verbatim as a laboratory notice even if score unavailable |
| Optional reference range | `lower_limit`, `upper_limit`, `reference_range_applicable: true`; `reference_unit` defaults to observation unit |
| Optional range identity | `reference_analyte` is the marker key, e.g. `serum_folate`; `reference_specimen_type` must match `specimen_type` when supplied |

Range applicability is trusted report/import metadata confirming age, sex, analyte and assay applicability. The engine cannot independently certify it. Explicit mismatches prevent derived reference flags. Context units are preserved without conversion; unknown units have no inferred universal ranges. Exact, valid context values may be compared with supplied applicable limits. Bounded or unreliable context retains source flags but receives no derived lab comparison.

`context.vitamin_d_supplementation`, `context.vitamin_d_treatment` and `context.relevant_conditions` accept `present | absent | unknown`. Present/unknown values add notices without changing points. Missing defaults to unknown. Invalid optional answers remain in provenance and add an invalid-context notice; they are treated as unknown, not as absent, and do not erase the component. No fasting input is required.

Duplicate vitamin D IDs prevent unambiguous selection. A selected ID duplicated elsewhere also withholds that component. Duplicates among unrelated context observations are flagged locally. An invalid selected result is never replaced by a different result. Dates and values are not averaged.

## Output and display rules

- `components.vitamin_d`: numerical `score`, one-decimal string `display_score`, `status: scored | unavailable`, ordered `reasons`, notices and selected observation ID.
- `domain_score` is always null; `domain_aggregation_status` is always `limited_marker_coverage`.
- Global status is `component_available` only when points exist; otherwise `unavailable`, including context-only reports. Observations remain available for display in either case.
- `observations` preserves raw records, normalized values/units, qualifiers, elapsed specimen days, errors, metadata/reliability reasons, reference status and notices. Render flags from all records, including unselected/context results.
- Coverage includes scored/defined component counts (0 or 1 out of one implemented component), `available`, `unusable`, `missing`, and component `missing_requirements`. Entries identify observation index, marker, ID and reasons. Available context means displayable with the required metadata, not a validated nutrient assessment. Missing lists the absent scored marker only; optional absent tests do not create a testing checklist. Unselected vitamin D observations are marked `not_selected` for component use.
- Display top-level limitations as well as component/observation notices. Coverage is not the proportion of nutrition measured or a confidence percentage.

All bounds withhold points. For example, `<30` supports a low-band notice, `<=30` crosses a band boundary, `>=50` spans the plateau and high range, and `>125` supports a high-range notice. Band interpretation uses unrounded values and only applies to eligible adults with supported analyte/specimen identity and non-unreliable measurements. Source lab flags survive all exclusions.

An exact result above 125 nmol/L returns null points and a review notice. The domain total stays null even when the component is 100. Never convert withheld results to zero, infer deficiency from CBC, or promote this marker to overall nutrition. References and evidence limitations remain in the specification.

## Verification and next step

The 17 nutrition acceptance tests cover worked cases, unit parity, boundaries and bound endpoints, selection, age/pregnancy eligibility, metadata and specimen identity, reliability, retained lab flags, malformed inputs, overflow, strict serialization, input isolation, context-range mismatches and the CLI example. These are implementation checks, not clinical validation.

Stage 3 is now complete in [evaluate_nutrition.py](evaluate_nutrition.py), with [adapter tests](test_evaluate_nutrition.py), [the descriptive report](nhanes_inventory/nutrition_v01_evaluation.md), JSON summaries and a participant-level audit CSV. The verified CDC release contains already-standardized vitamin D values; no recalibration is applied. Missing specimen dates withhold every full-engine score, so adult curve-only diagnostics are reported separately. All 23 nutrition engine/adapter tests pass. This is not clinical validation.

Stage 4 is implemented in the shared [dashboard](DASHBOARD_README.md): vitamin D points, context observations, coverage/empty states, reference links, engine-sampled graphics and synthetic profiles. `POST /score/nutrition` is a local demonstration adapter; shared app API packaging remains deferred. Automated HTTP and interaction checks passed; desktop/mobile visual verification remains outstanding because no browser was available.
