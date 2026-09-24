# System Stability v0.1 — specification

Prepared 2026-09-24. **Stages 1–3 complete: preliminary specification, Python engine and descriptive behavior evaluation.** See [engine usage and contract](SYSTEM_STABILITY_ENGINE_README.md) and [NHANES evaluation](nhanes_inventory/system_stability_v01_evaluation.md). Stage 4 is implemented in the shared [dashboard](DASHBOARD_README.md); desktop/mobile visual verification remains outstanding. No deep learning. Parameters: [system_stability_v01_parameters.json](system_stability_v01_parameters.json). The decision log and implementation acceptance cases are below.

## Meaning and release decision

Keep **System Stability** as the domain heading; use **Electrolyte balance at collection** as the result label. This release compares available chemistry results with their applicable laboratory reference intervals. It does not establish stability over time, resilience, hydration adequacy, or overall health.

**Return `domain_score: null` and marker `score: null`.** Deliver a categorical panel summary and individual results instead. No clinical source reviewed here establishes a 0–100 wellness curve, severity-equivalent distances outside reference intervals, or defensible weights for these markers. A prototype can provide useful dashboard content without assigning such points. This is an explicit design decision, not missing implementation. Never convert an in-range result into 100 points or an unavailable score into zero. Do not include this domain in a numerical overall-score denominator.

