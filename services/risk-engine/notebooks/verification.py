# =============================================================================
# SAR PROJECT — Model Verification & Sanity Check
# Location: services/risk-engine/notebooks/verification.py
# Run:      cd services/risk-engine/notebooks && python verification.py
# =============================================================================

import os
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # non-interactive backend — safe for .py scripts
import matplotlib.pyplot as plt
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
    accuracy_score,
    f1_score,
)
from sklearn.model_selection import train_test_split

# ── Resolve the notebooks directory regardless of where Python is invoked ─────
HERE = os.path.dirname(os.path.abspath(__file__))   # .../notebooks/

# ── Paths — all relative to notebooks/ ───────────────────────────────────────
# pkl files were saved directly into notebooks/ (not notebooks/models/)
MODEL_PATH   = os.path.join(HERE, "xgboost_academic_risk_pipeline.pkl")
ENCODER_PATH = os.path.join(HERE, "label_encoder_academic_risk.pkl")

# SHAP outputs are in notebooks/shap_outputs/
SHAP_DIR     = os.path.join(HERE, "shap_outputs")
SHAP_PKL     = os.path.join(SHAP_DIR, "shap_values.pkl")
JSON_PATH    = os.path.join(SHAP_DIR, "student_explanation.json")
FI_CSV       = os.path.join(SHAP_DIR, "shap_feature_importance.csv")
REPORT_MD    = os.path.join(SHAP_DIR, "shap_report.md")
WATERFALL_PNG= os.path.join(SHAP_DIR, "student_waterfall_plot.png")

# Dataset is three levels up from notebooks/
DATA_PATH    = os.path.join(HERE, "..", "..", "..", "datasets",
                            "student_success_dataset_30000.csv")
DATA_PATH    = os.path.normpath(DATA_PATH)

# ── Helper ────────────────────────────────────────────────────────────────────
PASS = "  ✓  PASS"
FAIL = "  ✗  FAIL"
results = []

def check(condition, label, detail=""):
    status = PASS if condition else FAIL
    print(f"{status} — {label}")
    if not condition and detail:
        print(f"         {detail}")
    results.append((label, condition))
    return condition

print("Verification script loaded.")
print(f"Notebooks dir : {HERE}")
print(f"Dataset path  : {DATA_PATH}\n")


# =============================================================================
# BLOCK 1 — ARTEFACT EXISTENCE
# =============================================================================
print("=" * 60)
print("BLOCK 1 — Artefact Existence")
print("=" * 60)

artefacts = {
    "Pipeline pkl"             : MODEL_PATH,
    "LabelEncoder pkl"         : ENCODER_PATH,
    "SHAP values pkl"          : SHAP_PKL,
    "Student explanation json" : JSON_PATH,
    "SHAP feature imp. csv"    : FI_CSV,
    "SHAP report md"           : REPORT_MD,
    "Student waterfall png"    : WATERFALL_PNG,
}

for label, path in artefacts.items():
    exists = os.path.exists(path)
    size   = f"{os.path.getsize(path)/1024:.1f} KB" if exists else "—"
    check(exists, f"{label}  [{size}]", detail=f"Expected at: {path}")


# =============================================================================
# BLOCK 2 — PIPELINE INTEGRITY
# =============================================================================
print("\n" + "=" * 60)
print("BLOCK 2 — Pipeline Integrity")
print("=" * 60)

pipeline = joblib.load(MODEL_PATH)
le       = joblib.load(ENCODER_PATH)

step_names = [name for name, _ in pipeline.steps]
check(step_names == ["preprocessor", "classifier"],
      f"Pipeline steps: {step_names}",
      detail="Expected ['preprocessor', 'classifier']")

clf_type = type(pipeline.named_steps["classifier"]).__name__
check(clf_type == "XGBClassifier",
      f"Classifier type: {clf_type}",
      detail="Expected XGBClassifier")

actual_classes = sorted(list(le.classes_))
check(actual_classes == sorted(["Critical", "High", "Low", "Medium"]),
      f"LabelEncoder classes: {actual_classes}")

n_classes = pipeline.named_steps["classifier"].n_classes_
check(n_classes == 4, f"n_classes: {n_classes}", detail="Expected 4")

