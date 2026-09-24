# Nutrition v0.1: descriptive behavior evaluation

Stage 3 completed 2026-09-24. This checks implementation and provisional curve behavior, not clinical validity. The production engine and point anchors are unchanged. There is still no overall nutrition score.

## Sources and mapping

The [CDC vitamin D codebook](https://wwwn.cdc.gov/nchs/data/Nhanes/Public/2005/DataFiles/VID_D.htm) describes serum measurements in examined participants aged 1+. The local file reconciles with its 9,440 records, 8,306 measured values, 1,134 missing values and 13.2–195 nmol/L range. It reports a 3.75 nmol/L detection limit and no values below detection; no fill value is treated as a measurement.

The [CDC analytical note](https://wwwn.cdc.gov/nchs/nhanes/vitamind/analyticalnote.aspx) identifies LBDVIDMS as already regression-standardized total 25(OH)D, derived from the original DiaSorin RIA. It is not a direct LC-MS/MS measurement. Use the released nmol/L values without recalibration, fraction summation or unit conversion. Assay equivalence does not establish individual clinical accuracy. The note's precise conversion differs slightly from the engine's conventional 2.5 multiplier; native SI input avoids that issue here.

Following the [CDC weighting tutorial](https://wwwn.cdc.gov/nchs/nhanes/tutorials/weighting.aspx), use WTMEC2YR for this examination component, not fasting weights. The cohort includes positive-weight examined participants with screening age >=1; retain missing vitamin D in the denominator. No item-nonresponse adjustment, age standardization, standard errors or confidence intervals are calculated. SDMVSTRA and SDMVPSU are retained for later survey inference. These are historical sample descriptions, not current Canadian prevalence estimates.

The [demographics codebook](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/DEMO_D.htm) supports exam age RIDAGEEX/12; age 85 is a topcoded lower bound where exam age is unavailable. Other missing exam ages remain unknown. RIDEXPRG 1/2 map to pregnant/not pregnant; missing/3 remain unknown without gender-based inference. Supplement, treatment and condition context were not extracted and remain unknown. No exact specimen dates are supplied. Research observation/report IDs identify the joined public records, not original clinical reports.

## Full engine versus curve diagnostics

All actual engine component scores are null: public specimen dates are missing. Pregnancy eligibility is also unknown for many participants. Every domain total remains null. Do not remove these requirements to manufacture public-data scores.

Separate adult curve-only columns apply the curve to measured concentrations while ignoring pregnancy and collection-date requirements. This includes pregnant/unknown participants solely to inspect numerical behavior, with pregnancy subgroups shown separately. These columns must never be exposed as valid patient scores. Children and unknown-age records receive no curve-only points.

| Group | N | Measured N | Curve N | Weighted curve mean | Weighted median | Weighted % at 100* |
|---|---:|---:|---:|---:|---:|---:|
| all_examined_screen_age_1plus | 9440 | 8306 | 4984 | 90.84 | 100.00 | 67.60 |
| adults_18plus_curve_diagnostics | 5339 | 5019 | 4984 | 90.84 | 100.00 | 67.60 |
| age_1_to_under_18 | 4077 | 3270 | 0 | unavailable | unavailable | unavailable |
| age_18_to_under_40 | 2407 | 2229 | 2204 | 90.81 | 100.00 | 68.05 |
| age_40_to_under_60 | 1445 | 1381 | 1375 | 90.60 | 100.00 | 67.64 |
| age_60_to_under_85 | 1339 | 1274 | 1270 | 91.53 | 100.00 | 67.12 |
| age_85_to_under_200 | 148 | 135 | 135 | 88.56 | 100.00 | 62.27 |
| unknown_exam_age | 24 | 17 | 0 | unavailable | unavailable | unavailable |
| adult_pregnancy_not_pregnant | 1630 | 1546 | 1528 | 89.57 | 100.00 | 65.90 |
| adult_pregnancy_pregnant | 354 | 336 | 330 | 92.95 | 100.00 | 75.81 |
| adult_pregnancy_unknown | 3355 | 3137 | 3126 | 91.51 | 100.00 | 68.32 |

*Among non-null curve-only points, excluding missing and above-range results. Counts are unweighted. JSON includes weighted quantiles and concentration distributions.

### Adult concentration coverage and bands

| Band (nmol/L) | N | Weighted % of all adults | Weighted % of measured adults |
|---|---:|---:|---:|
| missing_or_invalid | 320 | 5.40 | unavailable |
| below_30 | 427 | 4.96 | 5.24 |
| 30_to_under_50 | 1718 | 25.41 | 26.86 |
| 50_to_125 | 2839 | 63.37 | 66.99 |
| above_125 | 35 | 0.86 | 0.91 |

Screening-age 20+ measured count: 4495 (reconciles the earlier inventory independently of exam-age grouping).

## Anchor sensitivity

| Scenario | N | Weighted mean | Weighted mean paired change |
|---|---:|---:|---:|
| curve_only | 4984 | 90.84 | 0.00 |
| anchor_30_points_25 | 4984 | 86.72 | -4.12 |
| anchor_30_points_75 | 4984 | 94.96 | 4.12 |

Sensitivity changes only the points at 30 nmol/L from 50 to 25 or 75, holding (0,0), (50,100), the plateau and high-range withholding fixed. These illustrative alternatives are not fitted, endorsed or installed. The paired sample is identical. High mean points and a large plateau do not imply excellent overall nutrition; the plateau intentionally cannot rank its concentrations. Above 125, points become null rather than zero; excluding these values from point means requires displaying their counts separately.

No aggregation or compensation exists: favorable vitamin D cannot offset a flagged context marker, and context cannot fill a missing vitamin D component. Synthetic checks cover that rule, exact boundaries and bounded results absent from the public dataset. Published rounding near thresholds, within-person variation and assay error are not quantified by this audit.

## Worked public records

| Band | SEQN | nmol/L | Curve-only points | Full engine |
|---|---:|---:|---:|---|
| missing_or_invalid | 31130 | unavailable | unavailable | withheld |
| below_30 | 31175 | 22.90 | 38.17 | withheld |
| 30_to_under_50 | 31131 | 37.50 | 68.75 | withheld |
| 50_to_125 | 31132 | 73.80 | 100.00 | withheld |
| above_125 | 31486 | 139.00 | unavailable | withheld |

## Automated checks

- full_engine_scores_all_null: True
- domain_totals_all_null: True
- present_results_withhold_for_missing_date: True
- missing_marker_never_imputed: True
- high_range_never_scored: True
- no_child_or_unknown_age_points: True
- diagnostic_points_bounded: True
- Synthetic cases: 14 passed; details in JSON.


## Reproduction and stage 4 handoff

From the workspace root, with Python 3.10+ and Node:

```powershell
.\.venv\Scripts\python.exe new_scoring_NHANES_inspired\evaluate_nutrition.py --node C:/nvm4w/nodejs/node.exe
.\.venv\Scripts\python.exe -m unittest discover -s new_scoring_NHANES_inspired -p "test*nutrition*.py" -v
```

Regeneration is offline with standard-library Python and the existing XPORT reader. The exporter verifies inventory hashes, joins and codebook counts. The evaluator verifies source snapshot hashes and records code/parameter hashes. Outputs are this report, `nutrition_v01_evaluation.json` and `nutrition_v01_rows.csv`; null CSV values are empty, never zero. Array columns use JSON.

Stage 4 can use the existing engine, showing the experimental vitamin D component, missing-date/context reasons, separate lab context and an empty overall nutrition score. Do not import the curve-only diagnostic columns into the app. Keep high-range and source flags visible even when points are withheld. Review the meaning of 100 and whether points add value beyond bands. Clinical review, prospective validation and desktop/mobile dashboard verification remain outstanding.
