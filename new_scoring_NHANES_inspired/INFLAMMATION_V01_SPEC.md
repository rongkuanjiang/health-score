> Update 25 September 2026: inflammation now uses the provisional v0.2 fixed-core hs-CRP/WBC domain total. See [current specification](INFLAMMATION_V02_SPEC.md). Earlier marker-only/null-total descriptions below are historical. Nutrition and system stability are unchanged.

# Inflammation v0.1 — implementation specification

Update 2026-09-24: stage 4 is implemented in the shared [dashboard](DASHBOARD_README.md), using these unchanged rules. Automated engine, HTTP and DOM checks pass; desktop/mobile visual review remains outstanding. Earlier stage-status text below is retained as a historical checkpoint.

Prepared 2026-09-24. **Stages 1-3 complete: preliminary specification, tested engine and descriptive behavior evaluation, not a clinically validated score.** See [engine usage and verification](INFLAMMATION_ENGINE_README.md) and [behavior report](nhanes_inventory/inflammation_v01_evaluation.md). Third domain, selected by the user. No deep learning. Dashboard integration is next. Parameters: [inflammation_v01_parameters.json](inflammation_v01_parameters.json). Decisions are recorded below.

## Meaning and first-release scope

Use **Inflammation markers** as the domain heading and **hs-CRP marker score** as the numerical component label. The component describes one blood measurement through an experimental 0–100 curve; it is not a measure of total inflammation, immune strength, disease probability or cardiovascular risk. A low CRP does not exclude inflammatory disease. [MedlinePlus CRP interpretation](https://medlineplus.gov/ency/article/003356.htm).

Return `domain_score: null`, `domain_aggregation_status: limited_marker_coverage`; show the available hs-CRP component. Do not silently promote one marker to a comprehensive domain score. CBC-only reports remain useful as observations but return **Insufficient information for the hs-CRP score**. Missing hs-CRP is expected on routine panels; this specification does not require customers to obtain additional testing.

| Input | Role | Metadata |
|---|---|---|
| High-sensitivity CRP | Sole scored component, conditional on eligibility | Value, unit, qualifier, assay designation, date and report ID |
| Standard CRP / CRP of unknown sensitivity | Context only | Preserve assay identity, lab flags, limits, units and date |
| WBC, absolute neutrophils, absolute lymphocytes | Context only; no points or combined penalty | Applicable lab ranges, flags, units and dates |
| ESR, other differential counts | Optional displayed context | Original result and laboratory interpretation |

Standard CRP and hs-CRP measure the same protein with different analytical sensitivity; do not substitute a conventional assay into a low-concentration scoring curve. [MedlinePlus CRP test](https://www.medlineplus.gov/lab-tests/c-reactive-protein-crp-test/). WBC can be high or low for different reasons and cannot establish a diagnosis alone. Our decision is therefore to preserve CBC flags without an inflammation curve, neutrophil-to-lymphocyte ratio score, or inferred hs-CRP. [MedlinePlus WBC](https://medlineplus.gov/lab-tests/white-blood-count-wbc/).

## Evidence boundaries

The historical CDC/AHA statement describes hs-CRP bands below 1, 1–3, and above 3 mg/L in cardiovascular assessment, emphasizes stable measurements, and recommends further assessment and repeat measurement for results above 10 mg/L. These are not whole-body wellness categories. [CDC/AHA statement, 2003](https://www.ahajournals.org/doi/pdf/10.1161/01.cir.0000052939.59093.45).

The ACC's current explanatory article identifies **hs-CRP >=2 mg/L** as a cardiovascular risk-enhancing finding. Keep this separate from the prototype's point curve and do not calculate cardiovascular risk or treatment recommendations from it. [ACC, December 2025](https://www.acc.org/Latest-in-Cardiology/Articles/2025/12/01/01/Prioritizing-Health-hsCRP). The linked 2025 JACC statement's full text could not be retrieved during this review; the directly accessible ACC article supports this threshold. This is a focused source check, not an exhaustive clinical review.

Every point assignment, interpolation rule, eligibility gate and aggregation decision below is **our provisional modeling choice**, not an endorsed clinical scoring system.

## Eligibility, context and observation selection

- Require finite age >0 at collection. Points only at age >=18; younger users retain observations with `pediatric_points_not_defined`. Age >=85 gets `older_age_limited_evidence`; no age or sex adjustment of points. These domain-specific choices do not inherit metabolism's experimental pediatric extension.
- Pregnancy status must be `not_pregnant` or `not_applicable`; `pregnant` or `unknown` withholds points. Never infer pregnancy eligibility from gender.
- Use `acute_context: absent | present | unknown`, referring to illness, infection, injury, surgery or an inflammatory flare **around collection**. `present` withholds points; `unknown` withholds points as `acute_context_unknown`. Ask this in plain language, without requiring users to diagnose the cause. Do not invent a fixed recovery interval.
- Record `chronic_inflammatory_condition: present | absent | unknown` and `inflammation_affecting_treatment: present | absent | unknown`. A reported condition or treatment adds a prominent interpretation notice, not a medication correction or automatic exclusion. Unknown produces a limitation notice. Do not instruct users to stop medication.
- Require `assay_type: hs_crp` or verified research equivalence, and a report ID and valid collection date. Missing assay identity/date withholds points. Preserve imported assay evidence; do not ask consumers to certify laboratory performance. `reliability: unreliable` withholds; `unknown` permits points with a notice when assay identity is established.
- Require one explicitly selected observation. Do not choose the lowest result, average different dates, or merge duplicate CRP and hs-CRP values. Ambiguous selection returns `selection_required`. Repeated measurements remain independently visible; automatic baseline/trend calculation is outside v0.1.
- Reject invalid or future dates relative to an explicit evaluation date. Display collection date and elapsed days, with no arbitrary expiry rule. Do not describe an old result as current health. No fasting gate is required.

Single measurements must display `single_measurement_not_persistent_inflammation`; the prototype cannot establish chronicity. Unknown context must never be converted to a negative answer by an importer or sample profile.

## Units, values and bounds

Canonical CRP unit: mg/L. Convert mg/dL by multiplying by 10. Support only these units initially. Store original and normalized values. Reject Boolean, nonnumeric, negative, nonfinite and exact zero CRP values; zero is a mathematical curve endpoint, not assumed analytical absence. Unsupported units or invalid inputs affect that observation and must not erase other valid observations.

Support qualifiers `=`, `<`, `<=`, `>`, `>=`. Limits must be finite and positive. Treat censored values as intervals, never exact measurements or substituted midpoints. For bounds, return points only if **every possible nonnegative value lies within the same defined constant plateau**: `<1` or `<=1` mg/L gives 100 with `scored_from_bound`. `<2` returns null, `bounded_result`; `>10` returns null, `above_scoring_range`. All other non-plateau bounds return null; v0.1 does not calculate score envelopes. A bound potentially crossing 10 is never silently truncated to 10.

Only issue a threshold notice as established when the whole interval supports it. Otherwise use `threshold_indeterminate_from_bound`. Preserve source lab flags even when their range differs from the cardiovascular threshold. Exact or definitely >10 mg/L results remain visible with a clinical-review notice; they are not zero-point scores or proof of acute infection.

For CBC context, support `10^9/L` and `10^3/uL` as numerically equivalent absolute-count units, and `cells/uL` divided by 1000. Preserve differential percentages as percentages; do not interpret them as absolute counts. Context reference limits must be finite, ordered, in matching units and applicable to the person/assay before deriving low/high flags. Otherwise retain supplied flags and mark `reference_interpretation_unavailable`. Never assume a universal WBC reference interval.

## Provisional hs-CRP curve

For an eligible, exact measurement with `0 < x <=10` mg/L, interpolate linearly:

| hs-CRP (mg/L) | Points | Rationale |
|---|---:|---|
| 0 to 1 | 100 | Plateau avoids rewarding ever smaller low values; 0 is endpoint only |
| 2 | 80 | Visible anchor at the cardiovascular risk-enhancer threshold |
| 3 | 60 | Historical cardiovascular band boundary |
| 10 | 20 | End of the prototype scoring interval; the 20-point assignment is arbitrary |
| >10 | null | Outside this limited baseline-oriented curve; preserve result and notice |

No extrapolation above 10. The 3-to-10 slope is -40/7 points per mg/L. The positive-to-null transition is deliberate; downstream code must distinguish a withheld result from a score of zero. A score of 100 only means the top of this curve. Do not label it “no inflammation” or “healthy immune system.” At >=2, preserve the risk-enhancer context notice even when points appear favorable; no patient-level cardiovascular risk label is generated.

Do not average the component with WBC, ESR, standard CRP, or other domains. Optional tests never alter the curve or its denominator.

## Result contract for stage 2

Follow existing engine conventions: immutable input, strict JSON, model version, raw/provenance data, normalized observations, unrounded score, one-decimal half-up display, status, reasons, notices and coverage. This is a local engine design, not the final integration API.

- `components.hs_crp`: `score`, `display_score`, `status` (`scored`, `scored_from_bound`, `unavailable`), `reasons`, `notices`, `observation_id`.
- Global `status`: `component_available` if numerical points exist; otherwise `context_only` if at least one valid observation exists; otherwise `unavailable`. Invalid records remain visible with errors.
- `domain_score: null` always; missing/withheld component scores are also null, never zero.
- `coverage`: separate `hs_crp_present`, `hs_crp_usable`, `missing_requirements`, `context_markers_present`. Availability is not a confidence percentage. Always state limited marker coverage.
- Collect all applicable reasons in a stable order: invalid input, ambiguous selection, age/pregnancy, assay/reliability, specimen metadata, acute context, bound/range. Evaluate independent notices even when a score is withheld.

Minimal dashboard text: “This experimental score describes your hs-CRP result at collection. It does not measure all inflammation or diagnose its cause.” Missing-data text: “A suitable hs-CRP result and collection context are needed for this score. Available blood-cell results are shown separately.” Lab flags and above-range notices must remain visible alongside high points.

## Acceptance cases for stage 2

Unless varied: age 40, not pregnant, acute context absent, valid selected hs-CRP assay/report/date and exact value.

| Input | Expected result |
|---|---|
| 0.5 / 1 / 2 / 3 / 10 mg/L | 100 / 100 / 80 / 60 / 20 points |
| 1.5 mg/L | 90 points |
| 6.5 mg/L | 40 points |
| 0.2 mg/dL | Same result and notice as 2 mg/L |
| 10.0001 mg/L | Null; above scoring range, observation retained |
| hs-CRP <1 mg/L | 100; scored from bound, never claim exact concentration |
| hs-CRP <2 / >3 / >=10 mg/L | Null; bound prevents exact scoring |
| hs-CRP >10 mg/L | Null; definitely above scoring range |
| Standard CRP 0.5 mg/L; normal CBC | Context only; no fallback points |
| Missing hs-CRP; WBC supplied | Context only; insufficient information |
| hs-CRP 0.5 with abnormal WBC flag | 100 component points; WBC flag remains prominent |
| Age 17.99 / 18 / 85 | Withheld / eligible / eligible with older-age notice |
| Acute context present or unknown | Withheld with distinct reason |
| Pregnancy present or unknown | Withheld |
| Chronic condition/treatment present, no acute flare | Points with context limitation notice |
| Missing date/assay identity; unreliable result | Withheld; explicit reason |
| Exact 0, negative, Boolean, NaN, infinity | Invalid measurement; no points |
| Multiple unselected results | Selection required; no favorable-result selection |

Also check all anchors and just either side, monotonicity only within the defined interval, conversion parity, bounds in mg/dL, strict serialization, no mutation and existing-domain regression cases. Stage 2 implements these requirements; see the engine guide for the completed verification record.

## NHANES preparation for stage 3

The local [inventory](nhanes_inventory/variable_dictionary.md) lists `CRP_D.LBXCRP` plus `CBC_D.LBXWBCSI`, `LBDNENO`, `LBDLYMNO`. CDC reports CRP in mg/dL and marks 0.01 as an at-or-below-detection fill value. Convert units once and preserve censoring; do not score that fill as an exact measurement. Recover the actual detection interval and assay sensitivity from the laboratory documentation before admitting a research-equivalent hs-CRP route. [CDC CRP_D codebook](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/CRP_D.htm).

Verify raw-file availability, assay metadata, demographic joins, eligibility mappings, MEC weights, strata and PSU before evaluation. Do not reuse fasting-subsample weights automatically. Missing collection dates or acute-context data must remain missing: report full-engine eligibility separately from a clearly labeled numerical curve diagnostic with assumed eligibility. Inspect >10 exclusions, detection-limit handling, missingness and age strata; do not claim representative population estimates without the proper design. Descriptive distributions cannot validate the chosen points or prove clinical accuracy.

## Decision log — 2026-09-24

1. Selected inflammation as domain 3 following user confirmation; no new dashboard behavior in stage 1.
2. Chose one hs-CRP component and no broad domain total because available markers do not justify a comprehensive inflammation score.
3. Kept CBC and optional markers as context; avoided correlated penalties and low-WBC rewards.
4. Kept conventional and high-sensitivity assay roles distinct; no assumption that routine bloodwork contains hs-CRP.
5. Proposed a simple transparent curve to unblock implementation; all point values remain experimental, with sensitivity review needed in stage 3.
6. Withheld baseline-oriented points for >10 and acute/unknown collection context instead of interpreting transient illness as a wellness score.
7. Limited points to adults and nonpregnant eligibility; these are scope decisions, not evidence that other groups cannot have CRP measured.
8. Retained one-observation scoring with an explicit chronicity limitation; no automatic repeat-test averaging or treatment advice.

Stages 1-3 are complete. The reusable engine and acceptance checks preserve the specified scoring rules. The [stage-3 behavior report](nhanes_inventory/inflammation_v01_evaluation.md) separates full-engine abstention from assumed-eligibility curve diagnostics, with censoring and endpoint sensitivity analyses. Exact detection bounds are not available by calibrator lot, so detection-limit fills are excluded from primary diagnostics and retained in a separate plateau sensitivity. Pregnancy eligibility is not inferred from gender or skipped questions. Next is dashboard work (stage 4) and review. Shared integration packaging stays deferred. Clinical review of the provisional curve remains outstanding and is not represented as completed.
