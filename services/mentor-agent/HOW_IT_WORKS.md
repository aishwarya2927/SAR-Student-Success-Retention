# Mentor Agent API

The Mentor Agent is an AI-powered decision support service for the Student Success & Retention platform. It retrieves a student's risk profile from the Risk Engine, evaluates additional support needs, retrieves relevant university resources, and generates a structured intervention plan using Gemini. The complete workflow is orchestrated using LangGraph, enabling modular, stateful execution of each decision step.

---

# Folder Structure

```text
SAR-Student-Success-Retention/
├── services/
│   ├── mentor-agent/
│   │   ├── app.py
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   ├── state.py
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
│   │   │   ├── ingest.py
│   │   │   └── search.py
│   │   └── resources/
│   │
│   └── risk-engine/
│       └── api/
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

Verify:

```
http://127.0.0.1:8001/docs
```

---

# Step 4 — Test the API

Endpoint:

```
POST /generate-intervention
```

Example Request

```json
{
    "student_id": "STU202600033"
}
```

Example Response

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

# LangGraph Workflow

```text
                    START
                      │
                      ▼
              Risk Profile Node
                      │
                      ▼
              Risk Band Router
            ┌─────────┴─────────┐
            ▼                   ▼
      Low Risk Node      Scholarship Node
            │                   │
            │                   ▼
            │            Resource Node
            │                   │
            │                   ▼
            │          Intervention Node
            │          (Gemini + RAG)
            └───────────┬────────────┘
                        ▼
                       END
```

---

# Node Responsibilities

### Risk Profile Node

- Calls the Risk Engine API.
- Retrieves:
  - Risk Band
  - Risk Score
  - Prediction Confidence
  - Top Risk Factors
  - Fee Delay Days
- Stores the result in the LangGraph state.

### Risk Router

Routes execution based on the student's predicted risk band.

- Low Risk → Low Risk Node
- Medium / High / Critical Risk → Scholarship Node

### Low Risk Node

Creates a simple monitoring response without invoking additional tools.

### Scholarship Node

Evaluates scholarship eligibility using the student's fee delay information.

### Resource Node

Retrieves relevant university support resources from the ChromaDB vector database using semantic search.

### Intervention Node

Combines:

- Risk Profile
- Scholarship Assessment
- Retrieved University Resources

and sends them to Gemini to generate a structured intervention plan.

---

# Current Features

- LangGraph-based workflow orchestration
- Conditional routing based on student risk
- Risk Engine API integration
- Scholarship Eligibility Tool
- RAG-based university resource retrieval (ChromaDB + HuggingFace)
- Gemini intervention planning
- Automatic Gemini retry mechanism
- Structured JSON intervention reports
- Human Approval Workflow (`pending_approval`)
- Tool execution tracking (`tools_called`)
- FastAPI REST API
- Swagger documentation
- Node-level logging for workflow execution

---

# API Endpoints

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | Service Information |
| GET | `/health` | Health Check |
| POST | `/generate-intervention` | Generate AI Intervention Plan |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |

---

# Dashboard Integration

Endpoint

```http
POST http://localhost:8001/generate-intervention
```

The Mentor Dashboard consumes this endpoint to display:

- Student Risk Summary
- AI Generated Intervention Plan
- Recommended Actions
- Follow-up Plan
- Approval Status
- Tool Execution History

The API contract remains unchanged after migrating from the manual orchestrator to LangGraph.

---

# Error Handling

The Mentor Agent includes:

- Invalid Student ID handling
- Risk Engine availability checks
- Gemini JSON validation
- Automatic Gemini retry (3 attempts)
- FastAPI exception handling
- Node-level execution logging

---

# System Architecture

```text
                  React Dashboard
                         │
                         ▼
                 Mentor Agent API
                         │
                         ▼
                  LangGraph Workflow
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

- The Mentor Agent is orchestrated using LangGraph instead of a manually coded workflow.
- All business logic is encapsulated inside independent workflow nodes.
- The external API contract remains unchanged, ensuring seamless integration with the Faculty Dashboard.
- Every intervention recommendation requires human approval before any action is taken.
- The LangGraph design allows additional workflow nodes and decision branches to be incorporated with minimal changes to the overall architecture.