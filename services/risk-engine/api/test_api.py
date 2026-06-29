"""
test_api.py — Integration tests against the running FastAPI server.

REQUIRES the server to be running first:
  cd services/risk-engine/api
  uvicorn main:app --reload --port 8000

Then in a second terminal:
  cd services/risk-engine/api
  python test_api.py

Tests:
  1. GET  /health
  2. GET  /          (root)
  3. POST /predict   with a real dataset row
  4. POST /predict   with a minimal payload (3 fields)
  5. POST /predict_proba
  6. POST /predict   with an empty payload (tests imputer)
"""

import sys
import requests
import pandas as pd

from config import DATASET_PATH

BASE_URL = "http://127.0.0.1:8000"
PASS = "  ✓  PASS"
FAIL = "  ✗  FAIL"


def check(condition, label, detail=""):
    status = PASS if condition else FAIL
    print(f"{status} — {label}")
    if not condition and detail:
        print(f"         {detail}")
    return condition


def build_sample_payload():
    """
    Load one row from the dataset and strip columns that are NOT
    pipeline features (true targets, scores derived from the target).
    The recommended_* leakage columns are intentionally kept because
    the current saved pipeline still expects them.
    """
    df = pd.read_csv(DATASET_PATH)

    drop_cols = [
        "academic_risk_band",
        "academic_risk_score",
        "dropout_risk_band",
        "placement_risk_band",
        "placement_probability",
        "placement_readiness_score",
        "career_readiness_score",
    ]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])

    row = df.iloc[0].to_dict()

    # Convert numpy types to plain Python (required for JSON serialisation)
    return {k: (v.item() if hasattr(v, "item") else v) for k, v in row.items()}


def main():
    print("=" * 58)
    print("FastAPI Integration Tests")
    print(f"Base URL: {BASE_URL}")
    print("=" * 58)

    results = []

    # ── Test 1 — Health ───────────────────────────────────────────────────────
    print("\n── Test 1: GET /health ──")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"  Status code : {r.status_code}")
        print(f"  Body        : {r.json()}")
        body = r.json()
        results.append(check(r.status_code == 200,          "HTTP 200"))
        results.append(check(body.get("status") == "ok",    "status == ok"))
        results.append(check(body.get("model_loaded"),       "model_loaded"))
        results.append(check(body.get("n_features") == 62,  f"n_features == 62  (got {body.get('n_features')})"))
    except requests.exceptions.ConnectionError:
        print(f"\n  ERROR: Cannot connect to {BASE_URL}")
        print("  Make sure the server is running:")
        print("    cd services/risk-engine/api")
        print("    uvicorn main:app --reload --port 8000")
        sys.exit(1)

    # ── Test 2 — Root ─────────────────────────────────────────────────────────
    print("\n── Test 2: GET / ──")
    r = requests.get(f"{BASE_URL}/", timeout=5)
    print(f"  Status code : {r.status_code}")
    print(f"  Body        : {r.json()}")
    results.append(check(r.status_code == 200, "HTTP 200"))
    results.append(check("docs" in r.json(),   "docs key present"))

    # ── Test 3 — Full predict (real row) ─────────────────────────────────────
    print("\n── Test 3: POST /predict  (real dataset row) ──")
    payload = build_sample_payload()
    r = requests.post(f"{BASE_URL}/predict", json=payload, timeout=10)
    print(f"  Status code : {r.status_code}")
    body = r.json()
    print(f"  risk_band   : {body.get('risk_band')}")
    print(f"  risk_score  : {body.get('risk_score')}")
    print(f"  confidence  : {body.get('confidence')}")
    print(f"  student_id  : {body.get('student_id')}")

    results.append(check(r.status_code == 200, "HTTP 200"))
    results.append(check(
        body.get("risk_band") in {"Critical", "High", "Medium", "Low"},
        f"risk_band valid: {body.get('risk_band')}"
    ))
    results.append(check(
        0 <= (body.get("risk_score") or -1) <= 100,
        f"risk_score in [0,100]: {body.get('risk_score')}"
    ))
    results.append(check(
        set(body.get("probabilities", {}).keys()) == {"Critical", "High", "Low", "Medium"},
        "probabilities has all 4 classes"
    ))
    results.append(check(
        "last_updated" in body,
        "last_updated present"
    ))

    # ── Test 4 — Minimal payload (3 fields) ──────────────────────────────────
    print("\n── Test 4: POST /predict  (minimal — 3 fields) ──")
    minimal = {
        "cgpa":                   7.5,
        "backlog_count":          2,
        "attendance_percentage":  72.0,
    }
    r = requests.post(f"{BASE_URL}/predict", json=minimal, timeout=10)
    print(f"  Status code : {r.status_code}")
    body = r.json()
    print(f"  risk_band   : {body.get('risk_band')}")
    print(f"  confidence  : {body.get('confidence')}")

    results.append(check(r.status_code == 200, "HTTP 200 on minimal input"))
    results.append(check(
        body.get("risk_band") in {"Critical", "High", "Medium", "Low"},
        f"risk_band valid: {body.get('risk_band')}"
    ))

    # ── Test 5 — predict_proba ────────────────────────────────────────────────
    print("\n── Test 5: POST /predict_proba ──")
    r = requests.post(f"{BASE_URL}/predict_proba", json=minimal, timeout=10)
    print(f"  Status code : {r.status_code}")
    body = r.json()
    probs = body.get("probabilities", {})
    print(f"  Proba : {probs}")

    results.append(check(r.status_code == 200, "HTTP 200"))
    results.append(check(len(probs) == 4,       "4 probabilities returned"))
    results.append(check(
        abs(sum(probs.values()) - 1.0) < 1e-4,
        f"probabilities sum to 1.0  ({sum(probs.values()):.6f})"
    ))

    # ── Test 6 — Empty payload (all features imputed) ─────────────────────────
    print("\n── Test 6: POST /predict  (empty payload — all imputed) ──")
    r = requests.post(f"{BASE_URL}/predict", json={}, timeout=10)
    print(f"  Status code : {r.status_code}")
    body = r.json()
    print(f"  risk_band   : {body.get('risk_band')}")

    results.append(check(r.status_code == 200, "HTTP 200 on empty payload"))
    results.append(check(
        body.get("risk_band") in {"Critical", "High", "Medium", "Low"},
        f"risk_band valid on empty payload: {body.get('risk_band')}"
    ))

    # ── Summary ───────────────────────────────────────────────────────────────
    passed = sum(results)
    total  = len(results)
    print(f"\n{'='*58}")
    print(f"  {passed}/{total} integration tests passed")
    if passed == total:
        print("  ✓ All API tests passed. Ready for Person B / C integration.")
    else:
        print("  ✗ Fix failures above. Check server logs for details.")
    print("=" * 58)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
