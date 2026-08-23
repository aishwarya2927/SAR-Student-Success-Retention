# Faculty Risk Dashboard — Student Success & Retention System

This is the **Faculty Dashboard** component (Person C) of the Agentic AI Student Success and Retention System. It gives mentors a live, filterable view of student dropout risk pulled from Person A's XGBoost risk-prediction API, tools to drill into individual students, a mentoring workflow tracker, and a human-in-the-loop approval workflow for two kinds of AI-generated plans from Person B's Mentor Agent — academic intervention plans and placement readiness plans. Approved plans are exposed to Person D's Student Agent via a REST API. Access is gated behind mentor authentication; there is no public signup.

**Live deployment:**
- **Dashboard (frontend):** https://sar-student-success-retention-k5zbfryfbnvqsa3g2prgmd.streamlit.app/
- **API (backend, for Person D's integration):** https://sar-student-success-retention-3kvj.onrender.com

The sections below cover both running this locally for development and how the deployed version is set up.

## What it does

- Pulls real-time risk scores and SHAP-based top contributing factors for each student from the Risk Engine API, stored in a persistent PostgreSQL database
- Landing page splits users into **Mentor** (logs into this dashboard) or **Student** (redirected to Person D's separate app)
- Mentor accounts are **provisioned by an administrator** (`create_mentor.py`) — there is no self-serve signup, since the app is intended for a known, small set of faculty
- Displays a faculty-facing dashboard with summary metrics (total students, high/medium/low risk counts)
- Lets faculty filter students by **risk band** and **academic year** (FY / SY / TY / Final Year)
- Shows a detailed per-student view with CGPA, attendance, backlogs, fee delay, prediction confidence, a SHAP-based "top contributing factors" chart, and target companies (fetched from Person D)
- Lets faculty **compare any two students side-by-side** on a grouped bar chart plus a summary table
- Includes a **mentoring workflow tracker** with a visual stage pipeline (flagged → assigned → scheduled → resolved, with an escalation branch); the assigned mentor is automatically the logged-in user, not a manually picked name
- Fetches AI-generated **intervention plans** from Person B's Mentor Agent, stores them as `pending_approval`, and lets faculty approve or reject each one
- Fetches AI-generated **placement plans** from Person B's Mentor Agent (which independently pulls the student's current target companies from Person D), with the same approve/reject workflow
- Exposes only approved plans (of either kind) to Person D's Student Agent via a REST API (`services/dashboard/api.py`)

## Project structure

```
.
├── datasets/
│   └── student_success_dataset_30000.csv   # Source student data (not committed)
├── docs/
├── pages/
│   ├── Overview.py
│   ├── Student_Detail.py                   # Intervention + Placement plan tabs, approve/reject UI
│   ├── Comparison.py
│   └── Workflow.py
├── research/
├── services/
│   └── dashboard/
│       ├── api.py                          # REST API exposing approved plans to Person D
│       ├── HOW_IT_WORKS.md                 # Internal design notes for this service
│       ├── render.yaml                     # Render deployment config for the API service
│       └── requirements.txt                # Lean dependency list for the API service only
├── app.py                                  # Landing page, mentor login, dashboard home
├── auth.py                                 # Postgres-backed credential loader for streamlit-authenticator
├── database.py                             # Core tables + risk-scoring logic + intervention approval functions
├── add_users_table.py                      # One-time script: creates the users table
├── create_mentor.py                        # Admin-only script: provisions a mentor account
├── create_placement_table.py               # One-time script: creates the placement_reports table
├── add_target_companies_columns.py         # One-time script: adds target_companies columns to students
├── load_all_students.py                    # One-time script: loads the full 30,000-student dataset (chunked, checkpointed)
├── load_progress.txt                       # Checkpoint file for load_all_students.py
├── utils.py                                # Shared data-loading and formatting helpers
├── requirements.txt
└── dashboard.db                            # Legacy SQLite file, no longer used (superseded by Postgres)
```

---

## Setup — running this locally

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a Postgres database and set `DATABASE_URL`

This project uses PostgreSQL (Render, Supabase, or any Postgres provider — no code changes needed either way, since it's standard Postgres). Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://user:password@host:port/dbname
AUTH_COOKIE_KEY=<a long random string — see Authentication section below>
```

Generate a random value for `AUTH_COOKIE_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**`.env` must never be committed** — confirm it's listed in `.gitignore` before doing anything else.

### 3. Create all tables

Run each of these once, in order:

```bash
python database.py                        # creates students, risk_history, mentoring_workflow, intervention_reports
python add_users_table.py                  # creates users (mentor login)
python create_placement_table.py           # creates placement_reports
python add_target_companies_columns.py     # adds target_companies columns to students
```

`database.py` also loads the first 200 students from the CSV and calls Person A's Risk Engine API to get real risk scores and SHAP factors for each. Console output shows how many were scored live vs. fell back to an estimate. Re-running `database.py` refreshes `students` only (deletes and reinserts) — it does not touch `intervention_reports`, `placement_reports`, `mentoring_workflow`, or `users`.

To load the full 30,000-student dataset instead of just 200:
```bash
python load_all_students.py
```
This processes students in chunks of 500 with checkpointing (`load_progress.txt`) — safe to interrupt with Ctrl+C and resume later without redoing completed chunks. Expect a long runtime depending on the Risk Engine's response time.

### 4. Provision at least one mentor account

There is no signup page. Edit the `create_mentor(...)` call at the bottom of `create_mentor.py` with a real name, email, and temporary password, then run:

```bash
python create_mentor.py
```

### 5. Start the Faculty Dashboard API (needed for Person D's integration)

**For local development only.** This runs the API on your own machine, reachable at `http://127.0.0.1:8002` — nobody outside your machine can reach this address, so it's for testing only, not for Person D's actual integration.

```bash
uvicorn services.dashboard.api:app --port 8002
```
Verify at `http://127.0.0.1:8002/docs`.

**In production**, this API is already deployed on Render at its own public URL (see `services/dashboard/render.yaml` for the deployment config):

```
https://sar-student-success-retention-3kvj.onrender.com
```

Person D's Student Agent should call **this deployed URL**, not `localhost:8002`, which only exists while someone is running the API locally on their own computer. For example, the intervention endpoint in production is:
```
https://sar-student-success-retention-3kvj.onrender.com/intervention/{student_id}
```

### 6. Launch the Streamlit dashboard

**For local development:**
```bash
streamlit run app.py
```

Open the app, choose **"I am a Mentor / Faculty"**, and log in with the account created in step 4. Person B's Mentor Agent must be reachable (locally on port 8001, or its deployed URL — see `MENTOR_AGENT_URL` / `PLACEMENT_AGENT_URL` in `pages/Student_Detail.py`) for plan generation to work.

**In production**, the dashboard is already deployed on Streamlit Community Cloud:
```
https://sar-student-success-retention-k5zbfryfbnvqsa3g2prgmd.streamlit.app/
```
Anyone with a provisioned mentor account can log in directly at this URL — no local setup needed.

---

## Approval Workflow (applies to both plan types)

```text
Mentor Agent generates a plan
   (intervention OR placement)
                │
                ▼
   Stored as status = pending_approval
      (new row every generation —
       rejected attempts are kept
       as history, never overwritten)
                │
                ▼
        Mentor reviews plan
        ┌───────┴───────┐
        ▼               ▼
    Approve          Reject
        │               │
        ▼               ▼
status=approved   status=rejected
approved_by = logged-in mentor
approved_at set    (mentor can regenerate
        │           a fresh plan any time)
        ▼
  Visible to Person D's
  Student Agent via
  GET /intervention/{id} or
  GET /placement/{id}
```

Placement plans have one structural difference: the Mentor Agent fetches the student's **current** target companies directly from Person D's endpoint at generation time, rather than the Faculty Dashboard relaying that data — so each placement plan snapshot is always based on fresh company selections at the moment it was drafted.

---

## Database Schema

```sql
-- ── Students: core risk-scored records ─────────────────────────────────
CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    department TEXT,
    current_year TEXT,
    academic_risk_band TEXT,
    attendance_percentage REAL,
    backlog_count INTEGER,
    fee_delay_days INTEGER,
    cgpa REAL,
    recommended_intervention TEXT,
    prediction_confidence REAL,
    risk_band TEXT,
    score_source TEXT,
    top_factors TEXT,
    target_companies TEXT,
    target_companies_updated_at TIMESTAMP
);

-- ── Risk history: timestamped log of prediction confidence over time ────
CREATE TABLE IF NOT EXISTS risk_history (
    id SERIAL PRIMARY KEY,
    student_id TEXT,
    prediction_confidence REAL,
    risk_band TEXT,
    timestamp TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- ── Mentoring workflow: manual flag/assign/schedule/resolve tracking ────
CREATE TABLE IF NOT EXISTS mentoring_workflow (
    student_id TEXT PRIMARY KEY,
    status TEXT CHECK(status IN ('flagged','assigned','scheduled','resolved','escalated')),
    assigned_mentor TEXT,
    meeting_date TEXT,
    outcome_notes TEXT,
    history TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- ── Intervention reports: AI-generated academic intervention plans ──────
CREATE TABLE IF NOT EXISTS intervention_reports (
    intervention_id SERIAL PRIMARY KEY,
    student_id TEXT NOT NULL,
    risk_band TEXT,
    prediction_confidence REAL,
    student_summary TEXT,
    recommended_actions TEXT,
    priority_level TEXT,
    follow_up_plan TEXT,
    status TEXT DEFAULT 'pending_approval',
    approved_by TEXT,
    approved_at TIMESTAMP,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- ── Placement reports: AI-generated placement readiness plans ───────────
CREATE TABLE IF NOT EXISTS placement_reports (
    placement_id SERIAL PRIMARY KEY,
    student_id TEXT NOT NULL,
    target_companies TEXT,              -- JSON-encoded list
    readiness_summary TEXT,
    company_comparison TEXT,
    company_selection_guidance TEXT,
    preparation_steps JSONB,             -- structured list, auto-parsed by psycopg2
    timeline TEXT,
    risk_factors JSONB,                  -- structured list, auto-parsed by psycopg2
    data_verification_note TEXT,
    status TEXT DEFAULT 'pending_approval',
    approved_by TEXT,
    approved_at TIMESTAMP,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- ── Users: mentor login credentials ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'mentor'
);
```

**Column notes:**

| Column | Notes |
|---|---|
| `students.prediction_confidence` | From the Risk Engine API. Indicates how confident the model is in the predicted `risk_band` — **not** an independent risk magnitude. Renamed from an earlier, misleading `risk_score` field. |
| `students.top_factors` | JSON-encoded list of SHAP-attributed contributing features per student, rendered as a bar chart on Student Detail. |
| `students.target_companies` / `target_companies_updated_at` | Cached, best-effort snapshot fetched from Person D on demand (via the "Refresh" button on Student Detail) — used for display in Overview/Student Detail, not for plan generation itself. |
| `students.score_source` | `"api"` or `"fallback"` — internal QA field, not shown in the UI. |
| `students.recommended_intervention` | Static, dataset-sourced category, kept for reference only in a collapsed expander — not treated as a live recommendation. |
| `intervention_reports.recommended_actions` | Stored via `json.dumps()` — a plain `TEXT` column, not `jsonb`. |
| `placement_reports.preparation_steps` / `risk_factors` | Declared as `jsonb` — psycopg2 auto-parses these into native Python lists on read, no manual `json.loads()` needed. |
| `placement_reports.target_companies` | Declared as `TEXT` (not `jsonb`) — stored via `json.dumps()`, so it **does** need `json.loads()` on read. |

---

## Mentor Authentication (bcrypt)

There is no public signup. Mentor accounts are provisioned directly by an administrator, and passwords are never stored in plain text.

**1. Password hashing — `create_mentor.py`**
```python
import bcrypt

def create_mentor(username, name, plain_password):
    password_hash = bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()
    # only password_hash is inserted into the users table
    ...
```

**2. Loading stored hashes — `auth.py`**
```python
def load_credentials():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT username, name, password_hash FROM users WHERE role = 'mentor'")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    usernames = {}
    for username, name, password_hash in rows:
        usernames[username] = {"name": name, "password": password_hash}

    return {"usernames": usernames}
```

**3. Password verification (login) — `app.py`**
```python
import streamlit_authenticator as stauth
import auth

credentials = auth.load_credentials()
authenticator = stauth.Authenticate(
    credentials,
    "student_dashboard_cookie",
    os.environ["AUTH_COOKIE_KEY"],   # signature key — .env / Streamlit Cloud secrets, never hardcoded
    cookie_expiry_days=7
)

authenticator.login()
```
`authenticator.login()` internally runs the equivalent of `bcrypt.checkpw(entered_password.encode(), stored_password_hash.encode())` to verify the entered password against the stored hash — plain-text passwords are never compared directly.

**Security note:** `AUTH_COOKIE_KEY` must be stored as an environment variable (locally in `.env`, and separately in Streamlit Cloud's Secrets for the deployed app) — never hardcoded in `auth.py`. A hardcoded key committed to git history would let anyone forge valid session cookies for any mentor account.

---

## API Endpoints (`services/dashboard/api.py`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/intervention/{student_id}` | Latest approved intervention plan for a student |
| GET | `/placement/{student_id}` | Latest approved placement plan for a student |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |

Both plan endpoints return `404` if no approved plan exists for that student (pending or rejected plans are never returned) — this is the mechanism that enforces the human-approval guarantee structurally, not by convention.

### GET `/intervention/{student_id}`

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

### GET `/placement/{student_id}`

```json
{
  "placement_id": 1,
  "student_id": "STU202600058",
  "target_companies": [],
  "readiness_summary": "This student is currently in a high risk band primarily due to four backlogs...",
  "company_comparison": "",
  "company_selection_guidance": "To identify target companies, begin by researching industries...",
  "preparation_steps": [
    {"title": "Resolve Outstanding Backlogs", "duration": "2-4 weeks", "priority": "primary", "detail": "..."}
  ],
  "timeline": "Your immediate timeline over the next 2-3 months should focus on...",
  "risk_factors": [
    {"risk": "backlog_count", "action": "Prioritize and clear all four outstanding academic backlogs immediately."}
  ],
  "data_verification_note": "No target companies selected; guidance is based on general knowledge.",
  "status": "approved",
  "approved_by": "Dr. Sharma",
  "approved_at": "2026-07-05 09:12:00",
  "generated_at": "2026-07-05 09:11:40"
}
```

Full field notes for Person D's integration are documented separately (see `faculty_dashboard_api_for_person_d.md`).

---

## Notes

- **Persistence:** the project was migrated from SQLite (`dashboard.db`, now unused) to PostgreSQL specifically because Render's free-tier web services use an ephemeral filesystem — a local SQLite file would be wiped on every restart or redeploy, losing all approval history.
- **`score_source`** is intentionally not displayed in the UI — it exists so the team can run `SELECT * FROM students WHERE score_source='fallback'` to audit which scores came from the live model vs. an estimate.
- **No public signup, by design.** Given the dashboard is exposed on a public domain for evaluation, open self-registration would let unverified users approve recommendations for real students. Accounts are provisioned only via `create_mentor.py`, run by an administrator.
- **`mentoring_workflow`'s `assigned_mentor`** is now set automatically from the logged-in mentor's session, replacing an earlier hardcoded `MENTOR_LIST` dropdown.
- Every plan generation (intervention or placement) inserts a **new row** rather than updating an existing one — regeneration after rejection requires no special handling from Person B, since the Mentor Agent is stateless with respect to this workflow.
- `database.py`'s one-time setup (table creation, CSV load, API scoring) runs only when the file is executed directly (`python database.py`), guarded behind `if __name__ == "__main__":`. Other files safely import its functions without re-triggering a full data reload.
- The dataset CSV, `dashboard.db`, and `.env` are excluded from version control — confirm `.gitignore` covers all three before committing.

---

## Status

- [x] PostgreSQL database with 6 tables (students, risk_history, mentoring_workflow, intervention_reports, placement_reports, users)
- [x] Live prediction confidence + SHAP top-factors from Risk Engine API, with fallback handling
- [x] Mentor authentication (bcrypt, admin-provisioned accounts, no public signup)
- [x] Landing page routing mentors vs. students
- [x] Faculty dashboard with filtering (risk band, year)
- [x] Student detail view with SHAP factor chart, target companies display
- [x] Student-to-student comparison view
- [x] Mentoring workflow tracker (auto-assigns logged-in mentor)
- [x] Intervention plan generation, approve/reject, full history retained
- [x] Placement plan generation (target companies fetched live by Mentor Agent), approve/reject
- [x] REST API exposing approved intervention and placement plans to Person D
- [ ] Stale-plan detection when a student's target companies change after approval (future enhancement)
- [ ] Editable plans before approval (future enhancement)
- [ ] Rejection remarks (future enhancement)