# Metabolism v0.1: implementation specification

**Superseding age-policy update:** the current engine is `metabolism-v0.2-age-extension-unadjusted`; see [age extension and details](AGE_EXTENSION_AND_DETAILS.md). It accepts positive ages with explicit experimental notices below 20 and at 85+, and suppresses adult clinical labels below 20. Curves and weights below remain unchanged; the original age eligibility statements are historical.

Implementation update, 2026-09-24: Step 2 is implemented in `metabolism_score.py`, with acceptance checks in `test_metabolism_score.py`. See `ENGINE_README.md` for the request contract and implementation decisions. The original Step 1 baseline below is retained as design history; statements that the engine is not implemented describe that earlier stage. The model remains preliminary and not clinically validated. NHANES domain evaluation, dashboard, and HTTP API are subsequent steps.

Date: 2026-09-24. Status: proposed implementation baseline for an integration demo, not a clinically validated model. This document specifies Step 1; it does not implement the Python scorer or dashboard. Model ID: `metabolism-v0.1-unadjusted`. HbA1c component ID remains `hba1c-v0.1-unadjusted`.

## 1. What the score means

A 0–100 description of how favorable four measured blood biomarkers are under explicit prototype rules. Higher scores mean smaller penalties under those rules. It is not percent health, insulin sensitivity, immune function, cardiovascular event probability, diabetes severity, or achievement of an individualized treatment target. A 100 does not exclude disease. A score change describes a change in measured profile; clinical responsiveness has not been established.

Clinical interpretation, scoring, and treatment decisions are distinct. All numerical score ordinates and weights below are modeling choices. Clinical sources inform reference locations and interpretation, not the exact points. Numerical points are not yet calibrated to equal units of health loss across biomarkers.

Population: adults age 20+, with no upper age exclusion. Known pregnancy is outside this model. Treated diabetes and lipid-lowering medication use do not automatically exclude a person; results describe their currently measured state, not an untreated counterfactual. Known acute illness can be recorded and flagged as limiting wellness interpretation, without an automatic numerical adjustment.

## 2. Fixed structure and required measurements

```
Metabolism
  Blood sugar: HbA1c
  Lipid health
    LDL cholesterol: LDL-C
    Triglycerides and HDL: triglycerides + HDL-C
  Body measurements: context only
```

Four numerical scores are required for a combined metabolism result: HbA1c, LDL-C, triglycerides (fasting, nonfasting or unknown fasting status), HDL-C. No inferred marker values or replacement with population averages. Blood sugar can display alone; lipid health can display when all three lipid scores exist. A triglycerides/HDL component needs both scores. No silent weight renormalization.

The display must not call LDL-C "total cholesterol" or label TG/HDL an "insulin resistance score". These measurements neither count all lipid particles nor diagnose insulin resistance.

Optional context: total cholesterol, derived non-HDL-C, ApoB, fasting or random glucose (with type), BMI, waist, blood pressure, medication and disease history. These do not change v0.1 points or fill a missing required marker. Do not convert glucose to estimated HbA1c to fill a gap. Wearables are reserved for a future version. No deep learning in this delivery.

## 3. Evidence and what it does—and does not—justify

| Evidence | Supported interpretation | Consequence for this prototype |
|---|---|---|
| Diabetes Canada diagnostic guidance [S1] | HbA1c 6.0–6.4% is a prediabetes range; 6.5% is a diabetes diagnostic criterion requiring appropriate context and usually confirmation without unequivocal symptoms | Retain HbA1c mapping already agreed. No score is itself a diagnosis. |
| CCS primary prevention [S2] | LDL-C 3.5 mmol/L is relevant in specified risk groups; 5.0 mmol/L can indicate treatment even with low estimated short-term risk | Use these as interpretation references, not universal normal/severe cutoffs. |
| CCS lipid selection/sampling [S3] | Nonfasting screening is acceptable; non-HDL-C/ApoB are preferred over LDL-C when TG >1.5 mmol/L; fasting testing is suggested with a history of TG >4.5 mmol/L | Fixed LDL-only scoring is a deliberate simplification. Flag the limitation and display optional non-HDL/ApoB without quietly changing the model. |
| Canadian metabolic syndrome analysis using harmonized criteria [S4] | TG >=1.7 mmol/L and HDL-C <1.0 in males / <1.3 in females are component criteria | Use for clinical reference flags. These do not diagnose metabolic syndrome alone and do not establish our numerical HDL curve. |
| CCS very-high-TG guidance [S5] and Endocrine Society [S6] | Very high TG warrants separate clinical attention; pancreatitis prevention becomes relevant at high concentrations | Keep prominent marker-level notices independent of the average score. No treatment recommendations generated. |
| Prospective HDL cohort evidence [S7] | Very high HDL-C is not consistently favorable; associations do not establish a causal penalty curve | Stop rewarding HDL once the plateau is reached; abstain in the extreme-high region rather than invent a mortality-derived penalty. |

