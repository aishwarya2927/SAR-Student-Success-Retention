import sqlite3
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "students.db"))
print(f"Connecting to database at {db_path}...")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Insert default faculty user
cursor.execute("""
    INSERT OR REPLACE INTO faculty (email, name, password, department)
    VALUES ('sharma@spit.ac.in', 'Dr. Sharma', 'password123', 'Computer Engineering')
""")

conn.commit()
conn.close()
print("SUCCESS: Default faculty member (sharma@spit.ac.in / password123) successfully inserted!")
