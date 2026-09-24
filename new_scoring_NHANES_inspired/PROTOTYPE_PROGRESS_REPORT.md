> Current integration status (24 September 2026): all five dashboard domains and the shared API 1.0 handoff are implemented. See [integration handoff](INTEGRATION_HANDOFF.md) and [release review](RELEASE_REVIEW.md). Earlier statements below about pending domain/dashboard work or deferred step 5 describe historical checkpoints. Domain rules remain unchanged. Rendered browser acceptance and deployment ownership remain open.

**Metabolism scoring prototype — progress report**

Prepared for internal project review, 24 September 2026. Current model: `metabolism-v0.2-age-extension-unadjusted`.

A working local dashboard now demonstrates the metabolism scoring engine, from manual bloodwork entry to component results and consumer explanations. It provides a concrete prototype for review by the app team. The model remains preliminary: implementation tests and a descriptive NHANES check have been completed, but clinical accuracy has not been established. The supported integration API and final consumer-interface refinement remain outstanding.

| Planned step | Current status |
|---|---|
| 1. Scoring specification | Provisional curves, weights, input requirements and exclusions documented. A subsequent age-policy amendment is recorded separately. |
| 2. Python scoring engine | Implemented, including units, input checks, missing-data handling and versioned results. |
| 3. NHANES behavior check | Completed for the original v0.1 adult model; descriptive evaluation, not clinical validation. |
| 4. Dashboard | Working local demonstration implemented, including themes, marker details and scoring diagrams. Browser visual/interaction verification and the broader consumer-questionnaire redesign remain pending. |
| 5. Integration handoff | Deferred until the other domains are implemented. The reusable engine and local HTTP adapter provide a starting point for one shared integration package. |

**Scoring and result handling**

The engine uses HbA1c, LDL cholesterol, triglycerides and HDL cholesterol. Each measurement is converted into provisional 0–100 points. Triglyceride and HDL points are averaged; that result is averaged with LDL points to form lipid health; lipid health is averaged with HbA1c points to form the metabolism score. The effective weights are 50% HbA1c, 25% LDL, and 12.5% each for triglycerides and HDL. These are modeling choices, not validated proportions of health.

The engine accepts the supported laboratory units and handles fasting context, LDL calculation reliability, specimen dates and report selection. Missing or unsuitable measurements can withhold the combined score while preserving available component results. Missing components are not replaced or reweighted. Marker notices remain visible beside the total because an average can conceal a concerning individual measurement. Pregnancy and unknown pregnancy eligibility retain their existing scoring restrictions.

**Dashboard and consumer explanations**

The dashboard includes a context questionnaire, manual bloodwork entry, eight synthetic sample profiles, component scores, missing-data explanations and interpretation notices. Changing scoring inputs clears the previous result until recalculation. Five visual themes are available: Forest, Ocean, Lavender, Terracotta and Midnight.

Each marker has expandable information explaining what it measures, interpretation limitations, its provisional scoring rule and links to supporting references. Curve diagrams show the user's result when it is scorable and within the displayed range; anchor tables provide the numerical details. Chart data come from the Python engine rather than a second implementation of the scoring equations.

The metabolism snapshot includes an expandable calculation flow, a proportional weight diagram and explanations of rounding, missing results and model limitations. General explanations can also be opened before entering any health data. Technical JSON output is labeled as developer information.

A separate seven-day activity section accepts manually entered step totals and a selected source. It distinguishes recorded zero from missing data, reports coverage and the average of recorded days, and shows a comparison between the first and last three days when the week is complete. Steps do not change metabolism points. Phone and watch labels identify transcribed data; device integration is not implemented.

**Age extension**

At the user's request following supervisor discussion, the model now accepts positive ages below 20 as experimental estimates using the unchanged adult curves. It displays a prominent limitation notice and suppresses adult clinical threshold labels for this group. Ages 85+ were already accepted; they now receive an explicit notice about limited exact-age evidence. Numerical points remain unadjusted for age and sex.

This change is versioned as v0.2. It does not establish pediatric validity or individualized accuracy in older adults. The original NHANES evaluation selected adults 20+, and the evaluated public data group ages 85 and above together. No new pediatric evaluation was performed. See the [age-policy amendment](AGE_EXTENSION_AND_DETAILS.md).

**Verification and evidence**

The latest completed test run passed all **27 automated tests**, covering scoring behavior, units, exclusions, age boundaries, missing information, HTTP requests and agreement between chart data and the engine. JavaScript syntax checks passed. A live local request confirmed that the updated engine returned the worked example score of **85.6** for age 16 with the experimental-age notice.

The earlier v0.1 NHANES analysis produced complete scores for **1,708 of 1,820 pregnancy-eligible participants in the fasting subsample**, with a weighted mean of **84.35** and median of **86.52**. These findings describe behavior in the selected dataset; they do not establish clinical accuracy, performance in children or suitability for all app users. The historical report was not rerun as a v0.2 evaluation. See the [NHANES evaluation](nhanes_inventory/metabolism_v01_evaluation.md).

Browser-based visual and interaction verification could not be completed because the browser connection was unavailable. Automated tests do not substitute for this check.

**Remaining work and step 5**

The existing `POST /score` endpoint connects the dashboard to the engine, and `GET /model` supplies diagram data. Both belong to a local demonstration server. They are a useful integration starting point, but do not yet constitute a supported app-facing service.

Step 5 should deliver:

1. A documented, versioned request/response schema, including units, required context, missing-data statuses, interpretation notices and errors.
2. A packaged service or module the app team can run, with setup instructions and example requests for complete, incomplete and age-extension cases.
3. Integration tests that verify the app preserves withheld results and important notices, rather than displaying every response as a valid complete score.
4. A clear deployment handoff identifying who owns hosting, access control and health-data handling. Production deployment is separate from the current local demo.

The consumer questionnaire also needs refinement: laboratory reliability, HbA1c interference and LDL method should not require patients to make technical judgments. This was discussed but has not yet been redesigned. Report upload, laboratory-data extraction, wearable connections and persistent accounts/history are not implemented. The current demo does not intentionally persist entries; reloading clears them.

The agreed sequence is to implement the remaining domains before preparing the shared integration package. The recommended next domain is **liver and kidney markers**, corresponding to the legacy “Organ Stress” area; this is a proposal, not a completed scoring specification. See the [next-domain plan](NEXT_DOMAIN_PLAN.md). Keep units, missing-data statuses, notices and model versions consistent across domains while building them. No deep learning is required for the current prototype. This release provides a metabolism-domain score only; an overall health score has not been defined.

[Launch instructions](DASHBOARD_README.md) · [Engine interface](ENGINE_README.md) · [Age extension and explanation design](AGE_EXTENSION_AND_DETAILS.md)
