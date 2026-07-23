import os
import sys
import time
import sqlite3
import datetime
from dotenv import load_dotenv

# Load env variables
load_dotenv(override=True)

# Add mentor-agent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import approve_intervention, get_connection

def test_approve_flow():
    # We will use the existing student in the database 2025801002 (Sakshi Patil)
    # or create a temporary student / intervention if needed.
    # Let's inspect the database first for Sakshi Patil (2025801002).
    student_id = "2025801002"
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Let's see if there is a pending intervention report for this student.
    cursor.execute("SELECT intervention_id, status FROM intervention_reports WHERE student_id = ? ORDER BY generated_at DESC LIMIT 1", (student_id,))
    row = cursor.fetchone()
    
    if not row:
        print(f"No intervention report found for student {student_id}. Creating a mock one...")
        import json
        actions = ["Maintain current study habits", "Attend all classes"]
        cursor.execute("""
            INSERT INTO intervention_reports (
                student_id, risk_band, prediction_confidence, student_summary,
                recommended_actions, priority_level, follow_up_plan, recommended_resources, status, generated_at
            ) VALUES (?, 'Low', 99.0, 'Summary text', ?, 'Low', 'Follow up text', '[]', 'pending_approval', ?)
        """, (student_id, json.dumps(actions), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        cursor.execute("SELECT intervention_id, status FROM intervention_reports WHERE student_id = ? ORDER BY generated_at DESC LIMIT 1", (student_id,))
        row = cursor.fetchone()
        
    intervention_id = row["intervention_id"]
    print(f"Found intervention report {intervention_id} with status '{row['status']}' for student {student_id}.")
    
    # If the intervention was already approved, let's reset it to pending_approval for this test
    if row["status"] != "pending_approval":
        print(f"Resetting intervention {intervention_id} status to 'pending_approval' for testing...")
        cursor.execute("UPDATE intervention_reports SET status = 'pending_approval', approved_by = NULL, approved_at = NULL WHERE intervention_id = ?", (intervention_id,))
        conn.commit()
        
    conn.close()
    
    # Capture the number of comments before approval
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM dashboard_comments WHERE student_id = ?", (student_id,))
    comments_before = cursor.fetchone()[0]
    conn.close()
    
    print(f"Approving intervention {intervention_id}...")
    approve_intervention(intervention_id, "Dr. Sharma")
    
    print("Waiting 25 seconds for background thread to complete email dispatch and log status...")
    time.sleep(25)
    
    # Query dashboard comments to verify status
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT comment_text, created_at FROM dashboard_comments WHERE student_id = ? ORDER BY created_at DESC LIMIT 2", (student_id,))
    comments_after = cursor.fetchall()
    conn.close()
    
    print("\n--- Latest Dashboard Comments for Student ---")
    for i, c in enumerate(comments_after):
        print(f"[{i}] Created At: {c['created_at']}")
        print(f"    Comment: {c['comment_text']}")
        
    # Read the end of outreach_notifications.log
    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outreach_notifications.log")
    if os.path.exists(log_path):
        print("\n--- Recent Lines in outreach_notifications.log ---")
        with open(log_path, "r", encoding="utf-8") as log_f:
            lines = log_f.readlines()
            for line in lines[-10:]:
                print(line.strip())
    else:
        print(f"\nLog file {log_path} does not exist!")

if __name__ == "__main__":
    test_approve_flow()
