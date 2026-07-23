import sqlite3
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "students.db"))
print(f"Connecting to database at {db_path}...")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT comment_id, student_id, faculty_name, comment_text, created_at FROM dashboard_comments WHERE faculty_name='AI Resume Auditor'")
rows = cursor.fetchall()
print(f"\nFound {len(rows)} comments by AI Resume Auditor:")
for row in rows:
    print(f"Comment ID: {row['comment_id']} | Student ID: {row['student_id']} | Created: {row['created_at']}")
    print(f"Text: {row['comment_text'][:200]}...")
    print("-" * 50)

conn.close()
