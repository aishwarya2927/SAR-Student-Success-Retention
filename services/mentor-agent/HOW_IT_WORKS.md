# Mentor Agent API

The Mentor Agent is responsible for generating personalized intervention plans for at-risk students. It integrates with the Risk Engine API, invokes supporting tools when required, and uses Gemini to generate structured intervention recommendations.

---

# Folder Structure

```text
SAR-Student-Success-Retention/
├── services/
│   ├── mentor-agent/
│   │   ├── app.py
│   │   ├── orchestrator.py
│   │   ├── requirements.txt
│   │   ├── llm/
│   │   │   └── gemini_client.py
│   │   ├── tools/
│   │   │   ├── get_risk_profile.py
│   │   │   ├── intervention_tool.py
│   │   │   ├── scholarship_tool.py
│   │   │   └── search_support_resources.py
│   │   ├── vector_store/
│   │   │   ├── chroma_db/
│   │   │   └── ingest.py
│   │   └── model_cache/
│   │
│   └── risk-engine/
│       └── api/
│           └── ... (Person A's Risk Engine API)
```

---

# Step 1 — Install Dependencies

Navigate to the Mentor Agent directory:

```bash
cd services/mentor-agent
```

Install the required packages:

```bash
pip install -r requirements.txt
```

---

# Step 2 — Start the Risk Engine API

The Mentor Agent depends on the Risk Engine developed by Person A.

Navigate to:

```bash
cd services/risk-engine/api
```

Run:

```bash
uvicorn main:app --reload --port 8000
```

Verify the API is running by opening:

```
http://127.0.0.1:8000/docs
```

---

# Step 3 — Start the Mentor Agent API

Open a new terminal.

Navigate to:

```bash
cd services/mentor-agent
```

Run:

```bash
uvicorn app:app --reload --port 8001
```

Expected output:

```text
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete.
```

---

# Step 4 — Open Swagger UI

Open the following URL in your browser:

```
http://127.0.0.1:8001/docs
```

Swagger UI allows interactive testing of the Mentor Agent endpoints.

---

# Step 5 — Test the API

Select:

```
POST /generate-intervention
```

Click **Try it out** and use the following request body:

```json
{
  "student_id": "STU202600033"
}
```

Expected response:

```json
{
  "student_id": "STU202600033",
  "risk_band": "High",
  "risk_score": 99.97,
  "student_summary": "...",
  "recommended_actions": [
    "...",
    "..."
  ],
  "priority_level": "High",
  "follow_up_plan": "...",
  "tools_called": [
    "get_risk_profile",
    "draft_intervention_plan"
  ],
  "status": "pending_approval"
}
```

---

# Step 6 — Error Handling Tests

## Invalid Student ID

Request:

```json
{
  "student_id": "INVALID001"
}
```

Expected:

- Appropriate HTTP error response.
- Mentor Agent should not crash.

---

## Risk Engine Unavailable

Stop the Risk Engine API and call:

```
POST /generate-intervention
```

Expected:

- HTTP 500 response.
- Clear error message indicating that the Risk Engine is unavailable.

---

# API Endpoints

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | Service information |
| GET | `/health` | Health check |
| POST | `/generate-intervention` | Generate an AI-based intervention plan |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc UI |

---

# Current Workflow

```text
Student ID
     │
     ▼
Mentor Agent API
     │
     ▼
Risk Engine API
     │
     ▼
Risk Profile
     │
     ▼
Gemini Intervention Planner
     │
     ▼
Structured Intervention Report
```

---

# Current Features

- Mentor Agent Orchestrator
- Risk Engine API Integration
- Gemini-based Intervention Planning
- Structured JSON Intervention Reports
- Human Approval Workflow (`pending_approval`)
- Tool Execution Tracking (`tools_called`)
- FastAPI-based REST API
- Swagger Documentation

---

# Planned Integration

The following components have already been implemented and will be automatically enabled once the Risk Engine exposes the required fields (`top_factors` and `fee_delay_days`):

- Scholarship Eligibility Tool
- RAG-based University Support Resource Retrieval (ChromaDB + HuggingFace)

No changes to the Mentor Agent API will be required.

---

# Integration for Person C (Dashboard)

### Endpoint

```http
POST http://localhost:8001/generate-intervention
```

### Request

```json
{
  "student_id": "STU202600033"
}
```

### Response

```json
{
  "student_id": "STU202600033",
  "risk_band": "High",
  "risk_score": 99.97,
  "student_summary": "...",
  "recommended_actions": [
    "...",
    "..."
  ],
  "priority_level": "High",
  "follow_up_plan": "...",
  "tools_called": [
    "get_risk_profile",
    "draft_intervention_plan"
  ],
  "status": "pending_approval"
}
```

---

# Suggested Dashboard Mapping

| Response Field | UI Component |
|----------------|--------------|
| `student_id` | Student Details |
| `risk_band` | Risk Badge |
| `risk_score` | Prediction Confidence |
| `student_summary` | Summary Card |
| `recommended_actions` | Recommended Actions List |
| `priority_level` | Priority Badge |
| `follow_up_plan` | Follow-up Section |
| `status` | Approval Status |
| `tools_called` | Debug / Audit Information |

---

# System Architecture

```text
                 React Dashboard
                        │
                        ▼
              Mentor Agent API (Person B)
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
 Risk Engine API                 Gemini LLM
   (Person A)                         │
        │                             │
        └───────────────┬─────────────┘
                        ▼
          Structured Intervention Report
```

---

# Notes

- The Mentor Agent currently consumes the Risk Engine API to obtain student risk predictions.
- Scholarship eligibility and RAG retrieval are already implemented and will be enabled automatically once the Risk Engine returns `top_factors` and `fee_delay_days`.
- All intervention recommendations require human approval before any action is taken.