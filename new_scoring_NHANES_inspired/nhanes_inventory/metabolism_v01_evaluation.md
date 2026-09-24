# Metabolism v0.1: NHANES behavior check

Model: `metabolism-v0.1-unadjusted`. NHANES 2005–2006, adults 20+. This is a descriptive implementation evaluation, not clinical validation or an outcome prediction study. No parameters were fitted or changed.

The engine produced 1708 complete scores. The weighted mean is 84.35, with a median of 86.52. Results support continuing the preliminary dashboard with visible marker notices and explicit missing-data statuses. Coverage restrictions and compensation remain material limitations, detailed below.

## Cohort and coverage

| Stage | Participants |
|---|---:|
| All adults in DEMO_D | 4979 |
| Positive fasting subsample weight | 1982 |
| Pregnancy eligible under documented research mapping | 1820 |
| Eligible with four positive raw measurements | 1743 |
| Full metabolism score | 1708 |

Coverage among pregnancy-eligible fasting participants: **93.85% unweighted**, **93.60% weighted**. These denominators exclude participants outside the fasting subsample; this is not routine-care or Canadian app-user availability.

Pregnancy mapping counts (positive-weight adults): `{"outside_documented_ridexprg_target": 1257, "recorded_cannot_ascertain": 16, "recorded_not_pregnant": 563, "recorded_pregnant": 146}`.

## Dataset mapping and limitations

- Join six component files one-to-one by SEQN; verify source hashes, row counts, unique IDs and linkage against the existing inventory. Raw files and historical HbA1c reports remain unchanged.
- Use dedicated TRIGLY_D SI triglycerides/LDL, HDL_D SI HDL and GHB_D HbA1c. Positive WTSAF2YR selects the documented fasting subsample. Exact fasting duration is unavailable locally. LDL method is Friedewald, not direct. [CDC lipid documentation](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/TRIGLY_D.htm).
- Pregnancy: RIDEXPRG 1 → yes; 2 → no; 3 → unknown. For missing codes only, recorded males and females age >=60 map to dataset-specific not-applicable because they lie outside the documented female 8–59 target. Missing within-target codes remain unknown. This is an explicit research applicability convention, not confirmation of nonpregnancy or a general application default. The explicit-recorded-nonpregnancy subgroup shows results without this convention, but is a different, female-only population. [CDC demographics](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/DEMO_D.htm).
- Select each participant's same-cycle MEC laboratory bundle explicitly. Exact specimen dates are unavailable, so all eligible results carry `dates_unverified`; the 90-day window cannot be verified here. Do not assign fictional specimen dates.
- HbA1c interference and individual laboratory reliability are unknown; no comprehensive assay-interference, illness or medication adjudication was performed. Sex flags use the recorded reference category; no numerical age/sex adjustment.
- Means, quantiles and proportions use WTSAF2YR within the stated complete-case group. Quantiles are the first score reaching the cumulative weight fraction. No confidence intervals or significance tests are computed; strata/PSUs are retained in the row export for later design-based inference. Complete-case selection bias remains.
- Diabetes uses DIQ010 yes/no/borderline separately. Diabetes medication is yes if DIQ050 or DID070 is yes; no only if both explicitly no; all other patterns remain unknown/skipped. Cholesterol medication uses BPQ100D yes/explicit no/unknown-or-skipped. Skips are not treated as no medication. No prescription-table joins or drug classification are needed. [CDC diabetes questionnaire](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/DIQ_D.htm), [cholesterol questionnaire](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/BPQ_D.htm).

The released DID070 field includes CDC-imputed medication responses for some borderline-diabetes participants. Here “explicit no” means a released code of 2; it does not establish that every such response was directly reported.

## Complete-case score distribution and subgroups

Subgroup differences are descriptive and confounded by age, treatment and selection. They do not establish calibration, fairness, causal effects or clinical responsiveness. Age is screening age and 85 is top-coded.

