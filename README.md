# Health scorer dashboard

The current five-domain dashboard is in [new_scoring_NHANES_inspired](new_scoring_NHANES_inspired/). It includes the initial questionnaire, optional wearable step data, bloodwork entry, scores and charts. This is a research prototype, not a clinically validated health assessment.

## Run the dashboard

1. Clone this repository, or choose **Code > Download ZIP** and extract it.
2. Install Python 3.10 or newer if needed.
3. Open a terminal in the repository folder and run:

```bash
cd new_scoring_NHANES_inspired
python dashboard_server.py
```

On Windows, `py dashboard_server.py` also works if Python is installed through the launcher.

4. Open **http://127.0.0.1:8765** in your browser. Keep the terminal running; press Ctrl+C to stop the server.
5. Complete the questionnaire, then enter your biomarkers or choose **Try a full example** for synthetic demonstration data.

The dashboard uses only the Python standard library. No pip installation, Node, database or frontend build is needed. The root `requirements.txt` applies only to the legacy scorer below. Entries last for the open page; reloading clears them. Wearable entries are manual, with no device connection.

GitHub stores the source code here; run the Python server to use the dashboard. Opening `index.html` directly will not run the scoring API.

See [dashboard notes](new_scoring_NHANES_inspired/DASHBOARD_README.md) and [integration instructions](new_scoring_NHANES_inspired/INTEGRATION_HANDOFF.md) for details. No overall health score is defined by the new dashboard.

## Checks

From `new_scoring_NHANES_inspired`, run:

```bash
python -m unittest discover -s . -p "test_*.py"
```

The shared package passed 118 Python tests and its JavaScript integration checks before upload. Rendered browser layout review remains outstanding.

---

## Legacy scorer

The original scorer remains below and in the repository root. Its four-domain combined score is a separate historical implementation.

# Wellness Health Scorer

A Python module that converts a routine blood panel into a 0–100 health score with four interpretable domains. This is the 16-marker version of the score, packaged for integration testing. It is a single file with no external services and no data files, depending only on NumPy and pandas.

## Contents

| File | Purpose |
|---|---|
| `wellness_scoring.py` | The scoring engine, about 300 lines. Marker curves and domain structure are plain dictionaries at the top; the scoring functions follow. |
| `test_wellness_scoring.py` | 20 unit tests. Run with `python -m unittest test_wellness_scoring`. |
| `requirements.txt` | Python dependencies. |

## Quick start

```bash
pip install -r requirements.txt
```

```python
import pandas as pd
from wellness_scoring import score

patient = pd.DataFrame([{
    "assessment_age": 45,
    "genetic_sex": "Female",
    "leukocyte_count (x10^9/L)": 6.2,
    "lymphocytes_pct (%)": 30.0,
    "neutrophil_pct (%)": 58.0,
    "hs_crp (mg/L)": 1.4,
    "random_glucose (mmol/L)": 5.3,
    "HbA1c (mmol/mol)": 35.0,
    "triglycerides (mmol/L)": 1.1,
    "HDL (mmol/L)": 1.6,
    "ApoB (g/L)": 0.9,
    "bmi": 23.5,
    "albumin (g/L)": 44.0,
    "vitamin_d (nmol/L)": 62.0,
    "ALT (U/L)": 19.0,
    "AST (U/L)": 21.0,
    "creatinine (umol/L)": 70.0,
    "urate_uric_acid (umol/L)": 280.0,
}])

result = score(patient)
print(result.loc[0, "Final_Health_Score"])   # 95.6
```

`score()` accepts one row per person, so batch scoring is the same call with more rows. If you want the two stages separately, `score_markers(df)` returns the per-marker scores and `score_domains(marker_scores)` aggregates them.

## Input contract

One row per person. Units are fixed; convert before calling. Unit labels in column names are discarded, not checked or used for conversion.

Derived inputs are calculated only when the target column is absent from the entire input table. An existing column with missing cells does not trigger per-person fallback. This applies to absolute differential counts, random glucose, age, and eGFR.

### Column naming

