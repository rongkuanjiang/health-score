"""Wellness Health Scorer, 16-marker version.

Pipeline
--------
raw lab values  ->  score_markers()  ->  0-100 per marker
                ->  score_domains()  ->  sub-signals, domains, final score

Both functions take a pandas DataFrame with one row per person and return a
DataFrame with the same index. `score()` runs both steps and returns everything
in one frame.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 1. Marker curves
#
# Each marker maps a raw value to a 0-100 score by straight-line interpolation
# through the knots below. 100 is the healthy plateau. Values beyond the first
# or last knot take that knot's score.
#
# transform: "raw" interpolates on the value itself, "log" on log1p(value).
# Sex-specific markers hold one knot set per sex.
# ---------------------------------------------------------------------------

MARKERS: dict[str, dict] = {
    # --- Inflammation ---
    "hs_crp": {
        "unit": "mg/L", "transform": "log",
        "x": [0.08, 1.0, 3.0, 10.0, 100.0],
        "y": [100, 100, 60, 15, 0],
    },
    "leukocyte_count": {
        "unit": "x10^9/L", "transform": "log",
        "x": [0.5, 1.5, 3.0, 4.0, 11.0, 15.0, 25.0, 50.0],
        "y": [0, 15, 30, 100, 100, 60, 15, 0],
    },
    "absolute_lymphocyte": {
        "unit": "x10^9/L", "transform": "raw",
        "x": [0.2, 0.5, 1.0, 4.0, 6.0, 10.0, 20.0],
        "y": [0, 30, 100, 100, 60, 30, 0],
    },
    "absolute_neutrophil": {
        "unit": "x10^9/L", "transform": "raw",
        "x": [0.2, 0.5, 1.0, 1.5, 8.0, 10.0, 20.0, 50.0],
        "y": [0, 15, 30, 100, 100, 60, 30, 0],
    },
    # --- Metabolism ---
    "random_glucose": {
        "unit": "mmol/L", "transform": "raw",
        "x": [2.5, 3.0, 3.8, 3.9, 7.8, 11.1, 13.9, 27.8],
        "y": [0, 15, 30, 100, 100, 30, 15, 0],
    },
    "hba1c": {
        "unit": "mmol/mol", "transform": "raw",
        "x": [15.0, 20.0, 26.0, 38.0, 39.0, 48.0, 86.0, 140.0],
        "y": [15, 30, 100, 100, 60, 30, 15, 0],
    },
    "triglycerides": {
        "unit": "mmol/L", "transform": "raw",
        "x": [0.2, 2.0, 2.3, 5.6, 11.3],
        "y": [100, 100, 60, 30, 0],
    },
    "hdl": {
        "unit": "mmol/L", "transform": "raw",
        "Male":   {"x": [0.4, 0.7, 1.0, 3.5], "y": [15, 30, 100, 100]},
        "Female": {"x": [0.5, 0.9, 1.2, 3.5], "y": [15, 30, 100, 100]},
    },
    "apob": {
        "unit": "g/L", "transform": "raw",
        "x": [0.4, 0.8, 1.0, 1.2, 1.45, 2.0],
        "y": [100, 100, 85, 60, 30, 0],
    },
    "bmi": {
        "unit": "kg/m^2", "transform": "raw",
        "x": [12.0, 15.0, 17.0, 18.5, 22.0, 25.0, 30.0, 40.0],
        "y": [0, 15, 30, 60, 100, 60, 30, 15],
    },
    # --- Nutrition & Repair ---
    "albumin": {
        "unit": "g/L", "transform": "raw",
        "x": [18.0, 25.0, 32.0, 35.0, 40.0, 50.0, 55.0, 60.0],
        "y": [0, 15, 30, 60, 100, 100, 60, 30],
    },
    "vitamin_d": {
        "unit": "nmol/L", "transform": "raw",
        "x": [10.0, 25.0, 30.0, 50.0, 100.0, 125.0, 250.0, 375.0, 500.0],
        "y": [0, 15, 30, 100, 100, 60, 30, 15, 0],
    },
    # --- Organ Stress ---
    "alt": {
        "unit": "U/L", "transform": "log",
        "Male":   {"x": [2.0, 7.0, 34.0, 60.0, 350.0, 1000.0], "y": [60, 100, 100, 60, 15, 0]},
        "Female": {"x": [2.0, 7.0, 25.0, 45.0, 350.0, 1000.0], "y": [60, 100, 100, 60, 15, 0]},
    },
    "ast": {
        "unit": "U/L", "transform": "log",
        "Male":   {"x": [2.0, 8.0, 30.0, 45.0, 80.0, 150.0, 400.0, 2000.0], "y": [60, 100, 100, 60, 30, 15, 15, 0]},
        "Female": {"x": [2.0, 7.0, 25.0, 35.0, 60.0, 120.0, 400.0, 2000.0], "y": [60, 100, 100, 60, 30, 15, 15, 0]},
    },
    "egfr": {
        "unit": "mL/min/1.73m^2", "transform": "raw",
        "x": [5.0, 15.0, 30.0, 45.0, 60.0, 90.0, 120.0],
        "y": [0, 15, 30, 60, 85, 100, 100],
    },
    "uric_acid": {
        "unit": "umol/L", "transform": "raw",
        "Male":   {"x": [100.0, 420.0, 500.0, 600.0, 900.0], "y": [100, 100, 60, 30, 0]},
        "Female": {"x": [100.0, 360.0, 430.0, 500.0, 800.0], "y": [100, 100, 60, 30, 0]},
    },
}

# ---------------------------------------------------------------------------
# 2. Structure: domains -> sub-signals -> markers, with weights
#
# Markers combine into a sub-signal by weighted arithmetic mean.
# Sub-signals combine into a domain by weighted geometric mean.
# Domains combine into the final score by equal-weight geometric mean.
# Anything missing drops out and the remaining weights renormalise.
# ---------------------------------------------------------------------------

DOMAINS: dict[str, dict[str, dict]] = {
    "Inflammation": {
        "Systemic_Load": {"weight": 1.8, "markers": {"hs_crp": 1.0}},
        "WBC_Profile": {"weight": 1.0, "markers": {
            "leukocyte_count": 1.0, "absolute_lymphocyte": 1.0, "absolute_neutrophil": 1.0}},
    },
    "Metabolism": {
        "Glycemic_Control": {"weight": 1.0, "markers": {"random_glucose": 0.5, "hba1c": 1.0}},
        "Lipid_Profile": {"weight": 1.0, "markers": {"triglycerides": 1.0, "hdl": 0.5, "apob": 1.5}},
        "Body_Composition": {"weight": 1.5, "markers": {"bmi": 1.0}},
    },
    "Nutrition_Repair": {
        "Protein_Repair": {"weight": 1.0, "markers": {"albumin": 1.0}},
        "Hormonal_Structural": {"weight": 1.0, "markers": {"vitamin_d": 1.0}},
    },
    "Organ_Stress": {
        "Hepatic_Stress": {"weight": 1.2, "markers": {"alt": 1.0, "ast": 1.0}},
        "Renal_Clearance": {"weight": 2.0, "markers": {"egfr": 1.0, "uric_acid": 0.35}},
    },
}

# ---------------------------------------------------------------------------
# 3. Input handling
#
# Columns are matched by exact name after normalisation: lower-case, unit
# suffix in parentheses removed, spaces and hyphens turned into underscores.
# So "HbA1c (mmol/mol)", "hba1c" and "HbA1c" all resolve to "hba1c".
# ALIASES maps other common spellings onto the canonical key.
# ---------------------------------------------------------------------------

ALIASES: dict[str, str] = {
    "wbc": "leukocyte_count", "white_blood_cells": "leukocyte_count", "leukocytes": "leukocyte_count",
    "lymphocytes_pct": "lymphocyte_pct", "lymphocytes": "lymphocyte_pct",
    "neutrophils_pct": "neutrophil_pct", "neutrophils": "neutrophil_pct",
    "crp": "hs_crp", "hscrp": "hs_crp", "c_reactive_protein": "hs_crp",
    "glucose": "random_glucose",
    "a1c": "hba1c", "glycated_hemoglobin": "hba1c",
    "tg": "triglycerides", "triglyceride": "triglycerides",
    "hdl_c": "hdl", "hdl_cholesterol": "hdl",
    "apolipoprotein_b": "apob", "apo_b": "apob",
    "body_mass_index": "bmi",
    "vitamin_d_25_oh": "vitamin_d", "25_oh_vitamin_d": "vitamin_d", "vit_d": "vitamin_d",
    "urate": "uric_acid", "urate_uric_acid": "uric_acid", "uric_acid_urate": "uric_acid",
    "age": "assessment_age",
    "sex": "genetic_sex", "gender": "genetic_sex",
}

CONTEXT_COLUMNS = {"assessment_age", "genetic_sex", "year_of_birth", "month_of_birth", "center_visit"}
DERIVED_INPUTS = {"lymphocyte_pct", "neutrophil_pct", "fasting_glucose", "creatinine"}


def _normalise_name(name: str) -> str:
    base = str(name).split("(")[0].strip().lower()
    base = base.replace("-", "_").replace(" ", "_").replace("/", "_")
    while "__" in base:
        base = base.replace("__", "_")
    return ALIASES.get(base, base)


def _parse_sex(value) -> str | None:
    if pd.isna(value):
        return None
    v = str(value).strip().lower()
    if v in ("m", "male", "1", "1.0"):
        return "Male"
    if v in ("f", "female", "0", "0.0", "2", "2.0"):
        return "Female"
    return None


def prepare_inputs(df: pd.DataFrame) -> pd.DataFrame:
    """Return a frame with canonical column names and derived inputs filled in.

    Derivations (only when the target is absent):
      absolute_lymphocyte = leukocyte_count * lymphocyte_pct / 100
      absolute_neutrophil = leukocyte_count * neutrophil_pct / 100
      random_glucose      = fasting_glucose
      assessment_age      = center_visit - (year_of_birth, month_of_birth)
      egfr                = CKD-EPI 2009 from creatinine (umol/L), age, sex
    """
    out = pd.DataFrame(index=df.index)
    for col in df.columns:
        key = _normalise_name(col)
        if key in MARKERS or key in CONTEXT_COLUMNS or key in DERIVED_INPUTS:
            if key in out.columns:
                continue  # first occurrence wins
            out[key] = df[col]

    numeric_cols = [c for c in out.columns if c not in ("genetic_sex", "center_visit")]
    for c in numeric_cols:
        out[c] = pd.to_numeric(out[c], errors="coerce").replace([np.inf, -np.inf], np.nan)

    # Negative lab values are not physical; treat as missing.
    for key in set(MARKERS) | DERIVED_INPUTS:
        if key in out.columns:
            out.loc[out[key] < 0, key] = np.nan

    for pct in ("lymphocyte_pct", "neutrophil_pct"):
        if pct in out.columns:
            out.loc[~out[pct].between(0, 100), pct] = np.nan

    # Sex
    if "genetic_sex" in out.columns:
        out["genetic_sex"] = out["genetic_sex"].map(_parse_sex)
    else:
        out["genetic_sex"] = None

    # Age
    if "assessment_age" not in out.columns:
        if {"year_of_birth", "center_visit"} <= set(out.columns):
            visit = pd.to_datetime(out["center_visit"], errors="coerce")
            month = out["month_of_birth"] if "month_of_birth" in out.columns else 6.5
            out["assessment_age"] = (
                visit.dt.year + (visit.dt.month - 0.5) / 12.0
                - out["year_of_birth"] - (month - 0.5) / 12.0
            )
        else:
            out["assessment_age"] = np.nan
    out.loc[~out["assessment_age"].between(18, 120), "assessment_age"] = np.nan

    # Differential counts
    if "leukocyte_count" in out.columns:
        for pct, target in (("lymphocyte_pct", "absolute_lymphocyte"), ("neutrophil_pct", "absolute_neutrophil")):
            if pct in out.columns and target not in out.columns:
                out[target] = out["leukocyte_count"] * out[pct] / 100.0

    # Glucose
    if "random_glucose" not in out.columns and "fasting_glucose" in out.columns:
        out["random_glucose"] = out["fasting_glucose"]

    # eGFR (CKD-EPI 2009, no ethnicity factor)
    if "egfr" not in out.columns and "creatinine" in out.columns:
        cr = out["creatinine"] / 88.4  # umol/L -> mg/dL
        age = out["assessment_age"]
        egfr = pd.Series(np.nan, index=out.index, dtype=float)
        for sex, kappa, alpha, factor in (("Male", 0.9, -0.411, 1.0), ("Female", 0.7, -0.329, 1.018)):
            m = out["genetic_sex"].eq(sex) & age.notna() & cr.gt(0)
            r = cr[m] / kappa
            egfr[m] = 141.0 * np.minimum(r, 1.0) ** alpha * np.maximum(r, 1.0) ** -1.209 * 0.993 ** age[m] * factor
        out["egfr"] = egfr

    # Validate again after derivation, including any arithmetic overflow.
    for key in MARKERS:
        if key in out.columns:
            out[key] = out[key].replace([np.inf, -np.inf], np.nan)
            out.loc[out[key] < 0, key] = np.nan

    return out


# ---------------------------------------------------------------------------
# 4. Scoring
# ---------------------------------------------------------------------------

def _interp(values: pd.Series, x: list[float], y: list[float], transform: str) -> pd.Series:
    v = values.astype(float)
    xs = np.asarray(x, dtype=float)
    if transform == "log":
        v = np.log1p(v)
        xs = np.log1p(xs)
    scored = pd.Series(np.interp(v, xs, y), index=values.index)
    return scored.where(values.notna()).clip(0, 100)


def score_markers(df: pd.DataFrame) -> pd.DataFrame:
    """Raw lab values -> one 0-100 column per marker, named '<marker>_score'."""
    prepared = prepare_inputs(df)
    scores = pd.DataFrame(index=df.index)
    sex = prepared["genetic_sex"]

    for key, spec in MARKERS.items():
        if key not in prepared.columns:
            continue
        values = prepared[key]
        if "x" in spec:
            scores[f"{key}_score"] = _interp(values, spec["x"], spec["y"], spec["transform"])
        else:
            col = pd.Series(np.nan, index=df.index, dtype=float)
            for s in ("Male", "Female"):
                m = sex.eq(s) & values.notna()
                if m.any():
                    col[m] = _interp(values[m], spec[s]["x"], spec[s]["y"], spec["transform"])
            scores[f"{key}_score"] = col
    return scores


def _weighted_mean(frame: pd.DataFrame, weights: dict[str, float], geometric: bool) -> pd.Series:
    cols = [c for c in frame.columns if c in weights]
    if not cols:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    vals = frame[cols].astype(float)
    w = np.array([weights[c] for c in cols], dtype=float)
    present = vals.notna()
    w_sum = (present * w).sum(axis=1).replace(0, np.nan)
    if geometric:
        logs = np.log(vals + 1e-9)  # epsilon keeps a zero score from collapsing the mean to -inf
        return np.exp((logs.fillna(0) * w).sum(axis=1) / w_sum)
    return (vals.fillna(0) * w).sum(axis=1) / w_sum


def score_domains(marker_scores: pd.DataFrame) -> pd.DataFrame:
    """Marker scores -> sub-signal, domain, and final scores plus Data_Strength."""
    out = pd.DataFrame(index=marker_scores.index)
    domain_cols: list[str] = []
    n_sub_present = pd.Series(0, index=out.index)
    n_dom_present = pd.Series(0, index=out.index)

    for domain, subs in DOMAINS.items():
        sub_cols: list[str] = []
        sub_weights: dict[str, float] = {}
        for sub, spec in subs.items():
            weights = {f"{m}_score": w for m, w in spec["markers"].items()}
            s = _weighted_mean(marker_scores, weights, geometric=False)
            if s.notna().any():
                name = f"sub_{sub}"
                out[name] = s
                sub_cols.append(name)
                sub_weights[name] = spec["weight"]
                n_sub_present += s.notna().astype(int)
        if sub_cols:
            d = _weighted_mean(out[sub_cols], sub_weights, geometric=True)
            name = f"{domain}_score"
            out[name] = d
            domain_cols.append(name)
            n_dom_present += d.notna().astype(int)

    if domain_cols:
        out["Final_Health_Score"] = _weighted_mean(out[domain_cols], {c: 1.0 for c in domain_cols}, geometric=True)
    else:
        out["Final_Health_Score"] = np.nan

    n_markers = marker_scores.notna().sum(axis=1)
    total_subs = sum(len(s) for s in DOMAINS.values())
    coverage = 0.5 * n_sub_present / total_subs + 0.5 * n_dom_present / len(DOMAINS)
    out["Data_Strength"] = 100.0 * (0.5 * coverage + 0.5 * n_markers / len(MARKERS))
    return out


def score(df: pd.DataFrame) -> pd.DataFrame:
    """Convenience wrapper: raw values -> marker scores + domain scores in one frame."""
    markers = score_markers(df)
    return pd.concat([markers, score_domains(markers)], axis=1)
