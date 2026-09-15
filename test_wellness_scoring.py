import unittest

import numpy as np
import pandas as pd

from wellness_scoring import prepare_inputs, score, score_domains, score_markers


def full_patient(**overrides):
    row = {
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
    }
    row.update(overrides)
    return pd.DataFrame([row])


class InputPreparationTests(unittest.TestCase):
    def test_absolute_counts_derived_from_wbc_and_percent(self):
        prepared = prepare_inputs(full_patient())
        self.assertAlmostEqual(prepared.loc[0, "absolute_lymphocyte"], 1.86)
        self.assertAlmostEqual(prepared.loc[0, "absolute_neutrophil"], 3.596)

    def test_age_derived_from_birth_and_visit_date(self):
        df = full_patient().drop(columns=["assessment_age"])
        df["year_of_birth"] = 1960
        df["month_of_birth"] = 6
        df["center_visit"] = "2010-06-15"
        prepared = prepare_inputs(df)
        self.assertAlmostEqual(prepared.loc[0, "assessment_age"], 50.0, places=1)

    def test_egfr_uses_ckd_epi_2009(self):
        df = full_patient(genetic_sex=1)  # male
        df["assessment_age"] = 50.0
        df["creatinine (umol/L)"] = 88.4
        prepared = prepare_inputs(df)
        self.assertAlmostEqual(prepared.loc[0, "egfr"], 87.37, places=1)

    def test_fasting_glucose_used_when_random_absent(self):
        df = full_patient().drop(columns=["random_glucose (mmol/L)"])
        df["fasting_glucose (mmol/L)"] = 5.8
        scores = score_markers(df)
        self.assertEqual(scores.loc[0, "random_glucose_score"], 100.0)

    def test_column_names_are_matched_exactly_not_by_substring(self):
        # "fasting_glucose" contains "ast"; it must not be read as AST.
        df = full_patient().drop(columns=["AST (U/L)"])
        df["fasting_glucose (mmol/L)"] = 5.8
        scores = score_markers(df)
        self.assertNotIn("ast_score", scores.columns)

    def test_negative_values_become_missing(self):
        scores = score_markers(full_patient(**{"hs_crp (mg/L)": -1.0}))
        self.assertTrue(np.isnan(scores.loc[0, "hs_crp_score"]))