## 4. Inputs and units

Each observation must preserve `value`, `unit`, marker ID, optional specimen date, report/source ID, and any laboratory reliability flag. Canonical units are HbA1c `%`, lipids `mmol/L`. Do not guess units from magnitude. Numeric strings may be parsed by the interface; the scoring engine accepts actual finite numbers and explicitly rejects booleans, zero, negatives, NaN and infinity. `<` or `>` laboratory results are censored values, not exact numbers; show them but do not score in v0.1.

| Measurement | Accepted units | Canonical conversion |
|---|---|---|
| HbA1c | %, mmol/mol | IFCC mmol/mol × 0.09148 + 2.152 = NGSP % [S8] |
| LDL-C, HDL-C, total cholesterol | mmol/L, mg/dL | mg/dL × 0.02586 = mmol/L [S9, S10] |
| Triglycerides | mmol/L, mg/dL | mg/dL × 0.01129 = mmol/L [S9] |
| ApoB, context only | g/L, mg/dL | mg/dL × 0.01 = g/L |
| Glucose, context only | mmol/L, mg/dL | Preserve supplied value/unit/type; no conversion needed for v0.1 scoring |
| BMI, context only | kg/m² | Preserve supplied value; not a blood concentration |

Convert once, keep full precision, then score. Never round to one decimal before applying the curve. Different laboratory rounding in equivalent unit reports can cause tiny differences; do not promise exact equality between independently rounded reports. Presentation rounds scores to one decimal, using a specified half-up rule; full precision is retained for aggregation. Display small positive scores below 0.1 as `<0.1`, not a misleading exact zero.

Required person/context fields: age at snapshot (must be >=20), pregnancy status (`yes`, `no`, `not_applicable`, `unknown`), HbA1c interference (`yes`, `no`, `unknown`), lipid fasting status (`fasting`, `nonfasting`, `unknown`), and LDL method (`direct`, `friedewald`, `other_lab_calculated`, `unknown`). Do not infer LDL method from a positive number. Unknown interference permits scoring with a context-incomplete notice; known interference blocks HbA1c and the combined domain only.

Pregnancy is a product eligibility gate BEFORE biomarker scoring or clinical interpretation. `yes` returns `pregnancy_outside_scope`, all scores null, and only "This prototype does not support assessment during pregnancy." Do not emit pregnancy-specific advice, diagnostic-range interpretations, clinical flags or alternative recommendations from this module. `unknown` or omitted returns `pregnancy_eligibility_required`, no scores or clinical interpretations, and asks the user to establish eligibility. Explicit `no` or `not_applicable` permits assessment; do not infer either solely from recorded sex. This is the team's scope decision, not a claim about specific regulations. For research, use only documented nonpregnancy/nonapplicability under a recorded dataset mapping; do not silently recode unknowns to negative. Previous HbA1c-only analyses are historical and used a more permissive unknown-status rule.

Collect age and recorded/reference sex for evaluation. Missing or unknown sex does not block this fixed numerical model; suppress sex-specific HDL flags when the reference category is unavailable. Do not infer sex from name or gender identity. The interface may use an explicitly selected laboratory reference category; ambiguous applicability requires interpretation rather than a hidden default.

