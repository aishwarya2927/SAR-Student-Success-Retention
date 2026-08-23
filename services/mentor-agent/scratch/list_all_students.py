import sqlite3
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "students.db"))
print(f"Connecting to database at {db_path}...")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT student_id, name, email, assigned_faculty_email FROM students")
students = cursor.fetchall()
print(f"Total students in DB: {len(students)}")
print("--- List of Students ---")
for student in students:
    print(f"ID: {student['student_id']} | Name: {student['name']} | Email: {student['email']} | Faculty Email: {student['assigned_faculty_email']}")

conn.close()
