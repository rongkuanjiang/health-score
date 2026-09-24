# Integration release review — 24 September 2026

Package 0.1.2 / API 1.0. All five domains have implemented specifications, engines, descriptive evaluations and dashboard panels. Their scopes differ; no overall health score is defined. Scoring rules and parameter files were not changed for this handoff.

The 0.1.2 dashboard keeps score cards, chart and biomarker sections in one page. All five domains can remain expanded, with scores/status repeated on their section headers. Calculate-all and full-example actions cover all domains together. The DOM suite verifies that navigation never hides the summary or other domain panels, that all five sections can remain open, and that global calculations produce the expected five plotted component/domain points. Invalid fields open their containing sections for correction. Browser discovery again returned no available browser; rendered verification remains open.

The dashboard now starts with a basic questionnaire, then a five-domain overview with biomarker-entry links and a 0–100 pentagon chart. Shared personal details prefill the report forms; overrides are inside expandable report details. The chart plots only existing domain/component points, including separate kidney/liver markers, and leaves unavailable/reference-only axes unplotted. There is no filled overall polygon or invented System Stability score. Cards retain report notices and emphasize critical laboratory flags. Updating inputs clears stale cards and plotted points.

## Verification record

- Baseline: 144 Python tests passed in this session before integration changes.
- Shared API: full workspace discovery passed **151 Python tests**, with no skips, including the seven new shared-boundary tests. They cover engine parity, missing data, age policy, error isolation, explicit dates, envelope rejection and real HTTP requests.
- Package: isolated extraction passed **118 bundled Python tests**, with no skips, SHA-256 manifest checks, all four CLI fixture comparisons and their exit codes. Evaluation-adapter tests are workspace-only because research inputs are not distributed.
- JavaScript: reference-client checks passed against all four response fixtures, including null/zero handling and error propagation. The dashboard DOM suite also covers questionnaire validation, demographic mapping, overview navigation, chart/engine agreement, bounded-score gaps, categorical stability, critical notices, profile isolation and clearing of stale overview/chart results.
- Browser runtime initialized, but selection returned `No browser is available`; browser discovery returned an empty list. Desktop/mobile rendered layout remains unverified. DOM tests are not visual tests.
- During 0.1.1 packaging, early-rejection HTTP tests hit Windows connection resets as the server rejected requests before consuming their bodies. Header-rejection tests now omit unused bodies; the size-limit test sends an oversized Content-Length without uploading a body. This directly verifies early rejection without the send/close race. Server behavior is unchanged. Final isolated verification passed all 118 tests, the CLI fixtures, manifest hashes and JavaScript client checks.
- Clinical validation remains outside this implementation release. Descriptive NHANES evaluation is not clinical validation; absent report metadata still limits full-engine evaluation for several domains.

## Rendered acceptance checklist still open

At desktop (approximately 1440 px) and mobile (approximately 390 px), open each of the five domains, load a worked and incomplete profile, and verify:

- All controls and results are readable; page has no unintended horizontal overflow. Wide tables may scroll within their container.
- Charts, qualifiers, bounds, missing-data messages and notices are visible in every theme.
- Keyboard users can reach domain navigation, forms and expandable explanations, with visible focus.
- Editing clears old results; late responses cannot restore them; switching domains retains separate state; clear affects only its domain.
- Technical report metadata is distinguishable from questions for the person. Unknown details remain unknown.

## Known limits and handoff decisions

- Manual entry selects a simplified report/result per marker. Full multi-observation selection belongs to the engine contract and app importer.
- Metabolism's age extension is experimental; age rules are domain-specific.
- No complete numeric nutrition, inflammation, organ-stress or System Stability total is created by the wrapper.
- Shared schema validates the envelope; nested domain fields use their documented engine contracts.
- The reference JS client preserves complete results. The receiving app's actual rendering still needs acceptance testing.
- Hosting and named operational owners require agreement with the app team. No production deployment has occurred.
- No deep learning is used or needed by this release.

See [integration contract and deployment responsibilities](INTEGRATION_HANDOFF.md).
