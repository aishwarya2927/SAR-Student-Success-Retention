import os
import json
import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]

app = FastAPI(
    title="Student Dashboard API",
    description="Person C — Faculty Dashboard API. Exposes approved intervention plans for Person D's student agent.",
    version="1.0.0"
)


def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "dashboard-api"}


# ── GET approved intervention for Person D ────────────────────────────────────
@app.get("/intervention/{student_id}")
def get_approved_intervention(student_id: str):
    """
    Returns the latest approved intervention plan for a student.
    Used by Person D's student agent.

    - Returns 200 + plan JSON if an approved plan exists.
    - Returns 404 if no approved plan exists (pending/rejected don't count).
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            intervention_id,
            student_id,
            risk_band,
            prediction_confidence,
            student_summary,
            recommended_actions,
            priority_level,
            follow_up_plan,
            status,
            approved_by,
            approved_at,
            generated_at
        FROM intervention_reports
        WHERE student_id = %s AND status = 'approved'
        ORDER BY approved_at DESC
        LIMIT 1
    """, (student_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No approved intervention found for student {student_id}"
        )

    return JSONResponse({
        "intervention_id":       row[0],
        "student_id":            row[1],
        "risk_band":             row[2],
        "prediction_confidence": row[3],
        "student_summary":       row[4],
        "recommended_actions":   json.loads(row[5]) if row[5] else [],
        "priority_level":        row[6],
        "follow_up_plan":        row[7],
        "status":                row[8],
        "approved_by":           row[9],
        "approved_at":           str(row[10]) if row[10] else None,
        "generated_at":          str(row[11]) if row[11] else None,
    })

# ── GET approved placement plan for Person D ─────────────────────────────────
@app.get("/placement/{student_id}")
def get_approved_placement(student_id: str):
    """
    Returns the latest approved placement plan for a student.
    Used by Person D's student agent.

    - Returns 200 + plan JSON if an approved plan exists.
    - Returns 404 if no approved plan exists (pending/rejected don't count).
    """
    conn = get_db()
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
        WHERE student_id = %s AND status = 'approved'
        ORDER BY approved_at DESC
        LIMIT 1
    """, (student_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No approved placement plan found for student {student_id}"
        )

    return JSONResponse({
        "placement_id":          row[0],
        "student_id":            row[1],
        "target_companies":      json.loads(row[2]) if row[2] else [],
        "readiness_summary":     row[3],
        "company_comparison":    row[4],
        "company_guidance":      row[5],
        "preparation_steps":     json.loads(row[6]) if row[6] else [],
        "timeline":              row[7],
        "risk_factors":          json.loads(row[8]) if row[8] else [],
        "data_verification_note":row[9],
        "status":                row[10],
        "approved_by":           row[11],
        "approved_at":           str(row[12]) if row[12] else None,
        "generated_at":          str(row[13]) if row[13] else None,
    })
