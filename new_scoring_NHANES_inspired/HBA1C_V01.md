# HbA1c baseline: a code walkthrough

Status: research candidate v0.1, unadjusted for age and sex. Not a production health score. Adult scope is age 20+. The caller must enforce adult eligibility; the NHANES evaluation does this explicitly.

## 1. Inputs and output

`scoreHba1c(5.75)` returns a result containing `score: 80`, `status: 'scored'`, the input and model version. Inputs are numbers in NGSP percent: use 6.0, not 0.06. Other units are rejected rather than silently converted. Missing, invalid and out-of-scope inputs return a null score and an explanatory status.

## 2. Anchor table

The `ANCHORS` array holds [HbA1c, score] pairs: [4,100], [5,100], [5.5,90], [6,70], [6.5,50], [8,25], [10,10]. All score ordinates are provisional design choices. Clinical reference points do not validate those point assignments. In particular, 4, 5, 8 and 10 are not asserted to be universal clinical boundaries. A 50 does not mean half healthy.

## 3. Straight lines between anchors

The function finds the two surrounding anchors, calculates how far the input lies between them, and moves the same fraction between their scores. For 5.75%, the surrounding points are [5.5,90] and [6,70]. Halfway between those points gives 80. Scores remain unrounded for subsequent calculations.

## 4. Endpoints

From 4 to 5 inclusive, the score is 100. Below 4, the candidate abstains: this is a provisional coverage rule, not an invalid-laboratory-result rule. There is no automatic low-end penalty.

Above 10%, score = 10 * 2^(-(HbA1c-10)/2). Each two percentage point increase halves the remaining score: 12 gives 5; 14 gives 2.5. This nonlinear tail is a deliberate exception to interpolation, avoiding a finite hard floor. It compresses point changes in the high tail. Extremely large computer inputs can underflow to zero; upstream laboratory validation remains necessary.

## 5. Interpretation context

Known pregnancy or known HbA1c interference returns no score. Defaults do not establish absence of interference; callers should provide available context. The NHANES script excludes known pregnancy but does not claim to screen all interferences. Diabetes diagnosis and medication history do not change this exposure-based mapping.

## 6. Run and verify

From the project root with Node.js available:

```
node --test new_scoring_NHANES_inspired/hba1c_score.test.mjs
node new_scoring_NHANES_inspired/evaluate_hba1c.mjs
```

`hba1c_score.mjs` is the reusable function. Tests check interpolation, boundaries, excluded inputs, continuity and monotonicity. `evaluate_hba1c.mjs` applies it to local NHANES files and writes aggregate reports, without changing raw data or the existing scorer.

## Remaining work

Compare predefined alternative curves; evaluate relevant outcomes with age/sex covariates and held-out data before tuning. Implement an explicitly defined age/sex adjustment approach as a separate version; it remains a user requirement. Subgroup summaries alone are not adjustment. No claim of clinical validation, within-person responsiveness, or suitability for combining with lipids is made yet.
