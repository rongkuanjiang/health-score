# System Stability Python engine — v0.2

Implements the [v0.2 sodium–potassium specification](SYSTEM_STABILITY_V02_SPEC.md).
The engine returns one provisional 0–100 score when both selected core measurements
and adult/nonpregnant eligibility are usable. It preserves the independent four-marker
laboratory reference summary and optional calcium notices. API, panel, overview and
radar share the total. Historical v0.1 NHANES outputs do not validate this score.

## Run

From the workspace root:

```powershell
& ./.venv/Scripts/python.exe new_scoring_NHANES_inspired/system_stability_score.py new_scoring_NHANES_inspired/example_system_stability_request.json --today 2026-09-24
& ./.venv/Scripts/python.exe -m unittest discover -s new_scoring_NHANES_inspired -p 'test_system_stability_score.py' -v
```

Use an available Python 3.10+ interpreter if the local virtual environment is inaccessible. The included example is synthetic, including its reference intervals. It returns `all_within_reference`, four interpretable reference results and a sodium–potassium score of 100.0/100.

```python
from datetime import date
from system_stability_score import score_system_stability

result = score_system_stability(request, today=date(2026, 9, 24))
```

The module directory must be on the import path. `today` defaults to the host date; supply it for reproducible evaluation. The engine does not mutate input, access the network, or persist patient entries. The CLI reads a file and prints its result, including provenance, to stdout. Callers control storage and logging.

## Request contract

See [the complete example](example_system_stability_request.json). Requests must contain JSON-shaped values with string object keys. Invalid envelope shapes raise `ValueError`; malformed individual records remain in output with errors. Nonfinite numbers are rejected for interpretation and preserved as strings in provenance, so output can be serialized with `json.dumps(result, allow_nan=False)`.

| Field | Meaning |
|---|---|
| `observations` | Object keyed by `sodium`, `potassium`, `chloride`, `total_co2`, `total_calcium`, or `ionized_calcium`; each value is one observation object or a list of candidates. Unknown markers are retained as unsupported. |
| `selection.report_id` | Required nonempty report identity. |
| `selection.specimen_date` | Required collection date in exact `YYYY-MM-DD` format, no later than evaluation date. |
| `selection.specimen_id` | Select when available; required for a report containing multiple known specimen IDs. If selected, every included observation must match. |
| `selection.observation_ids` | Object mapping each selected marker to its unique observation ID, even when only one candidate exists. No implicit best/latest result selection. |
| `person`, `context` | Points require finite `person.age >= 18` and `person.pregnancy_status` of `not_pregnant` or `not_applicable`. Unknown eligibility withholds points. Reference comparisons retain their own applicable-interval scope. Other context remains provenance; no medication, fasting or illness adjustment is inferred. |

No complete panel can be assembled across report/date/specimen mismatches. Without specimen IDs, a report and collection date identify the selected group; importers must preserve known specimen identities and must not discard them to bypass selection. Duplicate IDs are ambiguous, including across markers. All matching duplicate records are retained but none is interpretable; source warnings still survive.

Each observation uses:

| Fields | Requirement |
|---|---|
| `observation_id`, `raw_analyte_name` | Unique nonempty ID required; original analyte name retained when supplied. Canonical marker mapping belongs to the importer. |
| `value`, `unit`, `qualifier` | Positive finite number (not a Boolean/string); canonical supported unit; qualifier defaults to `=` and also accepts `<`, `<=`, `>`, `>=`. A bound stays a bound. |
| `lower_limit`, `upper_limit`, `reference_unit` | Positive ordered numerical limits and explicit supported unit. Limits can use a different convertible unit from the measurement. |
| `reference_applicability` | Must be `confirmed`; otherwise no derived interpretation. This is an importer/report assertion covering the actual person, specimen and method, not a patient questionnaire. |
| `reference_provenance` | Nonempty description/identifier of the applicable patient report or documented interval selection. No built-in interval fallback. |
| `reference_marker` | Optional explicit analyte identity; if supplied, must equal the canonical observation marker. |
| `report_id`, `specimen_date`, `specimen_id` | Source collection identity; must agree with selection. `specimen_date` is the contract spelling for collection date. |
| `specimen_type` | `serum` or `plasma`; ionized calcium additionally accepts `whole_blood`. Unknown specimens withhold interpretation. |
| `assay_type` | For total CO2, require `chemistry_total_co2`, or `chemistry_bicarbonate` with literal Boolean `chemistry_alias_verified: true`. Blood-gas bicarbonate and pCO2 are not accepted substitutes. |
| `reliability` | `not_flagged`, `unknown` (default, permits comparison with notice), or `unreliable` (withholds comparison). These names are specific to this domain; other modules need explicit adapter mapping. |
| `interference_affects_result` | Optional Boolean, default false. True withholds comparison and preserves a specimen-interference notice. Preserve report text in `interference_note`. |
| `source_flags` | List of canonical source flags: `low`, `high`, `within_reference`, `critical_low`, `critical_high`, `critical`. Missing means no supplied flags, not proof of no abnormality. Unknown flags are retained and block a reassuring complete summary. |