n_features = pipeline.named_steps["classifier"].n_features_in_
check(n_features > 0, f"n_features_in_: {n_features}")

preprocessor     = pipeline.named_steps["preprocessor"]
pipeline_columns = preprocessor.feature_names_in_.tolist()
print(f"\n  Pipeline feature count : {len(pipeline_columns)}")
print(f"  First 5 cols : {pipeline_columns[:5]}")
print(f"  Last  5 cols : {pipeline_columns[-5:]}")


# =============================================================================
# BLOCK 3 — DATA INTEGRITY
# =============================================================================
print("\n" + "=" * 60)
print("BLOCK 3 — Data Integrity")
print("=" * 60)

df = pd.read_csv(DATA_PATH)

check(len(df) == 30000,  f"Row count: {len(df)}",         detail="Expected 30 000")
check(df.isnull().sum().sum() == 0, "Zero missing values")
check(df.duplicated().sum() == 0,   "Zero duplicate rows")
check("academic_risk_band" in df.columns, "Target column present")

dist    = df["academic_risk_band"].value_counts(normalize=True) * 100
low_pct = dist.get("Low", 0)
print(f"\n  Target distribution:")
for band, pct in dist.items():
    print(f"    {band:<10}: {pct:.2f}%")
check(75 < low_pct < 90,
      f"Low class {low_pct:.1f}% in expected range 75–90%")


# =============================================================================
# BLOCK 4 — FEATURE MATRIX ALIGNMENT
# =============================================================================
print("\n" + "=" * 60)
print("BLOCK 4 — Feature Matrix Alignment")
print("=" * 60)

missing_cols = [c for c in pipeline_columns if c not in df.columns]
check(len(missing_cols) == 0,
      f"All {len(pipeline_columns)} pipeline columns present in dataframe",
      detail=f"Missing: {missing_cols}")

X             = df[pipeline_columns].copy()
X_transformed = preprocessor.transform(X)

check(X_transformed.shape == (30000, n_features),
      f"X_transformed shape: {X_transformed.shape}",
      detail=f"Expected (30000, {n_features})")

check(np.isnan(X_transformed).sum() == 0, "No NaNs in X_transformed")

KNOWN_LEAKAGE = [
    "academic_risk_score", "recommended_intervention", "recommended_career_path",
    "recommended_certification", "recommended_course_track",
    "placement_probability", "placement_readiness_score",
    "dropout_risk_band", "placement_risk_band",
]
leakage_found = [c for c in KNOWN_LEAKAGE if c in pipeline_columns]
check(len(leakage_found) == 0,
      "No known leakage columns in pipeline",
      detail=f"Leakage columns present — retrain with these removed: {leakage_found}")


# =============================================================================
# BLOCK 5 — PREDICTION SANITY
# =============================================================================
print("\n" + "=" * 60)
print("BLOCK 5 — Prediction Sanity")
print("=" * 60)

y_raw     = df["academic_risk_band"].copy()
y_encoded = le.transform(y_raw)

y_pred       = pipeline.predict(X)
y_pred_proba = pipeline.predict_proba(X)

check(y_pred.shape == (30000,),    f"y_pred shape: {y_pred.shape}")
check(y_pred_proba.shape == (30000, 4), f"y_pred_proba shape: {y_pred_proba.shape}")

prob_sums = y_pred_proba.sum(axis=1)
check(np.allclose(prob_sums, 1.0, atol=1e-5),
      "All probability rows sum to 1.0",
      detail=f"Min: {prob_sums.min():.6f}  Max: {prob_sums.max():.6f}")

unique_preds = set(le.inverse_transform(y_pred))
check(unique_preds == {"Critical", "High", "Low", "Medium"},
      f"All 4 classes predicted: {unique_preds}")

pred_dist = pd.Series(le.inverse_transform(y_pred)).value_counts(normalize=True) * 100
print(f"\n  {'Band':<12} {'Predicted':>12} {'True':>12}")
for band in ["Low", "Medium", "High", "Critical"]:
    pp = pred_dist.get(band, 0)
    tp = (y_raw == band).mean() * 100
    flag = "  ← large gap" if abs(pp - tp) > 15 else ""
    print(f"  {band:<12} {pp:>11.2f}% {tp:>11.2f}%{flag}")


