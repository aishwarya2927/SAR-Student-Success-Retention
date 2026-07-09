# reset_placement_table.py
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS placement_reports")

cur.execute("""
    CREATE TABLE placement_reports (
    placement_id        SERIAL PRIMARY KEY,
    student_id          TEXT NOT NULL,
    target_companies    TEXT,               -- JSON list
    readiness_summary   TEXT,
    company_comparison  TEXT,
    company_selection_guidance TEXT,
    preparation_steps   JSONB,              -- full structured list
    timeline            TEXT,
    risk_factors        JSONB,              -- structured risks/actions
    data_verification_note TEXT,
    status              TEXT DEFAULT 'pending_approval',
    approved_by         TEXT,
    approved_at         TIMESTAMP,
    generated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
)
""")

conn.commit()
cur.close()
conn.close()
print("placement_reports table dropped and recreated")