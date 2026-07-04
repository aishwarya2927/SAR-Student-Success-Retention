import sqlite3
import json
import pandas as pd
import requests


# ── Fallback helpers (used only when Person A's API call fails) ────────────
def band_to_score(band):
    if "Critical" in band: return 90
    elif "High" in band: return 75
    elif "Moderate" in band: return 55
    else: return 30

def band_to_simple(band):
    if "Critical" in band or "High" in band: return "high"
    elif "Moderate" in band: return "medium"
    else: return "low"


# ── Calls Person A's real risk model ────────────────────────────────────────
def get_real_risk(row):
    try:
        student_dict = row.to_dict()
        student_dict["current_year"] = str(student_dict["current_year"])
        response = requests.post(
            "http://localhost:8000/predict",
            json=student_dict,
            timeout=5
        )
        response.raise_for_status()
        result = response.json()

        if "risk_score" not in result or "risk_band" not in result:
            raise ValueError(f"API response missing expected keys: {result}")

        top_factors = result.get("top_factors", [])

        return result["risk_score"], result["risk_band"].lower(), "api", str(top_factors)

    except Exception as e:
        print(f"  [WARN] API call failed for {row['student_id']}: {e}")
        return band_to_score(row["academic_risk_band"]), band_to_simple(row["academic_risk_band"]), "fallback", "[]"


# ── Intervention approval workflow functions ────────────────────────────────

def insert_intervention(student_id, plan):
    c = sqlite3.connect("dashboard.db")
    c.execute("""
        INSERT INTO intervention_reports
        (student_id, risk_band, prediction_confidence, student_summary,
         recommended_actions, priority_level, follow_up_plan, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending_approval')
    """, (
        student_id,
        plan.get("risk_band"),
        plan.get("prediction_confidence"),
        plan.get("student_summary"),
        json.dumps(plan.get("recommended_actions", [])),  # ← json.dumps not str()
        plan.get("priority_level"),
        plan.get("follow_up_plan"),
    ))
    c.commit()
    new_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.close()
    return new_id


def approve_intervention(intervention_id, faculty_name):
    c = sqlite3.connect("dashboard.db")
    c.execute("""
        UPDATE intervention_reports
        SET status='approved', approved_by=?, approved_at=CURRENT_TIMESTAMP
        WHERE intervention_id=?
    """, (faculty_name, intervention_id))
    c.commit()
    c.close()


def reject_intervention(intervention_id):
    c = sqlite3.connect("dashboard.db")
    c.execute("""
        UPDATE intervention_reports
        SET status='rejected'
        WHERE intervention_id=?
    """, (intervention_id,))
    c.commit()
    c.close()


def get_latest_approved(student_id):
    c = sqlite3.connect("dashboard.db")
    row = c.execute("""
        SELECT * FROM intervention_reports
        WHERE student_id=? AND status='approved'
        ORDER BY approved_at DESC LIMIT 1
    """, (student_id,)).fetchone()
    c.close()
    return row


# ── One-time setup ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    conn = sqlite3.connect("dashboard.db")
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students(
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
        top_factors TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS risk_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        prediction_confidence REAL,
        risk_band TEXT,
        timestamp TEXT,
        FOREIGN KEY (student_id) REFERENCES students(student_id))
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mentoring_workflow (
        student_id TEXT PRIMARY KEY,
        status TEXT CHECK(status IN ('flagged','assigned','scheduled','resolved','escalated')),
        assigned_mentor TEXT,
        meeting_date TEXT,
        outcome_notes TEXT,
        history TEXT,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS intervention_reports (
        intervention_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        risk_band TEXT,
        prediction_confidence REAL,
        student_summary TEXT,
        recommended_actions TEXT,
        priority_level TEXT,
        follow_up_plan TEXT,
        status TEXT DEFAULT 'pending_approval',
        approved_by TEXT,
        approved_at DATETIME,
        generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    )
    """)

    conn.commit()

    df = pd.read_csv("datasets/student_success_dataset_30000.csv")
    df = df.head(200)

    print("Getting real risk scores from Person A's API...")
    df[["prediction_confidence", "risk_band", "score_source", "top_factors"]] = df.apply(
    lambda row: pd.Series(get_real_risk(row)), axis=1
    )

    n_api      = (df["score_source"] == "api").sum()
    n_fallback = (df["score_source"] == "fallback").sum()
    print(f"Done. {n_api} scored by API, {n_fallback} fell back to estimated scores.")
    if n_fallback > 0:
        print(f"  -> Fallback student_ids: {df[df['score_source']=='fallback']['student_id'].tolist()}")

    df_students = df[[
        "student_id", "department", "current_year", "cgpa",
        "attendance_percentage", "backlog_count", "fee_delay_days",
        "academic_risk_band", "recommended_intervention",
        "prediction_confidence", "risk_band", "score_source","top_factors"
    ]]

    df_students.to_sql("students", conn, if_exists="replace", index=False)
    print(f"Loaded {len(df_students)} students successfully")
    conn.close()