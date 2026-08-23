"""
add_users_table.py

Standalone, one-time script to create the `users` table for mentor
authentication, WITHOUT touching the `students`, `intervention_reports`,
or `mentoring_workflow` tables.

This is deliberately separate from database.py, because database.py's
setup block deletes and reloads the entire `students` table every time
it runs (via DELETE FROM students + re-insert). Running database.py
again after using load_all_students.py to load thousands of real,
API-scored students would wipe that work and replace it with only the
original 200-student baseline.

Run this once:
    python add_users_table.py
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'mentor')
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("users table created")

if __name__ == "__main__":
    main()