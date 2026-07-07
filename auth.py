import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]


def load_credentials():
    """
    Reads all mentor accounts from Postgres and returns them in the
    dict structure streamlit-authenticator expects:

    {
        "usernames": {
            "sharma@spit.ac.in": {
                "name": "Dr. Sharma",
                "password": "<bcrypt hash>"
            },
            ...
        }
    }
    """
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT username, name, password_hash FROM users WHERE role = 'mentor'")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    usernames = {}
    for username, name, password_hash in rows:
        usernames[username] = {
            "name": name,
            "password": password_hash
        }

    return {"usernames": usernames}