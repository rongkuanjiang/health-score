# System Stability v0.2: sodium–potassium profile

25 September 2026. Implemented provisional model `system-stability-v0.2-provisional`.
The parameter filename stays `system_stability_v01_parameters.json` for compatibility.
This specification supersedes v0.1's permanently null point output.

## Construct and marker selection

One collection's sodium–potassium laboratory profile, scored from 0 to 100 with
higher points more favourable on the defined curves. It does not measure resilience,
physiological reserve, longitudinal stability, diet quality, or complete electrolyte
and acid–base health. Neither the score nor the curves have clinical validation.

| Candidate | Decision and rationale | Availability evidence and limitations | Confounders / metadata |
| --- | --- | --- | --- |
| Sodium | Required, 50%; a distinct electrolyte concentration | Explicit Ontario community requisition entry [1]; actual customer coverage unknown | Fluid balance, glucose, assay effects and treatment affect interpretation; exact serum/plasma result, unit, applicable lab range, reliability and collection identity required |
| Potassium | Required, 50%; complementary electrolyte, relevant to cardiac and neuromuscular function [2] | Explicit entry [1]; actual ordering frequency unknown | Hemolysis can falsely increase potassium [3]; preserve interference and medication/report comments, never correct an affected result into points |
| Chloride | Supporting reference comparison only | Canadian hospital electrolyte grouping [2], but not a dedicated checkbox on [1]; no population coverage estimate | Related to sodium and acid–base state; not independent evidence for another equal-weight axis |
| Chemistry total CO2 | Supporting reference comparison only | Hospital grouping [2]; no verified routine Canadian community coverage | Preserve chemistry analyte identity; blood-gas bicarbonate is not an accepted replacement |
| Total / ionized calcium | Separate optional reference comparisons | Laboratory orderability does not establish routine coverage | Protein binding and specimen/method context differ; no corrected-calcium formula |
| Magnesium, anion gap | Excluded from scoring | No verified customer coverage or validated point model | Magnesium is not a complete body-store measure; anion gap would reuse chloride/CO2/sodium and introduce assay/albumin dependencies |

Choosing two scoring markers is a conservative product modelling decision, not a
claim that they exhaust System Stability. The 50/50 split avoids an unsupported
claim that either has an established optimal weight. Chloride/CO2 abnormalities
and calcium warnings remain visible even when the sodium–potassium score is high.
Missing tests do not imply normality or a recommendation to order more tests.

## Explicit point curves

Values are in mmol/L; supported core unit alias mEq/L has multiplier 1.
Between adjacent anchors, interpolate linearly. Clamp below/above the endpoints
to zero. Do not round before aggregation. Both low and high concentrations lose
points; concentrations on the plateau receive 100.

| Marker | (Concentration, points) anchors |
| --- | --- |
| Sodium | (120,0), (125,25), (130,60), (135,100), (145,100), (150,60), (155,25), (160,0) |
| Potassium | (2,0), (2.5,25), (3,60), (3.5,100), (5,100), (5.5,60), (6,25), (6.5,0) |

The plateau intervals match those stated in the primary NHANES distribution
study [4]. That US study does not validate a Canadian wellness score. Canadian
laboratory bulletins demonstrate that reference and critical limits vary by site
and method [3,5]. Accordingly these fixed model plateaus are **not substituted
for the person's laboratory reference intervals**. Every tail anchor, point
ordinate, interpolation rule and weight is an explicit provisional design choice.
The tails provide a gradual decline on marker-specific concentration scales;
equal points do not establish equal clinical severity. Endpoint zero means the
bottom of this model, not zero physiological function. Do not use these points
for triage, treatment, or clinical severity classification.

`domain_score = 0.5 * sodium_points + 0.5 * potassium_points`

Worked example: sodium 132.5 gives 80 points; potassium 5.5 gives 60 points.
Contributions are 40 and 30, so total = **70.0/100**. The original fixture,
sodium 140 and potassium 4, now gives **100.0/100**, previously null.

An average can conceal one abnormal component. There is no invented severity cap.
The output preserves components, source critical flags and conflicts, and sets
`review_required` for selected flagged/outside-range results or scored points
below 100. The panel and overview show review notices even at 100. A critical
source flag may coexist with 100 when it conflicts with the entered value; both
pieces of information remain visible, without reinterpreting the flag.

