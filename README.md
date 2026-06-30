# Faculty Risk Dashboard — Student Success & Retention System

This is the **Faculty Dashboard** component (Person C) of the Agentic AI Student Success and Retention System. It gives faculty and mentors a live, filterable view of student dropout risk, pulled from Person A's XGBoost risk-prediction API, along with tools to drill into individual students and track mentoring follow-ups.

## What it does

- Pulls real-time risk scores for each student from the XGBoost risk API and stores them in a local SQLite database
- Displays a faculty-facing dashboard with summary metrics (total students, high/medium/low risk counts)
- Lets faculty filter students by **risk band** and **academic year** (FY / SY / TY / Final Year)
- Shows a detailed per-student view with CGPA, attendance, backlogs, fee delay, risk score, and a recommended intervention
- Lets faculty **compare any two students side-by-side** on a grouped bar chart plus a summary table
- Includes a **mentoring workflow tracker** with a visual stage pipeline (flagged → assigned → scheduled → resolved, with an escalation branch) — each student is shown one relevant action at a time, and escalation reassigns the case to a dedicated escalation contact (counselor, dean, financial aid, HOD) rather than another peer mentor

## Project structure

```
.
├── database.py      # Builds the SQLite DB, loads dataset.csv, fetches risk scores from the API
├── app.py           # Streamlit dashboard (UI layer)
├── dataset.csv       # Source student data (not committed — see Data note below)
└── dashboard.db      # Generated SQLite database (not committed)
```

## Setup

1. Install dependencies:
   ```bash
   pip install streamlit pandas plotly requests
   ```

2. Make sure Person A's risk-prediction API is running locally at `http://localhost:8000/predict` before running `database.py` — risk scores are fetched live from this endpoint.

3. Build the database (run this first, and re-run any time `dataset.csv` changes):
   ```bash
   python database.py
   ```
   This loads the first 200 students from `dataset.csv`, calls the risk API for each one, and writes everything into `dashboard.db`. Console output will show how many students were scored by the live API vs. how many fell back to an estimated score (e.g. if the API was unreachable).

4. Launch the dashboard:
   ```bash
   streamlit run app.py
   ```

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
| `recommended_intervention` | TEXT | |
| `risk_score` | REAL | From the XGBoost API (or fallback estimate) |
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

Stores a timestamped log of risk scores per student over time (for future trend tracking).

## Notes

- **`score_source` is intentionally not displayed anywhere in the dashboard UI.** It exists purely so the team can run `SELECT * FROM students WHERE score_source='fallback'` to verify which scores actually came from the live model vs. an estimated fallback, without exposing that to faculty users.
- `current_year` is stored as the raw numeric value (1–4) from the dataset; the dashboard maps it to FY/SY/TY/Final Year for display and filtering only — the underlying data is untouched.
- The mentor list (`MENTOR_LIST`) and escalation contact list (`ESCALATION_CONTACTS`) are plain Python lists at the top of `app.py` for now. Could move to their own DB table later if this grows.
- `dataset.csv` and `dashboard.db` are excluded from version control (see `.gitignore`) since they contain student data.

## Status

- [x] SQLite database with 3 tables
- [x] Live risk scores from XGBoost API with fallback handling
- [x] Faculty dashboard with filtering (risk band, year)
- [x] Student detail view with Plotly chart
- [x] Student-to-student comparison view
- [x] Mentoring workflow tracker
- [ ] Integration with Person B (Mentor Agent) and Person D (Roadmap Agent) — Week 4