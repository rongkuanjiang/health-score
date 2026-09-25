## Uniform domains and wearable tracking, 25 September 2026

Compact wearable layout: **Trends**, **Daily entry**, and **Records & ECG** replace one another inside a bounded dashboard panel. Desktop trends use a narrow measurement list beside the chart; mobile measurements scroll horizontally. Entry and logs scroll within the panel, preserving unsaved fields when switching views. This avoids extending the dashboard into a long page.

All five domain workspaces share a score header, marker card styling, typography, spacing and view controls. Metabolism entry now uses marker fieldsets like the other domains. Calculations and eligibility rules are unchanged.

The overview has a separate **Wearable device data** section with a selectable 30-day chart and recorded-day averages for steps, sleep, active minutes, resting heart rate, HRV (RMSSD), oxygen saturation and respiratory rate. Add or edit one daily summary and one device-reported ECG record per date. The ECG log stores result, local time, heart rate and report notes; it does not ingest or analyze waveforms. Missing days stay gaps, and zero remains a recorded value. The fictional preview is separate from personal records and the bloodwork demo. Quick step entry copies entered steps into daily records when saved.

Wearable entries never contribute to scores or scoring requests. Entry is manual and page-session-only; reload clears records. No device sync is implemented. The Python suite and dashboard DOM interactions were checked for this update; rendered desktop/mobile review remains outstanding because no browser is available. Earlier visual verification below applies only to the previous revision.

## Previous dashboard revision, 25 September 2026

The overview shows all five domain scores beside a connected radar chart. Select a domain to switch to its workspace, then choose **Results** or **Edit biomarkers**. Inputs persist when switching; collection context and optional measurements expand on demand. Missing radar scores remain gaps.

Select **Explore a demo score** on the opening screen, or **Demo score** on the overview, to load Alex: one fictional 42-year-old male with consistent collection dates, demographics and shared marker values. This replaces all five domains with illustrative values, not population averages or clinical reference defaults. Scores from the current engines are Metabolism 86.4, Organ stress 100.0, Inflammation 90.4, Nutrition 100.0 and System Stability 100.0. Generic unnamed marker slots remain empty. Other example scenarios are available under the collapsed menu in each workspace.

The demo covers bloodwork only; wearable entries are not changed or displayed as Alex's data. Reloading clears page entries. Scores are provisional model points, not an overall health score. Desktop (1440 px) and mobile (390 px) browser layouts and interactions were checked for this revision. The sections below retain earlier implementation history.

> Nutrition update, 25 September 2026: [v0.2](NUTRITION_V02_SPEC.md) now provides one provisional B12/ferritin total (50% each), with vitamin D separate and optional. Prior vitamin-D-only/null-total descriptions are historical.

> Update 25 September 2026: inflammation now uses the provisional v0.2 fixed-core hs-CRP/WBC domain total. See [current specification](INFLAMMATION_V02_SPEC.md). Earlier marker-only/null-total descriptions below are historical. Nutrition and system stability are unchanged.

> Current organ-stress model (25 September 2026): v0.2 now combines eGFR (50%), ALT (30%) and ALP (20%) into one domain score. AST and bilirubin are optional context. See [the current specification](ORGAN_STRESS_V02_SPEC.md) for inputs, curves, missing-data rules and Canadian source rationale. The v0.1 descriptions and evaluation results below are historical and do not validate v0.2.

# Five-domain dashboard and integration release

## Questionnaire and layout update

Daily steps now appear under the optional **Wearable device data** section in the opening questionnaire. A separate dashboard summary provides an **Edit wearable data** button. Entries remain manual, with no device connection or activity score. Updating only wearable data preserves calculated bloodwork results; Cancel restores the previous entries, and Clear metabolism leaves wearable data intact.

Layout fixes give score cards more space, add padding inside expandable sections, improve mobile wrapping and wearable fields, and correct the inflammation border theme token. The dashboard interaction suite passes, including wearable placement, recorded zero, edit/cancel and reset isolation. Rendered desktop/mobile review remains outstanding because the Browser runtime reports no available browser.

## Unified dashboard (package 0.1.2)

Start by entering age at collection, laboratory sex reference and pregnancy context. The main dashboard shows all five score cards, the pentagon chart and expandable biomarker sections together. Select **Enter biomarkers** on a card or a domain shortcut to open its inline section; other domains remain available. **Calculate all domains** evaluates every form in one action. **Try a full example** fills all five domains with synthetic worked profiles and calculates them. Neither action leaves the dashboard. Domain section headers show current scores/status, and **Jump to scores** scrolls to the summary. Personal details are prefilled; expand **Personal details for this report** to adjust them. Synthetic profiles have their own example context and are labeled on score cards. **Edit my details** updates shared context and clears previous results so they must be recalculated.