Missing age blocks a combined domain with `age_required`; age below 20 blocks all component scoring with `age_outside_scope`. Synthetic example profiles must supply an explicit adult age. Laboratory reliability status is `valid`, `invalid`, or `unknown`; `invalid` blocks that marker. For high-TG other-calculated LDL, the exception requires explicit `valid` confirmation, not merely absence of an invalid flag.

## 5. Dates, specimen selection and fasting

- One selected lipid report supplies LDL-C, TG and HDL-C. Do not automatically combine the most recent value of each from unrelated reports.
- Pair HbA1c with that report when specimen dates differ by at most 90 days (absolute difference). This is a provisional snapshot-consistency window, not a clinical guideline.
- If dates are farther apart, individual components may display but the combined domain is null with `dates_not_aligned`.
- If dates are unavailable, an explicitly selected snapshot/report bundle may be scored with `dates_unverified`; do not claim it reflects today's health. The integration request must declare the selected bundle. Never silently merge arbitrary patient history.
- If dates are known, the snapshot date is the latest selected specimen date; preserve all original dates. Results remain historical scores regardless of age. Display the date instead of applying a time-decay penalty. Future dates are invalid metadata.
- All three TG states are supported numerically. Report-confirmed fasting, or known 8–<24 hours, selects the fasting curve. Nonfasting selects the provisional nonfasting curve in Section 9. Missing state selects the explicitly labeled unknown route; do not assume fasting silently. Conflicting duration/state requires correction, or explicit selection of the unknown route with the conflict retained in provenance.
- Unknown status uses the fasting curve as a conservative provisional point estimate and returns the nonfasting alternative as a sensitivity result. The alternative is not a confidence interval. Both may produce a full domain result when other requirements pass, labeled provisional for unknown status.
- Do not convert nonfasting TG into an estimated fasting concentration. Changes in fasting state between reports must be flagged in trend comparisons; a score change alone is not evidence of health change.
- HbA1c has no fasting requirement. LDL-C and HDL-C retain their separate reliability requirements.

## 6. Common numerical rule

Between adjacent anchors (x0, s0) and (x1, s1):

`score = s0 + (x - x0) / (x1 - x0) * (s1 - s0)`

No jumps at the numerical anchors. Values exactly at an anchor get its stated score. Eligibility boundaries can change between null and scored: they are explicitly distinct from the continuous numerical curve.

For a declining upper tail beginning at (t, s), with halving interval h:

`score = s * 2 ** (-(x - t) / h)` for x > t.

All curves, tails and plateaus are provisional. The lower sensitivity at the top/bottom of the scale is a known tradeoff. Do not optimize spread alone.

## 7. HbA1c curve — retained unchanged

Canonical unit: NGSP %.

| HbA1c | Score |
|---:|---:|
| 4.0 | 100 |
| 5.0 | 100 |
| 5.5 | 90 |
| 6.0 | 70 |
| 6.5 | 50 |
| 8.0 | 25 |
| 10.0 | 10 |

Below 4: null with `below_model_coverage`, not "invalid laboratory value". Above 10: tail with h=2. At 12 the score is 5; at 14 it is 2.5. Known interference blocks scoring. Wrapper adds age, pregnancy and unit conversion; after normalization, in-scope values must match the existing JavaScript function. No universal clinical optimum at 5 or severity boundary at 8/10 is claimed.

## 8. LDL-C curve — proposed

Canonical unit: mmol/L. Measures the model's penalty for LDL cholesterol exposure, not all atherogenic particles or personalized treatment adequacy.

| LDL-C | Score | Why this location is included |
|---:|---:|---|
| 2.0 | 100 | Proposed plateau endpoint; not a universal treatment target |
| 3.0 | 80 | Intermediate shape choice |
| 3.5 | 65 | CCS risk-dependent decision reference; score is our choice |
| 5.0 | 30 | CCS marked-elevation reference; score is our choice |
| 7.0 | 10 | Upper-tail shape choice, not a severity guideline |

For 0 < LDL-C <=2, score 100; no extra reward for still lower values. Above 7: tail with h=2. No low-LDL illness penalty is inferred. Values below 0.5 receive a contextual low-value notice, a modeling review trigger rather than a clinical diagnosis. Medication context remains visible; the plateau does not imply there is no clinical benefit to further lowering in a particular patient.

