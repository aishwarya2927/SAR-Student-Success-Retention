# Faculty Risk Dashboard — Student Success & Retention System

This is the **Faculty Dashboard** component (Person C) of the Agentic AI Student Success and Retention System. It gives faculty and mentors a live, filterable view of student dropout risk pulled from Person A's XGBoost risk-prediction API, tools to drill into individual students, a mentoring workflow tracker, and a human-in-the-loop approval workflow for AI-generated intervention plans from Person B's Mentor Agent. Approved plans are exposed to Person D's Student Roadmap Agent via a REST API.

## What it does

- Pulls real-time risk scores for each student from the XGBoost risk API and stores them in a local SQLite database
- Displays a faculty-facing dashboard with summary metrics (total students, high/medium/low risk counts)
- Lets faculty filter students by **risk band** and **academic year** (FY / SY / TY / Final Year)
- Shows a detailed per-student view with CGPA, attendance, backlogs, fee delay, prediction confidence, and a recommended intervention
- Lets faculty **compare any two students side-by-side** on a grouped bar chart plus a summary table
- Includes a **mentoring workflow tracker** with a visual stage pipeline (flagged → assigned → scheduled → resolved, with an escalation branch) — each student is shown one relevant action at a time, and escalation reassigns the case to a dedicated escalation contact (counselor, dean, financial aid, HOD) rather than another peer mentor
- Fetches AI-generated intervention plans from Person B's Mentor Agent, stores them as `pending_approval`, and lets faculty **approve or reject** each plan
- Exposes approved plans to Person D's Student Roadmap Agent via a REST API (`services/dashboard/api.py`)

## Project structure

```
.
├── datasets/
│   └── student_success_dataset_30000.csv   # Source student data (not committed — see Data note below)
├── docs/
├── pages/
│   ├── Overview.py
│   ├── Student_Detail.py        # Intervention plan fetch + approve/reject UI
│   ├── Comparison.py
│   └── Workflow.py
├── services/
│   └── dashboard/
│       ├── api.py               # REST API exposing approved interventions to Person D
│       └── HOW_IT_WORKS.md      # Internal design notes for this service
├── app.py                       # Streamlit dashboard home (UI layer)
├── database.py                  # Builds the SQLite DB, loads dataset.csv, fetches risk scores from the API
├── utils.py                     # Shared data-loading and formatting helpers
├── requirements.txt
└── dashboard.db                  # Generated SQLite database (not committed)
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Make sure Person A's risk-prediction API is running locally at `http://localhost:8000/predict` before running `database.py` — confidence scores are fetched live from this endpoint.

3. Build the database (run this first, and re-run any time the dataset changes):
   ```bash
   python database.py
   ```
   This loads the first 200 students from the dataset CSV, calls the risk API for each one, and writes everything into `dashboard.db`. Console output will show how many students were scored by the live API vs. how many fell back to an estimated score (e.g. if the API was unreachable).

