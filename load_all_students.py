"""
load_all_students.py

One-time script to load ALL 30,000 students (not just the 200 used in
database.py) into the students table, with real risk scores from
Person A's API.

WHY THIS IS SEPARATE FROM database.py:
- database.py loads 200 students, fast, used for everyday dev/testing.
- This script processes 30,000 students, which means 30,000 calls to
  Person A's API — even with concurrency, this takes real time
  (expect roughly 30-60+ minutes, possibly more depending on her
  server's response time and rate limits).

WHAT THIS SCRIPT ACTUALLY DOES, STEP BY STEP:

1. Reads the full CSV (all 30,000 rows), not just df.head(200).

2. Splits those 30,000 rows into CHUNKS of 500 students each
   (60 chunks total). We process one chunk at a time, not all
   30,000 at once, so that:
     - Progress is saved incrementally (checkpointing) — if the
       script crashes or your connection drops at chunk 40, you
       don't lose the first 39 chunks' worth of API calls and
       inserts. You just resume from chunk 40.
     - Memory usage stays reasonable (30,000 rows in memory at
       once, with results, is more than a mid-sized chunk).

3. Within each chunk, calls Person A's risk API for each of the
   500 students CONCURRENTLY using a small thread pool (5 workers
   at a time), instead of one-at-a-time. This cuts wall-clock time
   significantly compared to your original database.py, which calls
   the API strictly one student after another with a 0.5s delay
   between each — sequential like that, 30,000 students would take
   4+ hours just in sleep time alone.

   We keep the concurrency LOW (5 workers) on purpose — Person A's
   API is on Render's free tier, which likely runs a single worker
   process. Too much concurrency could overwhelm it (causing 429/502
   errors) rather than actually speeding things up.

4. Once a chunk's API calls are done, we bulk-insert all 500 rows
   into Postgres in a SINGLE database call using psycopg2's
   execute_values() — much faster than inserting row-by-row.

5. After each successful chunk, we write the chunk number to a
   small local checkpoint file (load_progress.txt). If you have to
   stop and restart this script later, it reads that file first and
   skips chunks already completed, instead of starting over from
   student #1.

6. ON CONFLICT (student_id) DO NOTHING is used in the insert, so
   if a chunk somehow gets processed twice (e.g., you re-run without
   deleting the checkpoint), it won't create duplicate rows or error
   out — it just skips students already in the table.

WHAT THIS SCRIPT DOES NOT DO:
- It does NOT touch intervention_reports or mentoring_workflow —
  those are untouched, since this script only ever inserts into
  students.
- It does NOT delete existing data first — if you already have
  200 students loaded (from database.py), those stay, and this
  script adds the rest on top (skipping any student_id that
  already exists, thanks to ON CONFLICT DO NOTHING).
"""

import os
import time
import json
import math
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Reuse the exact same scoring logic as database.py, so results are
# consistent with however your 200-student baseline was scored.
from database import get_real_risk

load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]

CSV_PATH = "datasets/student_success_dataset_30000.csv"
CHUNK_SIZE = 500
MAX_WORKERS = 2
CHECKPOINT_FILE = "load_progress.txt"

COLUMNS = [
    "student_id", "department", "current_year", "cgpa",
    "attendance_percentage", "backlog_count", "fee_delay_days",
    "academic_risk_band", "recommended_intervention",
    "prediction_confidence", "risk_band", "score_source", "top_factors"
]


def get_last_completed_chunk():
    """Read the checkpoint file to see which chunk we last finished."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            content = f.read().strip()
            return int(content) if content else -1
    return -1


def save_checkpoint(chunk_index):
    """Record that this chunk is done, so a restart can skip it."""
    with open(CHECKPOINT_FILE, "w") as f:
        f.write(str(chunk_index))


def score_row(row):
    """
    Wraps get_real_risk() so it returns a full tuple ready for insertion,
    in the same column order as COLUMNS.
    """
    confidence, risk_band, source, top_factors = get_real_risk(row)
    return (
        row["student_id"],
        row["department"],
        row["current_year"],
        row["cgpa"],
        row["attendance_percentage"],
        row["backlog_count"],
        row["fee_delay_days"],
        row["academic_risk_band"],
        row["recommended_intervention"],
        confidence,
        risk_band,
        source,
        top_factors,
    )


def process_chunk(chunk_df):
    """Score all rows in this chunk concurrently, using a small thread pool."""
    rows = [row for _, row in chunk_df.iterrows()]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(score_row, rows))
    return results


def insert_chunk(conn, rows):
    """Bulk insert this chunk's scored rows into Postgres in one call."""
    cur = conn.cursor()
    columns_sql = ",".join(COLUMNS)
    query = f"""
        INSERT INTO students ({columns_sql})
        VALUES %s
        ON CONFLICT (student_id) DO NOTHING
    """
    execute_values(cur, query, rows)
    conn.commit()
    cur.close()


def main():
    print(f"Reading full dataset from {CSV_PATH} ...")
    df = pd.read_csv(CSV_PATH)
    total_students = len(df)
    total_chunks = math.ceil(total_students / CHUNK_SIZE)
    print(f"Total students: {total_students} -> {total_chunks} chunks of {CHUNK_SIZE}")

    last_done = get_last_completed_chunk()
    start_chunk = last_done + 1
    if start_chunk > 0:
        print(f"Resuming from chunk {start_chunk} (chunks 0-{last_done} already completed)")

    conn = psycopg2.connect(DATABASE_URL)

    for chunk_index in range(start_chunk, total_chunks):
        start_row = chunk_index * CHUNK_SIZE
        end_row = min(start_row + CHUNK_SIZE, total_students)
        chunk_df = df.iloc[start_row:end_row]

        t0 = time.time()
        print(f"\nChunk {chunk_index + 1}/{total_chunks}: scoring students {start_row}-{end_row}...")

        scored_rows = process_chunk(chunk_df)

        insert_chunk(conn, scored_rows)
        save_checkpoint(chunk_index)

        elapsed = time.time() - t0
        n_api = sum(1 for r in scored_rows if r[11] == "api")
        n_fallback = sum(1 for r in scored_rows if r[11] == "fallback")
        print(f"  Done in {elapsed:.1f}s — {n_api} scored by API, {n_fallback} fell back. Checkpoint saved.")

    conn.close()
    print("\nAll chunks completed. Full dataset loaded.")


if __name__ == "__main__":
    main()