# Nutrition v0.2: B12 and iron-marker profile

Implemented 25 September 2026. This supersedes the vitamin-D-only v0.1 domain.
The navigation label remains Nutrition. The measured construct is a limited
laboratory B12/ferritin profile at collection, not dietary quality, protein or
calorie intake, all deficiencies, or overall nutritional adequacy.

## Formula and example

`Nutrition = 0.50 * B12_points + 0.50 * ferritin_points`

Both core inputs must be usable. No imputation, zero substitution, averaging
of available inputs, or redistribution of weights occurs. Equal weighting is
a provisional modelling choice giving each distinct marker equal influence;
it is not an empirically optimized or guideline-endorsed balance.

| Marker | Canonical units | Linear anchors (concentration, points) |
| --- | --- | --- |
| Total vitamin B12 | pmol/L | (0,0), (150,50), (220,80), (300,100) |
| Ferritin | ug/L | (0,0), (15,40), (30,75), (100,100) |

Interpolate between anchors; plateau at 100 only through the supplied applicable
laboratory upper limit. Higher results receive no points and an explicit review
reason, rather than a fabricated toxicity penalty. Zero is a limiting anchor,
not an accepted exact result. Positive finite exact values only; all bounds
remain bounds and receive no exact points. B12 converts pg/mL or ng/L by 0.738;
ferritin ng/mL equals ug/L. Reference limits must be in the measurement unit.

All point ordinates, interpolation, weights, and the 300-pmol/L B12 plateau
are **unvalidated display choices**. Clinical interpretation thresholds do not
validate this scale. The ferritin plateau must not be read as a recommendation
to raise ferritin to 100, and a score of 100 does not exclude deficiency.

Worked synthetic example: B12 150 pmol/L -> 50 points; ferritin 100 ug/L ->
100 points. Total = 25 + 50 = **75.0/100**. Vitamin D 40 nmol/L still has its
separate 75-point component, but contributes zero weight to this total. Before
v0.2 this same vitamin D result produced no domain total. Removing either core
marker now withholds the total; removing vitamin D does not change it.

## Canadian marker audit and rationale

Sources reviewed 25 September 2026. These sources establish interpretation and
testing limitations, not customer-report prevalence or validation of a score.

| Candidate | Decision | Rationale / limitations |
| --- | --- | --- |
| Total B12 | Core, 50% | Direct nutrient-related laboratory measure, with substantial diagnostic uncertainty. BC guidance notes variable laboratory thresholds and poor symptom correlation. Routine screening is unsupported. |
| Ferritin | Core, 50% | Preferred initial iron-deficiency test in BC guidance; acute-phase behaviour limits its interpretation. High ferritin is not good iron nutrition. |
| Vitamin D | Separate optional component | Canadian Choosing Wisely guidance discourages routine testing in low-risk adults; cannot assume availability. Existing exact-result curve and safeguards retained. |
| Folate | Context | Routine screening unsupported; BC states routine serum/RBC folate testing is no longer offered. Not a universal Canadian input. |
| Iron, transferrin, TIBC, TSAT | Context | Related iron-status information, not four additional independent nutritional dimensions. This version does not define a TSAT-based rescue model for confounded ferritin. |
| Hemoglobin, MCV, RDW | Context | Blood-cell findings do not establish overall nutritional adequacy or independently diagnose iron deficiency. |
| Albumin, prealbumin, total protein | Context | No direct intake/adequacy model established here; no promotion of illness-sensitive proteins into nutrition points. |
| Calcium, magnesium | Context | No validated dietary-adequacy interpretation or Canadian report coverage established for this score. |

Primary sources:

