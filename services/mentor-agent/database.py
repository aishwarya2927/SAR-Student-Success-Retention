import os
import json

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_POSTGRES = DATABASE_URL is not None

if IS_POSTGRES:
    import psycopg2
    from psycopg2.extras import DictCursor
else:
    import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "students.db")

class PostgresCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor
    
    def execute(self, query, params=None):
        # Translate SQLite placeholders to PostgreSQL placeholders
        query = query.replace('?', '%s')
        # Translate SQLite AUTOINCREMENT to PostgreSQL SERIAL keys
        query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
        self.cursor.execute(query, params or ())

    def executemany(self, query, params_seq):
        query = query.replace('?', '%s')
        query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
        self.cursor.executemany(query, params_seq)
        
    def fetchone(self):
        return self.cursor.fetchone()
        
    def fetchall(self):
        return self.cursor.fetchall()
        
    def __getattr__(self, name):
        return getattr(self.cursor, name)

class DatabaseConnectionWrapper:
    def __init__(self, conn, is_postgres=False):
        self.conn = conn
        self.is_postgres = is_postgres
        
    def cursor(self):
        cursor = self.conn.cursor(cursor_factory=DictCursor) if self.is_postgres else self.conn.cursor()
        return PostgresCursorWrapper(cursor) if self.is_postgres else cursor
        
    def commit(self):
        self.conn.commit()
        
    def close(self):
        self.conn.close()
        
    def __getattr__(self, name):
        return getattr(self.conn, name)

def get_connection():
    if IS_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        return DatabaseConnectionWrapper(conn, is_postgres=True)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return DatabaseConnectionWrapper(conn, is_postgres=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        
        -- Academics
        cgpa REAL,
        backlog_count INTEGER DEFAULT 0,
        attendance_rate REAL DEFAULT 100.0,
        internal_marks_avg REAL,
        gpa_trend TEXT DEFAULT 'Stable',
        assignment_submission_rate REAL DEFAULT 100.0,
        lms_login_frequency INTEGER,
        
        -- Skills & Study
        hackathon_count INTEGER DEFAULT 0,
        weekly_study_hours REAL,
        time_management_score INTEGER,
        coding_score INTEGER,
        ai_ml_score INTEGER,
        communication_score INTEGER,
        teamwork_score INTEGER,
        presentation_score INTEGER,
        internship_count INTEGER DEFAULT 0,
        completed_certifications INTEGER DEFAULT 0,
        
        -- Financial & Stress
        fee_delay_days INTEGER DEFAULT 0,
        financial_stress_score REAL,
        
        -- Placement preferences
        target_companies TEXT, -- JSON array of strings
        preferred_roles TEXT, -- JSON array of strings
        preferred_locations TEXT, -- JSON array of strings
        min_ctc TEXT,
        company_types TEXT, -- JSON array of strings
        max_bond_years TEXT,
        work_mode TEXT,
        
        -- Additional tracking columns
        department TEXT,
        current_year TEXT,
        is_newly_active INTEGER DEFAULT 0,
        added_by_mentor INTEGER DEFAULT 0
    )
    """)
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
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_tasks (
        student_id TEXT,
        task_index INTEGER,
        title TEXT NOT NULL,
        duration TEXT,
        priority TEXT,
        detail TEXT,
        completed INTEGER DEFAULT 0,
        PRIMARY KEY (student_id, task_index)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        title TEXT NOT NULL,
        type TEXT,
        link TEXT,
        description TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS intervention_reports (
        intervention_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        risk_band TEXT,
        prediction_confidence REAL,
        student_summary TEXT,
        recommended_actions TEXT,
        priority_level TEXT,
        follow_up_plan TEXT,
        recommended_resources TEXT,
        status TEXT DEFAULT 'pending_approval',
        approved_by TEXT,
        approved_at TEXT,
        generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    )
    """)
    # Faculty Dashboard workflow status table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dashboard_workflow (
        student_id TEXT PRIMARY KEY,
        is_flagged INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Under Review',
        updated_at TEXT,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    )
    """)
    # Faculty Dashboard comments/notes log table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dashboard_comments (
        comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        faculty_name TEXT DEFAULT 'Dr. Sharma',
        comment_text TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    )
    """)
    # Mentor-assigned tasks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mentor_tasks (
        student_id TEXT,
        task_index INTEGER,
        title TEXT NOT NULL,
        completed INTEGER DEFAULT 0,
        PRIMARY KEY (student_id, task_index)
    )
    """)
    # Faculty login/registration table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faculty (
        email TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        password TEXT NOT NULL,
        department TEXT
    )
    """)
    # Migration helper to add recommended_resources column if table existed prior
    try:
        cursor.execute("ALTER TABLE intervention_reports ADD COLUMN recommended_resources TEXT")
    except Exception:
        pass
    # Migration helper to add assigned_faculty_email to students table
    try:
        cursor.execute("ALTER TABLE students ADD COLUMN assigned_faculty_email TEXT")
    except Exception:
        pass
    conn.commit()
    conn.close()