The pentagon uses a 0–100 scale and plots existing points: metabolism, one weighted organ-stress domain score on the organ axis, hs-CRP and vitamin D. System Stability remains a categorical reference summary. Missing or bounded-only scores are not plotted as exact values; ranges stay visible on cards. No overall filled shape or additional domain score is manufactured. Expand report notices on a card or open full results for all context. Editing biomarkers removes old card results and chart points, including when an older request finishes later.

Restart the Python server and hard-refresh the page to load the new overview asset. Automated interaction checks pass; browser visual review remains outstanding because no browser is available in the tool runtime.

All five domain panels are active. Start with [integration handoff](INTEGRATION_HANDOFF.md) for API 1.0, runnable packaging and examples, and [release review](RELEASE_REVIEW.md) for current checks and known limits. Older sections below retain their historical test counts; statements about disabled placeholders, missing domains or deferred integration are superseded by this update.

Metabolism's laboratory interference assessment and LDL method now live in an expandable report-details section. Copy information supplied by the laboratory or clinician; do not infer validity yourself. Unknown defaults and all scoring behavior are unchanged. Organ reference-applicability wording likewise identifies the report/importer as the source.

The module/package handoff is implemented. Production deployment and named owners still require the receiving team's agreement; desktop/mobile visual acceptance remains outstanding because the browser runtime has no available browser.

## Historical implementation checkpoints

# Health scorer dashboard — step 4

## Historical Nutrition v0.1 checkpoint, 2026-09-24

Choose **04 · Nutrition markers**, select **Worked example**, and click **Load nutrition profile**. Expect **75.0 vitamin D points** and a separate low-albumin flag. The dashboard calls the unchanged engine through `POST /score/nutrition`. `GET /model/nutrition` samples its actual curve for the diagram and accessible example table. The overall nutrition score remains null, including when vitamin D receives 100 points.

Enter one selected total 25-hydroxyvitamin D result, its specimen type, report ID and collection date, plus an explicit evaluation date. Dates and technical metadata start blank or unknown; synthetic profiles fill illustrative information. Report metadata should be copied from the laboratory, not certified by patients. All supported context marker types are available in the optional section, with original units, separate dates, flags and applicable reference limits. Context results do not change points. The simplified manual form accepts one result per marker; multiple observations and explicit selection remain supported by the engine contract. No values are averaged.

Profiles cover low/plateau/high values, bounds, routine bloodwork only, B12/ferritin only, unsupported test identity, missing dates, pregnancy and pediatric cases. Withheld points display a dash. The panel preserves all engine notices, laboratory flags, collection age, coverage reasons and complete result JSON. Editing clears stale results; switching domains retains independent entries. References link to the NIH vitamin D fact sheet and Endocrine Society guideline, checked during implementation; neither validates the experimental point curve.

Verification: all **144 Python tests passed**, including the original HbA1c JavaScript parity test, HTTP/engine parity and actual-engine curve checks. JavaScript syntax and the shared DOM interaction suite passed against a real temporary server. Nutrition checks cover profiles, unit conversion, missing dates/report identity/specimen type, unreliable results, optional zero values, safe rendering of laboratory text, domain isolation, stale responses, reset and connection errors. Scoring parameters and engine rules were not changed.

The Browser runtime returned no available browser, confirmed by an empty browser list. Desktop/mobile visual verification remains outstanding; automated DOM checks do not verify rendered layout. Shared production API packaging and clinical validation remain separate work. Restart the server and refresh the dashboard to load nutrition.

## System Stability v0.2, 2026-09-25

Choose **05 · System Stability**, select **All four within illustrative ranges**, and click **Load stability profile**. Expect **100.0/100** from the sodium/potassium scoring core, one radar point, a within-reference headline and four reference diagrams. The [v0.2 specification](SYSTEM_STABILITY_V02_SPEC.md) defines provisional curves, weights and eligibility. Missing core information leaves a gap rather than zero; chloride/CO2/calcium provide supporting comparisons without changing the total.

The manual form selects one report/date/specimen group and one result per marker. Enter actual report ranges, units and interval provenance; applicability, reliability, specimen type and CO2 identity start unknown. Reference applicability and chemistry alias verification are laboratory/importer metadata, not judgments patients should make themselves. Multiple specimens/candidate observations remain supported by the engine contract rather than this simplified form. Do not combine different collections in the manual panel. Known specimen IDs must be retained. Optional total and ionized calcium remain distinct and cannot change core coverage.