LDL reliability rules:

- Use laboratory-reported LDL; do not calculate LDL from total cholesterol in this release.
- If Friedewald-calculated and TG >=400 mg/dL (4.516 mmol/L using our conversion), return null `ldl_calculation_unreliable`. Use this exact implementation boundary rather than an inconsistent rounded unit threshold.
- If method unknown and same-report TG >=4.516, return null `ldl_method_required`.
- Other laboratory-calculated LDL at that TG level also requires explicit laboratory validity confirmation; no assumption that every equation shares the Friedewald restriction. Direct LDL is allowed unless the report says unreliable.
- If TG unavailable, an LDL result may display a component score with `ldl_reliability_context_incomplete`; full lipid/domain scoring is already impossible. A report saying LDL could not be calculated produces null, never zero.
- At TG >1.5, add `ldl_limited_at_elevated_tg` whether LDL is direct or calculated. This is about the information LDL captures, distinct from calculation invalidity. ApoB/non-HDL remain context in this fixed version.

## 9. Triglyceride curves — fasting, nonfasting and unknown routes

Canonical unit: mmol/L.

| Fasting TG | Score | Why this location is included |
|---:|---:|---|
| 1.0 | 100 | Proposed favorable plateau endpoint |
| 1.7 | 80 | Metabolic-syndrome component reference, not diagnosis |
| 2.3 | 60 | Intermediate shape choice |
| 4.5 | 30 | Shape/reference location near a fasting/reliability concern, not a severity category |
| 5.6 | 20 | Approximate clinical high-TG intervention reference [S6]; score is our choice |
| 10.0 | 5 | CCS very-high-TG reference [S5]; score is our choice |

For 0 < TG <=1, score 100. Above 10: tail with h=5. No automatic penalty for low TG. TG <0.3 receives a contextual low-value notice only (provisional review trigger).

Nonfasting route: anchors `[1,100], [2,80], [2.3,60], [4.5,30], [5.6,20], [10,5]`, same plateau and upper tail. Only the 80-point anchor moves from 1.7 to 2.0. Separate fasting/nonfasting reference values are supported by guidance [S11]; the common point assignment and interpolation, including the steeper 2.0–2.3 segment, remain provisional design choices, not a clinically validated correction. Test sensitivity of this segment. No claim that both routes are calibrated to equal risk.

Unknown route: use the fasting numerical curve, set `tg_fasting_unknown`, and include the alternative nonfasting TG score. Propagate the alternative through the same fixed aggregation when the full domain is otherwise eligible. At TG=1.7, fasting/unknown primary score=80 and nonfasting alternative=86; at 2.0 the corresponding scores are 70 and 80. The actual concentration is unchanged. If both routes agree, the unknown-status notice remains. The NHANES fasting subset can assess curve mechanics but does not validate nonfasting equivalence.

Independent notices: TG >=5.6: "Triglycerides are markedly elevated; discuss this result with a clinician." TG >=10: replace with higher-priority "Very high triglycerides need prompt clinical review because of pancreatitis risk." Neither notice is an acute diagnosis or automated treatment instruction. Model notice triggers use stated mmol/L values; these are not exact equivalents of every guideline's rounded mg/dL value.

## 10. HDL-C curve — proposed, shared numerical curve

Canonical unit: mmol/L.

| HDL-C | Score | Basis |
|---:|---:|---|
| 0.5 | 10 | Low-tail shape choice |
| 0.8 | 40 | Shape choice |
| 1.0 | 60 | Male low-HDL reference location; shared score remains a choice |
| 1.3 | 85 | Female low-HDL reference location; shared score remains a choice |
| 1.5 | 100 | Proposed saturation of reward, not a treatment target |

