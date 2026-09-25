# Nutrition engine v0.2

Nutrition now returns one **B12/ferritin domain score out of 100**. See [the complete specification](NUTRITION_V02_SPEC.md) for Canadian evidence, provisional curves, confounders and availability limits. This is a limited laboratory profile, not overall nutrient adequacy or diet quality.

The core is B12 50% plus ferritin 50%; both must be usable and from the same report, collection date and specimen type. Vitamin D retains a separate optional component and never changes the total. No weights are redistributed for missing inputs.

Run `python nutrition_score.py example_nutrition_request.json` from this directory. The synthetic example returns `domain_score: 75.0`, `display_score: "75.0"`, B12 50 points and ferritin 100 points. Its vitamin D component is also 75 points, independently. The supplied low-albumin flag remains visible. Example reference limits are synthetic, not clinical defaults.

The request retains `evaluation_date`, `person`, `context`, and `observations`. Required core observation metadata includes observation/report IDs, collection date, supported analyte/specimen, units and applicable laboratory reference limits. See [the request fixture](example_nutrition_request.json). Repeated measurements require `selected_observation_ids`. Pregnancy/age eligibility, result reliability, bounds, high results and confounders can withhold points with reasons.

Import `score_nutrition` for Python use. HTTP endpoints remain `POST /score/nutrition`, `GET /model/nutrition`, and shared `POST /api/v1/score`. The model endpoint exposes required markers, weights, core curves, collection policy and the existing optional vitamin D curve. Main score fields are `domain_score`, `score`, `display_score`; components retain weights and contributions. Display all marker and lab notices alongside the total.

`nutrition_v01_parameters.json` retains its filename for compatibility but now identifies v0.2. Historical vitamin-D-only evaluation files under `nhanes_inventory/nutrition_v01_*` do not validate this model. The historical evaluator CLI is guarded against overwriting them with a newer engine. No representative Canadian report-coverage audit or clinical validation has been completed.

Engine, HTTP and DOM interaction tests are implementation checks. Browser rendering and clinical validity require separate verification. See `test_nutrition_v02.py`, `test_nutrition_score.py`, `test_dashboard.py` and `test_dashboard_ui.cjs`.
