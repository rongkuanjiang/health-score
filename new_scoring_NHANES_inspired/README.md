# Health scorer prototype — current status

All five domains have specifications, Python engines, descriptive NHANES evaluations and dashboard panels. The shared integration package is now implemented. Start with [INTEGRATION_HANDOFF.md](INTEGRATION_HANDOFF.md) for setup, versioned API contracts, examples, rendering rules and deployment responsibilities.

Dashboard 0.1.2 starts with a basic questionnaire, followed by one unified dashboard: five prominent score cards, a pentagon chart and inline expandable biomarker sections. Calculate all domains together or load a full synthetic example. Domain shortcuts open sections without hiding the dashboard or other domains. The chart preserves existing score scopes and missing-data gaps; it does not create new scores. Restart the server and refresh the browser after updating.

| Domain | Implemented output |
|---|---|
| Metabolism | Combined HbA1c/lipid points; experimental age extension documented |
| Organ stress | Separate liver and kidney components; no combined total |
| Inflammation | Conditional hs-CRP points and contextual observations |
| Nutrition | Conditional vitamin D points and contextual observations |
| System Stability | Electrolyte reference summary and coverage; no numerical points |

The shared API does not create an overall health score. Parameters remain provisional, and descriptive evaluation does not establish clinical validity. No deep learning is used.

- [Integration handoff and API 1.0](INTEGRATION_HANDOFF.md)
- [Release review and outstanding visual acceptance](RELEASE_REVIEW.md)
- [Dashboard instructions](DASHBOARD_README.md)
- [Shared envelope JSON Schema](integration_schema.json)
- [Synthetic requests and expected responses](integration_examples/)
- [Metabolism contract](ENGINE_README.md), [age amendment](AGE_EXTENSION_AND_DETAILS.md)
- [Liver/kidney contract](LIVER_KIDNEY_ENGINE_README.md)
- [Inflammation contract](INFLAMMATION_ENGINE_README.md)
- [Nutrition contract](NUTRITION_ENGINE_README.md)
- [System Stability contract](SYSTEM_STABILITY_ENGINE_README.md)

Run `python dashboard_server.py` from this directory and open http://127.0.0.1:8765. Python 3.10+ with no runtime dependencies is sufficient. From the workspace root, the existing `.venv/Scripts/python.exe` may be used.

Step 5 implementation includes a reusable module, local versioned HTTP endpoints, documented contracts, synthetic fixtures, integration tests and an allowlisted distributable ZIP. The app team's rendered UI acceptance, named deployment owners and production deployment remain external handoff decisions. Browser visual verification remains outstanding; see the release review for exact evidence.

For maintainers, `python build_handoff.py` regenerates fixtures and the archive under `dist/`. `python verify_handoff.py` checks hashes and runs the packaged tests and CLI examples after isolated extraction. It uses a temporary directory and removes only that temporary extraction afterward.

Earlier HbA1c research and exploratory work are preserved separately under `../scoring_research_archive/`. Historical progress reports are retained as dated checkpoints and are superseded by this status page and the integration handoff.
