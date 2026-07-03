"""
main.py — FastAPI application for the Academic Risk Prediction Engine.

Endpoints:
  GET  /health             — liveness + model status check
  POST /predict            — full prediction (risk_band, score, probabilities, fee_delay_days)
  POST /predict_proba      — probabilities only
  GET  /predict/{student_id} — full prediction looked up by student_id from dataset
"""

import traceback
import datetime
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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
    description="Academic Risk Band Prediction Engine — XGBoost + SHAP Integration",
)

# ── CORS Configuration for Sub-Team Module Merging ────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singleton predictor instance
predictor = RiskPredictor()

# ── Target and True Target Leakage Columns ────────────────────────────────────
# Stripped out so the preprocessor matrix only holds valid model features.
# NOTE: fee_delay_days is kept intentionally out of this list so that the 
# scholarship team member can consume it from your engine.
TARGET_AND_LEAKAGE_COLS = [
    "academic_risk_band",
    "academic_risk_score",
    "dropout_risk_band",
    "placement_risk_band",
    "placement_probability",
    "placement_readiness_score",
    "career_readiness_score",
]

# ── Helper: Locate Student Row in Dataset ─────────────────────────────────────
def get_student_by_id(student_id: str) -> dict:
    """
    Loads the main dataset, locates the row matching student_id, and extracts
    features while ensuring cross-cutting variables remain intact.
    """
    try:
        df = pd.read_csv(DATASET_PATH)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read dataset from path: {str(e)}"
        )

    match = df[df["student_id"] == student_id]
    if match.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Student record {student_id} not found in repository.",
        )

    row = match.iloc[0].to_dict()

    # Drop true targets and target leakages
    for col in TARGET_AND_LEAKAGE_COLS:
        row.pop(col, None)

    # student_id itself is not a model feature — extract it but drop from matrix
    row.pop("student_id", None)

    # Convert numpy scalar types to plain Python for JSON / Pydantic serialization
    return {k: (v.item() if hasattr(v, "item") else v) for k, v in row.items()}


# ── Health Diagnostic ─────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["Diagnostics"])
def health():
    """Liveness check. Returns core model and encoder metadata."""
    return predictor.health_check()


# ── Predict Endpoint ──────────────────────────────────────────────────────────
@app.post("/predict", response_model=PredictionResponse, tags=["Inference"])
def predict(student: StudentInput):
    """
    Accepts a student feature object and processes full multi-class prediction.
    """
    try:
        # Compatibility handling for Pydantic v1 / v2 dump protocols
        payload = student.model_dump() if hasattr(student, "model_dump") else student.dict()
        result = predictor.predict(payload)
        return result

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail=traceback.format_exc(),
        )


# ── Predict by Student ID Lookup ──────────────────────────────────────────────
@app.get("/predict/{student_id}", response_model=PredictionResponse, tags=["Inference"])
def predict_by_id(student_id: str):
    """
    Looks up a student record by ID, extracts features, runs inference,
    and returns metrics alongside scholarship cross-cutting variables.
    """
    feature_dict = get_student_by_id(student_id)

    try:
        result = predictor.predict(feature_dict)
        # Explicitly assign key to response mapping
        result["student_id"] = student_id
        # Explicitly preserve fee_delay_days for the scholarship agent feature
        result["fee_delay_days"] = feature_dict.get("fee_delay_days")
        return result

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail=traceback.format_exc(),
        )


# ── Predict Probabilities Only ────────────────────────────────────────────────
@app.post("/predict_proba", response_model=ProbabilityResponse, tags=["Inference"])
def predict_proba(student: StudentInput):
    """
    Returns the raw probability array distribution for UI sparklines.
    """
    try:
        payload = student.model_dump() if hasattr(student, "model_dump") else student.dict()
        return {"probabilities": predictor.predict_proba(payload)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Service Root ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
def root():
    return {
        "service": "SAR Risk Engine API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }