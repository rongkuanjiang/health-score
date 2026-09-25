> Current organ-stress model (25 September 2026): v0.2 now combines eGFR (50%), ALT (30%) and ALP (20%) into one domain score. AST and bilirubin are optional context. See [the current specification](ORGAN_STRESS_V02_SPEC.md) for inputs, curves, missing-data rules and Canadian source rationale. The v0.1 descriptions and evaluation results below are historical and do not validate v0.2.

> Current integration status (24 September 2026): all five dashboard domains and the shared API 1.0 handoff are implemented. See [integration handoff](INTEGRATION_HANDOFF.md) and [release review](RELEASE_REVIEW.md). Earlier statements below about pending domain/dashboard work or deferred step 5 describe historical checkpoints. Domain rules remain unchanged. Rendered browser acceptance and deployment ownership remain open.

# Liver and kidney Python engine — stage 2

Implements [the v0.1 specification](LIVER_KIDNEY_V01_SPEC.md) and its adjacent parameter JSON using Python 3.10+ and the standard library. Returns separate **Kidney filtration estimate** and **Liver enzyme pattern** points. `domain_score` is always null and `aggregation_status` is `aggregation_not_defined`. Points remain preliminary and unvalidated.

Stage 3 is complete: see the [NHANES behavior evaluation](nhanes_inventory/liver_kidney_v01_evaluation.md), reproduced by `evaluate_liver_kidney.py`. Public NHANES dates cannot satisfy the kidney date gate, so the report clearly separates kidney equation/curve diagnostics from full-engine liver scores. No application gates or numerical curves were changed. Stage 4 is implemented in the shared [dashboard](DASHBOARD_README.md), with separate kidney and liver results; visual browser verification remains outstanding. The shared integration API remains deferred until the other domains are finished. These Python functions and CLI are a local development contract, not a deployed service.

## Run

From the workspace root:

```powershell
& ./.venv/Scripts/python.exe new_scoring_NHANES_inspired/liver_kidney_score.py new_scoring_NHANES_inspired/example_liver_kidney_request.json
& ./.venv/Scripts/python.exe -m unittest discover -s new_scoring_NHANES_inspired -p 'test_*.py' -v
```

Use another working Python 3.10+ interpreter if the workspace environment is unavailable. The example returns kidney **87.5**, liver **75.0**, and no domain total. The ALT notice survives alongside the scores.

From Python with this directory on the import path:

```python
from datetime import date
from liver_kidney_score import score_liver_kidney

result = score_liver_kidney(request, today=date(2026, 9, 24))
```

`today` defaults to the host date. Calls do not mutate input or share returned mutable structures. Invalid envelope shapes raise `ValueError`; malformed observations return reasons. The contract accepts JSON-shaped data. Nonfinite numeric inputs are rejected and preserved as strings in provenance, allowing `json.dumps(result, allow_nan=False)`.

## Request fields

| Field | Contract |
| --- | --- |
| `person.age` | Positive finite numeric years at collection, including fractional years. Under 18: estimates/observations only, no wellness points or point envelopes. |
| `person.pregnancy_status` | `not_pregnant`, `not_applicable`, `pregnant`, `unknown`. Missing/unknown blocks points. These names follow this domain's specification; the existing metabolism request uses `no`/`yes` and requires explicit mapping in a future shared adapter. |
| `person.equation_sex` | `male` or `female`, required only for local calculation; never inferred from other fields. |
| `context.kidney_route` | `reported` or `creatinine`. Defaults to reported whenever the `egfr` key is present, even if malformed or null. Otherwise selects creatinine. No automatic fallback. |
| `context.creatinine_equation` | `ckd_epi_2021_creatinine` or `ckid_u25_creatinine`; default adult equation from age 18, U25 below 18. Age limits are enforced. |
| `context.dialysis`, `context.acute_kidney_injury` | `yes`, `no`, `unknown` (default). `yes` blocks kidney calculation and points; unknown adds notices; invalid values block kidney. |
| `context.same_snapshot_confirmed` | Literal Boolean `true` required for liver grouping if either enzyme date is missing. Does not override conflicting dates or missing/mismatched report IDs. |
| `context.previous_egfr_equation` | Optional prior equation identifier; a change produces a longitudinal-comparison notice. |
| `observations` | Object containing `egfr`, `creatinine`, `height`, `alt`, `ast` as available. |
| `optional_observations` | Object with `alp`, `bilirubin`, `ggt`, `albumin`, `bun`, `uric_acid`, `uacr`, `cystatin_c`. Context only; no point contribution or inferred diagnosis. |

