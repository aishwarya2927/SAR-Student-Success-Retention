"""
main.py — FastAPI application for the Academic Risk Prediction Engine.

Endpoints:
  GET  /health         — liveness + model status check
  POST /predict        — full prediction (risk_band, score, probabilities)
  POST /predict_proba  — probabilities only

Run:
  cd services/risk-engine/api
  uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import traceback

from predictor import RiskPredictor
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