# =============================================================================
# BLOCK 6 — MODEL PERFORMANCE METRICS
# =============================================================================
print("\n" + "=" * 60)
print("BLOCK 6 — Model Performance Metrics")
print("=" * 60)

X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
)

y_test_pred = pipeline.predict(X_test)
acc         = accuracy_score(y_test, y_test_pred)
f1_w        = f1_score(y_test, y_test_pred, average="weighted")
f1_macro    = f1_score(y_test, y_test_pred, average="macro")

print(f"\n  Test set size : {len(y_test)} rows")
print(f"  Accuracy      : {acc*100:.2f}%")
print(f"  Weighted F1   : {f1_w:.4f}")
print(f"  Macro F1      : {f1_macro:.4f}")

check(acc > 0.90, f"Accuracy {acc*100:.2f}% > 90%")

report = classification_report(
    y_test, y_test_pred, target_names=le.classes_, output_dict=True
)
print(f"\n  {'Class':<12} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}")
for cls in le.classes_:
    r = report[cls]
    print(f"  {cls:<12} {r['precision']:>10.4f} {r['recall']:>10.4f} "
          f"{r['f1-score']:>10.4f} {int(r['support']):>10}")

zero_recall = [cls for cls in le.classes_ if report[cls]["recall"] == 0.0]
check(len(zero_recall) == 0, "No class with recall = 0",
      detail=f"Zero-recall classes: {zero_recall}")

critical_recall = report.get("Critical", {}).get("recall", 0)
check(critical_recall > 0.50,
      f"Critical recall {critical_recall:.4f} > 0.50",
      detail="Minority class poorly caught — consider rebalancing")

cm = confusion_matrix(y_test, y_test_pred)
fig, ax = plt.subplots(figsize=(6, 5))
ConfusionMatrixDisplay(cm, display_labels=le.classes_).plot(
    ax=ax, colorbar=False, cmap="Blues"
)
ax.set_title("Confusion Matrix — Test Set (20%)", fontsize=12)
plt.tight_layout()
out_cm = os.path.join(HERE, "verification_confusion_matrix.png")
plt.savefig(out_cm, dpi=120, bbox_inches="tight")
plt.close()
print(f"\n  Saved: {out_cm}")


# =============================================================================
# BLOCK 7 — OVERFITTING CHECK
# =============================================================================
print("\n" + "=" * 60)
print("BLOCK 7 — Overfitting Check")
print("=" * 60)

train_acc = accuracy_score(y_train, pipeline.predict(X_train))
gap       = train_acc - acc
print(f"  Train accuracy : {train_acc*100:.2f}%")
print(f"  Test  accuracy : {acc*100:.2f}%")
print(f"  Gap            : {gap*100:.2f}%")
check(gap < 0.05, f"Train-test gap {gap*100:.2f}% < 5%",
      detail="Gap > 5% — consider reducing n_estimators or max_depth")


# =============================================================================
# BLOCK 8 — SHAP ARTEFACT INTEGRITY
# =============================================================================
print("\n" + "=" * 60)
print("BLOCK 8 — SHAP Artefact Integrity")
print("=" * 60)

shap_bundle   = joblib.load(SHAP_PKL)
required_keys = {"shap_values", "expected_value", "feature_names", "class_names", "generated_at"}
check(required_keys.issubset(set(shap_bundle.keys())),
      f"SHAP bundle keys: {sorted(shap_bundle.keys())}",
      detail=f"Missing: {required_keys - set(shap_bundle.keys())}")

shap_values   = shap_bundle["shap_values"]
feature_names = shap_bundle["feature_names"]
class_names   = shap_bundle["class_names"]

check(len(shap_values) == 4,
      f"shap_values list length: {len(shap_values)}")

for i, sv in enumerate(shap_values):
    check(sv.shape == (30000, n_features),
          f"shap_values[{i}] ({class_names[i]}) shape: {sv.shape}",
          detail=f"Expected (30000, {n_features})")
    check(np.isnan(sv).sum() == 0,
          f"shap_values[{i}] ({class_names[i]}) has no NaNs")