Profiles cover incomplete and abnormal panels, critical flags with missing values, conflicting flags, uncertain bounds, missing ranges, interference and critical calcium alongside a within-range core panel. Report instructions and notices remain visible even with a high score. Exact interpretable results get reference diagrams; bounds keep their qualifiers without an exact-value dot or point score. The education panel lists numerical curve anchors and the 50/50 formula. JSON preserves provenance. Editing clears stale results, and switching domains retains independent entries. Shared age/pregnancy details now propagate into this domain.

Verification: the full suite passed **144 Python tests** at this checkpoint. The shared DOM interaction suite passed against an actual temporary Python server, including System Stability profiles, endpoint parity, unknown collection dates, CO2 identity, unit conversions, safe rendering of report text, stale responses, reset isolation and connection errors. One initial HTTP run encountered a Windows connection reset; the full rerun passed. Syntax checks passed. Consumer references were checked against MedlinePlus [electrolyte panel](https://medlineplus.gov/lab-tests/electrolyte-panel/), [CO2 testing](https://medlineplus.gov/lab-tests/carbon-dioxide-co2-in-blood/) and [calcium testing](https://medlineplus.gov/ency/article/003477.htm).

The Browser runtime reported no available browser, confirmed by an empty browser list. Desktop/mobile visual verification remains outstanding; DOM checks do not verify layout. Stage 5 integration packaging and clinical validation remain separate work. Restart the local server and refresh the page to load the domain. Other dashboard sections below record their own implementation checkpoints.

## Inflammation markers added, 2026-09-24

Choose **03 · Inflammation markers**, then **Worked example** and **Load inflammation profile**. Expect **80.0 hs-CRP marker points** with the separate high-WBC laboratory flag visible. The panel calls the unchanged inflammation engine through `POST /score/inflammation`; no combined inflammation total is created. `GET /model/inflammation` samples the actual engine for the explanatory curve.

The panel supports manual selection of one CRP result, explicit assay identity, qualifiers, mg/L or mg/dL, collection context, per-result dates/report IDs, optional laboratory limits and flags. WBC, neutrophils, lymphocytes, ESR and other differential counts remain separate context. The form defaults to unknown context and unknown assay sensitivity. Multiple-result selection and simultaneous CRP assay records remain available through the engine contract, rather than this simplified manual form.

Try the profiles for low hs-CRP with an abnormal WBC flag, above 10, `<1`, `<2`, CBC only, standard CRP, unknown context, pregnancy and age 16. Withheld points display a dash. Observations, qualifiers, collection age, errors, coverage and all engine notices remain visible. The three implemented domains keep independent entries; editing clears stale results. JSON output is available for inspection.

Verification: **126 Python tests passed**, JavaScript syntax passed, and the shared DOM interaction suite passed against a real temporary Python server. Added checks cover inflammation engine parity, curve parity, route restrictions, profiles, unit conversion, missing dates, zero context counts, safe rendering of laboratory text, domain isolation, stale responses and connection errors. No scoring parameters changed. Consumer reference links were checked against the linked MedlinePlus CRP and WBC pages.

The Browser runtime returned no available browser. Desktop/mobile visual verification remains outstanding; DOM checks do not verify rendering. Stage 5 integration packaging and clinical validation remain separate work. Restart the server and refresh the page to load the added domain.

## Organ stress added, 2026-09-24

Choose **Organ stress** in the domain navigation. Each implemented domain keeps independent inputs and results while switching and has its own clear button. The shared theme applies across domains. Two domain slots remain disabled placeholders. Add completed domains to `dashboard/domains.js` and supply their panel, script and local scorer route; no overall score or cross-domain weighting is defined.

The organ panel calls the existing liver/kidney engine without changing its rules. It displays **Kidney filtration estimate** and **Liver enzyme pattern** separately; there is no combined organ-stress score. Step 5 remains deferred. `/score/organ-stress` is only a local dashboard adapter, alongside `/score` and the equivalent `/score/metabolism`.

Organ-stress walkthrough:

1. Choose **Worked example** and **Load organ profile**. Expect kidney **87.5** and liver **75.0**, with the ALT notice visible. Dates are generated locally for synthetic profiles.
2. Try **eGFR >60**: expect a 75–100 point range and no exact kidney score. **eGFR ≥90** yields plateau points without inventing an exact eGFR.
3. Try missing AST, pregnancy, creatinine calculation, and age 16. Partial/withheld points and usable estimates remain distinct. Pediatric organ points follow this domain’s specification, independently of metabolism’s experimental age extension.
4. For manual entry, select reported eGFR or creatinine. Inactive-route values are retained in the form but excluded from requests. Supply actual report IDs, dates, reliability and equation metadata. U25 additionally exposes height; creatinine requires calibration information.
5. Copy ALT/AST lower and upper reference limits and explicitly confirm their applicability. Neither reference limits nor snapshot confirmation are assumed. Optional laboratory observations retain zero, qualifiers and laboratory flags, without adding points.
6. Edit a field: previous results clear immediately, and an older in-flight response cannot restore them. Switching domains preserves their independent work; reloading clears both.

Automated verification passed **56 Python tests**, including organ request routing, engine-output parity, bounds, missing metadata, pregnancy, pediatric estimates, optional context, invalid requests, and origin checks. JavaScript syntax checks passed. `test_dashboard_ui.cjs` also passed DOM interaction checks against a real temporary Python server: both domains, synthetic profiles, bounds, eligibility, missing report metadata, optional zero values, safe rendering of laboratory text, stale responses, reset isolation, theme switching and connection errors. These tests require an optional development-only `jsdom` installation under `tmp/dashboard_dom_tests`; the dashboard itself still has no package dependencies.

```powershell
npm install --prefix tmp/dashboard_dom_tests --no-save --ignore-scripts jsdom
node new_scoring_NHANES_inspired/test_dashboard_ui.cjs
```

The Browser skill reported no available browser. DOM tests do not render the page, so desktop/mobile visual verification remains outstanding.

Update: [v0.2 age extension and consumer details](AGE_EXTENSION_AND_DETAILS.md) adds experimental scoring below 20, notices at 85+, expandable marker explanations, actual-engine curve diagrams, and a snapshot calculation/weight diagram. This supersedes the original age-20 eligibility statement below. After updating Python code, restart the server and refresh the page.

From the workspace root in PowerShell:

```powershell
& ./.venv/Scripts/python.exe new_scoring_NHANES_inspired/dashboard_server.py
```

Open **http://127.0.0.1:8765**. Alternatively use a working Python 3.10+ installation. No packages or frontend build required. Change the port with `--port 8766`; stop with Ctrl+C.

## Walkthrough

1. Select **Worked example** and click **Load profile**: expect **85.6**. Profiles are synthetic and use today's specimen date for demonstration.
2. Try high LDL, incomplete bloodwork, high HDL, unknown fasting, and pregnancy profiles. Notices remain beside the total, and blocked totals display a dash rather than zero.
3. For manual entry, complete the questionnaire and select one lipid report. Enter exact values and units, laboratory reliability, dates, fasting context, and LDL method. Leave unavailable measurements blank. If dates are unavailable, explicitly confirm the selected snapshot. Numerical scores are not adjusted for age or sex; eligibility requires age 20+ and pregnancy status.
4. Click **Calculate metabolism score**. Editing a scoring field clears the result until recalculation. JSON output is available below the result.
5. Enter daily step totals for a selected seven-day window and source. Zero is a recorded day; blank is missing. The average excludes missing days. The trend compares the final three days with the first three only when all seven days are available. Changing the source/window clears entries to avoid relabeling them. Mobility context is displayed without assigning activity points.

## Scope and implementation

- `dashboard_server.py` serves allowlisted dashboard assets and calls the existing scoring engines through local adapters. It binds to loopback, checks Host/Origin, does not enable CORS, limits requests to 64 KiB, and does not log or persist submitted health data.
- `dashboard/` contains plain HTML, CSS and JavaScript. There are no external scripts/fonts, analytics, browser storage, or duplicate scoring curves. Reloading loses all entries.
- Questionnaire medication/condition/mobility answers are retained as context only. Steps never change metabolism points. Phone/watch labels mean manually transcribed totals, not connected devices. No overall health score is defined.
- Lipids share one explicit report identifier and specimen date. This simplified form supports exact numerical results; censored measurements, arbitrary multi-report editing, and optional context biomarkers remain available through the underlying engine rather than the form.
- High-level and per-marker statuses, normalization, component scores, blocking reasons, all engine flags, model version, and unknown-fasting sensitivity are shown. Scores have no invented clinical color bands.
- Step 5 remains: a supported integration API, deployment/authentication decisions, and integration documentation. The local adapter is a demonstration server, not a production deployment.

## Checks

```powershell
& ./.venv/Scripts/python.exe -m unittest discover -s new_scoring_NHANES_inspired -p 'test_*.py' -v
```

HTTP tests cover the worked example, partial inputs, pregnancy gating, marker notices, fasting sensitivity, asset delivery, invalid requests and local-origin restrictions. Existing engine and NHANES tests remain unchanged.

Browser visual and interaction verification could not be completed in this session because the Browser runtime reported no available browser. Responsive CSS is included; check the walkthrough at desktop and mobile widths before sharing the demo.