Column names are normalised before matching: lower-cased, anything in parentheses removed, spaces and hyphens turned into underscores. So `HbA1c (mmol/mol)`, `hba1c`, and `HbA1c` all resolve to the same marker. Matching is then exact, so an unrelated column cannot be picked up by accident. Common alternative spellings are accepted (`wbc`, `crp`, `glucose`, `a1c`, `urate`, `age`, `sex`, and others; see `ALIASES` in the module). Columns that don't match anything are ignored.

### Required context

| Column | Values | Used for |
|---|---|---|
| `assessment_age` | years, 18–120 | eGFR derivation. Alternatively supply `year_of_birth`, `month_of_birth`, and `center_visit` (a date) and age is computed. |
| `genetic_sex` | `Male`, `Female`, `M`, `F`, `1` (male), `0` or `2` (female) | Sex-specific curves for HDL, urate, ALT, AST, and the eGFR formula. Missing or unrecognised sex prevents scoring those four sex-specific markers and deriving eGFR. Directly supplied eGFR can be scored without age or sex. |

### The 16 markers

| Column | Unit | Notes |
|---|---|---|
| `leukocyte_count` | ×10⁹/L | Total white blood cells. |
| `lymphocytes_pct` | % | With `leukocyte_count`, the absolute count is derived. Or supply `absolute_lymphocyte` in ×10⁹/L directly. |
| `neutrophil_pct` | % | Same; or supply `absolute_neutrophil`. |
| `hs_crp` | mg/L | High-sensitivity CRP. |
| `random_glucose` | mmol/L | Non-fasting curve. `fasting_glucose` is accepted as a substitute if `random_glucose` is absent. |
| `hba1c` | mmol/mol | IFCC units. From %: `(pct − 2.15) × 10.929`. |
| `triglycerides` | mmol/L | Non-fasting curve. |
| `hdl` | mmol/L | Sex-specific. |
| `apob` | g/L | |
| `bmi` | kg/m² | |
| `albumin` | g/L | |
| `vitamin_d` | nmol/L | 25-hydroxy vitamin D. From ng/mL: `× 2.496`. |
| `alt` | U/L | Sex-specific. |
| `ast` | U/L | Sex-specific. |
| `creatinine` | µmol/L | Converted to eGFR (CKD-EPI 2009, no ethnicity factor) using age and sex. Or supply `egfr` in mL/min/1.73 m² directly. |
| `uric_acid` | µmol/L | Sex-specific. `urate` also accepted. |

### Failsafes

- Missing markers are allowed. Leave the column out or set the value to `NaN`. The score is computed from whatever is present and `Data_Strength` reports how complete the input was.
- Non-numeric and infinite numeric values are treated as missing.
- Negative lab values are treated as missing, including inputs used in derivations. Derived marker values are checked again before scoring.
- Differential percentages outside 0–100 are treated as missing; percentages must be supplied as 30 for 30%, not 0.30.
- Values outside the curve's range take the score at the nearest end of the curve. Marker scores are always within 0–100.
- If no marker is present, `Final_Health_Score` is `NaN` rather than an error.

## Output contract

Scores are on a 0–100 scale (geometric averages may exceed 100 by a tiny floating-point offset). Missing values are `NaN`. A sub-signal or domain column is omitted if no person in the batch has a valid score for it; otherwise it is present with `NaN` for people without that component. Marker columns may also be absent when the input marker is unavailable. Consumers must handle both absent fields and missing values.

`Data_Strength` measures data coverage, not statistical confidence, and does not reduce the final score. There is no minimum coverage requirement: even one marker can produce a final score. The host app should decide when it has enough data to display a score.

