# Nutrition markers v0.1 — implementation specification

Prepared 2026-09-24. **Stages 1–3 complete:** specification, [Python engine with acceptance tests](NUTRITION_ENGINE_README.md), and [descriptive behavior evaluation](nhanes_inventory/nutrition_v01_evaluation.md). Companion configuration: [nutrition_v01_parameters.json](nutrition_v01_parameters.json). Stage 4 dashboard integration is implemented; desktop/mobile visual verification and clinical validation remain outstanding. See [dashboard usage and checks](DASHBOARD_README.md). This follows the specification/engine/behavior-check/dashboard sequence in [NEXT_DOMAIN_PLAN.md](NEXT_DOMAIN_PLAN.md); the shared integration handoff remains later work. No deep learning is required.

## Meaning and scope

Use **Nutrition markers** as the domain heading and **Vitamin D marker score (experimental)** for the numerical component. Return `domain_score: null` and `domain_aggregation_status: limited_marker_coverage` in every case. One nutrient measurement cannot represent overall diet quality, nutritional adequacy, protein intake, malnutrition or repair capacity.

The first release supplies one optional numerical component and useful observations. With routine CBC/CMP alone, display **Insufficient information for a nutrition marker score**. Missing tests are not abnormal results and do not trigger recommendations to order tests. Do not substitute albumin or CBC measurements when vitamin D is absent.

| Measurement | v0.1 role | Required distinction |
|---|---|---|
| Total serum/plasma 25-hydroxyvitamin D, 25(OH)D | Sole scored component, when eligible | Confirm total analyte identity; not 1,25-dihydroxyvitamin D or a D2/D3 fraction |
| B12; serum or RBC folate | Optional context, no points | Preserve analyte, specimen type, applicable laboratory range and flags |
| Ferritin, iron, transferrin, TIBC, transferrin saturation | Optional context, no points | Preserve individual observations; no inferred iron adequacy or composite |
| Albumin, prealbumin, total protein | Context only, no nutrition points | Do not label as protein intake, nutrient stores or repair capacity |
| Hemoglobin, MCV, RDW and other CBC observations | Context only | No inferred iron/B12 deficiency or nutrient score |
| Calcium, magnesium and other chemistry observations | Context only | No inferred dietary intake or added points |

Optional observations never change the vitamin D score or its denominator. Reuse observation IDs across domains to avoid counting shared results twice. Dietary questionnaires, if developed later, require a separate specification and label.

## Focused evidence review

