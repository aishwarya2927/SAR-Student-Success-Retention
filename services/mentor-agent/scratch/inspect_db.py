import sqlite3
import json

DB_PATH = "../students.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
print("Tables in database:", tables)

for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"Table '{table}' has {count} rows.")

print("\n--- Student IDs and Names (first 10) ---")
cursor.execute("SELECT student_id, name, cgpa, backlog_count, attendance_rate, fee_delay_days FROM students LIMIT 10")
for row in cursor.fetchall():
    print(dict(row))

print("\n--- Intervention Reports (first 10) ---")
cursor.execute("SELECT * FROM intervention_reports LIMIT 10")
for row in cursor.fetchall():
    print(dict(row))

conn.close()
