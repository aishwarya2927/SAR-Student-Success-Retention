"""
predictor.py — Loads the trained XGBoost pipeline and exposes predict /
predict_proba methods consumed by main.py.

Fix from original:
  - feature_names_in_ is on the Pipeline's preprocessor step, not on the
    Pipeline object itself.  Reading it from the wrong place returned None
    and silently skipped column alignment.
"""

import datetime
import pandas as pd
import numpy as np
import joblib

from config import MODEL_PATH, ENCODER_PATH, validate_artifacts


class RiskPredictor:

    def __init__(self):
        validate_artifacts()

        self.model   = joblib.load(MODEL_PATH)
        self.encoder = joblib.load(ENCODER_PATH)

        # ── Feature names come from the preprocessor, not the Pipeline ──────
        # Pipeline.feature_names_in_ does not exist in sklearn.
        # ColumnTransformer.feature_names_in_ holds the exact column order
        # the pipeline was fitted on.
        preprocessor         = self.model.named_steps["preprocessor"]
        self.feature_names   = list(preprocessor.feature_names_in_)
        self.n_features      = len(self.feature_names)
        self.classes         = list(self.encoder.classes_)

    # -------------------------------------------------------------------------
    # INPUT PREPARATION
    # -------------------------------------------------------------------------
    def _prepare(self, student_dict: dict) -> pd.DataFrame:
        """
        Builds a single-row DataFrame in the exact column order the pipeline
        expects.  Missing columns are filled with NaN — the pipeline's imputer
        handles them.  Extra columns (e.g. student_id) are silently dropped.
        """
        # Start with an empty row of the required columns
        row = {col: np.nan for col in self.feature_names}

        # Fill in whatever the caller provided
        for col in self.feature_names:
            if col in student_dict and student_dict[col] is not None:
                row[col] = student_dict[col]

        return pd.DataFrame([row])[self.feature_names]

    # -------------------------------------------------------------------------
    # PREDICT
    # -------------------------------------------------------------------------
    def predict(self, student_dict: dict) -> dict:
        df = self._prepare(student_dict)

        pred_enc   = self.model.predict(df)[0]
        risk_band  = self.encoder.inverse_transform([pred_enc])[0]
        probs      = self.model.predict_proba(df)[0]
        confidence = float(np.max(probs))
        risk_score = round(confidence * 100, 2)

        probabilities = {
            str(cls): round(float(p), 4)
            for cls, p in zip(self.classes, probs)
        }

        return {
            "student_id":    student_dict.get("student_id"),
            "risk_band":     str(risk_band),
            "risk_score":    risk_score,
            "confidence":    round(confidence, 4),
            "probabilities": probabilities,
            "last_updated":  datetime.datetime.utcnow().isoformat() + "Z",
        }

    # -------------------------------------------------------------------------
    # PROBABILITIES ONLY
    # -------------------------------------------------------------------------
    def predict_proba(self, student_dict: dict) -> dict:
        df    = self._prepare(student_dict)
        probs = self.model.predict_proba(df)[0]
        return {
            str(cls): round(float(p), 4)
            for cls, p in zip(self.classes, probs)
        }

    # -------------------------------------------------------------------------
    # HEALTH
    # -------------------------------------------------------------------------
    def health_check(self) -> dict:
        return {
            "status":         "ok",
            "model_loaded":   self.model   is not None,
            "encoder_loaded": self.encoder is not None,
            "n_features":     self.n_features,
            "classes":        self.classes,
        }
