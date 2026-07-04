import json
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Student Dashboard API",
    description="Person C — Faculty Dashboard API. Exposes approved intervention plans for Person D's student agent.",
    version="1.0.0"
)

DB_PATH = "dashboard.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
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
    row = conn.execute("""
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
        WHERE student_id = ? AND status = 'approved'
        ORDER BY approved_at DESC
        LIMIT 1
    """, (student_id,)).fetchone()
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
        "approved_at":           row[10],
        "generated_at":          row[11],
    })