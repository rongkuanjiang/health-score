> Current integration status (24 September 2026): all five dashboard domains and the shared API 1.0 handoff are implemented. See [integration handoff](INTEGRATION_HANDOFF.md) and [release review](RELEASE_REVIEW.md). Earlier statements below about pending domain/dashboard work or deferred step 5 describe historical checkpoints. Domain rules remain unchanged. Rendered browser acceptance and deployment ownership remain open.

**Next-domain development plan — liver and kidney markers**

Update 2026-09-24: stages 1-3 are complete: [specification](LIVER_KIDNEY_V01_SPEC.md), companion versioned parameters, [Python engine and acceptance tests](LIVER_KIDNEY_ENGINE_README.md), and [NHANES descriptive evaluation](nhanes_inventory/liver_kidney_v01_evaluation.md). The evaluation records the missing-date limitation for kidney scoring and preserves separate numerical diagnostics. The design uses separate kidney and liver component points without a combined total. The shared [dashboard](DASHBOARD_README.md) now includes organ stress; browser visual verification remains outstanding. The planning text below remains the original rationale.

Prepared for internal project review, 24 September 2026. Status: recommended next work, not an implemented or clinically validated model. The [accomplishment report](PROTOTYPE_PROGRESS_REPORT.md) describes the completed metabolism work.

I recommend developing the area previously called **Organ Stress** next, using **Liver and kidney markers** as the working consumer-facing name. This has a concrete starting point: the local NHANES inventory includes ALT, AST, creatinine, BUN, bilirubin and other relevant chemistry measurements. Availability in that dataset does not establish availability in every customer's report.