| Group | Positive-weight n | Eligible n | Scored n | Weighted mean | Median | P25–P75 | % exactly 100 |
|---|---:|---:|---:|---:|---:|---|---:|
| all | 1982 | 1820 | 1708 | 84.35 | 86.52 | 79.31–92.42 | 1.33 |
| age_20_39 | 757 | 598 | 569 | 88.42 | 90.55 | 84.14–95.25 | 2.87 |
| age_40_59 | 600 | 597 | 550 | 83.22 | 85.58 | 78.40–90.96 | 0.58 |
| age_60_plus | 625 | 625 | 589 | 79.94 | 82.35 | 73.50–87.78 | 0.16 |
| male | 963 | 963 | 906 | 83.42 | 85.29 | 78.50–91.04 | 0.57 |
| female | 1019 | 857 | 802 | 85.27 | 87.38 | 80.25–93.51 | 2.06 |
| explicit_recorded_nonpregnancy_only | 563 | 563 | 529 | 87.21 | 89.92 | 82.84–94.55 | 2.81 |
| diabetes_yes | 202 | 200 | 184 | 64.37 | 65.21 | 53.38–73.95 | 0.00 |
| diabetes_no | 1748 | 1589 | 1495 | 86.13 | 87.39 | 81.00–92.89 | 1.46 |
| diabetes_borderline | 29 | 28 | 26 | 76.95 | 78.40 | 71.42–84.79 | 0.00 |
| diabetes_unknown | 3 | 3 | 3 | 84.29 | 91.60 | 91.60–91.60 | 0.00 |
| cholesterol_medication_yes | 289 | 288 | 267 | 79.18 | 82.96 | 70.79–87.85 | 0.16 |
| cholesterol_medication_no_explicit | 49 | 47 | 42 | 73.25 | 75.30 | 67.83–80.91 | 0.00 |
| cholesterol_medication_unknown_or_skipped | 1644 | 1485 | 1399 | 85.54 | 87.28 | 80.79–93.01 | 1.56 |
| diabetes_medication_yes | 187 | 185 | 172 | 64.17 | 65.12 | 53.38–73.04 | 0.00 |
| diabetes_medication_no_both_explicit | 113 | 108 | 99 | 79.52 | 82.00 | 73.66–87.57 | 0.00 |
| diabetes_medication_unknown_or_skipped | 1682 | 1527 | 1437 | 86.26 | 87.64 | 81.19–93.01 | 1.51 |

## Marker distributions on the same scored participants

| Marker | n | Weighted mean | Median | % exactly 100 |
|---|---:|---:|---:|---:|
| hba1c | 1708 | 87.79 | 94.00 | 25.38 |
| ldl_c | 1708 | 76.96 | 81.56 | 13.21 |
| triglycerides | 1708 | 85.46 | 92.11 | 32.22 |
| hdl_c | 1708 | 84.31 | 90.25 | 38.93 |

## Score histogram

| Score interval | n | Weighted % of scored cohort |
|---|---:|---:|
| 0–10 exclusive upper | 0 | 0.00 |
| 10–20 exclusive upper | 0 | 0.00 |
| 20–30 exclusive upper | 3 | 0.06 |
| 30–40 exclusive upper | 10 | 0.41 |
| 40–50 exclusive upper | 34 | 1.45 |
| 50–60 exclusive upper | 59 | 2.27 |
| 60–70 exclusive upper | 130 | 5.89 |
| 70–80 exclusive upper | 308 | 17.09 |
| 80–90 exclusive upper | 623 | 37.22 |
| 90–100 inclusive | 541 | 35.61 |

## Missingness and exclusions

Marker statuses below are among pregnancy-eligible, positive-weight adults. Reasons overlap; do not add marker counts as if they were distinct people. Pregnancy-gated participants are counted separately above.

| Marker | Status | n |
|---|---|---:|
| hba1c | scored | 1809 |
| hba1c | missing | 9 |
| hba1c | below_model_coverage | 2 |
| ldl_c | scored | 1750 |
| ldl_c | missing | 70 |
| triglycerides | scored | 1798 |
| triglycerides | missing | 22 |
| hdl_c | scored | 1771 |
| hdl_c | high_hdl_outside_model_coverage | 35 |
| hdl_c | missing | 14 |

## Behaviors requiring dashboard attention

