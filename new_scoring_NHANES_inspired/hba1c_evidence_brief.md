# HbA1c evidence brief for the simple metabolism model

Date: 2026-09-22. Status: focused evidence review and proposed curve specification; not a finalized scoring rule. No scoring code changed. This is not an exhaustive systematic review.

## Conclusion

Use HbA1c as evidence of longer-term glycemic exposure, not a complete measure of diabetes severity or immune health. Canadian screening reference points at 5.5%, 6.0% and 6.5% can guide interpretation. None determines a particular 0-100 score. Evidence supports a continuous high-side decline in a favourable-health score; it does not establish universal severity boundaries at 8% or 10%. Evidence for penalizing low HbA1c is inconsistent and does not establish a causal low-glycemia penalty.

## Measurement and scope

- Local NHANES 2005-2006 variable: LBXGH, percent. Preserve this original unit.
- IFCC conversion, when needed: NGSP percent = 0.09148 * IFCC mmol/mol + 2.152. Source: [NGSP standardization](https://ngsp.org/ifccngsp.asp).
- HbA1c reflects glucose exposure over roughly three months and does not require fasting. It does not directly reveal glucose variability or hypoglycemic episodes.
- Red-cell turnover, blood loss/transfusion, some anemias, hemoglobin variants and other conditions can affect interpretation. Known interference is distinct from an adverse glucose result. Source: [NIDDK A1C explanation](https://www.niddk.nih.gov/health-information/diagnostic-tests/a1c-test).
- A treated person's current HbA1c is not their untreated metabolic state. The proposed snapshot is not a treatment-target achievement score; do not infer that a lower result proves disease resolution.

## Evidence table

Evidence assessments below are practical judgments for this project, not formal GRADE ratings.

| Source / population | Finding | What it supports | What it cannot establish |
|---|---|---|---|
| Diabetes Canada screening guideline and 2024 quick reference; adults | 5.5-5.9% is an increased-risk band in the screening algorithm; 6.0-6.4% is the Canadian prediabetes range; 6.5% is a diagnostic threshold, generally requiring confirmation in asymptomatic people | Strong clinical basis for interpretation reference points | Exact health-score values, abrupt biological transitions or complete severity |
| Zhang et al., 2010; systematic review of 16 prospective studies | Incident diabetes risk rises continuously; reported 5-year incidence ranges were about 9-25% at 5.5-6.0% and 25-50% at 6.0-6.5% | A graded decline before diagnosis, potentially steeper at higher values | Individual Canadian risk estimates or a universal mapping; cohorts and definitions varied |
| Colagiuri et al., 2011, DETECT-2 pooled analysis; approximately 45,000 participants | Diabetes-specific retinopathy findings supported 6.5% as a diagnostic criterion | Outcome-related justification for the diagnostic boundary | A jump in severity at exactly 6.5%, or a score of 30/50 at that boundary |
| Stratton et al., 2000, UKPDS 35; people with type 2 diabetes | Complication risk increased with updated mean HbA1c; no threshold was observed for the studied outcomes | Preserve differentiation above the diagnostic threshold | A general-population curve or a causal benefit estimate for an individual; this was observational analysis of a diabetes cohort |
| Carson et al., 2010; NHANES III adults without diabetes | HbA1c below 4% was associated with higher mortality; red-cell, iron and liver differences were present | Very low values deserve investigation | That low glucose itself caused the association or that a particular low-side score penalty is justified |
| Inoue et al., 2021; NHANES 1999-2015 participants without diabetes | Low HbA1c, 4.0 to below 5.0%, was associated with higher all-cause mortality | Low-end associations are not restricted to below 4% | A universally healthy lower boundary or causal effect; observational evidence and overlap with our NHANES cycles |
| Schottker et al., 2016; individual participant meta-analysis, six cohorts, 28,681 adults aged 50+ without diabetes | No consistent J-shaped association after adjustment for confounders | Evidence against assuming every low result deserves a penalty | Proof that all low values are benign; population and exposure categories differ from other studies |
| NIDDK laboratory interpretation guidance | Unusually low results can suggest interference; repeated measurements can differ | Separate interpretability from scoring, and avoid overreacting to tiny changes | A universal rejection rule below 4% or a universal change-detection threshold |

### Sources

1. [Diabetes Canada screening chapter](https://guidelines.diabetes.ca/GuideLines/media/Docs/cpg/Ch4-Screening-for-Diabetes-in-Adults.pdf) and [2024 quick reference](https://guidelines.diabetes.ca/getmedia/6c07d660-33a6-4cfa-abb0-e521eb4bb67d/2024-CPG-Quick-Reference-Guide_1.pdf).
2. [Zhang et al., A1C level and future risk of diabetes](https://pubmed.ncbi.nlm.nih.gov/20587727/).
3. [Colagiuri et al., Glycemic thresholds for diabetes-specific retinopathy](https://diabetesjournals.org/care/article/34/1/145/27752/Glycemic-Thresholds-for-Diabetes-Specific).
4. [UKPDS 35](https://pmc.ncbi.nlm.nih.gov/articles/27454/).
5. [Carson et al., low HbA1c and mortality](https://pubmed.ncbi.nlm.nih.gov/20923991/).
6. [Inoue et al., NHANES low HbA1c and mortality](https://pmc.ncbi.nlm.nih.gov/articles/PMC8562330/).
7. [Schottker et al., six-cohort analysis](https://pubmed.ncbi.nlm.nih.gov/26867584/).
8. [NIDDK testing limitations](https://www.niddk.nih.gov/health-information/professionals/diabetes/diabetes-prediabetes).

## Proposed curve specification: supported shape, unchosen point values

| Region or reference point | Proposed behavior | Evidence versus design |
|---|---|---|
| Low HbA1c | No automatic evidence-based penalty claimed. Numerical handling remains unresolved; do not silently assign a perfect score or reject all values below 4% | Conflicting evidence. A flag alone is not a complete scoring rule |
| Common low-risk region | Compare a plateau with a shallow slope before 5.5% | Plateau is a simplifying choice, not proof of identical risk throughout the region |
| 5.5% | Candidate transition toward a more noticeable decline | Supported as a screening reference and approximate risk-curve transition, not a precise biological turning point |
| 6.0% | Mark Canadian prediabetes entry; maintain continuity | Clinically supported location; score ordinate not established |
| 6.5% | Mark diagnostic threshold; maintain continuity | Clinically supported location; not a diagnosis from the score |
| Above 6.5% | Continue decreasing smoothly, preserving differences at higher values | Direction supported; tail shape and rate of decline are design choices |
| 8% / 10% | No mandatory anchor or hard score floor | Previous proposed boundaries withdrawn |

For a simple implementation, use a marker-specific piecewise-linear curve with explicitly chosen score ordinates, or a smooth declining high-side tail. We do not need five anchors. A tail approaching zero instead of reaching zero at 10% could preserve high-end responsiveness, but its parameters would remain modeling choices. Neither option should be called guideline-derived in its entirety.

Do not stitch published diabetes-incidence probabilities below 6.5% directly to complication or mortality risks above 6.5%: those studies estimate different endpoints, populations and time horizons. Do not use 100 minus a published risk percentage as the wellness score.

## Decisions still required before a numerical curve can be finalized

1. Shared meaning of marker-score bands: what departure from the favorable reference state should a given number represent? This is needed before averaging different markers.
2. Low-end policy: a contextual curve, explicit abstention where the result cannot be interpreted, or another declared conservative convention. Evidence does not uniquely determine this. The user's objection to a flag-only solution remains unresolved.
3. Plateau versus mild low-risk gradient: a plateau suppresses small changes; a steep gradient can amplify noise.
4. High-end tail: choose scale parameters without claiming 8% and 10% are universal severity boundaries.

## NHANES checks after provisional choices

- Inspect distributions and cohort counts, including how many low values each proposed policy affects; do not optimize points merely to spread the histogram.
- Test continuity and sensitivity to small perturbations. Quantify points changed per 0.1 percentage point HbA1c without declaring every such change clinically meaningful.
- Show treated and untreated groups separately and inspect relevant red-cell/context variables; absence of an interference flag does not prove an interference-free result.
- Compare external associations and missing-input behavior on held-out participants. If the curve is tuned against mortality, reserve separate evaluation data and do not call the same mortality analysis independent validation.
- Low-HbA1c papers using continuous NHANES overlap our cycle. A curve borrowed from them is not independent of NHANES evidence.
- A snapshot dataset cannot validate within-person clinical responsiveness. Keep repeated-measurement validation as a later requirement.

## Decision record

Retained: HbA1c-specific curve; Canadian interpretation; continuous mapping; explicit distinction between evidence and point assignments.

Withdrawn: fixed 75/50/25 intermediate points; 5.4% chosen merely because results are often rounded to one decimal; 4% as a proven lower optimal boundary; 8% as a universal severe boundary; 10% as an evidence-based floor.

The evidence brief is complete. Numeric score calibration and low-end handling remain open design decisions; this document is not a production-ready mapping.
