"""
test_predictor.py — Direct unit test for RiskPredictor (no server needed).

Run:
  cd services/risk-engine/api
  python test_predictor.py

Tests:
  1. Predict on a real row from the dataset
  2. Predict on a minimal input (only 3 fields — rest imputed)
  3. predict_proba returns 4 probabilities summing to 1.0
  4. health_check returns expected keys
"""

import sys
import pandas as pd
import numpy as np

from config import DATASET_PATH
from predictor import RiskPredictor

PASS = "  ✓  PASS"
FAIL = "  ✗  FAIL"

def check(condition, label, detail=""):
    status = PASS if condition else FAIL
    print(f"{status} — {label}")
    if not condition and detail:
        print(f"         {detail}")
    return condition


def main():
    print("=" * 55)
    print("RiskPredictor Unit Tests")
    print("=" * 55)

    predictor = RiskPredictor()
    results   = []

    # ── Test 1 — Predict on a real dataset row ────────────────────────────────
    print("\n── Test 1: Real dataset row ──")

    df = pd.read_csv(DATASET_PATH)

    # Drop only the true target + columns that are NOT in the pipeline
    # (student_id is not a pipeline feature; targets are not features)
    # We keep recommended_* because the current pipeline still expects them.
    drop_cols = [
        "student_id",
        "academic_risk_band",   # target — never feed to predictor
        "academic_risk_score",  # direct leakage of target
        "dropout_risk_band",    # separate target
        "placement_risk_band",  # separate target
        "placement_probability",
        "placement_readiness_score",
        "career_readiness_score",
    ]
    df_features = df.drop(columns=[c for c in drop_cols if c in df.columns])

    sample      = df_features.iloc[0].to_dict()
    sample["student_id"] = df["student_id"].iloc[0]   # pass id for display

    true_band   = df["academic_risk_band"].iloc[0]

    result = predictor.predict(sample)

    print(f"  Student ID      : {result['student_id']}")
    print(f"  True band       : {true_band}")
    print(f"  Predicted band  : {result['risk_band']}")
    print(f"  Risk score      : {result['risk_score']}")
    print(f"  Confidence      : {result['confidence']}")
    print(f"  Probabilities   : {result['probabilities']}")
    print(f"  Last updated    : {result['last_updated']}")

    results.append(check(
        result["risk_band"] in {"Critical", "High", "Medium", "Low"},
        "risk_band is a valid class"
    ))
    results.append(check(
        0 <= result["risk_score"] <= 100,
        f"risk_score {result['risk_score']} in [0, 100]"
    ))
    results.append(check(
        0 <= result["confidence"] <= 1,
        f"confidence {result['confidence']} in [0, 1]"
    ))
    results.append(check(
        set(result["probabilities"].keys()) == {"Critical", "High", "Low", "Medium"},
        "probabilities has all 4 classes"
    ))
    results.append(check(
        abs(sum(result["probabilities"].values()) - 1.0) < 1e-4,
        f"probabilities sum to 1.0  ({sum(result['probabilities'].values()):.6f})"
    ))

    # ── Test 2 — Minimal input (only 3 fields provided) ───────────────────────
    print("\n── Test 2: Minimal input (3 fields — rest NaN-imputed) ──")

    minimal = {
        "cgpa":          7.5,
        "backlog_count": 2,
        "attendance_percentage": 72.0,
    }
    result2 = predictor.predict(minimal)

    print(f"  Predicted band  : {result2['risk_band']}")
    print(f"  Confidence      : {result2['confidence']}")

    results.append(check(
        result2["risk_band"] in {"Critical", "High", "Medium", "Low"},
        "Minimal input: valid band returned"
    ))

    # ── Test 3 — predict_proba ────────────────────────────────────────────────
    print("\n── Test 3: predict_proba ──")

    proba = predictor.predict_proba(sample)
    print(f"  Probabilities: {proba}")

    results.append(check(
        len(proba) == 4,
        "predict_proba returns 4 entries"
    ))
    results.append(check(
        abs(sum(proba.values()) - 1.0) < 1e-4,
        f"predict_proba sums to 1.0  ({sum(proba.values()):.6f})"
    ))

    # ── Test 4 — health_check ─────────────────────────────────────────────────
    print("\n── Test 4: health_check ──")

    health = predictor.health_check()
    print(f"  {health}")

    results.append(check(health["status"]         == "ok",    "status == ok"))
    results.append(check(health["model_loaded"]   is True,    "model_loaded"))
    results.append(check(health["encoder_loaded"] is True,    "encoder_loaded"))
    results.append(check(health["n_features"]     == 62,      f"n_features == 62  (got {health['n_features']})"))
    results.append(check(len(health["classes"])   == 4,       "4 classes"))

    # ── Summary ───────────────────────────────────────────────────────────────
    passed = sum(results)
    total  = len(results)
    print(f"\n{'='*55}")
    print(f"  {passed}/{total} tests passed")
    if passed == total:
        print("  ✓ All predictor tests passed. Ready for API layer.")
    else:
        print("  ✗ Fix failures above before starting the server.")
    print("=" * 55)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
