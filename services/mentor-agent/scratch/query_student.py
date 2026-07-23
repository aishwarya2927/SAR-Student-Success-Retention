import sqlite3
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "students.db"))
print(f"Connecting to database at {db_path}...")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT * FROM students WHERE student_id='STU202600001'")
student = cursor.fetchone()
if student:
    print("\n--- STUDENTS TABLE ROW ---")
    for key in student.keys():
        print(f"{key}: {student[key]}")
else:
    print("Student STU202600001 not found.")

cursor.execute("SELECT * FROM student_risks WHERE student_id='STU202600001'")
risk = cursor.fetchone()
if risk:
    print("\n--- STUDENT_RISKS TABLE ROW ---")
    for key in risk.keys():
        print(f"{key}: {risk[key]}")

cursor.execute("SELECT * FROM intervention_reports WHERE student_id='STU202600001'")
interventions = cursor.fetchall()
if interventions:
    print("\n--- INTERVENTION_REPORTS TABLE ROWS ---")
    for row in interventions:
        print({key: row[key] for key in row.keys()})
else:
    print("No intervention reports found for STU202600001.")

conn.close()
