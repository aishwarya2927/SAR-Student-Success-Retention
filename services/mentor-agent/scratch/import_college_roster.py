import os
import sys
import csv
import sqlite3

# Ensure parent directory is in path for database helper imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_connection, init_db

def usage():
    print("Usage: python import_college_roster.py <path_to_college_roster.csv>")
    print("CSV headers must include: student_id, name, email, phone, department, current_year, cgpa, attendance_percentage, backlog_count, fee_delay_days, financial_stress_score")
    sys.exit(1)

def import_roster(csv_path: str):
    if not os.path.exists(csv_path):
        print(f"Error: File '{csv_path}' does not exist.")
        sys.exit(1)
        
    print(f"Connecting to database...")
    init_db() # Ensure tables exist
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Clean out existing student cohort data
    print("Wiping existing cohort records from 'students' and 'student_risks' tables...")
    cursor.execute("DELETE FROM students")
    cursor.execute("DELETE FROM student_risks")
    cursor.execute("DELETE FROM student_tasks")
    cursor.execute("DELETE FROM student_resources")
    cursor.execute("DELETE FROM mentor_tasks")
    cursor.execute("DELETE FROM intervention_reports")
    cursor.execute("DELETE FROM dashboard_workflow")
    cursor.execute("DELETE FROM dashboard_comments")
    conn.commit()
    
    students_data = []
    risks_data = []
    
    print(f"Parsing CSV file: {csv_path}...")
    try:
        with open(csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            
            # Simple header validation
            required_headers = {"student_id", "name", "email", "phone", "department", "current_year"}
            headers = set(reader.fieldnames or [])
            if not required_headers.issubset(headers):
                print(f"Error: Missing required headers. Your CSV must contain at least: {required_headers}")
                usage()
                
            for idx, row in enumerate(reader):
                student_id = row['student_id'].strip()
                name = row['name'].strip()
                email = row['email'].strip()
                phone = row['phone'].strip()
                department = row['department'].strip()
                current_year = row['current_year'].strip()
                
                # Metrics parsing with defaults
                cgpa = float(row['cgpa']) if row.get('cgpa') else 8.0
                attendance = float(row['attendance_percentage']) if row.get('attendance_percentage') else 90.0
                backlogs = int(row['backlog_count']) if row.get('backlog_count') else 0
                fee_delay = int(row['fee_delay_days']) if row.get('fee_delay_days') else 0
                stress = float(row['financial_stress_score']) if row.get('financial_stress_score') else 1.0
                
                # Mocking remaining columns as defaults
                students_data.append((
                    student_id, name, cgpa, backlogs, attendance, 75.0, "Stable",
                    95.0, 10, 0, 15.0, 75, 70, 60, 70, 70, 70, 0, 0, fee_delay,
                    stress, "[]", "[]", "[]", "5-10 LPA", "[]", "No Bond", "Hybrid",
                    department, current_year, 0, 0, email, phone
                ))
                
                # Initial default low-risk prediction for database start state
                # The Risk Engine will automatically update this on first prediction request
                probs = {"Low": 0.9, "Medium": 0.08, "High": 0.02}
                import json
                risks_data.append((
                    student_id, "Low", 10.0, 0.95, json.dumps([]), json.dumps(probs), "2026-07-22T00:00:00Z"
                ))
                
        # Batch insert
        print(f"Batch inserting {len(students_data)} real students into database...")
        cursor.executemany("""
            INSERT INTO students (
                student_id, name, cgpa, backlog_count, attendance_rate, internal_marks_avg, gpa_trend,
                assignment_submission_rate, lms_login_frequency, hackathon_count, weekly_study_hours,
                time_management_score, coding_score, ai_ml_score, communication_score, teamwork_score,
                presentation_score, internship_count, completed_certifications, fee_delay_days,
                financial_stress_score, target_companies, preferred_roles, preferred_locations,
                min_ctc, company_types, max_bond_years, work_mode, department, current_year, is_newly_active, added_by_mentor,
                email, phone
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, students_data)
        
        cursor.executemany("""
            INSERT INTO student_risks (
                student_id, risk_band, risk_score, confidence, top_factors, probabilities, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, risks_data)
        
        conn.commit()
        print("SUCCESS: College roster successfully ingested! Roster is ready for prediction.")
        
    except Exception as e:
        print(f"Fatal error during roster import: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
    import_roster(sys.argv[1])
