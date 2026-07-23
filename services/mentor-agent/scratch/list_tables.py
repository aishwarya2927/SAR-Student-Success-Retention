import psycopg2
import os

def list_tables():
    url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
    rows = cur.fetchall()
    print("--- Database Tables ---")
    for r in rows:
        print(r[0])
    conn.close()

if __name__ == "__main__":
    list_tables()