- High-HDL abstention excludes 35 eligible participants; it is the only scoring blocker for 33 (1.97% of eligible fasting weight).
- TG >=5.6 mmol/L occurs in 28 eligible participants; 0 have a full score. This NHANES release uses calculated LDL, so high-TG missing LDL limits examination of extreme-TG compensation. The synthetic direct-LDL acceptance example remains necessary.
- 1 scored participants have a composite >=80 while retaining a diabetes-range HbA1c, markedly elevated LDL or high-TG notice (0.13% of scored weight). The value 80 is only an audit threshold, not a health category. Marker notices must remain visible beside the average.
- Switching the same scored participants to the nonfasting numerical curve changes the weighted mean from 84.35 to 84.61; mean change 0.26, maximum 1.25. These are fasting specimens scored under an alternative rule, not observations validating nonfasting equivalence.

## Auditable example profiles

These are historical public NHANES records selected for inspection, not synthetic patients or treatment recommendations. Null scores are not zero. Units: HbA1c %, lipids mmol/L.

| Category | SEQN | HbA1c | LDL | TG | HDL | Score | Notices / blockers |
|---|---:|---:|---:|---:|---:|---:|---|
| lowest_scores | 37467 | 11.30 | 6.05 | 2.31 | 1.55 | 28.04 | a1c_diabetes_range, ldl_limited_at_elevated_tg, ldl_markedly_elevated, tg_elevated_reference |
| lowest_scores | 38178 | 11.00 | 5.90 | 0.82 | 1.03 | 29.11 | a1c_diabetes_range, ldl_markedly_elevated |
| lowest_scores | 35221 | 13.20 | 3.90 | 3.63 | 1.14 | 29.72 | a1c_diabetes_range, hdl_low_reference, ldl_limited_at_elevated_tg, tg_elevated_reference |
| highest_scores | 31380 | 4.80 | 1.97 | 0.95 | 1.78 | 100.00 |  |
| highest_scores | 32223 | 4.90 | 1.84 | 0.38 | 1.73 | 100.00 |  |
| highest_scores | 32714 | 4.90 | 1.19 | 0.72 | 1.91 | 100.00 |  |
| high_composite_with_reference_notice | 36868 | 4.70 | 5.30 | 0.97 | 1.63 | 81.75 | ldl_markedly_elevated |
| high_hdl_unscored | 31334 | 5.40 | 3.49 | 0.78 | 2.66 | — | hdl_high_outside_coverage, hdl_c:high_hdl_outside_model_coverage |
| high_hdl_unscored | 31666 | 5.10 | 1.76 | 0.58 | 3.00 | — | hdl_high_outside_coverage, hdl_c:high_hdl_outside_model_coverage |
| high_hdl_unscored | 31962 | 5.70 | 3.08 | 0.98 | 2.66 | — | hdl_high_outside_coverage, hdl_c:high_hdl_outside_model_coverage |
| high_tg | 31214 | 5.60 | — | 9.94 | 0.91 | — | hdl_low_reference, tg_elevated_reference, tg_markedly_elevated, ldl_c:missing |
| high_tg | 31343 | 9.50 | — | 8.61 | 0.70 | — | a1c_diabetes_range, hdl_low_reference, tg_elevated_reference, tg_markedly_elevated, ldl_c:missing |
| high_tg | 31442 | 11.30 | — | 5.97 | 0.80 | — | a1c_diabetes_range, hdl_low_reference, tg_elevated_reference, tg_markedly_elevated, ldl_c:missing |

## Reproduction and next step

Run `python evaluate_metabolism.py` from this directory (Node on PATH, or `--node PATH`). Standard library only. Outputs: this report, `metabolism_v01_evaluation.json` (statistics, checks and hashes), and `metabolism_v01_rows.csv` (one row per positive-weight adult, with retained survey design fields). The CLI prints a concise summary. Code assertions verify bounds, fixed-weight aggregation, pregnancy suppression and date notices; source extraction validates every file against the prior inventory.

This behavior check supports proceeding with a preliminary dashboard demonstration. It does not validate the model clinically. Preserve all eligibility, missingness, provisional-model and marker notices; show historical dates/unknown dates; keep steps separate. No numerical retuning was made from these distributions. Outcome validation, design-based uncertainty, interference adjudication, nonfasting observations and Canadian applicability remain future work.