For 0 < HDL <0.5: `10 * (HDL / 0.5) ** 2`. From 1.5 up to but not including 2.5: plateau at 100. At HDL >=2.5: null `high_hdl_outside_model_coverage`. The 2.5 abstention boundary is a conservative common coverage choice prompted by extreme-HDL uncertainty, NOT a universal harmful threshold or sex-specific risk estimate. This deliberately excludes some results that might be benign; quantify the coverage cost in NHANES. Do not invent an upper HDL penalty or treat increasingly high values as increasingly protective.

The common curve deliberately preserves an unadjusted baseline. Separate clinical flags use low HDL <1.0 for male reference / <1.3 for female reference [S4]. These flags do not alter points and do NOT fulfill the requested numerical age/sex adjustment. For unknown reference category, show the two thresholds as context without assigning one to the person. No advice to raise HDL pharmacologically or by alcohol use.

## 11. Aggregation and its limitations

Let A, L, T, H be unrounded HbA1c, LDL-C, TG and HDL-C scores.

```
TG_HDL = (T + H) / 2
Lipid = (L + TG_HDL) / 2
Metabolism = (A + Lipid) / 2
           = 0.50*A + 0.25*L + 0.125*T + 0.125*H
```

Return null for any component whose required children are not scored. Return the list of missing/blocked prerequisites, not only a generic error. Optional inputs never change the denominator. A bad optional input does not block otherwise valid core scoring; it gets its own status.

Averages compensate: A=100, L=100, T=5 and H=100 yield 88.125, even though TG is very high. Therefore the dashboard MUST show each marker and preserve its clinical notices beside the summary, not hide them in a collapsed details pane. Do not label a high composite "all clear", "healthy", or green/no concern. No composite severity categories or safety cap are introduced in this version. This known compensation is a key evaluation criterion, not a solved problem.

TG and HDL share information, and calculated LDL can share input measurements with them. The hierarchy limits their total weighting but does not make signals statistically independent. Optional ApoB and non-HDL are not additional votes.

## 12. Statuses and presentation contract

Minimum clinical reference notices after unit normalization (independent of numerical score):

| Condition | Flag / intended meaning |
|---|---|
| HbA1c >=6.0 and <6.5 | `a1c_prediabetes_range`: in the Canadian prediabetes measurement range; not a new diagnosis generated by the app |
| HbA1c >=6.5 | `a1c_diabetes_range`: diabetes diagnostic-range measurement; confirmation and clinical context apply |
| LDL-C >=5.0 | `ldl_markedly_elevated`: discuss the result with a clinician; do not diagnose familial hypercholesterolemia |
| TG >=1.7, fasting | `tg_elevated_reference`: above the selected fasting reference; not an insulin resistance diagnosis |
| TG >=2.0, nonfasting | `tg_elevated_nonfasting_reference`: at/above the prototype's rounded nonfasting reference [S11] |
| TG status unknown | Show both reference values with `tg_fasting_unknown`; do not issue a fasting-specific classification as if status were known |
| TG >=5.6 or >=10 | Escalating notices defined in Section 9, regardless of fasting status |
| HDL below the applicable sex-reference threshold | `hdl_low_reference`: use Section 10; no automatic lifestyle or drug prescription |
| HDL >=2.5 | `hdl_high_outside_coverage`: the prototype does not interpret this region numerically |

HbA1c interpretation notices must be qualified/suppressed when known assay interference makes interpretation unreliable. A laboratory-invalid result never receives a clinical classification based on its numeric value. Low-result and LDL-at-elevated-TG notices are specified in Sections 8–9. A value below these notice thresholds does not establish overall health.

Each marker result: original value/unit; normalized value/unit; score (number or null); component version; one primary status; all applicable flags; source/report and date; interpretation text. All flags are evaluated where the necessary trustworthy measurements exist, even when a separate condition blocks scoring. A null score never means zero health.

First apply the pregnancy eligibility gate, which suppresses clinical interpretation. After eligibility passes, marker primary-status precedence: missing -> invalid_input/unsupported_unit/censored_result -> age outside_scope -> laboratory_invalid/known_interference -> unresolved fasting conflict or LDL reliability restriction -> curve_coverage restriction -> scored. Retain secondary reasons except clinical interpretation suppressed by eligibility. For domain, distinguish `scored`, `incomplete`, `outside_scope`, `eligibility_required`, and `dates_not_aligned`.

