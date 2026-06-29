from pathlib import Path

# ── Project root (4 levels up from api/) ─────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# ── Artefact locations ────────────────────────────────────────────────────────
NOTEBOOK_DIR = PROJECT_ROOT / "services" / "risk-engine" / "notebooks"

MODEL_PATH   = NOTEBOOK_DIR / "xgboost_academic_risk_pipeline.pkl"
ENCODER_PATH = NOTEBOOK_DIR / "label_encoder_academic_risk.pkl"
SHAP_PKL     = NOTEBOOK_DIR / "shap_outputs" / "shap_values.pkl"

DATASET_PATH = PROJECT_ROOT / "datasets" / "student_success_dataset_30000.csv"

# ── Columns to strip from raw input before passing to pipeline ────────────────
# student_id is an identifier, not a feature.
# The remaining entries are leakage columns that the pipeline still expects
# (they were included at training time).  Remove from this list once the model
# is retrained without them.
NON_FEATURE_COLS = [
    "student_id",
    # leakage — still in current pipeline, keep feeding them for now
    # "recommended_intervention",
    # "recommended_career_path",
    # "recommended_certification",
    # "recommended_course_track",
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
