"""
predictor.py — Loads the trained XGBoost pipeline and exposes predict /
predict_proba methods consumed by main.py.

Fixes:
  - Dynamically extracts post-transformation feature names from OneHotEncoder steps.
  - Ensures xgb.DMatrix aligns shape expectations flawlessly.
  - Returns dynamic, student-specific top factors via absolute tree margins.
"""

import datetime
import pandas as pd
import numpy as np
import joblib
import xgboost as xgb
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
        """
        Builds a single-row DataFrame in the exact column order the pipeline
        expects. Missing columns are filled with NaN — the 
        pipeline's internal SimpleImputer handles them automatically.
        Extra features or non-modeled targets are safely ignored.
        """
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

        # Dynamically calculate the top 3 drivers on every live run
        top_factors_list = self._get_top_factors(df)

        return {
            "student_id":     student_dict.get("student_id"),
            "risk_band":      str(risk_band),
            "risk_score":     risk_score,
            "confidence":     round(confidence, 4),
            "confidence_score": risk_score,
            "fee_delay_days": student_dict.get("fee_delay_days"),
            "top_factors":    top_factors_list,
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
        Extracts the top 3 features uniquely driving THIS specific student's prediction
        using local tree feature weights mapped out post-preprocessing.
        """
        classifier = self.model.named_steps["classifier"]
        preprocessor = self.model.named_steps["preprocessor"]
        
        # Transform the single input row into the dense numeric matrix the model expects
        X_trans = preprocessor.transform(df_row)
        
        # Extract transformed feature names dynamically from encoders
        numeric_cols = preprocessor.transformers_[0][2]
        cat_transformer = preprocessor.transformers_[1][1]
        cat_encoder = cat_transformer.named_steps["encoder"]
        cat_base_cols = preprocessor.transformers_[1][2]
        
        try:
            encoded_cat_features = list(cat_encoder.get_feature_names_out(cat_base_cols))
            all_transformed_features = numeric_cols + encoded_cat_features
        except Exception:
            all_transformed_features = [f"feature_{i}" for i in range(X_trans.shape[1])]

        booster = classifier.get_booster()
        
        try:
            # Use safe transformed feature array length to create the DMatrix layout matching XGBoost
            row_mat = xgb.DMatrix(X_trans, feature_names=all_transformed_features)
            local_contribs = booster.predict(row_mat, pred_contribs=True)[0]
            
            # For multi-class classification, check shape dimensions to grab the primary raw coefficients
            if len(local_contribs.shape) > 1:
                # Target class index array selection
                local_features_weight = local_contribs[:, :-1].mean(axis=0)
            else:
                local_features_weight = local_contribs[:-1]
        except Exception:
            # Mathematical fallback mapping if prediction paths lock out
            feature_importances = classifier.feature_importances_
            local_features_weight = X_trans[0] * feature_importances

        # Map metrics to human-readable names
        impacts = []
        for i, weight in enumerate(local_features_weight):
            feat_name = all_transformed_features[i]
            
            # Locate value origins (maps clean values from original columns or binary indicators)
            base_col_match = [c for c in self.feature_names if c in feat_name]
            raw_val = df_row[base_col_match[0]].values[0] if base_col_match else "1"
            
            # Skip unselected sparse dimensions
            if X_trans[0, i] == 0 and feat_name not in numeric_cols:
                continue

            impacts.append({
                "feature": str(base_col_match[0] if base_col_match else feat_name),
                "importance": round(float(abs(weight)), 4),
                "value": str(raw_val)
            })
        
        # Sort by the absolute magnitude of local impact and return the top 3 drivers
        unique_impacts = {}
        for imp in impacts:
            feat = imp["feature"]
            if feat not in unique_impacts or imp["importance"] > unique_impacts[feat]["importance"]:
                unique_impacts[feat] = imp

        sorted_impacts = sorted(unique_impacts.values(), key=lambda x: x["importance"], reverse=True)
        return sorted_impacts[:3]

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