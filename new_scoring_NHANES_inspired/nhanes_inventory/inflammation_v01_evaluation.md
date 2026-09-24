# Inflammation v0.1: stage 3 behavior evaluation

Completed 2026-09-24. Descriptive NHANES 2005-2006 audit, not clinical validation. No fitted parameters, deep learning, or engine changes.

## Source and adapter decisions

The [CRP codebook](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/CRP_D.htm) distinguishes 1,079 detection-limit fills (0.01 mg/dL) from 7,093 reported measurements and 1,268 missing records. The local export is checked against inventory hashes and unique participant IDs; joins use SEQN.

The [laboratory manual](https://wwwn.cdc.gov/nchs/data/nhanes/public/2005/labmethods/crp_d_met_protein.pdf), pages 9-11, gives an approximate lowest reportable concentration of 0.02 mg/dL, varying by calibrator lot. Low-concentration QC supports a **research-equivalence inference** for exploring this curve, not clinical interchangeability with every hs-CRP assay. A participant-specific exact detection bound is unavailable. Thus fills retain their original value and censoring metadata, with no exact normalized concentration or primary diagnostic points. A separate sensitivity assumes their interval stays below 1 mg/L and assigns the plateau; it is not engine output. Exact values are converted from mg/dL to mg/L once.

The [CBC codebook](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/CBC_D.htm) identifies WBC and absolute differential units; the latter are derived from WBC and percentages. They remain context only, without invented reference ranges or point contributions.

The [demographics codebook](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/DEMO_D.htm) supplies examination age in months, with 85+ top coding handled as a lower-bound age surrogate. Other missing examination ages remain missing. Only recorded pregnancy code 2 establishes nonpregnant eligibility; skipped, unknown and absent responses remain unknown, including outside the question target. No inference from gender is used. Collection dates are absent from the public CRP file.

The [illness questionnaire](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/HSQ_D.htm) asks about three illnesses starting in the preceding 30 days. Neither three negative answers nor a positive answer determines the full acute state at collection (including injury, surgery and flares). The engine receives unknown acute context for everyone. Questionnaire responses define exploratory subgroups only; chronic condition and treatment context remain unknown.

Per [CDC weighting guidance](https://wwwn.cdc.gov/nchs/nhanes/tutorials/weighting.aspx), the report uses positive MEC examination weights, not fasting weights. Strata and PSU are preserved and checked. Weighted means, percentages and empirical quantiles describe the available analytic records; no design-based confidence intervals, hypothesis tests or representative population claims are made. Complete-case exclusions and assumed eligibility limit interpretation. Missing CRP remains in coverage denominators; point summaries use only non-null diagnostic points.

## Results

The cohort has **9440** positive-MEC-weight participants with screening age 1+, including **5339** with known examination age 18+ (85+ surrogate included). Missing examination age: 24. Full-engine component scores: **0**; all domain totals are null. This is expected abstention from missing dates and acute context, not a failed curve.

| Group | N | CRP present | Censored | >10 mg/L | Curve-only N | Weighted mean | Median | % at 100* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| all_age_1plus | 9440 | 8172 | 1079 | 708 | 4289 | 78.09 | 88.00 | 37.43 |
| adults_18plus_assumed_eligibility | 5339 | 5016 | 151 | 576 | 4289 | 78.09 | 88.00 | 37.43 |
| age_1_to_under_18 | 4077 | 3139 | 926 | 130 | 0 | unavailable | unavailable | unavailable |
| age_18_to_under_40 | 2407 | 2228 | 117 | 226 | 1885 | 80.90 | 94.00 | 45.23 |
| age_40_to_under_60 | 1445 | 1379 | 24 | 160 | 1195 | 76.95 | 84.00 | 34.94 |
| age_60_to_under_85 | 1339 | 1274 | 9 | 171 | 1094 | 75.23 | 80.00 | 28.27 |
| age_85_to_under_200 | 148 | 135 | 1 | 19 | 115 | 73.44 | 82.00 | 24.21 |
| adult_illness_any_yes_past_30_days | 1354 | 1296 | 23 | 201 | 1072 | 75.01 | 82.00 | 32.29 |
| adult_illness_all_three_no | 3517 | 3365 | 115 | 333 | 2917 | 79.12 | 88.00 | 39.10 |
| adult_illness_unknown_or_incomplete | 468 | 355 | 13 | 42 | 300 | 78.52 | 90.00 | 38.78 |
| adult_recorded_not_pregnant | 1630 | 1545 | 64 | 205 | 1276 | 76.53 | 84.00 | 37.54 |

*Weighted percentage among non-null curve-only points. Counts are unweighted. Curve-only diagnostics assume adult, nonpregnant, stable collection eligibility; they are never returned by the full engine. The recorded-not-pregnant subgroup still assumes stable collection. Pediatric records receive no diagnostic points.

## Sensitivity and interpretation

| Adult diagnostic scenario | N | Weighted mean | Weighted % at 100 |
|---|---:|---:|---:|
| curve_only | 4289 | 78.09 | 37.43 |
| sensitivity_fill_plateau | 4440 | 78.77 | 39.39 |
| sensitivity_endpoint_0 | 4289 | 76.05 | 37.43 |
| sensitivity_endpoint_40 | 4289 | 80.13 | 37.43 |

Endpoint sensitivities change only the illustrative points at 10 mg/L from 20 to 0 or 40, retaining the 1/2/3 mg/L anchors and all range exclusions. These arbitrary alternatives quantify dependence on our design; no alternative is selected. Censoring sensitivity changes sample membership and is not a paired estimate. JSON includes p05/p25/median/p75/p95 and ranges.

There is no component aggregation or compensation to assess: CBC cannot offset hs-CRP, and a broad domain total remains unavailable. A 100-point plateau cannot distinguish concentrations within it or establish absence of inflammation. Values above 10 retain notices and null points. The discontinuity at 10 is deliberate; the UI must distinguish withheld results from zero. Published rounding near thresholds and within-person variation remain limitations; this study does not estimate analytical error or repeatability.

## Worked public-data records

| Category | SEQN | Raw mg/dL | Exact mg/L | Curve-only points | Full engine |
|---|---:|---:|---:|---:|---|
| censored | 31154 | 0.01 | unavailable | unavailable | withheld |
| plateau | 31132 | 0.05 | 0.50 | 100.00 | withheld |
| threshold_2 | 31150 | 0.20 | 2.00 | 80.00 | withheld |
| endpoint_10 | 32602 | 1.00 | 10.00 | 20.00 | withheld |
| above_10 | 31131 | 2.44 | 24.40 | unavailable | withheld |
| missing_crp | 31130 | unavailable | unavailable | unavailable | withheld |

## Automated checks

- all_full_engine_scores_withheld: True
- all_domain_totals_null: True
- all_acute_context_unknown: True
- all_present_crp_dates_missing: True
- no_fill_values_treated_as_exact: True
- no_above_range_points: True
- points_bounded: True
- no_pediatric_points: True

## Reproduction and handoff

From the workspace root:

```powershell
.\.venv\Scripts\python.exe new_scoring_NHANES_inspired\evaluate_inflammation.py --node C:/nvm4w/nodejs/node.exe
.\.venv\Scripts\python.exe -m unittest discover -s new_scoring_NHANES_inspired -p test_evaluate_inflammation.py -v
```

The exporter verifies raw hashes and joins. The evaluator verifies saved source snapshots and records code/parameter hashes. Outputs: this report, `inflammation_v01_evaluation.json`, and `inflammation_v01_rows.csv`. The CSV retains survey design, raw values, censoring, reasons, notices and separate diagnostic fields. Regeneration needs Python and Node but no network or added packages.

Stage 3 is complete as a descriptive behavior audit. Stage 4 can build the dashboard using the existing engine, preserving missing-context questions, dates, separate CBC context and null semantics. Clinical review of anchors, prospective performance, longitudinal behavior, Canadian applicability and final integration packaging remain outstanding. These results do not validate the score or justify weakening its eligibility rules.