4. Start the Faculty Dashboard API (needed for Person D's integration):
   ```bash
   uvicorn services.dashboard.api:app --port 8002
   ```
   Verify at `http://127.0.0.1:8002/docs`.

5. Launch the Streamlit dashboard:
   ```bash
   streamlit run app.py
   ```
   Faculty can view students, fetch intervention plans from Person B's Mentor Agent (must be running on port 8001), and approve or reject them from the Student Detail page.

## Approval Workflow

```text
Mentor Agent generates intervention plan
                │
                ▼
   Stored in dashboard.db as
       status = pending_approval
                │
                ▼
        Faculty reviews plan
        ┌───────┴───────┐
        ▼               ▼
    Approve          Reject
        │               │
        ▼               ▼
status=approved   status=rejected
approved_by set   (faculty can click
approved_at set    "Get Intervention Plan"
        │           again to regenerate)
        ▼
  Visible to Student
  Roadmap Agent (Person D)
  via GET /intervention/{student_id}
```

Every click of "Get Intervention Plan" — whether the first attempt or a regeneration after rejection — inserts a **new row** in `intervention_reports` rather than overwriting the previous one, so rejected attempts remain in the table as history.

## Database schema

**`students`**

| Column | Type | Notes |
|---|---|---|
| `student_id` | TEXT (PK) | |
| `department` | TEXT | |
| `current_year` | TEXT | Raw value from dataset (1–4); mapped to FY/SY/TY/Final Year for display only |
| `academic_risk_band` | TEXT | Original band from source data |
| `attendance_percentage` | REAL | |
| `backlog_count` | INTEGER | |
| `fee_delay_days` | INTEGER | |
| `cgpa` | REAL | |
| `recommended_intervention` | TEXT | Static category from the source dataset — reference only, not shown as a live recommendation in the UI |
| `prediction_confidence` | REAL | From the XGBoost API (or fallback estimate). Indicates how confident the model is in the predicted `risk_band`, not the severity of risk itself |
| `risk_band` | TEXT | `high` / `medium` / `low` |
| `score_source` | TEXT | `"api"` or `"fallback"` — internal QA field, not shown in the dashboard UI |

**`mentoring_workflow`**

| Column | Type | Notes |
|---|---|---|
| `student_id` | TEXT (PK, FK) | |
| `status` | TEXT | `flagged` / `assigned` / `scheduled` / `resolved` / `escalated` |
| `assigned_mentor` | TEXT | Mentor name (regular flow), or escalation contact name if status is `escalated` |
| `meeting_date` | TEXT | |
| `outcome_notes` | TEXT | |
| `history` | TEXT | Pipe-separated audit trail, appended at each workflow transition |

**`risk_history`**

Stores a timestamped log of prediction confidence per student over time (for future trend tracking).

**`intervention_reports`**

| Column | Type | Notes |
|---|---|---|
| `intervention_id` | INTEGER (PK, autoincrement) | New row created on every generate/regenerate |
| `student_id` | TEXT (FK) | |
| `risk_band` | TEXT | |
| `prediction_confidence` | REAL | Pass-through from Person A via Person B's Mentor Agent |
| `student_summary` | TEXT | |
| `recommended_actions` | TEXT | Stored as a stringified list |
| `priority_level` | TEXT | |
| `follow_up_plan` | TEXT | |
| `status` | TEXT | `pending_approval` / `approved` / `rejected` |
| `approved_by` | TEXT | Faculty name, set on approval |
| `approved_at` | DATETIME | Set on approval |
| `generated_at` | DATETIME | Set automatically on insert |

## API Endpoints (`services/dashboard/api.py`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/intervention/{student_id}` | Get latest approved intervention for a student |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |

### GET `/intervention/{student_id}`

Returns the most recently approved intervention plan for a student, or 404 if none exists.

```json
{
  "intervention_id": 1,
  "student_id": "STU202600001",
  "risk_band": "High",
  "prediction_confidence": 87.5,
  "student_summary": "Student has poor attendance and multiple backlogs.",
  "recommended_actions": ["Schedule counseling session", "Refer to tutoring center"],
  "priority_level": "urgent",
  "follow_up_plan": "Follow up in 2 weeks to assess improvement.",
  "status": "approved",
  "approved_by": "Dr. Sharma",
  "approved_at": "2026-07-04 10:44:59",
  "generated_at": "2026-07-04 10:44:34"
}
```

Full field notes and error handling are documented separately for Person D's integration (see `faculty_dashboard_api_for_person_d.md`).

## Notes

- **`score_source` is intentionally not displayed anywhere in the dashboard UI.** It exists purely so the team can run `SELECT * FROM students WHERE score_source='fallback'` to verify which scores actually came from the live model vs. an estimated fallback, without exposing that to faculty users.
- **`prediction_confidence`** was renamed from an earlier `risk_score` field once it was confirmed the value represents model confidence in the predicted risk band, not an independent risk magnitude. All queries, columns, and UI labels were updated accordingly across `database.py`, `utils.py`, `Student_Detail.py`, and `Comparison.py`.
- **`recommended_intervention`** (static, dataset-sourced) is kept in the `students` table for reference/audit purposes but is only shown in a collapsed expander in the Student Detail page — it is not treated as a live recommendation, since that role is now filled by the Mentor Agent's `recommended_actions`.
- `current_year` is stored as the raw numeric value (1–4) from the dataset; the dashboard maps it to FY/SY/TY/Final Year for display and filtering only — the underlying data is untouched.
- The mentor list (`MENTOR_LIST`) and escalation contact list (`ESCALATION_CONTACTS`) are plain Python lists in `utils.py` for now. Could move to their own DB table later if this grows.
- `database.py`'s one-time setup (table creation, CSV load, API scoring) runs only when the file is executed directly (`python database.py`), guarded behind `if __name__ == "__main__":`. Other files safely import its functions (`insert_intervention`, `approve_intervention`, `reject_intervention`, `get_latest_approved`) without re-triggering the full data reload.
- The dataset CSV and `dashboard.db` are excluded from version control (see `.gitignore`) since they contain student data.

## Status

- [x] SQLite database with 4 tables (including `intervention_reports`)
- [x] Live prediction confidence scores from XGBoost API with fallback handling
- [x] Faculty dashboard with filtering (risk band, year)
- [x] Student detail view with Plotly chart
- [x] Student-to-student comparison view
- [x] Mentoring workflow tracker
- [x] Intervention plan generation via Person B's Mentor Agent
- [x] Faculty approve/reject workflow with full history retained
- [x] REST API exposing approved interventions to Person D
- [ ] Editable intervention plans before approval (future enhancement)
- [ ] Rejection remarks (future enhancement)