> Current integration status (24 September 2026): all five dashboard domains and the shared API 1.0 handoff are implemented. See [integration handoff](INTEGRATION_HANDOFF.md) and [release review](RELEASE_REVIEW.md). Earlier statements below about pending domain/dashboard work or deferred step 5 describe historical checkpoints. Domain rules remain unchanged. Rendered browser acceptance and deployment ownership remain open.

# Metabolism Python engine — Step 2

**Current policy:** [v0.2 age extension and consumer details](AGE_EXTENSION_AND_DETAILS.md) supersedes the historical age-20 restriction below. Positive ages can receive experimental scores; under-20 and 85+ results carry specific limitations. Curves and weights are unchanged. The prior NHANES report remains a v0.1 adult evaluation.

Step 4 update: the local dashboard is implemented. See [launch instructions, scope, and verification limitations](DASHBOARD_README.md). The HTTP adapter serves this local demo; the supported integration API remains step 5. Historical handoff notes below describe the earlier engine-only state.

Step 3 update: the NHANES behavior check is complete. See [evaluation report](nhanes_inventory/metabolism_v01_evaluation.md) and `evaluate_metabolism.py`. The dashboard and HTTP API remain subsequent work; no scoring parameters were changed by the evaluation.

Implements `METABOLISM_V01_SPEC.md` using the adjacent versioned parameter JSON. Python 3.10+; standard library only. No deep learning or third-party runtime dependencies. The model is preliminary and not clinically validated. The scoring engine and NHANES behavior check are complete; the dashboard and HTTP API remain subsequent steps.

## Run

From this directory, with a working Python installation:

```powershell
python metabolism_score.py example_metabolism_request.json
python -m unittest discover -s . -p test_metabolism_score.py -v
```

The included synthetic example produces **85.625**, displayed as **85.6**. From the workspace root, the existing `.venv/Scripts/python.exe` can be used in place of `python`; prefix the script and test directory with `new_scoring_NHANES_inspired/`.

The parity test executes the original `hba1c_score.mjs` using Node. Set `NODE_EXE` to the Node executable if it is not on PATH. That test explicitly skips if Node is unavailable; it must run for full acceptance. The original JavaScript engine remains here; historical evaluations are preserved in the cleanup archive linked from [README.md](README.md).

## Python interface

```python
import json
from pathlib import Path
from metabolism_score import score_metabolism

request = json.loads(Path('example_metabolism_request.json').read_text())
result = score_metabolism(request)
print(result['score'], result['status'])
```

`score_metabolism(request, today=date(...))` allows reproducible date validation in research/tests. Default `today` is the host's current date. Calls do not mutate their input. Outputs are fresh dictionaries. Invalid envelope shapes raise `ValueError`; malformed measurements return marker statuses. The input contract is JSON data, not arbitrary Python objects. Nonfinite numeric inputs are rejected and represented as strings in returned provenance so outputs support strict JSON serialization.

## Request contract

| Field | Contract |
| --- | --- |
| `person.age` | Positive finite numeric age; age >=20 required for a domain score. Missing/invalid age withholds the domain; age <20 also blocks marker scores. |
| `person.pregnancy_status` | `yes`, `no`, `not_applicable`, `unknown`. Omitted/unknown/unrecognized values require eligibility. `yes` blocks the entire domain before interpretation. |
| `person.sex_reference` | `male`, `female`, `unknown`; omitted/unrecognized reference suppresses assignment of sex-specific HDL flags. No numerical sex adjustment. |
| `context.hba1c_interference` | `yes`, `no`, `unknown` (default). Known interference blocks HbA1c; unknown adds a notice. |
| `context.fasting_status` | `fasting`, `nonfasting`, `unknown` (default). |
| `context.fasting_hours` | Optional finite nonnegative numeric hours. 8–<24 selects fasting; <8 selects nonfasting. >=24 needs resolution. |
| `context.use_unknown_fasting_on_conflict` | Explicit `true` resolves inconsistent fasting evidence to the unknown route and preserves the conflict notice/provenance. |
| `context.ldl_method` | `direct`, `friedewald`, `other_lab_calculated`, `unknown` (default). |
| `context.acute_illness` | `yes` adds an interpretation-limitation notice. |
| `observations` | Object with `hba1c`, `ldl_c`, `triglycerides`, `hdl_c`; missing entries are permitted but cannot produce a complete score. |
| Each observation | `value`, `unit`, `report_id`, optional `source_id`, `specimen_date` (`YYYY-MM-DD`), `reliability` (`valid`, `invalid`, `unknown`, default unknown), optional `qualifier` (`=` for exact results). Inequality-qualified results are unscored. |
| `snapshot_id` | Explicit selected-bundle identifier, required when any core specimen date is missing. It does not override conflicting report IDs or dates. |
| `optional_observations` | Context-only measurements; see below. |