check(len(feature_names) == n_features,
      f"SHAP feature_names count {len(feature_names)} == n_features {n_features}")

shap_stack    = np.stack(shap_values, axis=2)
mean_abs_shap = np.abs(shap_stack).mean(axis=(0, 2))
top_feature   = feature_names[np.argmax(mean_abs_shap)]
top_value     = mean_abs_shap.max()
print(f"\n  Top SHAP feature : {top_feature}  (mean |SHAP| = {top_value:.4f})")
check(top_value > 0.01, f"Top SHAP value {top_value:.4f} > 0.01")


# =============================================================================
# BLOCK 9 — STUDENT EXPLANATION JSON
# =============================================================================
print("\n" + "=" * 60)
print("BLOCK 9 — Student Explanation JSON")
print("=" * 60)

with open(JSON_PATH, encoding="utf-8") as f:
    explanation = json.load(f)

required_json = {"student_id", "predicted_risk", "confidence",
                 "class_probabilities", "top_factors"}
check(required_json.issubset(set(explanation.keys())),
      f"JSON top-level keys present",
      detail=f"Missing: {required_json - set(explanation.keys())}")

pred_risk = explanation.get("predicted_risk", "")
check(pred_risk in {"Critical", "High", "Low", "Medium"},
      f"predicted_risk value: '{pred_risk}'")

confidence = explanation.get("confidence", -1)
check(0 <= confidence <= 1, f"confidence {confidence} in [0, 1]")

top_factors = explanation.get("top_factors", [])
check(len(top_factors) == 5, f"top_factors count: {len(top_factors)}")

factor_keys = {"feature", "shap_value", "feature_value", "direction"}
for i, factor in enumerate(top_factors):
    missing = factor_keys - set(factor.keys())
    check(len(missing) == 0,
          f"top_factors[{i}] keys OK",
          detail=f"Missing fields: {missing}")

print(f"\n  Student     : {explanation.get('student_id')}")
print(f"  Predicted   : {pred_risk}  (confidence {confidence:.4f})")
print(f"  Top factor  : {top_factors[0]['feature']} "
      f"(SHAP {top_factors[0]['shap_value']:+.4f})")


# =============================================================================
# BLOCK 10 — SINGLE INFERENCE TEST
# =============================================================================
print("\n" + "=" * 60)
print("BLOCK 10 — Single Inference Test (FastAPI Simulation)")
print("=" * 60)

sample_row = X.iloc[[0]]
sample_id  = df["student_id"].iloc[0]

pred_enc   = pipeline.predict(sample_row)[0]
pred_proba = pipeline.predict_proba(sample_row)[0]
pred_band  = le.inverse_transform([pred_enc])[0]

response = {
    "student_id"          : sample_id,
    "risk_band"           : pred_band,
    "risk_score"          : round(float(pred_proba[pred_enc]) * 100, 2),
    "class_probabilities" : {cls: round(float(p), 4)
                             for cls, p in zip(le.classes_, pred_proba)},
}

print(f"  Student ID   : {sample_id}")
print(f"  Risk band    : {pred_band}")
print(f"  Risk score   : {response['risk_score']}")
print(f"  Proba        : {response['class_probabilities']}")

check(pred_band in {"Critical", "High", "Low", "Medium"},
      f"Inference returned valid band: {pred_band}")
check(0 <= response["risk_score"] <= 100,
      f"Risk score {response['risk_score']} in [0, 100]")


# =============================================================================
# FINAL SUMMARY
# =============================================================================
print("\n" + "=" * 60)
print("VERIFICATION SUMMARY")
print("=" * 60)

total  = len(results)
passed = sum(1 for _, p in results if p)
failed = total - passed

for label, p in results:
    print(f"  {'✓' if p else '✗'}  {label}")

print(f"\n  {passed}/{total} checks passed")
if failed == 0:
    print("\n  ✓ ALL CHECKS PASSED — pipeline is production-ready.")
    print("    Next step: FastAPI /predict endpoint.")
else:
    print(f"\n  ✗ {failed} check(s) FAILED — fix before FastAPI integration.")