- NIH ODS identifies total 25(OH)D as the usual vitamin D status measurement. Its NASEM-based summary places deficiency risk below 30 nmol/L, possible inadequacy at 30 to below 50, adequacy for most people at 50 or above, and potential adverse effects above 125. These are reference information, not validated wellness points. Conversion: ng/mL × 2.5 = nmol/L. [NIH ODS vitamin D](https://ods.od.nih.gov/factsheets/VitaminD-HealthProfessional/).
- The Endocrine Society's 2024 prevention guideline states that outcome-specific blood targets have not been established and advises against routine testing in generally healthy adults. Our curve is an experimental display choice, not its recommendation or a supplementation target. [Endocrine Society guideline](https://www.endocrine.org/clinical-practice-guidelines/vitamin-d-for-prevention-of-disease).
- ASPEN states that albumin and prealbumin should not be used as nutrition markers. This supports removing their legacy nutrition contribution. [ASPEN position paper](https://aspenjournals.onlinelibrary.wiley.com/doi/abs/10.1002/ncp.10588).
- B12 interpretation depends on method/laboratory and can require additional assessment such as MMA, which itself is affected by kidney function. v0.1 therefore preserves reported interpretation without a generic B12 curve. [NIH ODS vitamin B12](https://ods.od.nih.gov/factsheets/VitaminB12-HealthProfessional/).
- A dedicated iron-status review is deferred. The [WHO ferritin guideline](https://www.who.int/publications/i/item/9789240000124) is the starting reference for that extension; its landing page was checked, but a full threshold review was not completed. No ferritin threshold or iron algorithm is adopted here.

This is a focused review sufficient to document prototype choices, not an exhaustive clinical review. **Every point assignment, interpolation rule and eligibility restriction below is our provisional design.** Sources do not validate a 0–100 nutrition score.

## Eligibility and selection

1. Require finite positive age at collection; reject Boolean, nonnumeric or nonfinite values. Numerical points apply at age >=18. Younger users retain observations with `pediatric_points_not_defined`; age >=85 adds `older_age_limited_evidence`. No age/sex/race adjustment. Metabolism's age extension does not automatically apply here.
2. Pregnancy status must be `not_pregnant` or `not_applicable`; otherwise withhold points with `pregnancy_outside_scope` or `pregnancy_status_unknown`. Never infer status from gender. These are prototype restrictions.
3. Require an explicitly selected observation, nonempty observation/report IDs, total-25(OH)D identity, confirmed serum/plasma specimen type and collection date (`YYYY-MM-DD`). If a sole observation exists, it may be selected automatically; multiple candidates require an observation ID. Never select the most favorable value, combine dates or sum fractions in v0.1. Stage 2 makes the serum/plasma scope explicit in input validation; missing/other specimen types withhold points.
4. Validate collection date against a required evaluation date. Invalid/future dates withhold points. Show date and elapsed days; no invented expiration interval or claim that old bloodwork describes current health.
5. Preserve assay and reliability metadata. `unreliable` withholds points; `unknown` permits points with a notice if analyte identity is confirmed. Users should copy report details, not certify technical assay performance.
6. Record vitamin D supplementation/treatment and relevant conditions as optional `present | absent | unknown` context. Present and unknown generate notices without point correction. Do not infer unsupplemented status or suggest changing treatment. No fasting requirement or general acute-illness gate is defined in this limited release.

## Units, flags and bounded results

Canonical vitamin D unit: `nmol/L`; support `ng/mL` with multiplier 2.5 only. Preserve original value/unit, qualifier, date and provenance. Reject exact zero, negative, Boolean, nonnumeric and nonfinite values. Zero in the curve is a mathematical endpoint only. Unsupported units/analytes remain displayed as uninterpreted observations.

Accept qualifiers `=`, `<`, `<=`, `>`, `>=` with finite positive limits. **All non-exact results withhold numerical points** (`bounded_result`); never substitute a detection limit, midpoint or exact value. This simpler policy avoids falsely giving 100 to `>=50`, whose possible values include the unscored high range. Preserve the original bound. Issue a reference-band notice only if the entire possible interval lies in that band; otherwise `reference_band_indeterminate_from_bound`. Example: `<30` supports the low-band notice; `<50` spans two bands; `>125` supports the above-range notice. No score envelopes in v0.1.

Context-only observations retain original units without automatic conversion in this release. Derived low/high lab flags require matching units, finite ordered limits and confirmed applicability to the age/sex/analyte/assay. Otherwise preserve supplied flags and return `reference_interpretation_unavailable`. Do not apply serum folate ranges to RBC folate. Invalid context must not erase a usable vitamin D component. Source lab flags remain visible even if they conflict with the reference bands used here.

## Provisional vitamin D points

For an eligible exact total-25(OH)D result `x` in nmol/L:

| x | Points | Prototype rationale |
|---|---:|---|
| 0 < x < 30 | Linear from (0,0) to (30,50) | Low-end display gradient; not deficiency severity |
| 30 <= x < 50 | Linear from (30,50) to (50,100) | Transition to plateau |
| 50 <= x <=125 | 100 | No reward for increasing within the plateau |
| x >125 | null | `above_scoring_range`; preserve result and review notice |

Equations: `5*x/3` below 30; `50 + 2.5*(x-30)` from 30 to below 50; otherwise the defined plateau. No extrapolation above 125. The positive-to-null transition is deliberate: a withheld score is not zero. A score of 100 means only the top of this experimental curve, never optimal nutrition or a recommendation to increase vitamin D. The plateau's upper edge is not a treatment target.

Independent reference notices: `below_reference_band` for x<30; `possible_inadequacy_band` for 30<=x<50; `reference_adequacy_band` for 50<=x<=125; `above_scoring_range_review` for x>125. Use neutral consumer wording and preserve lab flags. These do not diagnose deficiency/toxicity, provide doses or constitute a triage system. Numerical scoring eligibility does not suppress valid observations or source flags; apply these adult reference notices only at age >=18 with known eligible pregnancy status.

## Result contract for stage 2

Follow existing engine conventions: immutable input; strict JSON; version; raw and normalized observations; unrounded score; one-decimal half-up display; reasons, notices and coverage. This is the local engine contract, not the final app API.

- `domain_score: null`, `domain_aggregation_status: limited_marker_coverage` always.
- `components.vitamin_d`: `score`, `display_score`, `status: scored | unavailable`, `reasons`, `notices`, `observation_id`.
- Global `status: component_available | unavailable` depends on numerical availability. Context-only observations do not make it `component_available`.
- Coverage: `scored_component_count` (0 or 1), `defined_component_count` (1), plus `available`, `missing` and `unusable` observation lists with reasons. This denominator describes implemented components, not the fraction of nutrition measured. No confidence/completeness percentage.
- Always include `limited_nutrition_coverage` and `provisional_points`; display supplied abnormal lab flags regardless of points.
- On multiple failures return all applicable reasons in stable order: invalid input, selection, metadata/analyte/unit, eligibility, reliability, bound/range. Null values must never be converted to zero by the dashboard.

Suggested empty-state copy: “These results do not provide enough information for a nutrition marker score. Available laboratory results are shown below.” Component detail copy: “This experimental score describes one vitamin D result. It does not measure overall nutrition or diet quality.”

## Stage 2 acceptance cases

Unless stated otherwise: adult, eligible pregnancy status, exact total-25(OH)D, supported units, reliable result, selected dated observation and valid evaluation date. Domain total stays null in every case.

| Case | Expected result |
|---|---|
| 15 / 30 / 40 / 50 nmol/L | 25 / 50 / 75 / 100 points |
| 20 ng/mL | Normalizes to 50 nmol/L; 100 points |
| 125 / 125.01 nmol/L | 100 / withheld with above-range notice |
| 29.99 / 30 / 49.99 / 50 | Boundary notices use unrounded values; no early rounding |
| 50 ng/mL / 50.01 ng/mL | 100 / withheld after conversion |
| `<30` / `<50` / `>=50` / `>125` | All withheld; low-band / indeterminate / indeterminate / high-range notices |
| Albumin and CBC only, or B12 and ferritin only | No numerical component; context remains visible |
| 1,25-dihydroxyvitamin D or D3 fraction | Unsupported analyte; no substitution |
| Zero, negative, NaN, infinity, Boolean or unsupported unit | Unusable observation; explicit reason |
| Two unselected vitamin D observations | `selection_required`; no averaging |
| Missing date/report ID; future date | Withheld; preserve observation |
| Age 17.99 / 18 / 85 | Withheld / allowed / allowed with older-age notice |
| Pregnancy unknown or pregnant | Withheld; supplied lab flags retained |
| Unreliable / unknown reliability | Withheld / score with notice |
| High B12 or low albumin flag beside vitamin D 75 nmol/L | Vitamin D 100; context flags remain; no nutrition total |
| Malformed context reference range | Context interpretation unavailable; valid vitamin D preserved |

## Behavior-check starting point

The local [variable inventory](nhanes_inventory/variable_dictionary.md) records `2005–2006 VID_D.LBDVIDMS` in nmol/L with 4,495 nonmissing adults 20+. Stage 3 independently reconciled this screening-age count. The CDC codebook and analytical note were retrieved and archived: values are already standardized estimates of total serum 25(OH)D, with no below-detection values. Stage 3 uses `WTMEC2YR`, with public age and pregnancy metadata preserved; see the [report and sources](nhanes_inventory/nutrition_v01_evaluation.md).

The completed evaluation preserves missing specimen dates/context and separates numerical-only diagnostics from full-engine results. It examines missingness, boundary behavior, high-range withholding and sensitivity to the arbitrary point anchors, with synthetic cases for paths absent from the dataset. These distributions are not clinical validation. Actual engine scores are all withheld for missing dates; no engine eligibility rules or anchors were changed.

## Decision log and handoff

| Decision | Reason | Later review |
|---|---|---|
| Optional vitamin D component only | Small transparent implementation scope | Evaluate whether points add useful information beyond reference bands |
| No domain total | One marker cannot cover nutrition | Additional components require their own evidence and aggregation design |
| Remove albumin/prealbumin from points | ASPEN position; legacy mapping is not validation | Keep available laboratory context |
| B12/iron/folate context only | No completed component-specific specification | Review assay, confounders, units and boundaries before adding points |
| High vitamin D is unscored | Avoid rewarding unlimited increases or inventing toxicity severity | Review high-result presentation in stage 3 |
| Adult, nonpregnant points | Explicit provisional scope | Separate pediatric/pregnancy review |
| All bounded values unscored | Simple and reproducible handling | Consider interval support only if needed |

Stage 2 is implemented in [nutrition_score.py](nutrition_score.py), with [acceptance tests](test_nutrition_score.py), a [synthetic request](example_nutrition_request.json), and [usage/contract documentation](NUTRITION_ENGINE_README.md). Stage 3 is complete in [the reproducible evaluation](evaluate_nutrition.py). Curve anchors are unchanged. Stage 4 now supplies the dashboard component and context/empty states, engine-sampled graphics, references and worked profiles; automated checks passed. The domain review should reconcile worked cases and desktop/mobile behavior with this specification. Shared API packaging is deferred with the other domains.
