# Inflammation v0.2: baseline hs-CRP and WBC profile

25 September 2026. Implemented provisional design; not clinically validated.
Supersedes the permanently null domain total in v0.1. Metabolism and organ stress
are unchanged. Nutrition and system stability still need their own redesigns.

## Construct and candidate review

This score summarizes a **baseline hs-CRP and white-cell marker profile** in eligible
adults. Higher points indicate a more favourable profile under the rules below.
It is not total inflammation, immune function, disease probability, cardiovascular
risk or an acute-illness severity scale. Normal results cannot exclude disease.

| Candidate | Role and rationale | Canadian evidence and limits |
| --- | --- | --- |
| hs-CRP | Core, 80%. Direct acute-phase protein measured with sufficient low-range sensitivity. | BC guidance supports CRP as an inflammatory investigation and distinguishes hs assays for low concentrations. This does not endorse wellness screening or our points. |
| WBC | Core, 20%. Adds a nonspecific cellular finding; both low and high counts reduce reference-conformity points. | Alberta's CBC service includes WBC. Availability does not establish ordering frequency in our customers. Both tails have non-inflammatory causes. |
| Standard/unknown-assay CRP | Visible context. No automatic substitution into the low-range hs curve. | Standard and hs assays measure the same protein, but low-range precision differs. A future supported alternative needs an explicit assay contract. Never count both as independent contributions. |
| Neutrophils, lymphocytes, other differential counts, NLR | Context only. | They overlap WBC information; a ratio also introduces denominator and method dependencies. No supported additional weights or universal wellness cutoffs established here. |
| ESR | Context only. | Choosing Wisely Canada discourages nonspecific ESR screening; slower kinetics and confounding weaken its case as a required wellness marker. |

Primary sources reviewed:
- [BC guideline, effective December 2018](https://www2.gov.bc.ca/assets/gov/health/practitioner-pro/bc-guidelines/esr.pdf): adult scope is 19+, clinical guidance rather than validation of a wellness composite. Historical pricing/policy statements are not used as current facts.
- [Canadian Association of Medical Biochemists, September 2026](https://choosingwiselycanada.org/recommendation/medical-biochemistry/): CRP/ESR selection.
- [Alberta Precision Laboratories CBC directory](https://www.albertahealthservices.ca/webapps/labservices/indexAPL.asp%3Fid%3D8717%26details%3Dtrue): CBC includes WBC; not a utilization study.
- [NIH MedlinePlus WBC](https://medlineplus.gov/lab-tests/white-blood-count-wbc/): high and low counts have multiple causes, including marrow disorders and treatments. Used for confounding, not Canadian ordering claims.

There is no representative Canadian customer-report dataset here. Canadian
coverage and outcome performance remain unknown. Do not recommend tests solely
to populate this score.

## Formula and explicit modelling choices

`domain = 0.80 * hs_crp_points + 0.20 * wbc_points`

The 80/20 weights deliberately make CRP dominant and limit the influence of
nonspecific WBC. They are transparent modelling choices, not fitted weights or
published clinical recommendations. They require expert and empirical review.

hs-CRP preserves v0.1: linear anchors in mg/L `(0,100), (1,100), (2,80),
 (3,60), (10,20)`. Exact zero is invalid; the zero anchor defines the plateau.
Above 10 mg/L withholds baseline points and retains a review notice.
Only `<`/`<=` bounds at or below 1 mg/L yield a single score of 100, since the
entire interval is on that plateau. Other bounds stay unavailable.

WBC uses the positive, applicable report lower limit `L` and upper limit `U`:
- `x < L`: `100*x/L`.
- `L <= x <= U`: `100`.
- `x > U`: `max(0, 100*(2-x/U))`.

The zero endpoints at zero cells and twice the upper limit are provisional curve
choices, not critical thresholds. WBC=0 therefore earns zero, not a healthy score.
Both limits and value must use the same unit; accepted units are 10^9/L,
10^3/uL and cells/uL. WBC bounds and percentages are not scored. Report-specific
ranges accommodate laboratory differences but also limit cross-lab comparability.

All points and the total lie within 0–100. Eligibility restrictions mean not
every point on that scale is attainable: with the retained hs-CRP cutoff the
lowest supported total is 16. Do not interpret unavailable values as zero.

## Eligibility, provenance and missingness

The existing 18+ modelling boundary is retained for consistency with the project;
the BC guideline's 19+ scope does not independently validate age 18. Pregnancy,
unknown pregnancy eligibility, acute illness and unknown acute context withhold
both components. This is deliberately a baseline profile. CRP above 10 remains
outside that baseline model, rather than assigning acute disease a wellness score.
Chronic conditions/treatment retain notices without invented numerical correction.

Both markers require report IDs, valid nonfuture collection dates and usable
measurements. Unreliable results are withheld; unknown reliability is disclosed.
Core collection dates must match exactly: fast-changing inflammatory markers do
not inherit metabolism's 90-day window. Separate report IDs are allowed on that
same date. A date match is a practical rule, not proof of identical sampling time.

Repeated results require explicit `selected_hs_crp_id` / `selected_wbc_id`.
Duplicate IDs block scoring. Never select the most favourable record or average
competing results. Missing core markers withhold the total without redistributing
weights; usable individual points remain visible. All supplied observations and
flags remain visible, including unselected and context-only observations.

## Output and dashboard contract

Existing routes remain unchanged. Output adds `score` (alias of `domain_score`),
`display_score`, `weights`, `marker_scores`, `weighted_contributions`, `reasons`,
`review_required`, and coverage `required/scored/missing_or_unusable`.
`components.hs_crp` remains compatible; `components.wbc` is new. Status is now
`scored`, `partial` or `unavailable`. Store model version with results.

The domain panel, overview and radar use the same domain total. Individual points,
contributions and abnormal flags remain visible even with a high total. Editing
inputs invalidates stale results. The model endpoint exposes weights, WBC formula,
date policy and hs-CRP curve samples from the engine.

Worked example: hs-CRP 2 mg/L = 80 points; WBC 12 with range 4–11 = 90.9091
points. Total = 64 + 18.1818 = **82.1818**, displayed **82.2**. Previously the
domain was null and the overview showed hs-CRP 80 alone. With hs-CRP 0.5, the
total is 98.2 but the WBC high flag remains visible.

## Research boundary

Existing v0.1 NHANES outputs are historical marker-only diagnostics, not validation
of v0.2. The adapter lacks collection dates and verified applicable WBC reference
metadata, so it cannot evaluate the composite. Its low-range CRP diagnostics remain
separate. No outcome calibration, Canadian population evaluation or clinical
validation is claimed. Release archives and upload copies were not regenerated.

## Verification

25 September 2026: 166 Python tests passed on Python 3.13.1, including
metabolism/organ-stress regressions, independent composite examples, WBC tails,
unit parity, eligibility, missing core inputs, dates, selection, flags and HTTP
parity. Real-server dashboard DOM and JavaScript integration-client suites passed
on Node 24.9.0. The dashboard test verifies the same 82.2 total in the domain,
overview and radar, and a 98.2 total with the WBC flag still visible.

The Browser runtime reported no available browsers. Rendered desktop/mobile
visual acceptance and measured browser performance are therefore outstanding.
Automated interaction tests do not establish clinical or population performance.
