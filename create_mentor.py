"""
create_mentor.py

Run this script yourself, locally, whenever a new mentor needs an account.
This is NEVER deployed and never exposed to the public — it's an admin-only
tool for creating accounts directly in the users table.

Usage:
    Edit the create_mentor(...) call at the bottom with the mentor's real
    details, then run:  python create_mentor.py
"""

import os
import bcrypt
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]


def create_mentor(username, name, plain_password):
    password_hash = bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (username, name, password_hash, role)
        VALUES (%s, %s, %s, 'mentor')
        ON CONFLICT (username) DO NOTHING
    """, (username, name, password_hash))
    conn.commit()
    cur.close()
    conn.close()

    print(f"Created mentor account for {name} ({username})")
    print(f"Temporary password: {plain_password}  -- share this with them directly")


if __name__ == "__main__":
    # Edit these details for each new mentor, then run this script.
    create_mentor(
        username="sharma@spit.ac.in",
        name="Dr. Sharma",
        plain_password="TempPassword123"
    )