def save_student(data: dict):
    conn = get_connection()
    cursor = conn.cursor()
    
    def to_json_str(val):
        if val is None:
            return "[]"
        if isinstance(val, (list, dict)):
            return json.dumps(val)
        return str(val)

    cursor.execute("""
    INSERT INTO students (
        student_id, name, cgpa, backlog_count, attendance_rate, internal_marks_avg, gpa_trend,
        assignment_submission_rate, lms_login_frequency, hackathon_count, weekly_study_hours,
        time_management_score, coding_score, ai_ml_score, communication_score, teamwork_score,
        presentation_score, internship_count, completed_certifications, fee_delay_days,
        financial_stress_score, target_companies, preferred_roles, preferred_locations,
        min_ctc, company_types, max_bond_years, work_mode,
        department, current_year, is_newly_active, added_by_mentor
    ) VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
    )
    ON CONFLICT(student_id) DO UPDATE SET
        name=excluded.name,
        cgpa=excluded.cgpa,
        backlog_count=excluded.backlog_count,
        attendance_rate=excluded.attendance_rate,
        internal_marks_avg=excluded.internal_marks_avg,
        gpa_trend=excluded.gpa_trend,
        assignment_submission_rate=excluded.assignment_submission_rate,
        lms_login_frequency=excluded.lms_login_frequency,
        hackathon_count=excluded.hackathon_count,
        weekly_study_hours=excluded.weekly_study_hours,
        time_management_score=excluded.time_management_score,
        coding_score=excluded.coding_score,
        ai_ml_score=excluded.ai_ml_score,
        communication_score=excluded.communication_score,
        teamwork_score=excluded.teamwork_score,
        presentation_score=excluded.presentation_score,
        internship_count=excluded.internship_count,
        completed_certifications=excluded.completed_certifications,
        fee_delay_days=excluded.fee_delay_days,
        financial_stress_score=excluded.financial_stress_score,
        target_companies=excluded.target_companies,
        preferred_roles=excluded.preferred_roles,
        preferred_locations=excluded.preferred_locations,
        min_ctc=excluded.min_ctc,
        company_types=excluded.company_types,
        max_bond_years=excluded.max_bond_years,
        work_mode=excluded.work_mode,
        department=excluded.department,
        current_year=excluded.current_year,
        is_newly_active=excluded.is_newly_active,
        added_by_mentor=excluded.added_by_mentor
    """, (
        data.get("student_id"),
        data.get("name"),
        data.get("cgpa"),
        data.get("backlog_count", 0),
        data.get("attendance_rate", 100.0),
        data.get("internal_marks_avg"),
        data.get("gpa_trend", "Stable"),
        data.get("assignment_submission_rate", 100.0),
        data.get("lms_login_frequency"),
        data.get("hackathon_count", 0),
        data.get("weekly_study_hours"),
        data.get("time_management_score"),
        data.get("coding_score"),
        data.get("ai_ml_score"),
        data.get("communication_score"),
        data.get("teamwork_score"),
        data.get("presentation_score"),
        data.get("internship_count", 0),
        data.get("completed_certifications", 0),
        data.get("fee_delay_days", 0),
        data.get("financial_stress_score"),
        to_json_str(data.get("target_companies", [])),
        to_json_str(data.get("preferred_roles", [])),
        to_json_str(data.get("preferred_locations", [])),
        data.get("min_ctc"),
        to_json_str(data.get("company_types", [])),
        data.get("max_bond_years"),
        data.get("work_mode"),
        data.get("department"),
        data.get("current_year"),
        data.get("is_newly_active", 0),
        data.get("added_by_mentor", 0)
    ))
    conn.commit()
    conn.close()