Medication use, relevant conditions and mobility limitations can be recorded as additional questionnaire fields in `context`; they are preserved in provenance and do not change points. The engine does not infer these answers.

Units are exact and never inferred: HbA1c `%` or `mmol/mol`; lipids `mmol/L` or `mg/dL`. Numeric strings are rejected. Convert in the interface only after validating user input. Conversion is performed once; scoring and aggregation retain full precision. Display uses decimal half-up to one decimal, with `<0.1` for tiny positive scores.

All three lipid observations must carry the same nonempty `report_id`. Contradictory lipid dates block lipid composites and the domain. A known HbA1c/lipid gap greater than 90 days blocks the domain but retains marker scores. Missing dates require an explicitly selected bundle and return `dates_unverified`. Invalid/future dates block the domain even when a bundle is selected.

## Result contract

- `model_version`, `model_status`, and explicit age/sex adjustment booleans.
- `score` and `display_score`: combined metabolism value or null; no weight renormalization.
- `status`: `scored`, `incomplete`, `outside_scope`, `eligibility_required`, or `dates_not_aligned`.
- `blocking_reasons`: all missing/blocked marker prerequisites plus age and metadata failures.
- `markers`: each original observation, normalized value/unit, version, primary status, secondary reasons, score, display score, flags, interpretation text and provenance IDs/dates.
- `components`: blood sugar, triglycerides/HDL, lipid health; each includes null-or-number score and blocked prerequisites.
- `coverage`: number of scored markers out of four; metadata can block aggregation even at 4/4.
- `flags`: marker notices also promoted to the top level for dashboard rendering. Show them visibly beside the combined result, including when the combined score is high.
- `alternative_nonfasting`: unknown-fasting sensitivity results for TG and available aggregates. This is not a confidence interval. Never returned as a complete alternative domain if primary-domain eligibility fails.
- `snapshot_date`: latest valid selected specimen date, or null. With `dates_unverified`, this is only the latest known date, not proof of a fully dated snapshot.
- `optional_context` and complete original `provenance`.

Optional observation IDs: `total_cholesterol`, `apob`, `glucose` (requires `type: fasting` or `random`), `bmi`, `waist`, `systolic_bp`, `diastolic_bp`. Total cholesterol uses lipid units; ApoB uses `g/L` or `mg/dL`; glucose preserves `mmol/L` or `mg/dL`; BMI accepts `kg/m²`/`kg/m2`; waist accepts `cm`/`in`; BP uses `mmHg`. Bad optional data has its own status and cannot block core scoring. Non-HDL is derived only from trustworthy compatible same-report total cholesterol and HDL values; it remains context only.

## Implementation decisions and verification

- Existing curve points, conversions, weights and boundaries are retained. The engine loads the adjacent JSON; distribute both files together. Parameter changes require version review and rerunning acceptance checks.
- Report selection is explicit via IDs; missing IDs never silently authorize mixing lipid history. LDL without same-report TG can show a provisional component with incomplete-reliability context, but cannot form a complete lipid/domain result.
- Invalid enum values get explicit blocking statuses, except unavailable sex reference (context only) and pregnancy (eligibility gate). Conflicting or out-of-window fasting duration requires correction or explicit unknown-route selection.
- Missing age permits individual components, as specified, but withholds the domain. Known under-20 age suppresses marker clinical interpretation as well as scores.
- Optional measurements and questionnaire context do not alter the numerical model.
- Tests cover worked profiles, anchors/interpolation, monotonicity and bounds, tails, original JavaScript HbA1c parity, unit equivalents, eligibility and input failures, fasting sensitivity/conflicts, LDL reliability, dates/reports, notice preservation, optional context, rounding and input immutability. Passing these establishes implementation behavior, not clinical validation.

## Dashboard handoff (user direction, 2026-09-24)

Order: **short questionnaire → bloodwork/metabolism results → separate activity section**. Questionnaire establishes adult/pregnancy eligibility and collects medication use, relevant conditions and mobility limitations. For this release, “overall score” refers only to the combined metabolism domain; an overall health score is not defined.

Daily steps are the first wearable input and do not change metabolism points. The future activity section should store date, daily total, source (phone/watch/manual) and availability. Missing is distinct from zero. Use one selected or deduplicated daily source; do not sum overlapping phone/watch counts. Show recent averages, trends and coverage, with mobility context. Wearable ingestion and activity calculations are dashboard work, not implemented in this scoring module.
