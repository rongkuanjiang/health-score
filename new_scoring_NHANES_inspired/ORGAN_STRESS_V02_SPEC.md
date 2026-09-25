# Organ stress v0.2 — Canadian-oriented prototype

Updated 25 September 2026. Supersedes the v0.1 separate-component specification.
Implemented in `liver_kidney_score.py`; the parameter filename remains
`liver_kidney_v01_parameters.json` for existing API and packaging paths, but its
model identifier is `organ-stress-v0.2-provisional`.

## One domain score

Each core marker is converted to 0–100 points, then combined with fixed weights:

| Core input | Domain weight | Role |
| --- | ---: | --- |
| eGFR, reported or calculated from creatinine | 50% | Kidney filtration estimate |
| ALT | 30% | Liver-associated enzyme measurement |
| ALP | 20% | Complementary enzyme measurement; not specific to liver |

`domain_score = 0.50 * eGFR_points + 0.30 * ALT_points + 0.20 * ALP_points`

Higher means more favourable on these prototype curves, as in metabolism. The
score is not a probability, diagnosis, percentage of organ function, or complete
assessment of organ health. Weights, point ordinates and linear interpolation
are provisional design choices, not a Canadian guideline-endorsed scoring tool.

The 50/50 kidney/liver split prevents the number of liver tests from deciding
organ weighting. ALT receives more of the liver weight than ALP because the
latter has important non-hepatic sources. This rationale is a modelling choice,
not evidence that 30/20 is an optimal split. No fitting or clinical validation
has been performed for this version.

## Canadian input selection

The [Ontario laboratory requisition (April 2026)](https://forms.mgcs.gov.on.ca/dataset/83a92b8f-f0ad-4be3-80c4-13a09e6676ce/resource/5af91189-4cfd-4db7-817d-ca85b90385e5/download/txt_4422-84e.htm)
lists creatinine/eGFR, ALT, ALP and bilirubin as separately selected tests.
This verifies availability, not the frequency of inclusion in patient reports.
Do not assume a US comprehensive metabolic panel or a universal Canadian panel.

[Choosing Wisely Canada / Canadian Society of Clinical Chemists](https://choosingwiselycanada.org/recommendation/clinical-biochemistry/)
(updated October 2025) discourages routine AST and urea screening. AST is
therefore no longer required or numerically scored. Creatinine is used to
estimate eGFR, not counted again as an independent marker.

[BC's abnormal liver chemistry guideline](https://www2.gov.bc.ca/gov/content/health/practitioner-professional-resources/bc-guidelines/abnormal-liver-chemistry)
recommends ALT and ALP as initial investigations when liver disease is suspected.
It also explains non-hepatic ALP sources and discourages indiscriminate screening.
This is an older, 2011 guideline, not contemporary utilization data or validation
of wellness scoring. ALP availability still needs checking against actual
Canadian customer reports; missing ALP must never be presumed normal.

AST, bilirubin, GGT, albumin, BUN, uric acid, urine ACR and cystatin C remain
optional context. Bilirubin is a Canadian laboratory test, but its routine
presence has not been established. Context does not change weights or scores.
Preserve supplied lab flags prominently. Adding more markers does not by itself
establish a better model.

## Curves

Kidney retains the previous eGFR anchors `(value, points)`:
`(0,0), (15,10), (30,30), (45,50), (60,75), (90,100)`.
Interpolate linearly; plateau at 100 above 90. Zero defines a curve boundary,
not an accepted exact measurement. Reported eGFR route and creatinine equation,
calibration, age and sex rules are unchanged from v0.1.

ALT and ALP use the applicable laboratory reference interval, in the same unit
as the measurement. Supported units: `U/L`, `IU/L`. Within the interval: 100.
Above the upper limit, use ratios and points:
`(1,100), (2,75), (5,40), (10,15), (20,0)` with linear interpolation and a zero
plateau above 20 times the upper limit. Below-range values remain unscored.
Applying this provisional display curve to ALP does not assert equal clinical
severity across enzymes. It measures deviation, not its cause.

Both measurements require positive exact values, valid lower/upper limits and
`reference_range_applicable: true`. `reference_unit`, when supplied, must match
the result unit. No universal reference interval is silently substituted.

## Missing data, dates and eligibility

All three scored core inputs are required for a total. No renormalization,
imputation, missing-as-zero, or kidney-only substitute. Individual usable results
remain visible with explicit blocking reasons.

ALT and ALP require matching report IDs and consistent dates. A missing liver
date can be resolved by `context.same_snapshot_confirmed: true`, but at least
one liver date is required for the total. The selected kidney input requires its
own date and report ID. The core date span must be at most 90 days, matching the
metabolism maximum-gap convention; this is not a biological validity guarantee.

Pregnancy/unknown eligibility and age below 18 still withhold points. Dialysis
or acute kidney injury withholds kidney points and therefore the domain total.
Unreliable results, unsupported units/equations and invalid dates remain blocked.
eGFR `>60` retains a kidney range but no exact domain score; `>=90` can supply
100 kidney points because its entire interval is on the plateau.

An average can conceal a very low component. The domain retains every marker
result and lab flag; a visible review notice appears on the domain card and
overview when an above-range enzyme, low-eGFR notice or supplied lab flag exists.
There is no invented clinical severity colour or outcome-based score cap.

## API and dashboard

The existing function and HTTP routes are retained. `domain_score` and `score`
contain the same overall result; `display_score` uses one-decimal half-up rounding.
`weights`, `marker_scores`, `weighted_contributions`, `reasons`, `review_required`
and core `coverage.required/scored/missing_or_unusable` expose the calculation.
Top-level status is `scored`, `partial` or `unavailable`.

Components remain available for explanation: kidney is unchanged and liver is
`0.6 * ALT_points + 0.4 * ALP_points`. Liver now requires ALT/ALP, not ALT/AST.
The overview and radar show exactly one organ-stress score.

Put ALP in `observations.alp`, with reference metadata like ALT. AST supplied in
the old `observations.ast` location is retained as context; new callers can use
`optional_observations.ast`. A legacy ALP in `optional_observations` is not
silently promoted to core scoring. Move it explicitly and supply its reference
metadata. Model-version changes must be retained in stored results.

The synthetic example yields eGFR 75 → 87.5, ALT 80 with ULN 40 → 75,
ALP 80 within 40–120 → 100. Liver = 85; domain = 86.25, displayed **86.3**.

The old NHANES v0.1 report is historical evidence about the old model. Its adapter
does not yet supply verified ALP reference metadata, so current full liver/domain
scores remain unavailable. No new population evaluation or clinical validation
is claimed. Existing release ZIPs and the GitHub upload copy are unchanged.

## Implementation verification

25 September 2026: 158 Python tests passed using Python 3.13.1, including scoring,
missingness, specimen boundaries, optional-marker independence, flag preservation,
HTTP and integration checks. The real-server dashboard DOM suite and JavaScript
integration-client checks passed using Node 24.9.0. The worked example was also
executed directly and returned 86.25 / displayed 86.3. No browser was available
for rendered visual inspection; DOM tests do not establish visual acceptance.
