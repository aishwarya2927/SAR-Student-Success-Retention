"""
main.py — FastAPI application for the Academic Risk Prediction Engine.

Endpoints:
  GET  /health             — liveness + model status check
  POST /predict            — full prediction (risk_band, score, probabilities)
  POST /predict_proba      — probabilities only
  GET  /predict/{student_id} — full prediction looked up by student_id from dataset

Run:
  cd services/risk-engine/api
  uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import traceback
import pandas as pd

from predictor import RiskPredictor
from config import DATASET_PATH
from schemas import (
    StudentInput,
    PredictionResponse,
    ProbabilityResponse,
    HealthResponse,
)

app = FastAPI(
    title="SAR Risk Engine API",
    version="1.0.0",
    description="Academic Risk Band Prediction — XGBoost + SHAP",
)

# ── Singleton predictor (loaded once at startup) ──────────────────────────────
predictor = RiskPredictor()


# ── Columns that are never model features ─────────────────────────────────────
# Same set used in test_api.py / test_predictor.py when building sample
# payloads from the raw dataset: true targets + columns derived from targets.
# student_id is handled separately (used for lookup, then dropped).
TARGET_AND_LEAKAGE_COLS = [
    "academic_risk_band",
    "academic_risk_score",
    "dropout_risk_band",
    "placement_risk_band",
    "placement_probability",
    "placement_readiness_score",
    "career_readiness_score",
]


# ── Helper: locate a student row in the dataset and extract model features ───
def get_student_by_id(student_id: str) -> dict:
    """
    Loads the dataset, finds the row matching student_id, and returns a dict
    containing only the model feature columns (student_id and target/leakage
    columns removed). Raises HTTPException(404) if not found.

    NOTE: recommended_* leakage columns are intentionally KEPT in the returned
    dict, matching the behaviour of build_sample_payload() in test_api.py,
    since the currently saved pipeline still expects them as input features.
    """
    df = pd.read_csv(DATASET_PATH)

    match = df[df["student_id"] == student_id]
    if match.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Student {student_id} not found.",
        )

    row = match.iloc[0].to_dict()

    # Drop true targets / leakage-of-target columns (not model features)
    for col in TARGET_AND_LEAKAGE_COLS:
        row.pop(col, None)

    # student_id itself is not a model feature — drop after using it to locate
    row.pop("student_id", None)

    # Convert numpy scalar types to plain Python for JSON / pydantic safety
    return {k: (v.item() if hasattr(v, "item") else v) for k, v in row.items()}


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
def health():
    """Liveness check. Returns model metadata."""
    return predictor.health_check()


# ── Predict ───────────────────────────────────────────────────────────────────
@app.post("/predict", response_model=PredictionResponse)
def predict(student: StudentInput):
    """
    Accepts a student feature object and returns:
      - risk_band       : Critical | High | Medium | Low
      - risk_score      : 0–100 (confidence × 100)
      - confidence      : raw probability of predicted class
      - probabilities   : all 4 class probabilities
      - last_updated    : ISO 8601 UTC timestamp

    Missing features are imputed by the pipeline automatically.
    """
    try:
        result = predictor.predict(student.dict())
        return result

    except ValueError as e:
        # Bad input — caller error
        raise HTTPException(status_code=422, detail=str(e))

    except Exception:
        # Internal error — return 500 with trace for debugging
        raise HTTPException(
            status_code=500,
            detail=traceback.format_exc(),
        )


# ── Predict by student_id (dataset lookup) ────────────────────────────────────
@app.get("/predict/{student_id}", response_model=PredictionResponse)
def predict_by_id(student_id: str):
    """
    Looks up student_id in the dataset, extracts the model feature columns
    for that row, and runs the exact same prediction logic as POST /predict.

    Returns the same JSON shape as POST /predict.
    Returns HTTP 404 if student_id is not found in the dataset.
    """
    feature_dict = get_student_by_id(student_id)

    try:
        result = predictor.predict(feature_dict)
        # Ensure the returned student_id matches the path param, not whatever
        # (if anything) was in the dataset row dict.
        result["student_id"] = student_id
        return result

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    except Exception:
        raise HTTPException(
            status_code=500,
            detail=traceback.format_exc(),
        )


# ── Predict proba ─────────────────────────────────────────────────────────────
@app.post("/predict_proba", response_model=ProbabilityResponse)
def predict_proba(student: StudentInput):
    """
    Returns only the class probability dict.
    Lighter than /predict — useful for dashboard sparklines.
    """
    try:
        return {"probabilities": predictor.predict_proba(student.dict())}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "service": "SAR Risk Engine API",
        "version": "1.0.0",
        "docs":    "/docs",
        "health":  "/health",
    }