All additional metadata, constraints, source instructions and raw text remain in observation provenance. Importers must map laboratory flags and known interferences explicitly; the engine does not parse free text, independently verify an applicability assertion, or determine critical thresholds. A malformed scalar canonical critical flag is still surfaced while the record is marked invalid.

Core measurements accept mmol/L or mEq/L (factor 1). Calcium accepts mmol/L or mg/dL (factor 0.2495); mEq/L is deliberately unsupported for calcium. Decimal conversion precedes reference comparison; no display rounding is used for classification. Inclusive reference endpoints are within range. One-sided bounds receive low/high only when every possible value is in that category; otherwise they are indeterminate.

## Output contract

- `model_version`, labels, evaluation date, selection and request provenance.
- `domain_score` and `score`: fixed 50/50 sodium/potassium total, or null when unavailable. `display_score` rounds half-up to one decimal. `marker_scores`, `weights`, `weighted_contributions`, `score_reasons` and `review_required` expose the calculation. Coverage adds `required`, `scored`, and `missing_or_unusable` for the two scoring markers. See v0.2 for point eligibility; reference comparisons use their existing scope.
- `panel_status`: priority order `source_critical_flag`, `source_flag_conflict`, `outside_reference`, `all_within_reference`, `partial`, `unavailable`.
- `coverage`: selected core markers present, interpretable, missing and uninterpretable, with fixed denominator four. This is not confidence. Ambiguous duplicate selections count once as present and zero as interpretable.
- `observations` and `context_observations`: lists retaining every candidate, with `selected`, normalized values/limits, qualifier, source flags, reasons, errors and notice codes. Unselected candidates retain raw data and normalization but cannot receive derived reference interpretation.
- `reference_status`: derived `low`, `within_reference`, `high`, `indeterminate_bound`, or `unavailable`; `classification_basis` distinguishes `derived`, `source_only`, `unavailable`. A source-only normal flag never increments interpretable coverage.
- Domain `notices`: code, marker, observation ID and selection status. Optional calcium warnings remain visible here while core panel status stays independent. Unselected historical warnings are tagged `selected: false` and do not alter the selected panel headline.
- Ordered top-level `reasons`: selection issues, then selected observation errors/reasons in fixed marker order, then missing selected markers. Per-observation errors remain available for unselected malformed records too.

Display a numerical `domain_score` on the 0–100 scale; a null total is unavailable, never zero. Retain reference status/range cards. Show coverage alongside abnormal headlines. Show all selected warnings even when another warning has higher headline priority; preserve optional calcium critical warnings even with a complete within-range core panel. A missing critical flag is not a noncritical assessment. Date-stamped results do not establish stability over time.

## Historical v0.1 verification scope

Verified 2026-09-24: all **27 System Stability tests passed**. The combined domain-engine command `python -m unittest discover -s new_scoring_NHANES_inspired -p 'test_*score.py' -v` passed **95 tests**, including the available metabolism, liver/kidney, inflammation and nutrition suites. The CLI example was exercised with the explicit evaluation date above. Dashboard and NHANES checks were not part of this stage.

The acceptance suite exercises synthetic worked cases, exact/bounded endpoints, independent unit conversion, missing/inapplicable ranges, invalid values and shapes, specimen selection, duplicate IDs, CO2 identity, conflicting/critical/unmapped flags, optional calcium, strict JSON, immutable input and CLI execution. These are implementation checks, not clinical validation. The engine has no dependency on or changes to the other domain engines.

## Historical v0.1 Stage 3 evaluation

Completed 2026-09-24: **35 tests passed** across the 27 engine tests and 8 evaluation tests. The reproducible evaluation uses `evaluate_system_stability.py` and `export_system_stability_nhanes.mjs`, with standard-library Python and Node. See the report for exact rerun commands, source review, age groups, distributions and limitations; JSON and CSV companions contain detailed audit outputs.

Among 6,980 examined participants aged 12+ at screening, 6,348 have all four measurements. All runtime interpretations remain unavailable because the public records lack required report metadata, including applicable reference intervals and exact collection dates. Ten full-cohort checks and seven separate synthetic scenarios passed. The original calcium measurement is retained in mg/dL because CDC's SI conversion factor differs slightly from the engine's. No fallback reference ranges, clinical parameters or engine behavior were changed.
