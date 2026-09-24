# Age extension and consumer explanations

Model: `metabolism-v0.2-age-extension-unadjusted`. Supersedes the age-20 eligibility restriction in the historical v0.1 specification and engine handoff. The parameter filename remains `metabolism_v01_parameters.json` for compatibility; its internal model version identifies the current behavior.

## Age policy

At the user's request, positive finite numeric ages can receive experimental scores, including fractional years. There is no upper age exclusion. Missing, zero, negative, nonnumeric, Boolean and nonfinite ages still block the combined score. The four curves, weights and adult numerical outputs are unchanged.

- Below 20: explicit `younger_age_extrapolation` notice and applicability field. Adult curves are reused without pediatric evaluation. Age-specific clinical interpretation has not been implemented; adult clinical threshold labels are suppressed for this group. Model/reliability statuses remain. This is not a pediatric clinical assessment or an alerting system.
- Ages 20–84: `adult_reference`, which does not mean clinical validation.
- Ages 85+: explicit `older_age_limited_evidence` notice and applicability field. The threshold reflects the 2005–2006 public-data age grouping, not a biological cutoff. This age range was already accepted numerically.
- Pregnancy gates still take precedence and return no scores or interpretation flags. Missing values, laboratory reliability, LDL method, unit, date, and curve-coverage checks still apply at every age.

The prior NHANES report remains an unchanged historical v0.1 evaluation of adults 20+. The evaluation script explicitly selects adults; this change does not claim a new pediatric evaluation. NHANES itself includes all ages, and 2005–2006 ages 85+ are top-coded. [CDC overview](https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/overview.aspx?BeginYear=2005).

Pediatric lipid references differ from adult references. A disclaimer communicates uncertainty but does not establish clinical suitability. [NHLBI pediatric guidance](https://www.nhlbi.nih.gov/health-topics/integrated-guidelines-for-cardiovascular-health-and-risk-reduction-in-children-and-adolescents).

## Consumer explanations

Each marker has an expandable explanation of its meaning, interpretation limitations, scoring rule, primary-source links, an SVG curve, and an accessible anchor table. The user's normalized measurement is marked when it has a score and is within the chart window. Unscored and off-chart results get explicit text instead of a misleading dot. TG diagrams use the selected fasting route; unknown fasting also shows the alternative as a dashed line.

The snapshot includes a calculation flow with current component values, a proportional weight diagram, missing-data and rounding explanations, age limitations, and sources. Explanations are also available before input under “Explore the score and blood markers.” JSON is labeled as developer details.

`GET /model` samples the Python engine's actual `_curve` function and serves the current parameters/version; JavaScript does not implement another scorer. Version mismatches with an existing result prompt refresh/recalculation. Explanations distinguish clinical references from provisional curve points and weights. External links open only when clicked.

Source review: NIDDK A1C information, NHLBI cholesterol/triglyceride information and pediatric guidance, CCS adult lipid guidance, CDC NHANES overview, and the original extreme-HDL cohort study linked in the existing specification. These are educational references, not validation of the combined score.

The larger questionnaire redesign discussed earlier is still separate work. This change adds age support and consumer details without guessing laboratory reliability or other unknown context.
