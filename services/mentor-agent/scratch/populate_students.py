import os
import sys
import csv
import json
import random
import sqlite3

# Add parent directory to sys.path for database imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_connection, init_db

# Indian Names lists for generating names
FIRST_NAMES = [
    "Aarav", "Aditya", "Akash", "Amit", "Ananya", "Arjun", "Dev", "Divya", "Gaurav", "Harsh",
    "Ishaan", "Karan", "Kavya", "Manish", "Neha", "Nikhil", "Pooja", "Pranav", "Priya", "Rahul",
    "Rohan", "Riya", "Sanjay", "Shreya", "Siddharth", "Sneha", "Sunita", "Tanvi", "Varun", "Vikram",
    "Yash", "Abhishek", "Deepak", "Jyoti", "Kiran", "Meera", "Pradeep", "Rajesh", "Sandeep", "Swati",
    "Vijay", "Vivek", "Ajay", "Anil", "Arvind", "Dinesh", "Manoj", "Ramesh", "Suresh", "Umesh"
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Mehta", "Joshi", "Patel", "Shah", "Rao", "Nair", "Iyer",
    "Reddy", "Choudhury", "Das", "Sen", "Bose", "Chatterjee", "Mukherjee", "Banerjee", "Singh", "Kumar",
    "Mishra", "Pandey", "Tripathi", "Dubey", "Yadav", "Prasad", "Saxena", "Srivastava", "Trivedi", "Mani",
    "Naidu", "Pillai", "Menon", "Jha", "Thakur", "Rathore", "Shekhawat", "Gill", "Bahl", "Malhotra",
    "Kapoor", "Khanna", "Chawla", "Anand", "Bhasin", "Sood", "Malik", "Dutt", "Roy", "Basu"
]

ROLES = ["Software Engineer", "Frontend Engineer", "Backend Engineer", "Data Scientist", "ML Engineer", "DevOps Engineer", "QA Engineer", "Product Manager"]
LOCATIONS = ["Mumbai", "Bengaluru", "Pune", "Hyderabad", "Delhi NCR", "Chennai"]
COMPANIES = ["tcs", "google", "microsoft", "ibm", "infosys", "wipro", "accenture", "amazon", "cognizant", "capgemini", "isro", "drdo"]

def safe_int(val):
    if val is None or str(val).strip() == "":
        return 0
    try:
        return int(float(val))
    except Exception:
        return 0

def safe_float(val, default=None):
    if val is None or str(val).strip() == "":
        return default
    try:
        return float(val)
    except Exception:
        return default

