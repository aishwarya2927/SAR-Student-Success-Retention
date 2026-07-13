import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cursor = conn.cursor()

cursor.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS target_companies TEXT")
cursor.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS target_companies_updated_at TIMESTAMP")

conn.commit()
cursor.close()
conn.close()
print("Columns added successfully")