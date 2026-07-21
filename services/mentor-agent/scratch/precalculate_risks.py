import os
import sys
import sqlite3
import json
import time

# Add parent directory to sys.path for database imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_connection
from tools.get_risk_profile import get_risk_profile

def init_risk_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_risks (
        student_id TEXT PRIMARY KEY,
        risk_band TEXT,
        risk_score REAL,
        confidence REAL,
        top_factors TEXT,      -- JSON string of list of dicts
        probabilities TEXT,    -- JSON string of dict
        last_updated TEXT,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    )
    """)
    conn.commit()
    conn.close()

def main():
    init_risk_table()
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, name FROM students")
    students = cursor.fetchall()
    conn.close()
    
    print(f"Found {len(students)} students in the database.")
    
    for idx, row in enumerate(students):
        student_id = row["student_id"]
        name = row["name"]
        print(f"[{idx+1}/{len(students)}] Fetching risk profile for {name} ({student_id})...")
        
        try:
            profile = get_risk_profile(student_id)
            
            risk_band = profile.get("risk_band", "Low")
            risk_score = profile.get("risk_score", 0.0)
            confidence = profile.get("confidence", 0.0)
            top_factors = json.dumps(profile.get("top_factors", []))
            probabilities = json.dumps(profile.get("probabilities", {}))
            import datetime
            last_updated = datetime.datetime.now().isoformat()
            
            conn = get_connection()
            curr = conn.cursor()
            curr.execute("""
            INSERT OR REPLACE INTO student_risks (
                student_id, risk_band, risk_score, confidence, top_factors, probabilities, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (student_id, risk_band, risk_score, confidence, top_factors, probabilities, last_updated))
            conn.commit()
            conn.close()
            print(f"  Success: Band={risk_band}, Score={risk_score}%")
            
        except Exception as e:
            print(f"  Error fetching {student_id}: {e}")
            # Fallback to local heuristic prediction if remote fails or times out
            # High Risk: cgpa < 6.0 and attendance_rate < 70
            # Low Risk: others
            # Let's inspect local database columns
            conn_fallback = get_connection()
            curr_fb = conn_fallback.cursor()
            curr_fb.execute("SELECT cgpa, attendance_rate, backlog_count, fee_delay_days FROM students WHERE student_id = ?", (student_id,))
            student_row = curr_fb.fetchone()
            conn_fallback.close()
            
            risk_band = "Low"
            risk_score = 15.0
            confidence = 90.0
            top_factors = []
            
            if student_row:
                cgpa = student_row["cgpa"] or 8.0
                attendance = student_row["attendance_rate"] or 90.0
                backlogs = student_row["backlog_count"] or 0
                fee_delay = student_row["fee_delay_days"] or 0
                
                # Heuristic scoring
                factors_list = []
                score_sum = 0.0
                if cgpa < 6.0:
                    score_sum += 40.0
                    factors_list.append({"feature": "cgpa", "value": str(cgpa), "importance": 0.4})
                elif cgpa < 7.0:
                    score_sum += 20.0
                
                if attendance < 65.0:
                    score_sum += 40.0
                    factors_list.append({"feature": "attendance_rate", "value": str(attendance), "importance": 0.4})
                elif attendance < 75.0:
                    score_sum += 20.0
                    
                if backlogs > 1:
                    score_sum += 15.0
                    factors_list.append({"feature": "backlog_count", "value": str(backlogs), "importance": 0.2})
                
                if fee_delay > 15:
                    score_sum += 15.0
                    factors_list.append({"feature": "fee_delay_days", "value": str(fee_delay), "importance": 0.15})
                    
                risk_score = max(5.0, min(98.0, score_sum + (100.0 - attendance) * 0.2))
                if risk_score > 60.0:
                    risk_band = "High"
                elif risk_score > 30.0:
                    risk_band = "Medium"
                
                top_factors = factors_list
                
            probabilities = {"Critical": 0.01 if risk_band=="High" else 0.001, "High": 0.8 if risk_band=="High" else 0.05, "Medium": 0.7 if risk_band=="Medium" else 0.1, "Low": 0.9 if risk_band=="Low" else 0.05}
            
            conn = get_connection()
            curr = conn.cursor()
            curr.execute("""
            INSERT OR REPLACE INTO student_risks (
                student_id, risk_band, risk_score, confidence, top_factors, probabilities, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (student_id, risk_band, risk_score, confidence / 100.0, json.dumps(top_factors), json.dumps(probabilities), "2026-07-19T21:30:00Z"))
            conn.commit()
            conn.close()
            print(f"  Saved Local Heuristic Fallback: Band={risk_band}, Score={round(risk_score, 1)}%")
            
        # Small delay to avoid overloading
        time.sleep(0.5)

    print("Precalculation finished!")

if __name__ == "__main__":
    main()
