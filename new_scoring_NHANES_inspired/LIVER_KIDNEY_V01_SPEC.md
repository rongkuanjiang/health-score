> Current organ-stress model (25 September 2026): v0.2 now combines eGFR (50%), ALT (30%) and ALP (20%) into one domain score. AST and bilirubin are optional context. See [the current specification](ORGAN_STRESS_V02_SPEC.md) for inputs, curves, missing-data rules and Canadian source rationale. The v0.1 descriptions and evaluation results below are historical and do not validate v0.2.

# Liver and kidney markers v0.1 — implementation specification

Prepared 2026-09-24. Stages 2 and 3 are complete: [Python engine and acceptance tests](LIVER_KIDNEY_ENGINE_README.md) and [NHANES descriptive evaluation](nhanes_inventory/liver_kidney_v01_evaluation.md). The evaluation preserves the kidney date gate and labels its date-neutral numerical analysis separately. Dashboard work remains; the model is not clinically validated. The shared integration API (original step 5) stays deferred until after the other domains.

## Meaning and scope

Display two components: **Kidney filtration estimate** and **Liver enzyme pattern**. Return `domain_score: null` with `aggregation_not_defined`; do not average the components or substitute one for the other. Neither is a complete assessment of organ health. A score of 100 means the top of this prototype's curve, not absence of disease. Points are not percentages of function or estimated disease probabilities.

The companion `liver_kidney_v01_parameters.json` records the proposed numerical rules. Published measurements, equation coefficients and interpretation boundaries are distinguished from our point assignments. All point assignments, interpolation, age policies and grouping choices below are modeling decisions pending behavior checks and review.

## Inputs and coverage

| Input | Role | Required metadata |
|---|---|---|
| Laboratory eGFR | Preferred kidney route when supplied and supported | Value, qualifier, indexed unit, equation identifier, specimen date/report ID |
| Creatinine | Alternative eGFR calculation route; never an independent score | Value, unit, calibration provenance, specimen date/report ID |
| Age and equation sex | Equation inputs | Age in years at specimen collection; male/female coefficient choice from the clinical record, never inferred from name or gender identity |
| Height | CKiD U25 calculation input | cm or m, measured near the specimen date |
| ALT and AST | One grouped liver component | Each value, U/L, applicable laboratory lower and upper reference limits, report/date |
| ALP, bilirubin, GGT, albumin, BUN, uric acid, UACR, cystatin C | Optional context only | Original values, units, qualifiers, dates and lab flags/ranges |

Context tests do not silently alter points. Show supplied abnormal lab flags beside component results, including when points are high. Missing UACR is explicitly reported as incomplete kidney-damage coverage; missing optional tests are not zero or evidence of normality. This release does not calculate a second eGFR from cystatin C.