| Column | Built from | Weight inside its parent |
|---|---|---|
| `<marker>_score` | one column per marker supplied | see below |
| `sub_Systemic_Load` | hs_crp | 1.8 in Inflammation |
| `sub_WBC_Profile` | leukocyte_count, absolute_lymphocyte, absolute_neutrophil (all 1.0) | 1.0 |
| `sub_Glycemic_Control` | random_glucose 0.5, hba1c 1.0 | 1.0 in Metabolism |
| `sub_Lipid_Profile` | triglycerides 1.0, hdl 0.5, apob 1.5 | 1.0 |
| `sub_Body_Composition` | bmi | 1.5 |
| `sub_Protein_Repair` | albumin | 1.0 in Nutrition & Repair |
| `sub_Hormonal_Structural` | vitamin_d | 1.0 |
| `sub_Hepatic_Stress` | alt, ast (both 1.0) | 1.2 in Organ Stress |
| `sub_Renal_Clearance` | egfr 1.0, uric_acid 0.35 | 2.0 |
| `Inflammation_score` | Systemic_Load, WBC_Profile | 1.0 |
| `Metabolism_score` | Glycemic_Control, Lipid_Profile, Body_Composition | 1.0 |
| `Nutrition_Repair_score` | Protein_Repair, Hormonal_Structural | 1.0 |
| `Organ_Stress_score` | Hepatic_Stress, Renal_Clearance | 1.0 |
| `Final_Health_Score` | the four domains | **the headline number** |
| `Data_Strength` | input completeness; 100 means all 16 markers present | |

### Worked example

The quick-start input produces:

```
sub_Systemic_Load         89.5
sub_WBC_Profile          100.0
sub_Glycemic_Control     100.0
sub_Lipid_Profile         96.2
sub_Body_Composition      80.0
sub_Protein_Repair       100.0
sub_Hormonal_Structural  100.0
sub_Hepatic_Stress       100.0
sub_Renal_Clearance      100.0
Inflammation_score        93.1
Metabolism_score          89.9
Nutrition_Repair_score   100.0
Organ_Stress_score       100.0
Final_Health_Score        95.6
Data_Strength            100.0
```

The same person with only hs-CRP, ALT, AST, creatinine, and BMI supplied scores 89.5 with `Data_Strength` 45.5. Nutrition & Repair is absent from the output because none of its markers were given.

## How the score works

1. **Marker scoring.** Each raw value is mapped to 0–100 by straight-line interpolation through clinically anchored knots. 100 is the healthy plateau. hs-CRP, WBC, ALT, and AST are interpolated on a log scale because they are right-skewed. HDL, urate, ALT, and AST have separate male and female curves. The knots are the `MARKERS` dictionary at the top of the module.
2. **Sub-signals.** Markers combine by weighted arithmetic mean.
3. **Domains.** Sub-signals combine by weighted geometric mean. The geometric mean penalises one bad component more than an arithmetic mean would, so a failing sub-signal cannot be hidden by good ones.
4. **Final score.** Equal-weight geometric mean of the four domains.

At every level, missing components drop out and the remaining weights renormalise. The structure and all weights are the `DOMAINS` dictionary at the top of the module.

## Interpretation

| Final score | Band |
|---|---|
| 60–100 | Green |
| 30–59 | Amber |
| 0–29 | Red |

The score describes distance from a healthy reference, not disease risk. It is not a diagnostic tool and has not been validated for clinical decision-making.

## Wrapping as a service

If the host application is not Python, the simplest integration is one HTTP endpoint that accepts a JSON object with the input columns above and returns the output columns. The following is an optional example, not a bundled running service. Install `fastapi` and an ASGI server such as `uvicorn` separately to use it; the scoring engine itself needs only NumPy and pandas. This wrapper omits missing fields, including `Final_Health_Score` when no markers can be scored:

```python
from fastapi import FastAPI
import pandas as pd
from wellness_scoring import score

app = FastAPI()

@app.post("/score")
def score_endpoint(payload: dict):
    result = score(pd.DataFrame([payload]))
    return result.iloc[0].dropna().to_dict()
```

## Known limitations of this version

- Curves and weights were developed on UK Biobank, a cohort aged 40–69. Scores for people outside that range have not been checked.
- Sub-signal weights were fit to hospital diagnosis counts, which favours markers that reflect existing illness over early-warning markers such as lipids.
- hs-CRP, ApoB, and vitamin D are not on standard blood panels. When they are absent the Inflammation and Nutrition & Repair domains rest on fewer markers.
- This version omits the interaction penalties present in the research build. On a random test set they lowered the score for about a third of people by 16 points on average; without them the score is the base aggregate only.

A revised version built on the routinely available CBC, metabolic, and lipid panels is in development.