Start with separate kidney and liver components. Decide whether a combined domain score is defensible after reviewing the component rules and compensation behavior. Do not present these blood tests as a complete measure of organ health. AASLD distinguishes liver-injury markers such as ALT/AST from measures of liver function; NIDDK identifies both eGFR and urine albumin as important kidney measures. [AASLD liver-test interpretation](https://www.aasld.org/liver-fellow-network/core-series/back-basics/how-approach-elevated-liver-enzymes), [NIDDK kidney assessment](https://www.niddk.nih.gov/health-information/professionals/advanced-search/quick-reference-uacr-gfr).

**Proposed first-release scope**

| Area | Proposed inputs | Initial role |
|---|---|---|
| Kidney filtration | Laboratory-reported eGFR, or creatinine with the inputs needed for a supported equation | Candidate primary component. Preserve the equation, units and provenance; never count creatinine and its derived eGFR as independent evidence. |
| Liver-related findings | ALT and AST, with applicable laboratory reference limits where available | Candidate grouped component. Review their overlap before assigning weights; do not assume lower always means healthier. |
| Additional liver context | ALP, bilirubin, GGT, albumin when supplied | Display available results and relevant interpretation limitations. Decide individually whether any belongs in scoring rather than automatically adding points. |
| Additional kidney context | BUN, urine albumin-to-creatinine ratio (UACR), cystatin C when supplied | Context and coverage information initially. Optional tests are not assumed to be present and do not silently change the base score. |
| Uric acid | If supplied | Context only initially. Do not copy its legacy contribution into a kidney-filtration score without justification. |

The legacy code used ALT/AST and creatinine-derived eGFR/uric acid with weighted geometric aggregation. That implementation is useful history, not a validated baseline. The new design should review the evidence and choose transparent rules independently.

**Development sequence**

| Stage | Work | Concrete deliverable |
|---|---|---|
| 1. Establish the specification | Review primary guidance; define marker roles, units, reference limits, age applicability, equation selection, missing-data rules and exclusions. Distinguish published reference information from our numerical design choices. | Short specification, versioned parameters and a decision log. No curve anchors are approved by this plan. |
| 2. Implement the engine | Build kidney and liver components with simple rules, explicit statuses and preserved laboratory metadata. Test aggregation only after defining how abnormal results and missing components are handled. | Reusable Python functions and meaningful acceptance tests. |
| 3. Check behavior | Use the local NHANES chemistry data after verifying codebooks, assay comparability and the appropriate sample weights. Inspect completeness, distributions, age groups, implausible outputs and compensation. | A reproducible descriptive report, explicitly separate from clinical validation. |
| 4. Add the dashboard domain | Reuse themes and result layouts. Add consumer explanations, marker details, engine-generated graphics, references, representative profiles and missing-data messages. | A working liver/kidney section with clear limitations and no patient-facing technical judgments. |
| 5. Review before moving on | Check worked cases, edge cases and desktop/mobile interaction; reconcile findings with the specification. | A concise review checklist and known-limitations record. |

**Important design decisions to resolve first**

1. **Kidney calculation and age support.** Support entry and explanation for younger and very old users as requested, but select a suitable equation and verify its inputs and intended age range. Adult and pediatric equations are not interchangeable. Review current adult options, including race-free CKD-EPI 2021, and pediatric/young-adult options such as CKiD U25. Do not simply reuse the old CKD-EPI 2009 code or apply an adult equation to a child with a disclaimer. Some pediatric routes require height. Preserve a laboratory-reported result when appropriate; if calculation is unsupported or inputs are missing, explain why an estimate is unavailable. Equation-based age terms are distinct from an age adjustment to wellness points. [NIDDK adult equations](https://www.niddk.nih.gov/research-funding/research-programs/kidney-clinical-research-epidemiology/laboratory/glomerular-filtration-rate-equations/adults), [NIDDK pediatric and young-adult equations](https://www.niddk.nih.gov/research-funding/research-programs/kidney-clinical-research-epidemiology/laboratory/glomerular-filtration-rate-equations/children-adolescents-young-adults).

2. **Reference ranges and score direction.** Preserve units and applicable age/sex/laboratory reference ranges. Define a plateau where justified rather than rewarding every decrease in an enzyme or increase in eGFR. A normal-looking measurement must not imply that disease is excluded. The first specification must explain the rationale for every proposed anchor.

3. **Bounded laboratory results.** Reports may give eGFR as “>60” or “>90.” Preserve the qualifier; do not turn it into an exact value. Specify whether the entire reported interval supports one score, an interval of scores, or no numerical score.

4. **Coverage and aggregation.** Show liver and kidney coverage separately. Do not hide a concerning kidney result behind favorable liver points, double-count related measurements, or redistribute missing-marker weights without an explicit design decision. A combined domain score is conditional on a defensible aggregation rule; useful component results can be delivered without it.

5. **Plain-language context.** Ask only questions whose answers affect the interpretation or calculation, using understandable wording. Obtain laboratory method/reliability from the report or a developer view. Do not ask patients to certify technical validity. Keep the larger metabolism-questionnaire redesign tracked as shared interface work.

**NHANES starting point and evaluation boundaries**

The existing inventory lists `BIOPRO_D` variables `LBXSATSI` (ALT), `LBXSASSI` (AST), `LBXSCR`/`LBDSCRSI` (creatinine), `LBXSBU`/`LBDSBUSI` (BUN), `LBXSAPSI` (ALP), and `LBXSTB`/`LBDSTBSI` (bilirubin), among others. Verify units, laboratory-method changes and any creatinine calibration requirements before calculation. Do not carry over the metabolism fasting-subsample weights automatically: select weights for the actual measurements and analytic sample. Urine/cystatin C availability requires its own inventory check. [Local variable inventory](nhanes_inventory/variable_dictionary.md), [CDC chemistry codebook](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/BIOPRO_D.htm).

Analyze pediatric cases only where measurements, equation inputs and interpretation rules support that analysis. Use synthetic cases to test unsupported or absent-data paths, not to claim accuracy. Document the consequences of public age grouping for older participants. Passing implementation checks does not establish clinical validation.

**Completion criteria**

- Reproducible worked examples, correct unit conversions, and explicit behavior at curve and age boundaries.
- No fabricated result when required inputs, reference information or a supported calculation route are missing.
- Individual notices remain visible regardless of the combined score.
- Consumer details describe both the measurement and what the prototype cannot infer.
- A documented behavior evaluation and desktop/mobile verification, or an explicit record of any verification still blocked.
- Existing metabolism results remain unchanged, with regression checks confirming this.

**Sequence after this domain**

Continue with the other selected domains, retaining shared conventions for inputs, statuses, notices and versioning. Inflammation and nutrition should remain conditional on the information actually available. The previously discussed System Stability concept remains an option to review, not a finalized replacement domain or proof that every routine marker merits a numerical score.

After the domains are implemented, complete the original **step 5 once for the shared scorer**: documented API contracts, examples, packaging, integration tests and an agreed deployment handoff. Domain completion does not automatically define an overall health score; cross-domain aggregation needs its own explicit design and evaluation. Deep learning is not part of this prototype plan.