NIDDK identifies eGFR and urine albumin as complementary kidney measures. [NIDDK kidney assessment](https://www.niddk.nih.gov/health-information/professionals/advanced-search/quick-reference-uacr-gfr).

Coverage reports availability and usability separately for kidney, ALT/AST, and context; it is not a confidence percentage. Return each missing or unusable input and its reason.

## Eligibility and specimen rules

- Accept finite positive ages, including fractional years. Reject Boolean, nonnumeric and nonfinite numbers. No upper age cutoff; ages 85+ carry `older_age_limited_evidence`.
- Require pregnancy status `not_pregnant` or `not_applicable` for points. `pregnant` and `unknown` withhold both component scores in this release. This is a conservative prototype scope restriction, not a diagnostic rule.
- Reported dialysis or suspected/known acute kidney injury withholds kidney points and locally calculated eGFR; retain laboratory observations with an explanation. Unknown status produces a limitation notice, never an invented negative answer.
- Under 18: support reported observations and an appropriate eGFR estimate, but withhold numerical wellness points for both components (`pediatric_points_not_defined`). Adult eGFR equations must never be applied below 18. The metabolism age extension does not establish suitability for this domain.
- Require matching nonempty report IDs for ALT and AST, and matching dates when dates are supplied. A missing date requires explicit same-snapshot confirmation; mismatched dates block the grouped liver score. Kidney can use its own dated report and remain independently available.
- Reject malformed or future dates. Display specimen age; this version does not invent an expiration interval or describe older results as current health.
- Preserve laboratory reliability metadata. A result marked unreliable is displayed but not scored. Unknown reliability gets a notice. Calibration and reference-range applicability are extracted from reports or supplied in a developer/import workflow, not technical questions for consumers.

## Kidney calculation

Prefer supplied eGFR to local calculation. Never silently replace an invalid, unsupported or bounded supplied eGFR with a more favorable calculation. An explicitly selected creatinine route may be used independently, with provenance visible. Never average routes.

Supported reported equation identifiers initially: `ckd_epi_2021_creatinine` (18+), `ckd_epi_2021_creatinine_cystatin_c` (18+), and `ckid_u25_creatinine` (1–25 inclusive). Unknown/other equations remain displayed with `unsupported_equation`, without points. Accept only indexed eGFR in `mL/min/1.73m2` (including a documented Unicode alias), not unindexed mL/min.

For local adult calculation (18+), use standardized creatinine in mg/dL:

`eGFR = 142 * min(SCr/k, 1)^a * max(SCr/k, 1)^(-1.200) * 0.9938^age * f`

Female: `k=0.7, a=-0.241, f=1.012`; male: `k=0.9, a=-0.302, f=1`. Convert creatinine from µmol/L by dividing by 88.4. Require documented IDMS traceability or a documented research calibration; otherwise return `calibration_unknown`. eGFR is an estimate; combined creatinine/cystatin C estimation can be more accurate. [NIDDK adult equations](https://www.niddk.nih.gov/research-funding/research-programs/kidney-clinical-research-epidemiology/laboratory/glomerular-filtration-rate-equations/adults).

For ages 1–17 use CKiD U25; ages 18–25 may explicitly select it, while the default adult route remains CKD-EPI. Preserve route in longitudinal displays and warn at route changes. Below 1, local calculation is unsupported. Require height, sex coefficient and supported creatinine calibration; record assay method and warn when enzymatic measurement is not confirmed.

`eGFR = k * height_m / SCr_mg_dL`

| Age | Female k | Male k |
|---|---|---|
| 1 to <12 | 36.1 × 1.008^(age−12) | 39.0 × 1.008^(age−12) |
| 12 to <18 | 36.1 × 1.023^(age−12) | 39.0 × 1.045^(age−12) |
| 18 to 25 inclusive | 41.4 | 50.8 |

CKiD U25 was developed for pediatric/young-adult CKD; equation applicability is distinct from validation of wellness points. [NIDDK pediatric/young-adult equations](https://www.niddk.nih.gov/research-funding/research-programs/kidney-clinical-research-epidemiology/laboratory/glomerular-filtration-rate-equations/children-adolescents-young-adults).

### Provisional adult filtration points

Piecewise-linear anchors `(eGFR, points)` are `(0,0), (15,10), (30,30), (45,50), (60,75), (90,100)`. Plateau at 100 above 90; no extra reward for very high eGFR. The zero anchor defines the curve's limit, not an accepted exact zero laboratory input. Reject exact nonpositive values and nonfinite computed results.

The eGFR boundaries are informed by published GFR categories; **the points and linear interpolation are ours**. A single measurement cannot establish chronic kidney disease; an eGFR of 60–89 alone does not establish CKD. Avoid disease-stage labels and age-percentile claims. [National Kidney Foundation eGFR interpretation](https://www.kidney.org/kidney-topics/estimated-glomerular-filtration-rate-egfr).

Preserve `=`, `>`, `>=`, `<`, `<=` qualifiers. Return a single score only when the entire possible interval lies on a constant plateau (e.g. `>=90` or `>90`: 100 with `scored_from_bound`). `>60` returns no point estimate, plus the conservative score envelope `[75,100]`, `bounded_result`, and original qualifier. All other non-plateau bounds return an envelope from the monotone curve, never a midpoint or an exact eGFR. Envelopes contain the range but need not encode open endpoints. Bounds at nonpositive values are unsupported initially. A low-eGFR notice is issued only when the bound establishes it; otherwise say interpretation is limited by the bound.

## Liver enzyme component

Use applicable laboratory limits, not a universal adult cutoff. Require finite `0 <= lower < upper`, positive exact ALT/AST, and verified range applicability to the person's age/sex and assay. Unknown range applicability or missing limits withholds that marker's points. Support U/L and IU/L as aliases only; other units remain unsupported for this release.

For each marker define `r = value / upper_limit`. Values below the lower limit return `below_reference_range_not_scored`; they are not rewarded. Within the reference interval, assign 100. Above it, interpolate linearly through `(r, points) = (1,100), (2,75), (5,40), (10,15), (20,0)`; plateau at 0 above 20. These are deliberately provisional display anchors, not validated injury-severity or risk estimates. No liver score is issued for censored ALT/AST in v0.1.

Require both ALT and AST to be scorable. The grouped score is `min(ALT_points, AST_points)`: one abnormal enzyme is not diluted by the other, and two correlated elevations are not added as separate penalties. Label this **Liver enzyme pattern**, not liver function. Preserve both measurements and explanations. Missing one enzyme leaves available marker information visible, with no grouped score.

ALT/AST are injury-associated markers; AST also has non-liver sources, and elevation magnitude does not measure the extent of liver injury. Normal enzymes do not establish absence of liver disease. Other liver-related observations remain visible context; this limited component does not evaluate cholestasis, synthetic function or fibrosis. [AASLD liver-test interpretation](https://www.aasld.org/liver-fellow-network/core-series/back-basics/how-approach-elevated-liver-enzymes).

## Output behavior and notices

Use the metabolism engine's conventions: immutable input, strict JSON-compatible output, raw observations/provenance, normalized values, status, reasons, notices, model version, unrounded score and one-decimal half-up display. This describes the local Python contract, not a supported integration API.

Return `components.kidney` and `components.liver`, each with `score`, `display_score`, `status`, `reasons`, `flags` and coverage. Preserve marker-level information. Withheld scores are null, never zero. Global `status` is `components_available`, `partial` or `unavailable`, according to whether two, one or zero numerical components exist. Domain aggregation remains unavailable in every case.

Always explain limited organ coverage and preliminary points. Add notices for laboratory out-of-range flags, eGFR below 60 (and a distinct below-15 notice), each ALT/AST above its applicable upper limit, missing UACR, unknown reliability, age limitations and bounded results. Notices survive high scores. Refer abnormal findings to clinical interpretation without turning these points into diagnoses, treatment advice or a triage system.

## Acceptance cases for stage 2

Unless stated otherwise: adult, eligible, valid metadata, supported reported equation and matched liver report; laboratory reference interval for both enzymes 5–40 U/L.

| Case | Expected behavior |
|---|---|
| eGFR 90; ALT 20; AST 30 | Kidney 100; liver 100; no domain total |
| eGFR 45; ALT 20; AST 30 | Kidney 50; liver 100; reduced-filtration notice retained |
| eGFR 75; ALT 80; AST 40 | Kidney 87.5; ALT 75; AST 100; liver 75 |
| ALT 200; AST 400 | Marker points 40 and 15; grouped liver 15 |
| ALT 4; AST 30 | ALT unscored below range; liver withheld |
| Missing AST or missing ALT reference limits | Liver withheld; usable kidney result preserved |
| Reported eGFR >60 / >=90 | No exact points plus [75,100] / 100 with bound provenance |
| Creatinine 88.4 µmol/L versus 1 mg/dL | Identical computed eGFR for the same equation/person |
| Male 18, height 1.8 m, creatinine 1, explicit U25 | eGFR 91.44; adult points 100 |
| Male 12, height 1.5 m, creatinine 0.6, U25 | eGFR 97.5; pediatric points withheld |
| Age <1, creatinine route | Calculation unsupported, no adult-equation fallback |
| Unknown equation sex, creatinine route | Missing equation input; no imputation |
| Pregnancy / unknown pregnancy | Both component scores withheld |
| Dialysis or acute kidney injury | Kidney calculation/points withheld; liver independently eligible |
| Unsupported reported eGFR plus valid creatinine | No silent fallback; route must be explicitly selected |
| High UACR lab flag with eGFR >=90 | Flag prominently retained; no claim of healthy kidneys |
| Different ALT/AST dates, invalid units, bool, NaN, infinity | Explicit unscorable reason; never a fabricated result |

Also test curve continuity, every anchor, ages 1/12/18/25 and just outside, under-18 reported-equation mismatch, no input mutation, strict serialization, and unchanged metabolism regression cases.

## NHANES evaluation preparation

Local inventory confirms ALT `LBXSATSI`, AST `LBXSASSI` and creatinine `LBXSCR` in `BIOPRO_D`. CDC recommends standardizing 2005–2006 creatinine as `-0.016 + 0.978 * original_mg_dL`. Apply once in the research adapter, preserving original and corrected values, never to arbitrary customer laboratory data. [CDC chemistry documentation](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/BIOPRO_D.htm).

Stage 3 must verify whether the local file is uncorrected, document the assay/reference limits needed for liver scoring, join demographics by SEQN and verify MEC weights for this nonfasting chemistry sample. Do not reuse fasting lipid weights. If suitable laboratory reference limits cannot be recovered, report liver coverage as unavailable; separately labeled threshold sensitivity experiments cannot masquerade as the specified lab-relative score. Report age top-coding and pregnancy mappings. Do not claim population estimates from naive unweighted means or clinical validation from these checks.

## Decision log and remaining work

1. Replaced the historical Organ Stress naming with a limited liver/kidney marker description, following the current next-domain plan.
2. Chose two separate component scores; combined weighting is undefined because compensation has not been justified.
3. Grouped ALT/AST by the lower points; this is a prototype choice to test, not a clinical recommendation.
4. Used plateau curves so lower enzymes and higher eGFR do not earn unlimited rewards; no point calibration against outcomes has occurred.
5. Supported pediatric estimation with its own equation, while leaving pediatric wellness points undefined. This domain does not inherit adult-curve extrapolation from metabolism.
6. Kept optional biomarkers visible without quietly changing points or assuming their availability.

Stages 2 and 3 are complete; see the engine guide for concrete field names and metadata rules and the evaluation report for source verification, coverage, distributions and limitations. The original stage-3 requirements above remain the evaluation rationale. Next: add and verify the dashboard section (stage 4). The source check and design do not constitute clinician approval. No numerical scoring rules were changed.