class MarkerScoringTests(unittest.TestCase):
    def test_invalid_fasting_glucose_is_missing(self):
        for value in (-1, np.inf, -np.inf, "invalid"):
            with self.subTest(value=value):
                result = score(pd.DataFrame([{"fasting_glucose": value}]))
                self.assertTrue(pd.isna(result.loc[0, "random_glucose_score"]))
                self.assertTrue(pd.isna(result.loc[0, "Final_Health_Score"]))
                self.assertEqual(result.loc[0, "Data_Strength"], 0)

    def test_invalid_percentages_do_not_create_scored_counts(self):
        for column, marker in (("lymphocyte_pct", "absolute_lymphocyte"),
                               ("neutrophil_pct", "absolute_neutrophil")):
            for value in (-10, 101, np.inf, -np.inf):
                with self.subTest(column=column, value=value):
                    result = score_markers(pd.DataFrame([{"wbc": 6, column: value}]))
                    self.assertTrue(pd.isna(result.loc[0, f"{marker}_score"]))

    def test_percentage_boundaries_are_valid(self):
        prepared = prepare_inputs(pd.DataFrame([
            {"wbc": 6, "lymphocyte_pct": 0, "neutrophil_pct": 100}
        ]))
        self.assertEqual(prepared.loc[0, "absolute_lymphocyte"], 0)
        self.assertEqual(prepared.loc[0, "absolute_neutrophil"], 6)

    def test_nonfinite_marker_and_creatinine_inputs_are_missing(self):
        for value in (np.inf, -np.inf):
            with self.subTest(value=value):
                result = score_markers(pd.DataFrame([{
                    "hs_crp": value, "creatinine": value,
                    "assessment_age": 45, "genetic_sex": "Female",
                }]))
                self.assertTrue(pd.isna(result.loc[0, "hs_crp_score"]))
                self.assertTrue(pd.isna(result.loc[0, "egfr_score"]))

    def test_supplied_egfr_does_not_require_context(self):
        result = score_markers(pd.DataFrame([{"egfr": 90}]))
        self.assertEqual(result.loc[0, "egfr_score"], 100)

    def test_existing_missing_target_does_not_trigger_derivation(self):
        prepared = prepare_inputs(pd.DataFrame([{
            "random_glucose": np.nan, "fasting_glucose": 5,
            "egfr": np.nan, "creatinine": 70,
            "assessment_age": 45, "genetic_sex": "Female",
        }]))
        self.assertTrue(pd.isna(prepared.loc[0, "random_glucose"]))
        self.assertTrue(pd.isna(prepared.loc[0, "egfr"]))

    def test_healthy_values_score_100(self):
        scores = score_markers(full_patient())
        for key in ["leukocyte_count", "absolute_lymphocyte", "random_glucose", "hba1c",
                    "triglycerides", "hdl", "albumin", "vitamin_d", "alt", "ast", "egfr", "uric_acid"]:
            self.assertEqual(scores.loc[0, f"{key}_score"], 100.0, key)

    def test_unknown_sex_gives_nan_for_sex_specific_markers(self):
        scores = score_markers(full_patient(genetic_sex=np.nan))
        for key in ["hdl", "uric_acid", "alt", "ast", "egfr"]:
            self.assertTrue(np.isnan(scores.loc[0, f"{key}_score"]), key)
        self.assertEqual(scores.loc[0, "bmi_score"], 80.0)  # sex-neutral still scores

    def test_scores_are_clipped_to_0_100(self):
        scores = score_markers(full_patient(**{"hs_crp (mg/L)": 1e6, "bmi": 1.0}))
        self.assertEqual(scores.loc[0, "hs_crp_score"], 0.0)
        self.assertEqual(scores.loc[0, "bmi_score"], 0.0)


class DomainScoringTests(unittest.TestCase):
    def test_full_panel_reference_values(self):
        result = score(full_patient())
        self.assertAlmostEqual(result.loc[0, "Final_Health_Score"], 95.6, places=1)
        self.assertAlmostEqual(result.loc[0, "Inflammation_score"], 93.1, places=1)
        self.assertAlmostEqual(result.loc[0, "Metabolism_score"], 89.9, places=1)
        self.assertEqual(result.loc[0, "Data_Strength"], 100.0)

    def test_partial_panel_still_scores_and_reports_low_data_strength(self):
        df = pd.DataFrame([{"assessment_age": 45, "genetic_sex": "Female", "hs_crp (mg/L)": 1.4,
                            "ALT (U/L)": 19.0, "AST (U/L)": 21.0, "creatinine (umol/L)": 70.0, "bmi": 23.5}])
        result = score(df)
        self.assertAlmostEqual(result.loc[0, "Final_Health_Score"], 89.5, places=1)
        self.assertNotIn("Nutrition_Repair_score", result.columns)
        self.assertLess(result.loc[0, "Data_Strength"], 50.0)

    def test_no_markers_gives_nan_final_score(self):
        result = score(pd.DataFrame([{"assessment_age": 45, "genetic_sex": "Female"}]))
        self.assertTrue(np.isnan(result.loc[0, "Final_Health_Score"]))

    def test_one_bad_domain_pulls_final_down_geometrically(self):
        bad = score(full_patient(**{"creatinine (umol/L)": 400.0}))
        good = score(full_patient())
        self.assertLess(bad.loc[0, "Organ_Stress_score"], 60.0)
        self.assertLess(bad.loc[0, "Final_Health_Score"], good.loc[0, "Final_Health_Score"] - 15.0)

    def test_batch_scoring_matches_single_rows(self):
        a, b = full_patient(), full_patient(bmi=32.0)
        batch = score(pd.concat([a, b], ignore_index=True))
        self.assertAlmostEqual(batch.loc[0, "Final_Health_Score"], score(a).loc[0, "Final_Health_Score"])
        self.assertAlmostEqual(batch.loc[1, "Final_Health_Score"], score(b).loc[0, "Final_Health_Score"])


if __name__ == "__main__":
    unittest.main()