The electrolyte panel supports assessment of fluid/electrolyte and acid–base disturbances; abnormal results can have several causes. It does not supply a validated wellness ranking. [MedlinePlus electrolyte panel](https://medlineplus.gov/lab-tests/electrolyte-panel/). The hospital laboratory's panel lists sodium, potassium, chloride, and carbon dioxide, with links to individual test guidance. [Children's Minnesota panel specification](https://www.childrensmn.org/references/lab/chemistry/electrolyte-panel.pdf).

## Marker roles

| Input key | Role | Canonical unit |
|---|---|---|
| `sodium` | Core, reference comparison | mmol/L |
| `potassium` | Core, reference comparison | mmol/L |
| `chloride` | Core, reference comparison | mmol/L |
| `total_co2` | Core, chemistry total CO2 / verified chemistry bicarbonate alias | mmol/L |
| `total_calcium` | Optional context, separate reference comparison | mmol/L |
| `ionized_calcium` | Optional context, separate from total calcium | mmol/L |

Chemistry total CO2 largely reflects bicarbonate. Preserve the reported analyte/method; do not import pCO2 or blood-gas calculated bicarbonate as a chemistry total-CO2 result. Do not diagnose acidosis or alkalosis from this marker alone. [MedlinePlus CO2 test](https://medlineplus.gov/lab-tests/carbon-dioxide-co2-in-blood/).

Total calcium includes protein-bound calcium and differs from ionized calcium. Keep them distinct; do not automatically calculate albumin-corrected calcium or infer dietary calcium adequacy. Albumin can be retained as a linked contextual observation without points. [MedlinePlus calcium test](https://medlineplus.gov/ency/article/003477.htm).

Hemoglobin, platelets, RBC, hematocrit and white-cell counts are outside this narrow first release. No derived anion-gap score, sodium correction, osmolality score, or duplicate bicarbonate contribution. Optional calcium cannot change the four-marker coverage denominator or core summary; its abnormal/critical flags must still be visible.

## Observation and reference contract

Each observation retains: unique ID, marker key, raw analyte name, value, unit, qualifier, collection date, report ID, specimen ID if available, specimen type, method if available, source flags, reliability status and source reference limits. Store raw and normalized values separately. Require explicit selection of one report/specimen group and one observation per marker; do not select the healthiest result, average duplicates, or assemble a complete panel from different collections.

For a derived reference comparison require:

- A finite positive numerical value and supported unit; reject Boolean values, numeric strings until explicitly parsed by the input adapter, zero, negatives, NaN and infinities. Retain invalid records with errors without losing valid records.
- A chemistry serum/plasma specimen for core markers, a valid collection date no later than the supplied evaluation date, and report identity. Unknown specimen or missing date/report preserves the observation but withholds derived classification. A report with multiple specimens requires explicit specimen selection; date alone is insufficient to merge records.
- Two finite positive source limits `lower < upper`, in supported convertible units for the same analyte. Normalize limits with the same conversion as the result.
- Reference applicability `confirmed` from a patient-specific laboratory report or documented laboratory interval selection. Preserve provenance and any age/sex/pregnancy/method constraints. Do not ask consumers to certify technical applicability. Unknown or mismatched applicability withholds derived classification; source lab flags remain visible.

No universal fallback reference ranges in this release. A range copied from a website or another person's report is not an applicable interval. No adult interval is silently applied to children. There is no categorical age exclusion when the report provides an applicable interval; known missing age/sex/context needed to select a generic interval prevents that selection. This is reference comparison, not an extension of adult numerical curves. Pregnancy likewise requires an applicable interval rather than an assumed nonpregnant interval.

Reliability values: `not_flagged`, `unknown`, `unreliable`. `unknown` permits comparison with `reliability_unknown`; it must not imply verified specimen quality. `unreliable` withholds comparison. A source report flagging hemolysis or another interference makes the affected marker unreliable when the report identifies it as affected; retain the flag and do not numerically correct the measurement. Potassium can be distorted by specimen-related factors. [MedlinePlus potassium test](https://medlineplus.gov/lab-tests/potassium-blood-test/).

No fasting gate or questionnaire about medications/acute illness is required for this report-comparison release. Preserve supplied clinical context without changing values or points. Display collection date; do not label historical results as current health. No arbitrary expiration interval is introduced.

## Units and qualifiers

Core markers accept mmol/L and mEq/L, factor 1 for these monovalent electrolyte equivalents. Do not generalize that factor to calcium. Calcium accepts mmol/L or mg/dL; multiply mg/dL by `0.2495`, including its reference limits. Retain original precision; classify before rounding. Unsupported units stay visible with `unsupported_unit`.

Support exact `=` and qualifiers `<`, `<=`, `>`, `>=`. Preserve bounds as intervals, never replace them with the printed limit or a midpoint. For an exact value x and reference [L,U], classify `low` when x<L, `high` when x>U, otherwise `within_reference` (inclusive endpoints).

For a bound, classify only if the entire positive-valued interval lies in a single category:

- `<b` is definitely low when b<=L; `<=b` is definitely low when b<L.
- `>b` is definitely high when b>=U; `>=b` is definitely high when b>U.
- All other one-sided bounds are `indeterminate_bound`. None is definitely within a finite reference interval.

Unrecognized qualifiers, impossible bounds and invalid limits produce observation-level errors. Classification never changes the source laboratory flag. If a source low/high flag conflicts with the derived category, add `source_flag_conflict`, preserve both, and prevent an all-within-reference summary. A source critical flag is always prominent, including when classification is unavailable or the numerical value conflicts. Do not derive new critical thresholds in v0.1; absence of a source critical flag is not evidence that a value is noncritical.

## Coverage and panel summary

Four core markers are expected. Report separate `present_count`, `interpretable_count`, `expected_count: 4`, `missing_markers`, and `uninterpretable_markers`. Present means a selected record exists, including an invalid record; interpretable means a trustworthy derived `low`, `within_reference`, or `high` category exists. Coverage is not confidence or a percentage of health.

Use the selected core observations only for `panel_status`, with this priority:

1. `source_critical_flag`: any core source critical flag, even on an otherwise unusable record.
2. `source_flag_conflict`: any core conflict between source and derived interpretation.
3. `outside_reference`: any core derived low/high or source low/high flag. Label the basis explicitly when only a source flag is available.
4. `all_within_reference`: all four core markers interpretable and within range, from the same selected collection, with no conflicting/abnormal source flags.
5. `partial`: at least one core interpretable result or recognized source within-reference flag, but conditions above not met.
6. `unavailable`: otherwise.

Summary priority affects the headline only: return all findings and coverage even when multiple conditions apply. Recognize explicit source flags `low`, `high`, `within_reference`, `critical_low`, `critical_high`, `critical`; preserve other raw flags as `unmapped_source_flag` and block an all-within-reference summary until mapped. A partial panel with one abnormal value is `outside_reference` plus incomplete coverage, never reassuring `partial` alone. Optional calcium notices are collected at domain level without rewriting core `panel_status`.

## Result contract and dashboard text

Return strict JSON, an immutable-input implementation, `model_version`, `domain_score: null`, `domain_aggregation_status: not_defined_reference_summary_only`, `panel_status`, `coverage`, ordered `reasons`, `notices`, `observations`, and `context_observations`. Each observation includes `score: null`, `reference_status`, `classification_basis` (`derived`, `source_only`, `unavailable`), provenance, source flags, and errors. Source-only flags do not increment `interpretable_count`. `reference_status` is one of `low`, `within_reference`, `high`, `indeterminate_bound`, `unavailable`; a separate source-only flag must not be passed off as derived comparison.

Suggested consumer copy:

- Complete within-range panel: “All four electrolyte results are within the reference ranges on this report.”
- Incomplete panel: “Some electrolyte results or reference information are missing. Available results are shown below.”
- Abnormal: “One or more results are outside the laboratory reference range. Review the flagged results with your healthcare professional.”
- Always: “These results describe the sample collected on [date]. They do not measure stability over time.”

Use a status card and marker range displays, not a score gauge or percentage of markers labeled healthy. Preserve individual report warnings and critical flags; carry through report instructions when supplied. This prototype does not replace a laboratory critical-result notification process. Do not generate diagnoses or supplement/medication recommendations.

## Acceptance cases for stage 2

The intervals below are **synthetic test fixtures**, not clinical defaults. Unless varied, use one valid selected chemistry specimen, known applicable ranges, exact results, and no source warnings.

| Case | Expected behavior |
|---|---|
| Na 140 [135,145], K 4 [3.5,5], Cl 102 [98,107], CO2 25 [22,29], all mmol/L | `all_within_reference`, 4/4 interpretable, all scores null |
| K equals 3.5 or 5 | Within reference; no midpoint reward |
| K 3.49 or 5.01 | Low or high; `outside_reference` |
| K 5.5; other markers missing | `outside_reference`, 1/4 coverage |
| CO2 absent; other three within range | `partial`, missing CO2; no synthetic value |
| K <3.5 / <=3.5 | Low / indeterminate bound |
| K >5 / >=5 | High / indeterminate bound |
| K <4 or >4 | Indeterminate bound |
| K 4 mEq/L with matching range | Same classification as 4 mmol/L |
| Total calcium 10 mg/dL, range [8,11] mg/dL | Normalize to 2.495 and [1.996,2.7445]; within range, no core coverage change |
| Applicable range missing, reversed, unit incompatible or applicability unknown | No derived category; source flags retained |
| K hemolysis marked as affecting result | K comparison unavailable; report warning remains visible |
| Source critical K flag with invalid value | Critical headline; invalid record preserved |
| Source high K flag but derived in-range K | Conflict headline; both retained |
| Three core results within range; fourth only source normal flag | Partial; fourth does not increment interpretable count |
| All core results in range; calcium critical flag | Core all-within-reference plus prominent domain-level calcium warning |
| Mixed specimen dates, duplicate unselected values, or future date | No fabricated complete panel; selection/date reasons |
| Pediatric or pregnant person with applicable laboratory interval | Reference comparison allowed; no adult range substitution |
| NaN, infinity, Boolean, negative, zero or missing value | Explicit errors/missing reasons; no crash or non-JSON number |

Also test result immutability, strict JSON, unknown flags, boundary behavior before display rounding, preserved notices when multiple reasons apply, and unchanged other-domain outputs when integrating later.

## Subsequent behavior check

Completed 2026-09-24: [stage 3 report](nhanes_inventory/system_stability_v01_evaluation.md), with reproducible extraction/evaluation scripts, JSON/CSV outputs and eight adapter/evaluation tests. The requirements below are retained as the original scope. Public data supports descriptive coverage and concentration checks; missing dates and applicable intervals prevent participant-level reference interpretation. The runtime parameters remain unchanged; their `local_inventory_only_codebook_and_applicability_review_pending` research-candidate note records the stage-1 snapshot, superseded by this report's source review.

The local inventory lists `BIOPRO_D.LBXSNASI`, `LBXSKSI`, `LBXSCLSI`, `LBXSC3SI`, and calcium `LBXSCA`/`LBDSCASI`. This confirms local inventory entries only. Stage 3 must verify CDC codebooks, methods, age coverage and survey weights before use. Determine whether patient-applicable reference limits and specimen dates exist; do not invent them to obtain full runtime results. Any externally chosen research intervals must be separately versioned and reported as sensitivity analyses, not silently installed as customer defaults. [Local inventory](nhanes_inventory/variable_dictionary.md).

## Decision log — 2026-09-24

| Decision | Reason / boundary |
|---|---|
| Four chemistry markers define the first release | Coherent electrolyte panel, bounded implementation scope |
| Reference summary with null points | Reviewed sources support interpretation, not a wellness curve or weighting scheme |
| No range-width-normalized penalties | Equal fractions of different lab ranges do not establish equal clinical severity |
| Applicable report ranges; no default intervals | Preserves patient/laboratory context and avoids adult fallback for children |
| Calcium optional and separate | Different analytes and interpretation context; does not silently change core coverage |
| CBC outside scope | Broadening into blood-cell function requires a separate specification |
| Flags cannot be averaged away | A single concerning result remains visible on incomplete or otherwise normal panels |
| No temporal claims | A single collection cannot establish persistence or resilience |

This is a focused source review, not exhaustive clinical validation. A future numerical index needs an explicit target, evidence for its anchors, and behavior evaluation. The present specification is implementable as a useful categorical dashboard domain without waiting for that research.
