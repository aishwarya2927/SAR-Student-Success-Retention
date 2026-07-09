import os
import time
import json
import pandas as pd
import psycopg2
import requests
from sqlalchemy import create_engine
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()  # reads DATABASE_URL from .env when running locally

DATABASE_URL = os.environ["DATABASE_URL"]


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
    time.sleep(0.5)
    try:
        student_id = row["student_id"]
        response = requests.get(
            f"https://sar-student-success-retention.onrender.com/predict/{student_id}",
            timeout=60
        )
        response.raise_for_status()
        result = response.json()

        if "risk_score" not in result or "risk_band" not in result:
            raise ValueError(f"API response missing expected keys: {result}")

        top_factors = result.get("top_factors", [])
        return result["risk_score"], result["risk_band"].lower(), "api", json.dumps(top_factors)

    except Exception as e:
        print(f"  [WARN] API call failed for {row['student_id']}: {e}")
        return band_to_score(row["academic_risk_band"]), band_to_simple(row["academic_risk_band"]), "fallback", "[]"


# ── Intervention approval workflow functions ────────────────────────────────
# Each function opens its own short-lived connection.

def insert_intervention(student_id, plan):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO intervention_reports
        (student_id, risk_band, prediction_confidence, student_summary,
         recommended_actions, priority_level, follow_up_plan, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending_approval')
        RETURNING intervention_id
    """, (
        student_id,
        plan.get("risk_band"),
        plan.get("prediction_confidence"),
        plan.get("student_summary"),
        json.dumps(plan.get("recommended_actions", [])),
        plan.get("priority_level"),
        plan.get("follow_up_plan"),
    ))
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return new_id


def approve_intervention(intervention_id, faculty_name):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        UPDATE intervention_reports
        SET status='approved', approved_by=%s, approved_at=CURRENT_TIMESTAMP
        WHERE intervention_id=%s
    """, (faculty_name, intervention_id))
    conn.commit()
    cur.close()
    conn.close()


def reject_intervention(intervention_id):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        UPDATE intervention_reports
        SET status='rejected'
        WHERE intervention_id=%s
    """, (intervention_id,))
    conn.commit()
    cur.close()
    conn.close()


def get_latest_approved(student_id):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM intervention_reports
        WHERE student_id=%s AND status='approved'
        ORDER BY approved_at DESC LIMIT 1
    """, (student_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def refresh_target_companies(student_id):
    try:
        response = requests.get(
            f"https://sar-roadmap-agent.onrender.com/student-target-companies/{student_id}",
            timeout=40
        )
        if response.status_code == 200:
            companies = response.json().get("target_companies", [])
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            cur.execute("""
                UPDATE students
                SET target_companies = %s, target_companies_updated_at = CURRENT_TIMESTAMP
                WHERE student_id = %s
            """, (json.dumps(companies), student_id))
            conn.commit()
            cur.close()
            conn.close()
            return companies
        else:
            return None
    except Exception as e:
        print(f"[WARN] Could not fetch target companies for {student_id}: {e}")
        return None
    
# ── Placement plan approval workflow functions ──────────────────────────────

# ── Placement plan approval workflow functions ──────────────────────────────
# Mirrors the intervention_reports workflow exactly.

def insert_placement(student_id, plan):
    pp = plan.get("placement_plan", {}).get("placement_plan", {})

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO placement_reports
        (student_id, target_companies, readiness_summary, company_comparison,
         company_selection_guidance, preparation_steps, timeline,
         risk_factors, data_verification_note, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending_approval')
        RETURNING placement_id
    """, (
        student_id,
        json.dumps(plan.get("target_companies", [])),
        pp.get("readiness_summary"),
        pp.get("company_comparison"),
        pp.get("company_selection_guidance"),
        json.dumps(pp.get("preparation_steps", [])),
        pp.get("timeline"),
        json.dumps(pp.get("risk_factors_and_actions", [])),
        pp.get("data_verification_note"),
    ))
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return new_id



def approve_placement(placement_id, faculty_name):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        UPDATE placement_reports
        SET status='approved', approved_by=%s, approved_at=CURRENT_TIMESTAMP
        WHERE placement_id=%s
    """, (faculty_name, placement_id))
    conn.commit()
    cur.close()
    conn.close()


def reject_placement(placement_id):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        UPDATE placement_reports
        SET status='rejected'
        WHERE placement_id=%s
    """, (placement_id,))
    conn.commit()
    cur.close()
    conn.close()


def get_latest_approved_placement(student_id):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            placement_id,
            student_id,
            target_companies,
            readiness_summary,
            company_comparison,
            company_selection_guidance,
            preparation_steps,
            timeline,
            risk_factors,
            data_verification_note,
            status,
            approved_by,
            approved_at,
            generated_at
        FROM placement_reports
        WHERE student_id=%s AND status='approved'
        ORDER BY approved_at DESC LIMIT 1
    """, (student_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row



# ── One-time setup ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS risk_history (
        id SERIAL PRIMARY KEY,
        student_id TEXT,
        prediction_confidence REAL,
        risk_band TEXT,
        timestamp TEXT,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    )
    """)

    cur.execute("""
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

    cur.execute("""
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
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

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
        "prediction_confidence", "risk_band", "score_source", "top_factors"
    ]]

    # pandas.to_sql needs a SQLAlchemy engine for Postgres, not a raw psycopg2 connection
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM students"))
    df_students.to_sql("students", engine, if_exists="append", index=False)

    print(f"Loaded {len(df_students)} students successfully")