## Eligibility, data integrity and comparison compatibility

Points require finite age >=18 and `pregnancy_status` equal to `not_pregnant`
or `not_applicable`. Unknown eligibility withholds points. The existing supplied
applicable laboratory comparisons remain available independently of point scope.

Both selected core results must be positive finite exact numbers, with supported
serum/plasma specimens and units, applicable reference metadata, and reliability
`not_flagged`. Unknown reliability still allows the historical comparison with
a notice, but withholds points. `<`, `<=`, `>` and `>=` retain their bounds and
may support a category, never an exact score. Missing or invalid core values
withhold the total; the usable other marker survives. No redistribution of weights.

Selection requires explicit unique observation IDs from the same report/date and
selected specimen group. No cross-collection completion or 90-day allowance.
Duplicate IDs, missing selections and mismatches block affected points. Future
dates are rejected. Old results describe their collection, not present health;
specimen age remains visible. Source flags, unknown flags, comments, unselected
observations and malformed values remain preserved. No medication adjustment,
glucose-corrected sodium, or hemolysis correction is inferred.

## Output and integration

Existing routes and request shape remain. `person` now determines point eligibility.
`domain_score`/`score`, one-decimal half-up `display_score`, `status`, `weights`,
`marker_scores`, `weighted_contributions`, `score_reasons` and `review_required`
expose the calculation. Selected observation records carry marker `score` and
`score_reasons`; supporting observations have no numerical points.

For compatibility `core_markers` in the parameter file and the Python `CORE`
constant still refer to the historical four-electrolyte **reference panel**.
`scoring_core_markers` and `weights` identify the two required scoring markers.
`coverage.required/scored/missing_or_unusable` describe scoring coverage.
`present_count/interpretable_count/expected_count/missing_markers` retain the
four-marker reference coverage. Neither measure is confidence. `panel_status`
continues to summarize references and is supplemental to the score.

The domain form carries age/pregnancy, including shared questionnaire propagation.
Panel, overview and radar use the same domain score, with exactly one point when
available and a gap when unavailable. Editing/resetting invalidates old results.

Historical NHANES v0.1 outputs remain historical, not validation of v0.2. The
evaluation script now writes v0.2 filenames and retains metadata-based withholding
for research rows; no full population evaluation was performed for this redesign.
Release ZIPs and historical upload copies are outside this change.

## Implementation verification, 25 September 2026

- Python 3.13.1: 179 combined tests passed. The 65-test targeted set also passed,
  covering System Stability reference and numerical behavior, evaluation fixtures,
  dashboard HTTP routes and shared API integration.
- Node 24.9.0: `test_stability_ui.cjs` passed against the actual local Python API.
  Checks cover 100/70 totals, shared person details, one radar point, missing-data
  and pregnancy gaps, supporting-marker independence, critical notices, safe text,
  stale responses and reset isolation. JavaScript integration-client checks passed.
- The last full shared dashboard DOM run stopped at a Nutrition assertion during
  its separate redesign; full combined DOM acceptance is not claimed here.
- No browser-control tool was available. DOM checks do not establish rendered
  desktop/mobile acceptance. No deployment or clinical validation was performed.

## Sources reviewed

1. [Ontario laboratory requisition, April 2026](https://forms.mgcs.gov.on.ca/dataset/83a92b8f-f0ad-4be3-80c4-13a09e6676ce/resource/5af91189-4cfd-4db7-817d-ca85b90385e5/download/txt_4422-84e.htm). Availability only, not utilization.
2. [LHSC electrolyte education, reviewed 2014](https://www.lhsc.on.ca/critical-care-trauma-centre/critical-care-trauma-centre-256). Hospital context, not community utilization.
3. [AHS potassium and hemolysis bulletin, 2012](https://www.albertahealthservices.ca/assets/wf/lab/wf-lab-elevated_potassium_on_i-stat.pdf). Historical local method warning, not national current limits.
4. [Serum Sodium and Potassium Distribution and Characteristics in the US Population, NHANES 2009–2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC10975823/). Descriptive research; not score validation.
5. [AHS reference-range change bulletin, 2011](https://www.albertahealthservices.ca/assets/wf/lab/wf-lab-new-reference-ranges.pdf). Historical example of laboratory-specific limits; not implementation defaults.
