# System Stability v0.1: stage 3 behavior evaluation

Completed 2026-09-24. Descriptive evaluation, not clinical validation. Engine and clinical parameters unchanged; no fitting or deep learning.

## Findings

Of **6,980** examined participants aged 12+ at screening, **6,348** have all four core measurements (91.698% MEC-weighted completeness). All runtime panels are `unavailable`, with zero interpretable markers and null numerical scores. This is expected: public records lack applicable patient reference intervals and exact collection dates. Measurement presence is not interpretation coverage. No abnormality prevalence is estimated.

## Source and method review

[CDC BIOPRO_D codebook](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/BIOPRO_D.htm) verifies age 12+ eligibility, units and chemistry total-CO2 identity for LBXSC3SI. Its Beckman LX20 methods use indirect ISE for sodium/potassium/chloride and a membrane/pH approach for total CO2. Only 2005-2006 is used; no cross-cycle pooling or assay harmonization is assumed. Total calcium is optional; ionized calcium is absent. Public column inspection found no patient reference bounds, collection dates, specimen IDs or individual laboratory flags. Synthetic IDs identify research rows only.

[CDC demographics](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/DEMO_D.htm) distinguishes screening age from exam age and top-codes ages 85+. Groups below use screening age, retain exam months, and make no exact oldest-age claim. Participants under 12 at screening are excluded even if they later reached 12 at examination; exclusions are recorded in JSON.

[CDC weighting guidance](https://wwwn.cdc.gov/nchs/nhanes/tutorials/weighting.aspx) supports MEC weights for this examined sample. Use positive `WTMEC2YR`, not fasting weights. Means and empirical cumulative-weight quantiles use available measurements; completeness uses all eligible participants. Strata and PSU are retained. No confidence intervals, significance tests or survey variance estimates are calculated. Item nonresponse is not separately adjusted; these are descriptive checks, not population clinical conclusions.

## Completeness and age groups

| Screening age group | Eligible n | All four present n | Weighted all-four % | Interpretable n |
|---|---:|---:|---:|---:|
| all_screening_age_12plus | 6980 | 6348 | 91.698 | 0 |
| screening_age_12_to_under_18 | 1646 | 1449 | 87.626 | 0 |
| screening_age_18_to_under_40 | 2400 | 2186 | 90.603 | 0 |
| screening_age_40_to_under_60 | 1446 | 1352 | 94.218 | 0 |
| screening_age_60_to_under_85 | 1340 | 1231 | 92.104 | 0 |
| screening_age_85_to_under_151 | 148 | 130 | 85.597 | 0 |
| sex_code_1 | 3383 | 3083 | 91.526 | 0 |
| sex_code_2 | 3597 | 3265 | 91.860 | 0 |

## Measurement distributions

Calcium is mg/dL; core markers are mmol/L. Quantiles are weighted; extrema and n are unweighted. These are observed distributions, not reference intervals.

| Marker | n | Min | Weighted p05 | Weighted median | Weighted p95 | Max | Weighted mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| sodium | 6434 | 99.000 | 135.000 | 139.000 | 142.000 | 146.000 | 138.972 |
| potassium | 6433 | 2.400 | 3.500 | 3.900 | 4.500 | 5.800 | 3.963 |
| chloride | 6434 | 73.000 | 99.000 | 104.000 | 108.000 | 115.000 | 103.623 |
| total_co2 | 6349 | 16.000 | 21.000 | 25.000 | 28.000 | 38.000 | 24.661 |
| total_calcium | 6434 | 6.900 | 9.000 | 9.500 | 10.100 | 12.700 | 9.520 |

## Missing patterns

| Missing core markers | n |
|---|---:|
| none | 6348 |
| sodium,potassium,chloride,total_co2 | 546 |
| total_co2 | 85 |
| potassium | 1 |

## Conversion, extremes and interpretation

NHANES converts total calcium with 0.250; the engine uses 0.2495. The adapter imports the original mg/dL measurement once and keeps the published SI column separately for audit. Every paired value matches the CDC factor. Published-SI minus engine-SI differences range from 0.00345 to 0.00635 mmol/L. Do not require equality between these differently converted columns or count them as two measurements.

All six extracted chemistry columns reconcile with published counts and extrema. No nonpositive or nonfinite observed values were found. Extreme records are preserved in JSON for inspection, not removed, diagnosed, or labeled artifacts. Missing source critical flags do not establish noncritical values. No NHANES value receives a derived category or numerical score.

No research reference intervals were introduced. Consequently, interval sensitivity and clinical abnormality rates cannot be estimated here. Compensation by favorable markers is tested in separate synthetic fixtures; no numerical aggregation exists.

## Behavior checks

- all_scores_null: PASS
- all_reference_comparisons_withheld: PASS
- all_panels_unavailable: PASS
- coverage_matches_raw: PASS
- calcium_does_not_change_core_summary: PASS
- co2_alias_verified: PASS
- all_present_dates_missing: PASS
- all_present_ranges_unconfirmed: PASS
- calcium_matches_cdc_conversion: PASS
- no_invalid_positive_measurements: PASS

Synthetic cases use the explicitly labeled example fixture ranges and dates, never NHANES participant metadata. Full requests/results are in JSON.

- complete_within_fixture_ranges: PASS (all_within_reference).
- one_abnormal_cannot_be_compensated: PASS (outside_reference).
- abnormal_incomplete_panel: PASS (outside_reference).
- missing_co2: PASS (partial).
- critical_flag_survives_conflict: PASS (source_critical_flag).
- optional_calcium_warning_preserved: PASS (all_within_reference).
- unreliable_potassium: PASS (partial).

## Reproduce and handoff

From the workspace root:

```powershell
& ./.venv/Scripts/python.exe new_scoring_NHANES_inspired/evaluate_system_stability.py --node C:/nvm4w/nodejs/node.exe
& ./.venv/Scripts/python.exe -m unittest discover -s new_scoring_NHANES_inspired -p 'test_*system_stability*.py' -v
```

Standard-library Python and Node; no network required to rerun. Extraction verifies the inventory SHA-256 and row counts before use. The evaluation verifies codebook counts and ranges. JSON contains input/code hashes, original column inventories, survey-design metadata, exclusions, group distributions, extreme records, examples and fixture outputs. CSV retains participant-level audit rows. Adjacent [source review](system_stability_source_review.json) records the reviewed CDC links and mapping decisions.

Stage 3 is complete within the available public-data limits. Stage 4 remains dashboard integration: show categorical status, collection date, individual ranges and 0-4 interpretable coverage; retain optional calcium warnings. Use synthetic demonstration reports with explicit fixture labels. To interpret real reports, obtain their actual dates, specimen context, reference intervals and applicable flags. No numerical System Stability score or overall-score contribution should be added. Desktop/mobile verification and clinical validation remain outside this evaluation.
