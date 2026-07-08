import os
from pathlib import Path

# Resolve the API directory dynamically (.../services/risk-engine/api)
HERE = Path(__file__).resolve().parent

# Check if running inside Render's Docker environment or if files are flat in the api folder
if os.path.exists("/app") or (HERE / "xgboost_academic_risk_pipeline.pkl").exists():
    # ── Flat Layout (Render Docker Container AND your current local api folder) ──
    PROJECT_ROOT = HERE
    MODEL_PATH   = HERE / "xgboost_academic_risk_pipeline.pkl"
    ENCODER_PATH = HERE / "label_encoder_academic_risk.pkl"
    SHAP_PKL     = HERE / "shap_outputs" / "shap_values.pkl"
    DATASET_PATH = HERE / "student_success_dataset_30000.csv"
else:
    # ── Fallback Original Nested Layout ──
    PROJECT_ROOT = HERE.parents[1] # climbs back to risk-engine
    NOTEBOOK_DIR = PROJECT_ROOT / "notebooks"
    
    MODEL_PATH   = NOTEBOOK_DIR / "xgboost_academic_risk_pipeline.pkl"
    ENCODER_PATH = NOTEBOOK_DIR / "label_encoder_academic_risk.pkl"
    SHAP_PKL     = NOTEBOOK_DIR / "shap_outputs" / "shap_values.pkl"
    DATASET_PATH = HERE.parents[2] / "datasets" / "student_success_dataset_30000.csv"

# Keep your exact list intact
NON_FEATURE_COLS = [
    "student_id",
    "academic_risk_score",
    "academic_risk_band",
    "dropout_risk_band",
    "placement_risk_band",
    "placement_probability",
    "placement_readiness_score",
    "career_readiness_score",
    "recommended_intervention",
    "recommended_career_path",
    "recommended_certification",
    "recommended_course_track"
]

# ── Validation ────────────────────────────────────────────────────────────────
def validate_artifacts():
    missing = []
    if not MODEL_PATH.exists():
        missing.append(f"MODEL_PATH not found: {MODEL_PATH}")
    if not ENCODER_PATH.exists():
        missing.append(f"ENCODER_PATH not found: {ENCODER_PATH}")
    if missing:
        raise FileNotFoundError("\n".join(missing))