def get_student(student_id: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    
    result = dict(row)
    
    for field in ["target_companies", "preferred_roles", "preferred_locations", "company_types"]:
        if result.get(field):
            try:
                result[field] = json.loads(result[field])
            except Exception:
                result[field] = []
        else:
            result[field] = []
            
    return result

def save_generated_tasks(student_id: str, tasks: list[dict]):
    conn = get_connection()
    cursor = conn.cursor()
    # Remove existing tasks for this student to rebuild
    cursor.execute("DELETE FROM student_tasks WHERE student_id = ?", (student_id,))
    for idx, task in enumerate(tasks):
        cursor.execute("""
        INSERT INTO student_tasks (student_id, task_index, title, duration, priority, detail, completed)
        VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (
            student_id,
            idx,
            task.get("title", ""),
            task.get("duration", "unspecified"),
            task.get("priority", "secondary"),
            task.get("detail", ""),
        ))
    conn.commit()
    conn.close()

def save_generated_resources(student_id: str, resources: list[dict]):
    conn = get_connection()
    cursor = conn.cursor()
    # Remove existing resources for this student to rebuild
    cursor.execute("DELETE FROM student_resources WHERE student_id = ?", (student_id,))
    for res in resources:
        cursor.execute("""
        INSERT INTO student_resources (student_id, title, type, link, description)
        VALUES (?, ?, ?, ?, ?)
        """, (
            student_id,
            res.get("title", ""),
            res.get("type", "Course"),
            res.get("link", ""),
            res.get("description", ""),
        ))
    conn.commit()
    conn.close()

def toggle_task_completion(student_id: str, task_index: int, completed: bool):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE student_tasks
    SET completed = ?
    WHERE student_id = ? AND task_index = ?
    """, (1 if completed else 0, student_id, task_index))
    conn.commit()
    conn.close()

def get_student_tasks(student_id: str) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM student_tasks WHERE student_id = ? ORDER BY task_index ASC", (student_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_student_resources(student_id: str) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM student_resources WHERE student_id = ?", (student_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_mentor_tasks(student_id: str, actions: list):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mentor_tasks WHERE student_id = ?", (student_id,))
    for idx, action in enumerate(actions):
        cursor.execute("""
        INSERT INTO mentor_tasks (student_id, task_index, title, completed)
        VALUES (?, ?, ?, 0)
        """, (student_id, idx, action))
    conn.commit()
    conn.close()

def get_mentor_tasks(student_id: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mentor_tasks WHERE student_id = ? ORDER BY task_index ASC", (student_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def toggle_mentor_task_completion(student_id: str, task_index: int, completed: bool):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE mentor_tasks
    SET completed = ?
    WHERE student_id = ? AND task_index = ?
    """, (1 if completed else 0, student_id, task_index))
    conn.commit()
    conn.close()

def insert_intervention(student_id: str, plan: dict) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    
    risk_band = plan.get("risk_band")
    prediction_confidence = plan.get("prediction_confidence")
    student_summary = plan.get("student_summary")
    recommended_actions = json.dumps(plan.get("recommended_actions", []))
    priority_level = plan.get("priority_level")
    follow_up_plan = plan.get("follow_up_plan")
    recommended_resources = json.dumps(plan.get("recommended_resources", []))
    
    cursor.execute("""
    INSERT INTO intervention_reports (
        student_id, risk_band, prediction_confidence, student_summary,
        recommended_actions, priority_level, follow_up_plan, recommended_resources, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending_approval')
    """, (
        student_id, risk_band, prediction_confidence, student_summary,
        recommended_actions, priority_level, follow_up_plan, recommended_resources
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def approve_intervention(intervention_id: int, faculty_name: str):
    import datetime
    conn = get_connection()
    cursor = conn.cursor()
    approved_at = datetime.datetime.now().isoformat()
    
    # Fetch details to generate checklist tasks automatically on approval
    cursor.execute("SELECT student_id, recommended_actions FROM intervention_reports WHERE intervention_id = ?", (intervention_id,))
    row = cursor.fetchone()
    if row:
        student_id = row["student_id"]
        try:
            actions = json.loads(row["recommended_actions"])
        except Exception:
            actions = []
        save_mentor_tasks(student_id, actions)
        
    cursor.execute("""
    UPDATE intervention_reports
    SET status = 'approved', approved_by = ?, approved_at = ?
    WHERE intervention_id = ?
    """, (faculty_name, approved_at, intervention_id))
    conn.commit()
    conn.close()

def reject_intervention(intervention_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE intervention_reports
    SET status = 'rejected'
    WHERE intervention_id = ?
    """, (intervention_id,))
    conn.commit()
    conn.close()

def get_latest_intervention(student_id: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM intervention_reports
    WHERE student_id = ?
    ORDER BY intervention_id DESC LIMIT 1
    """, (student_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    res = dict(row)
    if res.get("recommended_actions"):
        try:
            res["recommended_actions"] = json.loads(res["recommended_actions"])
        except Exception:
            res["recommended_actions"] = []
    else:
        res["recommended_actions"] = []
        
    if res.get("recommended_resources"):
        try:
            res["recommended_resources"] = json.loads(res["recommended_resources"])
        except Exception:
            res["recommended_resources"] = []
    else:
        res["recommended_resources"] = []
    return res

def register_faculty(name: str, email: str, password: str, department: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO faculty (name, email, password, department)
            VALUES (?, ?, ?, ?)
        """, (name, email.strip().lower(), password, department))
        conn.commit()
        return True
    except Exception as e:
        err_name = type(e).__name__
        if "IntegrityError" in err_name or "UniqueViolation" in err_name:
            return False
        raise e
    finally:
        conn.close()

def authenticate_faculty(email: str, password: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, email, department FROM faculty
        WHERE LOWER(email) = ? AND password = ?
    """, (email.strip().lower(), password))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_faculty(email: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, email, department FROM faculty
        WHERE LOWER(email) = ?
    """, (email.strip().lower(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def claim_student(student_id: str, faculty_email: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE students
            SET assigned_faculty_email = ?
            WHERE student_id = ?
        """, (faculty_email.strip().lower() if faculty_email else None, student_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def update_intervention(intervention_id: int, plan: dict):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE intervention_reports
            SET student_summary = ?, recommended_actions = ?, priority_level = ?, follow_up_plan = ?, recommended_resources = ?
            WHERE intervention_id = ?
        """, (
            plan.get("student_summary"),
            json.dumps(plan.get("recommended_actions", [])),
            plan.get("priority_level"),
            plan.get("follow_up_plan"),
            json.dumps(plan.get("recommended_resources", [])),
            intervention_id
        ))
        conn.commit()
    finally:
        conn.close()

# Initialize DB on import/start
init_db()