Every measurement uses `value`, `unit`, optional `qualifier` (default `=`), `report_id`, `specimen_date` (`YYYY-MM-DD`), `reliability` (`valid`, `invalid`/`unreliable`, `unknown`), and optional `lab_flag`. All supplied fields are retained in raw provenance, including source identifiers, method details and reference ranges. `lab_flag` is passed through as a laboratory notice without medical reinterpretation. Abnormal optional flags are retained in the relevant component and top-level notices. Exact core values must be positive; context accepts zero as a recorded measurement.

The selected kidney input requires a nonempty report ID and valid specimen date. Liver grouping requires matching nonempty report IDs and matching dates when both exist. Older dates do not expire automatically; `specimen_age_days` exposes their age. Unknown reliability permits scoring with a notice; explicitly unreliable results cannot be scored. Technical metadata belongs in the report/import workflow.

### Reported eGFR

Use indexed `mL/min/1.73m2` or Unicode alias `mL/min/1.73m²`, with an `equation` identifier from the spec. Do not pass unindexed `mL/min`. Supported qualifiers are `=`, `>`, `>=`, `<`, `<=` as separate fields with a positive numeric bound; embedded strings such as `">60"` are invalid.

Exact observations populate `components.kidney.egfr`; censored observations populate `egfr_bound` and leave `egfr` null. `>60` produces `score_envelope: [75,100]` and no point score. `>=90` produces 100 with `scored_from_bound`. Eligibility restrictions also withhold envelopes. No midpoint is substituted. Reported observations remain in provenance when dialysis/AKI prevents their use.

### Creatinine calculation

Use `mg/dL`, `µmol/L`, `μmol/L`, or ASCII `umol/L`. Provide `calibration: "idms_traceable"` or `"research_calibrated"`; the research option additionally requires a nonempty `calibration_provenance` description. This engine never applies the NHANES correction automatically. An explicit route may select creatinine independently of a supplied eGFR, with both retained in provenance.

CKiD U25 additionally requires `observations.height` in `cm` or `m`. Height should be measured near collection; a missing date gets a notice, and a malformed/future date blocks use. This version defines no maximum height-to-specimen interval. Set creatinine `assay_method: "enzymatic"` when confirmed; otherwise U25 carries an assay notice. Adult CKD-EPI does not require height. No local equation is supported below age 1.

### Liver enzymes

Each ALT/AST measurement requires `U/L` or `IU/L`, an exact positive value, numeric `lower_limit` and `upper_limit` with `0 <= lower < upper`, and `reference_range_applicable: true`. Applicability is a report/import assertion covering age, sex and assay. A below-range result is withheld. Both enzymes must be scorable and from the same snapshot; liver points are the lower of their points. Marker results remain visible when grouping fails.

## Results and coverage

Each component exposes `score`, `display_score`, `status`, `reasons`, `flags`, `markers`, and `coverage`. Display strings use one-decimal half-up rounding (with `<0.1` for tiny positive scores, matching metabolism). Full-precision points are retained. Top-level status is `components_available`, `partial`, or `unavailable` for two, one, or zero numerical components.

Coverage distinguishes available observations, usable estimation inputs, numerical points and specific blocking reasons. Context `usable_for_display` means a finite nonnegative value, supplied unit and acceptable basic metadata, not validated unit conversion, normality or clinical adequacy. Missing/unusable UACR produces an incomplete kidney-damage coverage notice. No completeness or confidence percentage is calculated.

The acceptance suite covers worked examples, all anchors and interpolation, bounded observations and bound-aware notices, both equations/sex coefficients, age boundaries, unit aliases, eligibility, calibration, reference limits, snapshots, missing/invalid data, context flags, immutability and strict serialization. Existing metabolism, evaluation and dashboard tests provide regression coverage. Passing tests establishes implementation behavior, not clinical validation.

Verification on 2026-09-24: **44 tests passed**, including 17 liver/kidney tests and all 27 existing metabolism, evaluation and dashboard tests. The JavaScript HbA1c parity check ran using `NODE_EXE=C:\nvm4w\nodejs\node.exe`; no tests were skipped. The documented CLI example also returned kidney 87.5 and liver 75.0 with no domain total. Numerical anchors and existing metabolism code were unchanged.
