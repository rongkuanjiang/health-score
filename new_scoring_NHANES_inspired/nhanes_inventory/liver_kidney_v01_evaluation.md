# Liver/kidney v0.1: NHANES 2005-2006 behavior evaluation

Completed 2026-09-24. Model `liver-kidney-v0.1-provisional`. Descriptive behavior check, **not clinical validation**. No numerical parameters changed.

## Main findings

- The primary group has **4770** pregnancy-eligible adults with examination age available and positive MEC weights.
- Kidney numerical diagnostics are available for **4458**: weighted mean **94.88**, median **100.00**, **63.65%** at 100. These isolate the equation and point curve; they are **not full-engine scores** because public specimen dates are unavailable.
- Full-engine liver scores are available for **4380** in that primary group: weighted mean **98.24**, median **100.00**, **84.98%** at 100.
- The full engine correctly issues **zero kidney scores** without specimen dates. No dates, negative dialysis answers or missing laboratory flags were fabricated. No combined domain total exists.
- Below-reference enzyme results withhold liver points for **23** otherwise scorable eligible adults, including the separate top-coded group. The effect is quantified below; the abstention policy was not changed.

## Data and source verification

The local BIOPRO_D XPORT is byte-identical to the CDC download retrieved on 2026-09-24: SHA256 `6de916025812b78db1b81e62f77d94d83ed8b046d9d5c8a9d584f7caec120310`. The release documents uncalibrated creatinine and the correction `-0.016 + 0.978 * original mg/dL`. The adapter applies it once to hash-verified raw values and retains both columns. The source assay is Jaffe, not confirmed enzymatic. Chemistry sampling starts at age 12. [CDC chemistry documentation](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/BIOPRO_D.htm).

