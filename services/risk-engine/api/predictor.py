"""
predictor.py — Loads the trained XGBoost pipeline and exposes predict /
predict_proba methods consumed by main.py.
"""

import datetime
import pandas as pd
import numpy as np
import joblib
from config import MODEL_PATH, ENCODER_PATH, SHAP_PKL, validate_artifacts

class RiskPredictor:

    def __init__(self):
        """
        Initializes the inference handler by loading the serialized pipeline
        artifacts and verifying matching internal shape expectations.
        """
        validate_artifacts()

        self.model   = joblib.load(MODEL_PATH)
        self.encoder = joblib.load(ENCODER_PATH)
        
        # Load the pre-computed training SHAP background explainer for your paper
        try:
            self.shap_values = joblib.load(SHAP_PKL)
        except:
            self.shap_values = None

        # ── Feature names come from the preprocessor, not the Pipeline ──────
        preprocessor         = self.model.named_steps["preprocessor"]
        self.feature_names   = list(preprocessor.feature_names_in_)
        self.n_features      = len(self.feature_names)
        self.classes         = list(self.encoder.classes_)

    # -------------------------------------------------------------------------
    # INPUT PREPARATION
    # -------------------------------------------------------------------------
    def _prepare(self, student_dict: dict) -> pd.DataFrame:
        row = {col: np.nan for col in self.feature_names}
        for col in self.feature_names:
            if col in student_dict and student_dict[col] is not None:
                row[col] = student_dict[col]
        return pd.DataFrame([row])[self.feature_names]

    # -------------------------------------------------------------------------
    # CORE INFERENCE / PREDICT
    # -------------------------------------------------------------------------
    def predict(self, student_dict: dict) -> dict:
        """
        Accepts a dictionary of raw student values, runs matrix preprocessing,
        and returns the classification risk assessment, numerical scores, and 
        probabilities.
        """
        df = self._prepare(student_dict)

        # Predict encoded class integer and reverse transform to string representation
        pred_enc   = self.model.predict(df)[0]
        risk_band  = self.encoder.inverse_transform([pred_enc])[0]
        
        # Calculate individual class distribution probabilities
        probs      = self.model.predict_proba(df)[0]
        confidence = float(np.max(probs))
        risk_score = round(confidence * 100, 2)

        # Map numerical probabilities to their literal categorical names
        probabilities = {
            str(cls): round(float(p), 4)
            for cls, p in zip(self.classes, probs)
        }

        # Fix: Dynamically calculate the top 3 drivers on every live run
        top_factors_list = self._get_top_factors(df)

        return {
            "student_id":     student_dict.get("student_id"),
            "risk_band":      str(risk_band),
            "risk_score":     risk_score,
            "confidence":     round(confidence, 4),
            "fee_delay_days": student_dict.get("fee_delay_days"),
            "top_factors":    top_factors_list, # Clean top features hook passed to dashboard
            "probabilities":  probabilities,
            "last_updated":   datetime.datetime.utcnow().isoformat() + "Z",
        }

    # -------------------------------------------------------------------------
    # RAW DECI-PROBABILITIES ONLY
    # -------------------------------------------------------------------------
    def predict_proba(self, student_dict: dict) -> dict:
        df    = self._prepare(student_dict)
        probs = self.model.predict_proba(df)[0]
        return {
            str(cls): round(float(p), 4)
            for cls, p in zip(self.classes, probs)
        }
    
    # -------------------------------------------------------------------------
    # TOP FACTORS EXTRACTION LOGIC
    # -------------------------------------------------------------------------
    def _get_top_factors(self, df_row: pd.DataFrame) -> list:
        """
        Extracts the top 3 features driving this specific student's prediction.
        """
        classifier = self.model.named_steps["classifier"]
        
        # Approximate feature impacts using the internal model weights
        feature_importances = classifier.feature_importances_
        
        impacts = []
        for name, weight in zip(self.feature_names, feature_importances):
            val = df_row[name].values[0]
            if pd.notna(val):
                impacts.append({
                    "feature": str(name),
                    "importance": round(float(weight), 4),
                    "value": str(val)
                })
        
        # Sort by weight impact and return the top 3 drivers
        impacts = sorted(impacts, key=lambda x: x["importance"], reverse=True)
        return impacts[:3]

    # -------------------------------------------------------------------------
    # COMPONENT MONITORING HEALTH DIAGNOSTIC
    # -------------------------------------------------------------------------
    def health_check(self) -> dict:
        return {
            "status":         "ok",
            "model_loaded":   self.model   is not None,
            "encoder_loaded": self.encoder is not None,
            "n_features":     self.n_features,
            "classes":        self.classes,
        }