def populate_from_csv(csv_path: str):
    random.seed(42) # Deterministic names/preferences for the 30,000 entries
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return
        
    print(f"Opening CSV dataset at {csv_path}...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Clean tables first to avoid unique constraint violations
    print("Clearing existing students and student_risks tables...")
    cursor.execute("DELETE FROM students")
    cursor.execute("DELETE FROM student_risks")
    
    students_data = []
    risks_data = []
    
    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            student_id = row['student_id']
            name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            
            # Numeric fields parsing with safe helpers
            cgpa = safe_float(row.get('cgpa'))
            backlog_count = safe_int(row.get('backlog_count'))
            attendance_rate = safe_float(row.get('attendance_percentage'), 100.0)
            internal_marks_avg = safe_float(row.get('internal_marks_avg'))
            gpa_trend = row.get('cgpa_trend', 'Stable')
            assignment_submission_rate = safe_float(row.get('assignment_submission_rate'), 100.0)
            lms_login_frequency = safe_int(row.get('lms_login_frequency'))
            
            hackathon_count = safe_int(row.get('hackathon_count'))
            weekly_study_hours = safe_float(row.get('study_hours_per_week'))
            time_management_score = safe_int(row.get('time_management_score'))
            coding_score = safe_int(row.get('coding_score'))
            ai_ml_score = safe_int(row.get('ai_ml_score'))
            communication_score = safe_int(row.get('communication_score'))
            teamwork_score = safe_int(row.get('teamwork_score'))
            presentation_score = safe_int(row.get('presentation_score'))
            internship_count = safe_int(row.get('internship_count'))
            completed_certifications = safe_int(row.get('certification_count'))
            
            fee_delay_days = safe_int(row.get('fee_delay_days'))
            financial_stress_score = safe_float(row.get('financial_stress_score'))
            
            # Initialize preferences as empty/null defaults (not present in original CSV)
            target_companies = json.dumps([])
            preferred_roles = json.dumps([])
            preferred_locations = json.dumps([])
            min_ctc = None
            company_types = json.dumps([])
            max_bond_years = None
            work_mode = None
            
            # Read CSV specific fields
            department = row.get('department')
            current_year = row.get('current_year')
            
            students_data.append((
                student_id, name, cgpa, backlog_count, attendance_rate, internal_marks_avg, gpa_trend,
                assignment_submission_rate, lms_login_frequency, hackathon_count, weekly_study_hours,
                time_management_score, coding_score, ai_ml_score, communication_score, teamwork_score,
                presentation_score, internship_count, completed_certifications, fee_delay_days,
                financial_stress_score, target_companies, preferred_roles, preferred_locations,
                min_ctc, company_types, max_bond_years, work_mode, department, current_year, 0, 0
            ))
            
            # Parse risks
            risk_band = row.get('academic_risk_band', 'Low')
            risk_score = safe_float(row.get('academic_risk_score'), 10.0)
            confidence = 0.95
            
            # Generate probabilities based on risk band
            if risk_band in ('High', 'Critical'):
                probs = {"Low": 0.05, "Medium": 0.15, "High": 0.80}
            elif risk_band == 'Medium':
                probs = {"Low": 0.15, "Medium": 0.70, "High": 0.15}
            else:
                probs = {"Low": 0.85, "Medium": 0.10, "High": 0.05}
                
            risks_data.append((
                student_id, risk_band, risk_score, confidence, json.dumps([]), json.dumps(probs), "2026-07-20T00:00:00Z"
            ))
            
            if (idx + 1) % 5000 == 0:
                print(f"Processed {idx + 1} records...")
                
    print(f"Inserting {len(students_data)} students into database...")
    cursor.executemany("""
        INSERT INTO students (
            student_id, name, cgpa, backlog_count, attendance_rate, internal_marks_avg, gpa_trend,
            assignment_submission_rate, lms_login_frequency, hackathon_count, weekly_study_hours,
            time_management_score, coding_score, ai_ml_score, communication_score, teamwork_score,
            presentation_score, internship_count, completed_certifications, fee_delay_days,
            financial_stress_score, target_companies, preferred_roles, preferred_locations,
            min_ctc, company_types, max_bond_years, work_mode, department, current_year, is_newly_active, added_by_mentor
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """, students_data)
    
    print(f"Inserting risk profiles for {len(risks_data)} students...")
    cursor.executemany("""
        INSERT INTO student_risks (
            student_id, risk_band, risk_score, confidence, top_factors, probabilities, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, risks_data)
    
    conn.commit()
    conn.close()
    print("Database population completed successfully!")

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    csv_path = os.path.join(base_dir, "datasets", "student_success_dataset_30000.csv")
    
    # Clean file database first
    db_path = os.path.join(base_dir, "services", "mentor-agent", "students.db")
    if os.path.exists(db_path):
        print(f"Deleting existing database file at {db_path} to recreate with new schema...")
        try:
            os.remove(db_path)
        except Exception as e:
            print(f"Could not delete database file: {e}. Dropping tables instead...")
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("DROP TABLE IF EXISTS students")
                cursor.execute("DROP TABLE IF EXISTS student_risks")
                cursor.execute("DROP TABLE IF EXISTS student_tasks")
                cursor.execute("DROP TABLE IF EXISTS student_resources")
                cursor.execute("DROP TABLE IF EXISTS intervention_reports")
                conn.commit()
                conn.close()
            except Exception as drop_err:
                print(f"Drop failed: {drop_err}")
                
    print("Initializing Database structure...")
    init_db()
    
    populate_from_csv(csv_path)

if __name__ == "__main__":
    main()