ALT/AST reference ranges were recovered from page 7 of the cycle-specific method manuals and checked visually. ALT: completed ages 12-20, male 8-36 and female 8-29 U/L; age 21+, male 11-47 and female 7-30. AST: completed ages 12-20, 13-38 U/L; age 21+, 13-33. The adapter's completed-year convention interprets the manuals' 10-20 / >20 bands explicitly; it is separate from the fractional-year eGFR equation. [ALT manual](https://wwwn.cdc.gov/nchs/data/nhanes/public/2005/labmethods/biopro_d_met_alt.pdf#page=7), [AST manual](https://wwwn.cdc.gov/nchs/data/nhanes/public/2005/labmethods/biopro_d_met_ast.pdf#page=7).

**Document discrepancy:** AST page 7 says 2003-2004, while the CDC 2005-2006 methods index links this file and its release-identification page names BIOPRO_D. The chemistry codebook states no equipment, method or laboratory change. We use the linked method's range with this discrepancy recorded; this is a research mapping, not a universal cutoff for customer reports. [CDC methods index](https://wwwn.cdc.gov/Nchs/Nhanes/ContinuousNhanes/LabMethods.aspx?BeginYear=2005).

Downloaded sources, hashes and rendered reference pages are retained in `liver_kidney_sources/`. The extractor checks every local XPORT hash and row count against the prior inventory, rejects duplicate SEQN and unlinked rows, and joins by SEQN. Optional UACR/cystatin C are absent from the selected local files; missing tests are not normal results.

## Cohort, metadata and weights

- Use **WTMEC2YR**, not fasting-subsample weights. The chemistry panel is not a fasting subsample; combining its laboratory data with interview data requires MEC weights. [CDC weighting guidance](https://wwwn.cdc.gov/nchs/nhanes/tutorials/weighting.aspx).
- Use examination months / 12 for age when available. Do not substitute screening age for missing examination age. The public 85+ age is top-coded: its age-85 surrogate is excluded from the primary kidney summaries and analyzed separately at assumed ages 85, 89 and 95. These assumptions are not recovered individual ages. [CDC demographics](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/DEMO_D.htm).
- Pregnancy codes 1/2/3 map to pregnant/not pregnant/unknown. Missing codes map to not applicable only for males or females with screening age >=60, outside the published RIDEXPRG target. Other missing/unknown codes remain excluded. This is a dataset mapping, not an application default.
- KIQ025 code 1 excludes kidney calculation; code 2 is an explicit no within the questionnaire's prior-12-month scope. Missing, skipped, refused and unknown remain unknown. The question targets age 20+ and is conditional; a missing answer is not evidence of no dialysis. Acute kidney injury remains unknown for everyone. [CDC kidney questionnaire](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/KIQ_U_D.htm).
- ALT and AST share the same released BIOPRO_D participant row, supporting an explicit same-panel snapshot assertion and a research bundle ID. Exact collection dates and individual reliability adjudication are unavailable. Reliability stays unknown. Kidney's required-date gate is preserved. Its separate date-neutral diagnostic calls the same engine equation/curve helpers, not a second implementation.
- Means, quantiles and percentages use MEC weights within each stated observed subset. No confidence intervals, significance tests or nationally representative prevalence claims are made. Strata/PSU are retained for future design-based inference. Complete-case selection, age composition and treatment confound subgroup comparisons.

| Cohort step | Unweighted n |
|---|---:|
| demographics_n | 10348 |
| positive_mec_weight_screen_age12plus_n | 6980 |
| exam_age_missing_n | 19 |
| adult_exam_age_or_topcode_n | 5339 |
| adult_pregnancy_eligible_n | 4918 |
| primary_exact_exam_age_eligible_n | 4770 |
| eligible_topcoded_n | 148 |
| full_engine_liver_scored_n | 4508 |
| full_engine_kidney_scored_n | 0 |
| pediatric_n | 1622 |
| pediatric_numerical_estimates_n | 1395 |

Adult pregnancy codes after mapping: `{"not_applicable": 3288, "not_pregnant": 1630, "pregnant": 354, "unknown": 67}`. Adult dialysis mapping: `{"unknown": 5210, "no": 113, "yes": 16}`.

## Component distributions and subgroups

Kidney is a numerical diagnostic only; liver uses the full engine. The final row is separate from the primary population. Neither scores nor subgroup differences are disease probabilities or age-adjusted comparisons.

| Group | Eligible n | Kidney numerical n | Kidney mean | Kidney median | Kidney %100 | Liver n | Liver mean | Liver median | Liver %100 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all_eligible_exact_exam_age | 4770 | 4458 | 94.88 | 100.00 | 63.65 | 4380 | 98.24 | 100.00 | 84.98 |
| male | 2507 | 2343 | 95.46 | 100.00 | 65.26 | 2303 | 97.96 | 100.00 | 83.13 |
| female | 2263 | 2115 | 94.29 | 100.00 | 62.04 | 2077 | 98.52 | 100.00 | 86.84 |
| age_18_to_under_40 | 1998 | 1843 | 99.30 | 100.00 | 89.10 | 1819 | 98.25 | 100.00 | 84.17 |
| age_40_to_under_60 | 1433 | 1361 | 96.10 | 100.00 | 62.18 | 1342 | 97.89 | 100.00 | 83.86 |
| age_60_to_under_85 | 1339 | 1254 | 84.79 | 88.71 | 21.44 | 1219 | 98.87 | 100.00 | 88.54 |
| reported_weak_failing_kidneys | 116 | 91 | 78.84 | 90.03 | 36.07 | 100 | 98.03 | 100.00 | 84.75 |
| reported_no_weak_failing_kidneys | 4102 | 3857 | 95.00 | 100.00 | 62.89 | 3772 | 98.25 | 100.00 | 84.83 |
| 85plus_surrogate_age85_separate | 148 | 133 | 67.35 | 71.39 | 0.00 | 128 | 98.60 | 100.00 | 91.26 |

## Primary score histograms

Percentages use the available component subset, so kidney and liver denominators differ.

| Component | Interval | n | Weighted % |
|---|---|---:|---:|
| kidney_numerical_points | 0 to <25 | 13 | 0.15 |
| kidney_numerical_points | 25 to <50 | 85 | 1.30 |
| kidney_numerical_points | 50 to <75 | 201 | 3.38 |
| kidney_numerical_points | 75 to <90 | 614 | 13.09 |
| kidney_numerical_points | 90 to <100 | 720 | 18.43 |
| kidney_numerical_points | exactly 100 | 2825 | 63.65 |
| liver_score | 0 to <25 | 0 | 0.00 |
| liver_score | 25 to <50 | 14 | 0.26 |
| liver_score | 50 to <75 | 96 | 1.98 |
| liver_score | 75 to <90 | 161 | 3.61 |
| liver_score | 90 to <100 | 400 | 9.17 |
| liver_score | exactly 100 | 3709 | 84.98 |

## Measurement and extreme-value checks

These summaries cover observed values in the primary eligible group; creatinine summaries include reported-dialysis participants whose kidney calculations are withheld.

| Measurement | n | Weighted mean | P05 | Median | P95 | Min | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| raw_creatinine_mg_dl | 4471 | 0.93 | 0.60 | 0.90 | 1.30 | 0.40 | 17.80 |
| corrected_creatinine_mg_dl | 4471 | 0.90 | 0.57 | 0.86 | 1.26 | 0.38 | 17.39 |
| kidney_numerical_egfr | 4458 | 95.79 | 60.18 | 97.65 | 125.76 | 9.99 | 148.24 |
| alt_u_l | 4401 | 25.95 | 13.00 | 21.00 | 52.00 | 7.00 | 217.00 |
| ast_u_l | 4401 | 25.60 | 16.00 | 23.00 | 42.00 | 9.00 | 193.00 |

No point values escaped 0-100 and no nonfinite eGFR entered the analysis. The observed adult liver-score range does not reach the lowest curve anchors, so severe-enzyme tail behavior remains covered by synthetic tests rather than this sample. Extreme original creatinine values were retained; dialysis exclusions were applied independently of their magnitude.

## Missingness and abstention

Reasons overlap; do not add them as mutually exclusive people. Counts below cover pregnancy-eligible adults including top-coded ages.

| Marker | Reason | n |
|---|---|---:|
| alt | missing | 387 |
| alt | below_reference_range_not_scored | 11 |
| ast | missing | 387 |
| ast | below_reference_range_not_scored | 12 |
| kidney numerical | creatinine_missing_or_invalid | 314 |
| kidney numerical | dialysis_outside_scope | 16 |

Optional-context availability: `{"alp": 4604, "bilirubin": 4603, "ggt": 4603, "albumin": 4604, "bun": 4604, "uric_acid": 4604, "uacr": 0, "cystatin_c": 0}`. Missing UACR produces incomplete kidney-damage coverage; no abnormal lab flags were invented from these optional values.

## Sensitivity checks, not alternative recommended models

| Experiment | Field | n | Weighted mean | Min | Max |
|---|---|---:|---:|---:|---:|
| calibration_sensitivity_same_primary_people | uncorrected_points | 4458 | 93.70 | 6.46 | 100.00 |
| calibration_sensitivity_same_primary_people | kidney_numerical_points | 4458 | 94.88 | 6.66 | 100.00 |
| calibration_sensitivity_same_primary_people | calibration_point_delta | 4458 | 1.18 | 0.00 | 4.53 |
| u25_sensitivity_same_people | kidney_numerical_points | 852 | 99.82 | 82.35 | 100.00 |
| u25_sensitivity_same_people | u25_alternative_points | 852 | 97.63 | 72.28 | 100.00 |
| u25_sensitivity_same_people | u25_point_delta | 852 | -2.19 | -16.59 | 0.00 |
| topcoded_age_sensitivity | kidney_numerical_points | 133 | 67.35 | 13.12 | 99.14 |
| topcoded_age_sensitivity | age89_points | 133 | 65.72 | 12.56 | 97.32 |
| topcoded_age_sensitivity | age95_points | 133 | 63.32 | 11.73 | 94.67 |
| age20_reference_boundary_sensitivity | liver_score | 61 | 98.78 | 77.63 | 100.00 |
| age20_reference_boundary_sensitivity | literal_over20_reference_sensitivity | 61 | 99.22 | 72.88 | 100.00 |

The uncorrected-creatinine experiment deliberately omits the required calibration to quantify its effect; only corrected values enter the main analysis. U25 is compared on the same 18-25-year-old people with usable height. Its assay/population limitations remain, and the alternative must never be silently selected because it gives better points. Top-coded age scenarios measure sensitivity to unavailable age, not true within-person changes.

The age-20 reference-band experiment compares the completed-year rule with a literal fractional-age >20 interpretation on the same scorable people aged >20 and <21. It makes the boundary convention auditable without changing the main analysis.

Setting both lower reference limits to zero, solely as a counterfactual, increases liver coverage from 4508 to 4531. Corresponding weighted means are 98.25 and 98.25; these have different denominators. This exposes selection from below-range abstention, not a reason to label low enzymes unhealthy or to change the specified curve.

## Unexpected combinations and dashboard implications

Among 4367 primary participants with both liver points and kidney numerical diagnostics:

- 89 have kidney numerical points of 100 with liver points below 75.
- 249 have liver points of 100 with kidney numerical points below 75.
- 399 have liver points >=90 despite an enzyme above its applicable upper limit.

The 75/90 audit thresholds are modeling checks, not clinical categories. Separate components prevent cross-organ averaging. Marker notices must remain visible even at high point values. High plateau frequencies limit discrimination within the top range; 100 must not mean disease-free. The lower-range abstention needs an understandable dashboard explanation and later review. Dates must remain explicit, and research diagnostics must not be shown as ordinary application scores.

## Auditable public-record examples

Units: creatinine mg/dL; ALT/AST U/L; eGFR mL/min/1.73m2. Kidney points below are date-neutral research diagnostics. These are historical public records, not treatment examples.

| Category | SEQN | Exam age / surrogate | Raw / corrected creatinine | ALT | AST | Kidney numerical points | Liver points | Blockers |
|---|---:|---:|---|---:|---:|---:|---:|---|
| lowest_kidney_numerical_points | 34029 | 50.42 | 5.10 / 4.97 | 57.00 | 48.00 | 6.66 | 77.50 |  |
| lowest_kidney_numerical_points | 31877 | 62.25 | 5.00 / 4.87 | 16.00 | 15.00 | 8.47 | 100.00 |  |
| lowest_liver_points | 32955 | 18.67 | 0.90 / 0.86 | 186.00 | 87.00 | 100.00 | 32.93 |  |
| lowest_liver_points | 31378 | 19.33 | 0.80 / 0.77 | 185.00 | 128.00 | 100.00 | 33.10 |  |
| below_range_abstention | 31587 | 70.42 | 0.80 / 0.77 | 10.00 | 16.00 | 100.00 | unavailable | below_reference_range_not_scored |
| below_range_abstention | 32150 | 31.00 | 0.70 / 0.67 | 14.00 | 11.00 | 100.00 | unavailable | below_reference_range_not_scored |
| kidney_plateau_with_low_liver | 32955 | 18.67 | 0.90 / 0.86 | 186.00 | 87.00 | 100.00 | 32.93 |  |
| kidney_plateau_with_low_liver | 31378 | 19.33 | 0.80 / 0.77 | 185.00 | 128.00 | 100.00 | 33.10 |  |
| liver_plateau_with_low_kidney | 31877 | 62.25 | 5.00 / 4.87 | 16.00 | 15.00 | 8.47 | 100.00 |  |
| liver_plateau_with_low_kidney | 39621 | 78.83 | 4.40 / 4.29 | 16.00 | 18.00 | 8.91 | 100.00 |  |
| reported_dialysis | 31463 | 48.08 | unavailable / unavailable | unavailable | unavailable | unavailable | unavailable | dialysis_outside_scope, creatinine_missing_or_invalid, missing, missing |
| reported_dialysis | 31808 | 79.75 | 5.50 / 5.36 | 16.00 | 26.00 | unavailable | 100.00 | dialysis_outside_scope |

## Reproduction and remaining limits

From the workspace root: `python new_scoring_NHANES_inspired/evaluate_liver_kidney.py --node C:/nvm4w/nodejs/node.exe`. Standard-library Python plus Node; saved source evidence permits an offline rerun. The temporary PDF reader was used only to inspect source tables and is not an evaluation dependency.

Outputs: this Markdown report, `liver_kidney_v01_evaluation.json` (full distributions, sensitivity results, checks and hashes), and `liver_kidney_v01_rows.csv` (one row per positive-weight participant with screening age 12+). The latter distinguishes full-engine scores from numerical diagnostics and retains original/corrected creatinine, survey design, notices and exclusion reasons.

Pediatric CKiD estimates are exploratory only, with Jaffe assay and CKD-development-population limitations; no pediatric points are issued. Ages below the chemistry sample's coverage, bounded reported eGFR, acute kidney injury, measured GFR accuracy, longitudinal responsiveness and clinical outcomes cannot be evaluated here. Existing synthetic engine tests cover input/qualifier behavior. No claim of Canadian calibration, diagnosis, fairness or clinical validation follows from these checks.

Stage 3 is complete as a descriptive behavior evaluation with these limits. Next is the dashboard section, preserving separate components, provisional-model notices, below-range abstention, context flags and required dates. Shared integration remains deferred.

Verification: all 52 project tests passed on 2026-09-24, including eight research-adapter tests and the JavaScript HbA1c parity check; none were skipped. The full-cohort evaluation also checks score bounds, grouping, eligibility, dialysis exclusion, date abstention and retained enzyme notices.
