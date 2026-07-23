import psycopg2
import os

def check():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set.")
        return
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("""
        SELECT pid, query, state, wait_event_type, wait_event, age(clock_timestamp(), query_start) 
        FROM pg_stat_activity 
        WHERE state != 'idle';
    """)
    rows = cur.fetchall()
    print("--- Active PostgreSQL Queries ---")
    for r in rows:
        print(f"PID: {r[0]} | Query: {r[1][:100]} | State: {r[2]} | Wait Type: {r[3]} | Wait Event: {r[4]} | Age: {r[5]}")
    conn.close()

if __name__ == "__main__":
    check()