Pregnancy is domain-wide, unlike the earlier HbA1c-only evaluation. Do not retroactively rewrite existing published HbA1c charts; the domain analysis is a new report with its own cohort flow.

UI labels: "Metabolism — preliminary", "Blood sugar", "Lipid health", "LDL cholesterol", "Triglycerides and HDL". Show the model version and "No numerical age/sex adjustment" in the explanatory panel. Score interpretations must not use "diagnosed", "safe", "optimal health", or "percent healthy". Any diagnostic-range notice explains that a measurement alone may require confirmation.

Display input coverage as a count, e.g. "3 of 4 required markers scored", not a confidence percentage. Display dates and fasting status. Historical/synthetic example data must be labeled. Adding optional data may add context but cannot change v0.1 numerical scores.

## 13. Age and sex adjustment: retained requirement, deferred implementation

No numerical adjustment in this baseline. Age and sex subgroup checks are evaluation, not adjustment. Sex-specific interpretation flags likewise do not equal an adjusted domain score. A subsequent version must define an explicit adjustment method and meaning before claiming the requirement fulfilled. Age/sex-adjusted outcome analyses are planned separately. Do not claim that subgroup means should be equal or that an older person should automatically receive more points for the same measurements.

## 14. NHANES evaluation plan

Use local 2005–2006: GHB_D `LBXGH`; HDL_D `LBDHDD` or `LBDHDDSI`; TRIGLY_D `LBXTR`/`LBDTRSI`, `LBDLDL`/`LBDLDLSI`; DEMO_D age, sex, pregnancy and design fields. Join by SEQN, one row per person; never join long medication rows directly without aggregation. Raw files remain unchanged.

For the complete fasting-lipid domain use positive `WTSAF2YR`, not the HbA1c-only `WTMEC2YR`. The CDC codebook specifies the AM fasting subsample, 8.5–<24 hours, and prefers the dedicated TG assay over biochemistry TG [S9]. Positive fasting weight documents this eligibility for this cycle; verify the file rather than treating all morning measurements as fasting. Use provided SI fields for the first evaluation; conversion tests use synthetic equivalences, with tolerance for rounding of parallel NHANES unit columns.

Describe complete-case coverage, exclusions by marker and reason, score distributions, exact-100 proportions, age/sex subgroups and medication/diabetes context. Show the cost of the high-HDL coverage rule. Use the same eligible participants when comparing numerical curves; separately report coverage differences. Avoid comparing HbA1c-only and complete-domain distributions as if they used the same population. Complete-case selection may bias weighted results; the weights do not remove all missing-data bias or make this a Canadian sample.

For uncertainty/outcome analyses account for strata and PSUs, not just weights. Cross-sectional differences do not demonstrate within-person health improvement. No outcome-based anchor optimization or new disease-prediction claim in this step.

## 15. Worked profiles and acceptance checks for implementation

All examples use %, mmol/L, valid fasting reports, aligned dates, age >=20, no known pregnancy/interference, and valid direct LDL. Flags remain independent of the arithmetic.

| Profile | HbA1c / LDL / TG / HDL | Marker scores A / L / T / H | Metabolism |
|---|---|---|---:|
| Plateau example | 5.0 / 2.0 / 1.0 / 1.5 | 100 / 100 / 100 / 100 | 100 |
| Intermediate example | 5.5 / 3.0 / 1.7 / 1.3 | 90 / 80 / 80 / 85 | 85.625 |
| Multiple penalties | 6.0 / 3.5 / 2.3 / 1.0 | 70 / 65 / 60 / 60 | 66.25 |
| Larger penalties | 6.5 / 5.0 / 5.6 / 0.8 | 50 / 30 / 20 / 40 | 40 |
| Compensation example | 5.0 / 2.0 / 10.0 / 1.5 | 100 / 100 / 5 / 100 | 88.125 + prominent TG notice |
| High HDL outside coverage | 5.5 / 3.0 / 1.7 / 2.5 | 90 / 80 / 80 / null | null; other components retained |