- [BC B12 and Folate Deficiency, revised January 2023](https://www2.gov.bc.ca/gov/content/health/practitioner-professional-resources/bc-guidelines/vitamin-b12): variable B12 deficiency cutoffs of 150–220 pmol/L, indeterminate results, high-B12 evaluation and testing limitations.
- [BC Iron Deficiency, 2019 guideline](https://www2.gov.bc.ca/gov/content/health/practitioner-professional-resources/bc-guidelines/iron-deficiency?keyword=2022): ferritin interpretation around 15/30 ug/L, higher thresholds in older/inflammatory populations, and the limitations of CBC as a surrogate. Its >100 discussion is clinical context, not approval of a wellness plateau.
- [BC High Ferritin and Iron Overload](https://www2.gov.bc.ca/gov/content/health/practitioner-professional-resources/bc-guidelines/iron-overload): high ferritin has numerous non-iron causes; upper intervals vary with demographic and assay factors. High ferritin alone does not establish overload.
- [Choosing Wisely Canada, Family Medicine](https://choosingwiselycanada.org/recommendation/family-medicine/): routine vitamin D testing in low-risk adults is discouraged.

No representative Canadian customer-report dataset has been verified. B12 and
ferritin are not guaranteed routine tests. This model may therefore be unavailable
for many reports. It does not recommend ordering tests solely to fill the score.
NHANES availability is not evidence of Canadian ordering frequency.

## Confounders, scope and missing information

- Existing adult (18+) and explicitly nonpregnant/not-applicable eligibility
  gates apply. Unknown age/pregnancy does not yield points. Age 85+ retains the
  older-age evidence notice; no age-specific numerical adjustment is validated.
- `iron_confounders: present` (known inflammation/infection, relevant liver or
  kidney disease, malignancy) withholds ferritin points. So does
  `recent_iron_treatment_or_transfusion: present`. No clinical washout interval
  is invented; this records known interference in interpretation at collection.
- Unknown confounder/treatment context produces explicit notices. The numeric
  profile can remain available, but it must not be interpreted as establishing
  iron sufficiency. CRP is not a hidden required test, and absent CRP is never
  interpreted as absent inflammation. This conditional interpretation is an
  important limitation of the chosen construct, especially in older adults.
- B12 supplements/treatment are retained as context, without guessed point
  adjustments. Above-range B12 is withheld regardless of reported supplements.
- Lab upper/lower limits must be explicitly applicable, coherent, in the same
  units, and compatible with the marker curve. An upper limit below the plateau
  anchor withholds points rather than silently using a different scale.
- Critical/abnormal lab flags survive high averages and unavailable totals.
  Flags are not converted into invented triage thresholds or treatment advice.

## Selection, provenance and contract

Require observation ID, report ID, collection date, evaluation date, supported
analyte (`total_vitamin_b12` or `ferritin`), and serum/plasma specimen. Invalid or
unreliable results withhold points; unspecified laboratory reliability retains
the existing unknown-reliability notice. Dates cannot be in the future.

The two selected core results must share report ID, collection date and specimen
type. This conservative snapshot rule avoids merging separate treatment periods;
same-day dates alone cannot establish an exact draw time. Repeated results require
`selected_observation_ids: {"b12": "...", "ferritin": "..."}`. Never pick the most
favourable result or average repeated observations. Duplicate IDs block use.

Endpoints remain `/score/nutrition`, `/model/nutrition`, `/api/v1/score`.
Results expose `domain_score`, `score`, `display_score`, `weights`, `reasons`,
component weights/contributions, original observations and coverage. The dashboard
panel, overview and radar use the domain total. Vitamin D remains separately
visible. Coverage describes two implemented core markers, not confidence or the
fraction of nutrition measured. Historical parameter filenames are retained for
packaging compatibility; the model version is `nutrition-v0.2-provisional`.

Historical `nutrition_v01_*` research outputs describe vitamin D only and do not
evaluate or validate this new core. Clinical validation and representative
Canadian availability evaluation remain outstanding.

## Implementation verification, 25 September 2026

179 Python tests passed across all domains, including core anchors, unit parity,
selection, missingness, eligibility, confounders, API parity and retained flags.
The shared dashboard DOM interaction suite and integration-client checks passed.
The Browser runtime returned no browser and an empty browser list; desktop/mobile
rendered visual inspection remains outstanding. No deployment or release ZIP
rebuild was performed. Other domains were not redesigned in this Nutrition pass.
