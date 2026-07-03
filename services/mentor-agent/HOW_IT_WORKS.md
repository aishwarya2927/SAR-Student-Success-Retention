# Mentor Agent API

The Mentor Agent is responsible for generating personalized intervention plans for at-risk students. It integrates with the Risk Engine API, invokes supporting tools, retrieves relevant university resources, and uses Gemini to generate structured intervention recommendations for human review.

---

# Folder Structure

```text
SAR-Student-Success-Retention/
├── services/
│   ├── mentor-agent/
│   │   ├── app.py
│   │   ├── orchestrator.py
│   │   ├── requirements.txt
│   │   ├── HOW_IT_WORKS.md
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

Navigate to the Mentor Agent directory.

```bash
cd services/mentor-agent
```

Install dependencies.

```bash
pip install -r requirements.txt
```

---

# Step 2 — Start the Risk Engine API

The Mentor Agent depends on the Risk Engine API.

```bash
cd services/risk-engine/api
uvicorn main:app --reload --port 8000
```

Verify:

```
http://127.0.0.1:8000/docs
```

---

# Step 3 — Start the Mentor Agent API

Open a new terminal.

```bash
cd services/mentor-agent
uvicorn app:app --reload --port 8001
```

Expected output:

```text
INFO: Uvicorn running on http://127.0.0.1:8001
INFO: Application startup complete.
```

---

# Step 4 — Open Swagger UI

Open:

```
http://127.0.0.1:8001/docs
```

---

# Step 5 — Test the API

Select:

```
POST /generate-intervention
```

Example request:

```json
{
  "student_id": "STU202600033"
}
```

Example response:

```json
{
  "student_id": "STU202600033",
  "risk_band": "High",
  "prediction_confidence": 99.88,
  "student_summary": "...",
  "recommended_actions": [
    "...",
    "..."
  ],
  "priority_level": "High",
  "follow_up_plan": "...",
  "tools_called": [
    "get_risk_profile",
    "check_scholarship_eligibility",
    "search_support_resources",
    "draft_intervention_plan"
  ],
  "status": "pending_approval"
}
```

---

# Step 6 — Error Handling Tests

## Invalid Student ID

```json
{
  "student_id": "INVALID001"
}
```

Expected:

- HTTP error response.
- Mentor Agent remains stable.

---

## Risk Engine Unavailable

Stop the Risk Engine API.

Call:

```
POST /generate-intervention
```

Expected:

- HTTP 500 response.
- Clear error indicating that the Risk Engine is unavailable.

---

# API Endpoints

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | Service information |
| GET | `/health` | Health check |
| POST | `/generate-intervention` | Generate AI intervention plan |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc UI |

---

# Current Workflow

```text
Student ID
     │
     ▼
Risk Engine API
     │
     ▼
Risk Profile
(top_factors + fee_delay_days)
     │
     ▼
Mentor Agent Orchestrator
     │
     ├──────────────► Scholarship Eligibility Tool
     │
     ├──────────────► University Resource Retrieval (RAG)
     │
     └──────────────► Gemini Intervention Planner
                       │
                       ▼
Structured Intervention Report
                       │
                       ▼
Pending Human Approval
```

---

# Current Features

- Mentor Agent Orchestrator
- Risk Engine API Integration
- Scholarship Eligibility Tool
- RAG-based University Support Resource Retrieval (ChromaDB + HuggingFace)
- Gemini-based Intervention Planning
- Structured JSON Intervention Reports
- Human Approval Workflow (`pending_approval`)
- Tool Execution Tracking (`tools_called`)
- FastAPI REST API
- Swagger Documentation

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
  "prediction_confidence": 99.88,
  "student_summary": "...",
  "recommended_actions": [
    "...",
    "..."
  ],
  "priority_level": "High",
  "follow_up_plan": "...",
  "tools_called": [
    "get_risk_profile",
    "check_scholarship_eligibility",
    "search_support_resources",
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
| `prediction_confidence` | Confidence Indicator |
| `student_summary` | Summary Card |
| `recommended_actions` | Recommendations |
| `priority_level` | Priority Badge |
| `follow_up_plan` | Follow-up Section |
| `status` | Approval Status |
| `tools_called` | Audit / Debug Panel |

---

# System Architecture

```text
                  React Dashboard
                         │
                         ▼
               Mentor Agent API
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  Risk Engine      Scholarship Tool     RAG Retrieval
                         │                │
                         └──────┬─────────┘
                                ▼
                       Gemini Intervention Planner
                                │
                                ▼
                Structured Intervention Report
                                │
                                ▼
                     Pending Human Approval
```

---

# Notes

- The Mentor Agent consumes the Risk Engine API to obtain student risk predictions and explainability information (`top_factors`).
- Scholarship eligibility is evaluated using `fee_delay_days` returned by the Risk Engine.
- Relevant university support resources are retrieved using ChromaDB and HuggingFace embeddings before intervention generation.
- Gemini generates structured intervention recommendations based on the student's risk profile and retrieved contextual information.
- Every generated recommendation is marked as `pending_approval` to support a human-in-the-loop review workflow before any intervention is acted upon.