Tests required in Step 2: HbA1c parity; unit-equivalent synthetic inputs; all anchors and interpolation; monotonicity within supported regions; continuous tails; no negative or >100 results; exact eligibility boundaries; missing/unit/boolean/censored input handling; unsupported HDL; fasting conflicts; LDL validity; date alignment; versioned output; preservation of flags when average is high; optional markers cannot change scores; known pregnancy blocks whole domain; sex/age changes within eligible adults do not change numeric v0.1 scores. Expected values above are acceptance examples, not empirical findings.

## 16. Decision log and remaining limits

Additional Step 2 acceptance cases after the user's revision: nonfasting TG=1.7 gives 86; TG=2.0 gives 80; unknown TG=2.0 returns primary 70 and alternative 80. With A=L=H=100, unknown TG=2.0 gives domain primary 96.25 and alternative 97.5. Pregnancy=yes returns no scores and no clinical flags even for extreme input values; unknown pregnancy returns eligibility-required. These additions supersede the earlier fasting-only and permissive unknown-pregnancy policies in the initial draft. Existing JavaScript code is not changed by this specification revision.

Retained: fixed four-marker core, HbA1c curve, equal-weight hierarchy, adults 20+, context-only body measurements, unadjusted numerical baseline, no AI requirement now.

New proposed rules for implementation: LDL/TG/HDL curves with fasting/nonfasting/unknown TG routes, high-HDL abstention, date alignment, unit normalization, LDL reliability checks, and marker notices. Pregnancy is excluded before any interpretation; unknown eligibility needs clarification. Age/sex adjustment is the subsequent model stage. These rules have not been fit to NHANES or implemented in the existing scorer.

Most consequential unresolved research issues: cross-marker scale calibration; compensation by averages; model coverage under routine nonfasting Canadian testing; replacing/augmenting LDL with non-HDL/ApoB; alternative low/high HDL policies; age/sex adjustment; historical measurement comparability and longitudinal validation. These are limitations to evaluate, not reasons to stop building the authorized demo.

## Sources

Focused source review, not a systematic review. Accessed 2026-09-24. Websites' crawl dates do not change guideline publication years.

- S1: [Diabetes Canada screening and diagnosis](https://www.diabetes.ca/for-professionals/health-care-provider-tools/screening-diagnosis-algorithm) and [interpretation context](https://www.diabetes.ca/for-professionals/health-care-provider-tools/screening-for-and-diagnosing-diabetes).
- S2: [2021 CCS primary prevention](https://ccs.ca/guideline/2021-lipids/chapter-3-overview-of-the-management-of-dyslipidemia-in-primary-prevention/).
- S3: [2021 CCS introduction](https://ccs.ca/guideline/2021-lipids/chapter-1-introduction/) and [CCS pocket guide](https://ccs.ca/app/uploads/2022/07/2022-Lipids-Gui-PG-EN.pdf).
- S4: [Statistics Canada: Metabolic syndrome in Canadian adults, 2007 to 2019](https://www150.statcan.gc.ca/n1/pub/82-003-x/2025009/article/00001-eng.htm).
- S5: [CCS dyslipidemia at a glance](https://ccs.ca/wp-content/uploads/2021/10/CCS-Dyslipidemia-At-A-Glance-.pdf).
- S6: [Endocrine Society lipid management guideline, 2020](https://www.endocrine.org/clinical-practice-guidelines/lipid-management-guideline).
- S7: [Madsen et al., 2017: extreme HDL and mortality, two cohorts](https://pubmed.ncbi.nlm.nih.gov/28419274/).
- S8: [NGSP/IFCC standardization](https://ngsp.org/ifccngsp.asp).
- S9: [CDC TRIGLY_D codebook, 2005–2006](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/TRIGLY_D.htm).
- S10: [CDC HDL_D codebook, 2005–2006](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/HDL_D.htm).
- S11: [ADA 2026 cardiovascular risk guidance](https://doi.org/10.2337/dc26-s010), fasting TG >1.7 and nonfasting >2.0 mmol/L reference values. The prototype uses inclusive rounded triggers as specified above; these are context references, not universal severity bands or treatment instructions.
