import os
import sys
import time
import json
import datetime
from dotenv import load_dotenv

# Load env variables
load_dotenv(override=True)

# Add mentor-agent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import retry_outreach_email, get_connection

def test_retry_flow():
    student_id = "2025801002"
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if there is an approved intervention report. If not, create/approve one.
    cursor.execute("""
        SELECT intervention_id, status FROM intervention_reports 
        WHERE student_id = ? AND status = 'approved' 
        ORDER BY generated_at DESC LIMIT 1
    """, (student_id,))
    row = cursor.fetchone()
    
    if not row:
        print("No approved intervention report found. Inserting a mock approved one...")
        actions = ["Maintain current study habits", "Attend all classes"]
        cursor.execute("""
            INSERT INTO intervention_reports (
                student_id, risk_band, prediction_confidence, student_summary,
                recommended_actions, priority_level, follow_up_plan, recommended_resources, status, approved_by, approved_at, generated_at
            ) VALUES (?, 'Low', 99.0, 'Summary text', ?, 'Low', 'Follow up text', '[]', 'approved', 'Dr. Sharma', ?, ?)
        """, (student_id, json.dumps(actions), datetime.datetime.now().isoformat(), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        
    conn.close()
    
    print(f"Triggering retry_outreach_email for student {student_id}...")
    success, message = retry_outreach_email(student_id)
    print(f"Result: success={success}, message={message}")
    
    if success:
        print("Waiting 15 seconds for background thread to execute email retry...")
        time.sleep(15)
        
        # Query comments to see if a retry comment was posted
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT comment_text, created_at FROM dashboard_comments 
            WHERE student_id = ? ORDER BY created_at DESC LIMIT 2
        """, (student_id,))
        comments = cursor.fetchall()
        conn.close()
        
        print("\n--- Latest comments after retry ---")
        for i, c in enumerate(comments):
            print(f"[{i}] Created At: {c['created_at']}")
            print(f"    Comment: {c['comment_text']}")
            
if __name__ == "__main__":
    test_retry_flow()
