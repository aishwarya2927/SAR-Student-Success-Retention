# How to Run & Test the Risk Engine API

## Folder structure expected

```
SAR-Student-Success-Retention/
├── datasets/
│   └── student_success_dataset_30000.csv
└── services/
    └── risk-engine/
        ├── api/                        ← you are here
        │   ├── config.py
        │   ├── main.py
        │   ├── predictor.py
        │   ├── schemas.py
        │   ├── test_predictor.py
        │   ├── test_api.py
        │   └── requirements.txt
        └── notebooks/
            ├── xgboost_academic_risk_pipeline.pkl
            ├── label_encoder_academic_risk.pkl
            └── shap_outputs/
                └── shap_values.pkl
```

---

## Step 1 — Install dependencies

```bash
cd services/risk-engine/api
pip install -r requirements.txt
```

---

## Step 2 — Unit test the predictor (no server needed)

Run this first. It loads the model directly and checks predictions
without starting any server. Catches config / path errors early.

```bash
cd services/risk-engine/api
python test_predictor.py
```

Expected output:
```
✓ PASS — risk_band is a valid class
✓ PASS — risk_score 96.81 in [0, 100]
...
11/11 tests passed
✓ All predictor tests passed. Ready for API layer.
```

---

## Step 3 — Start the API server

```bash
cd services/risk-engine/api
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

---

## Step 4 — Check the interactive docs

Open in your browser:
```
http://127.0.0.1:8000/docs
```

This is Swagger UI — you can test every endpoint interactively.
Click an endpoint → "Try it out" → fill in fields → "Execute".

---

## Step 5 — Run integration tests (server must be running)

Open a **second terminal**:

```bash
cd services/risk-engine/api
python test_api.py
```

Expected output:
```
✓ PASS — HTTP 200
✓ PASS — status == ok
...
20/20 integration tests passed
✓ All API tests passed. Ready for Person B / C integration.
```

---

## Step 6 — Manual curl tests

```bash
# Health check
curl http://127.0.0.1:8000/health

# Minimal predict (only 3 fields — rest are imputed)
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"cgpa": 7.5, "backlog_count": 2, "attendance_percentage": 72.0}'

# Probabilities only
curl -X POST http://127.0.0.1:8000/predict_proba \
  -H "Content-Type: application/json" \
  -d '{"cgpa": 7.5, "backlog_count": 2, "attendance_percentage": 72.0}'
```

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Service info |
| GET | `/health` | Model status, n_features, classes |
| POST | `/predict` | Full prediction — risk_band, score, probabilities |
| POST | `/predict_proba` | Probabilities only |
| GET | `/docs` | Swagger UI (interactive) |
| GET | `/redoc` | ReDoc UI |

---

## Sample /predict response

```json
{
  "student_id":    "STU202600001",
  "risk_band":     "Low",
  "risk_score":    96.81,
  "confidence":    0.9681,
  "probabilities": {
    "Critical": 0.0001,
    "High":     0.0002,
    "Low":      0.9681,
    "Medium":   0.0316
  },
  "last_updated":  "2026-06-28T14:00:00Z"
}
```

---

## Known issue — leakage columns

The current saved pipeline includes 4 post-prediction columns that are
technically leakage (`recommended_intervention`, `recommended_career_path`,
`recommended_certification`, `recommended_course_track`).

For the Week 3 demo these can be left as `null` in the request payload —
the imputer fills them with the training mode value.

Action before production: retrain the model with these columns removed
from DROP_COLS and resave the pipeline.

---

## Integration for Person B (Mentor Agent)

```python
import requests

response = requests.post(
    "http://localhost:8000/predict",
    json={
        "student_id": "STU202600001",
        "cgpa": 7.2,
        "backlog_count": 3,
        "attendance_percentage": 68.0,
        "fee_delay_days": 45,
        "financial_stress_score": 72.0,
    }
)
result = response.json()
# result["risk_band"]      → "High"
# result["risk_score"]     → 87.3
# result["probabilities"]  → {"Critical":..., "High":..., ...}
```

## Integration for Person C (Dashboard)

Same call. Map `risk_band` to badge colour:
- `"Low"`      → green
- `"Medium"`   → amber
- `"High"`     → red
- `"Critical"` → dark red / flashing
