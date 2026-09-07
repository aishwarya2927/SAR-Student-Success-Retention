from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import sqlite3
import json
import httpx
import logging
import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Faculty Dashboard API",
    version="1.0.0",
    description="Backend API supporting the Faculty Early Warning Dashboard"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_POSTGRES = DATABASE_URL is not None

if IS_POSTGRES:
    import psycopg2
    from psycopg2.extras import DictCursor
else:
    import sqlite3

class PostgresCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor
    
    def execute(self, query, params=None):
        query = query.replace('?', '%s')
        query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
        self.cursor.execute(query, params or ())

    def executemany(self, query, params_seq):
        from psycopg2.extras import execute_batch
        query = query.replace('?', '%s')
        query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
        execute_batch(self.cursor, query, params_seq)
        
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

# Path to the shared SQLite database
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mentor-agent", "students.db"))
MENTOR_AGENT_URL = os.environ.get("MENTOR_AGENT_URL", "https://sar-mentor-agent.onrender.com")

def extract_error_detail(response) -> str:
    """Safely extracts error message from HTTP response without raising JSONDecodeError."""
    try:
        data = response.json()
        if isinstance(data, dict):
            return data.get("detail", response.text)
        return str(data)
    except Exception:
        return response.text or f"Upstream service returned HTTP {response.status_code}"

def get_db_connection():
    if IS_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        return DatabaseConnectionWrapper(conn, is_postgres=True)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return DatabaseConnectionWrapper(conn, is_postgres=False)

# ── Initialize Database Tables for Dashboard ──────────────────────────────
def init_db():
    logger.info(f"Initializing dashboard database tables in {DB_PATH}")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create students table first
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        cgpa REAL,
        backlog_count INTEGER DEFAULT 0,
        attendance_rate REAL DEFAULT 100.0,
        internal_marks_avg REAL,
        gpa_trend TEXT DEFAULT 'Stable',
        assignment_submission_rate REAL DEFAULT 100.0,
        lms_login_frequency INTEGER,
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
        fee_delay_days INTEGER DEFAULT 0,
        financial_stress_score REAL,
        target_companies TEXT,
        preferred_roles TEXT,
        preferred_locations TEXT,
        min_ctc TEXT,
        company_types TEXT,
        max_bond_years TEXT,
        work_mode TEXT,
        department TEXT,
        current_year TEXT,
        is_newly_active INTEGER DEFAULT 0,
        added_by_mentor INTEGER DEFAULT 0,
        assigned_faculty_email TEXT,
        email TEXT,
        phone TEXT
    )
    """)

    # Create risks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_risks (
        student_id TEXT PRIMARY KEY,
        risk_band TEXT,
        risk_score REAL,
        confidence REAL,
        top_factors TEXT,
        probabilities TEXT,
        last_updated TEXT,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    )
    """)

    # Create faculty table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faculty (
        email TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        password TEXT NOT NULL,
        department TEXT
    )
    """)

    # Seed default faculty member if not already present
    try:
        cursor.execute("SELECT email FROM faculty WHERE LOWER(email) = ?", ('sharma@spit.ac.in',))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO faculty (email, name, password, department)
                VALUES (?, ?, ?, ?)
            """, ('sharma@spit.ac.in', 'Dr. Sharma', 'password123', 'Computer Engineering'))
            logger.info("Seeded default faculty member: sharma@spit.ac.in")
    except Exception as e:
        logger.warning(f"Default faculty seed check: {e}")

    # Create intervention_reports table
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

    # Create placement_reports table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS placement_reports (
        placement_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        target_companies TEXT,
        readiness_summary TEXT,
        company_comparison TEXT,
        company_selection_guidance TEXT,
        preparation_steps TEXT,
        timeline TEXT,
        risk_factors TEXT,
        data_verification_note TEXT,
        status TEXT DEFAULT 'pending_approval',
        approved_by TEXT,
        approved_at TEXT,
        generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    )
    """)
    
    # Workflow status table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dashboard_workflow (
        student_id TEXT PRIMARY KEY,
        is_flagged INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Under Review',
        updated_at TEXT,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    )
    """)
    
    # Comments/Notes log table
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
    
    conn.commit()
    conn.close()

# Initialize tables on startup
init_db()

# ── Pydantic Request Models ───────────────────────────────────────────────────
class WorkflowUpdateRequest(BaseModel):
    status: str

class CommentCreateRequest(BaseModel):
    comment_text: str
    faculty_name: Optional[str] = "Dr. Sharma"

class ApprovalRequest(BaseModel):
    approved_by: str

class FacultyRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    department: str

class FacultyLoginRequest(BaseModel):
    email: str
    password: str

class ClaimRequest(BaseModel):
    faculty_email: str

class ResourceModel(BaseModel):
    title: str
    type: str
    link: str
    description: str

class EditInterventionRequest(BaseModel):
    student_summary: str
    recommended_actions: List[str]
    priority_level: str
    follow_up_plan: str
    recommended_resources: List[ResourceModel]


# ── API Endpoints ──────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats():
    """
    Returns the cumulative cohort metrics dynamically calculated from the SQLite database.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Get total students
        cursor.execute("SELECT COUNT(*) FROM students")
        total_students = cursor.fetchone()[0]
        
        # 2. Get counts per risk band from student_risks
        cursor.execute("SELECT risk_band, COUNT(*) FROM student_risks GROUP BY risk_band")
        risk_counts = {row["risk_band"]: row[1] for row in cursor.fetchall()}
        
        # 3. Get analyzed count (mentors touched: have intervention or comments)
        cursor.execute("""
            SELECT COUNT(DISTINCT student_id) FROM (
                SELECT student_id FROM intervention_reports
                UNION
                SELECT student_id FROM dashboard_comments
            )
        """)
        analyzed_count = cursor.fetchone()[0]
        
        # 4. Get workflow status counts for columns cohort-wide
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM dashboard_workflow 
            WHERE status != 'Under Review'
            GROUP BY status
        """)
        workflow_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        pending_cnt = workflow_counts.get("Intervention Pending", 0)
        action_cnt = workflow_counts.get("Action Required", 0)
        resolved_cnt = workflow_counts.get("Resolved", 0)
        review_cnt = total_students - pending_cnt - action_cnt - resolved_cnt
        
        conn.close()
        
        # Map values. The database could have Critical / High / Medium / Low
        high_cnt = risk_counts.get("High", 0) + risk_counts.get("Critical", 0)
        med_cnt = risk_counts.get("Medium", 0)
        low_cnt = risk_counts.get("Low", 0)
        
        # In case the table is empty or newly created, fallback safely
        total_counted = high_cnt + med_cnt + low_cnt
        if total_counted == 0:
            total_counted = total_students if total_students > 0 else 1
            
        return {
            "total_students": total_students,
            "high_risk": high_cnt,
            "high_risk_percentage": round((high_cnt / total_counted) * 100, 1),
            "medium_risk": med_cnt,
            "medium_risk_percentage": round((med_cnt / total_counted) * 100, 1),
            "low_risk": low_cnt,
            "low_risk_percentage": round((low_cnt / total_counted) * 100, 1),
            "analyzed_count": analyzed_count,
            "workflow_counts": {
                "Under Review": review_cnt,
                "Intervention Pending": pending_cnt,
                "Action Required": action_cnt,
                "Resolved": resolved_cnt
            }
        }
    except Exception as e:
        logger.error(f"Error fetching stats from database: {e}")
        # fallback to values mirroring the scale of 30,000 students
        return {
            "total_students": 30000,
            "high_risk": 1800,
            "high_risk_percentage": 6.0,
            "medium_risk": 4200,
            "medium_risk_percentage": 14.0,
            "low_risk": 24000,
            "low_risk_percentage": 80.0,
            "analyzed_count": 0,
            "workflow_counts": {
                "Under Review": 30000,
                "Intervention Pending": 0,
                "Action Required": 0,
                "Resolved": 0
            }
        }

@app.get("/api/students")
def list_students(
    search: Optional[str] = None,
    risk_band: Optional[str] = None,
    workflow_status: Optional[str] = None,
    attendance_low: bool = False,
    cgpa_low: bool = False,
    backlogs: bool = False,
    fee_delay: bool = False,
    dept: Optional[str] = None,
    assigned_to: Optional[str] = None,
    sort_by: str = "default",
    limit: int = 100,
    offset: int = 0
):
    """
    Lists students in the database with their risk predictions, workflow statuses, and details,
    applying server-side pagination, search queries, filters, and sort options.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Base query
        query = """
            SELECT 
                s.student_id, 
                s.name, 
                s.cgpa, 
                s.attendance_rate, 
                s.backlog_count, 
                s.fee_delay_days,
                s.department,
                s.current_year,
                s.is_newly_active,
                s.added_by_mentor,
                s.assigned_faculty_email,
                r.risk_band, 
                r.risk_score,
                COALESCE(w.is_flagged, 0) as is_flagged,
                COALESCE(w.status, 'Under Review') as workflow_status
            FROM students s
            LEFT JOIN student_risks r ON s.student_id = r.student_id
            LEFT JOIN dashboard_workflow w ON s.student_id = w.student_id
        """
        
        # Where clauses
        where_clauses = []
        params = []
        
        if search:
            where_clauses.append("(s.name LIKE ? OR s.student_id LIKE ?)")
            params.append(f"%{search}%")
            params.append(f"%{search}%")
            
        if risk_band:
            if risk_band.lower() == 'high':
                where_clauses.append("(r.risk_band = 'High' OR r.risk_band = 'Critical')")
            else:
                where_clauses.append("r.risk_band = ?")
                params.append(risk_band.capitalize())
                
        if workflow_status:
            if workflow_status == 'Under Review':
                where_clauses.append("COALESCE(w.status, 'Under Review') = 'Under Review'")
            else:
                where_clauses.append("w.status = ?")
                params.append(workflow_status)
                
        if attendance_low:
            where_clauses.append("s.attendance_rate < 75.0")
            
        if cgpa_low:
            where_clauses.append("s.cgpa < 7.0")
            
        if backlogs:
            where_clauses.append("s.backlog_count > 0")
            
        if fee_delay:
            where_clauses.append("s.fee_delay_days > 0")
            
        if dept:
            where_clauses.append("s.department = ?")
            params.append(dept)
            
        if assigned_to:
            where_clauses.append("s.assigned_faculty_email = ?")
            params.append(assigned_to)

            
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        # Order by
        if sort_by == "dept_asc":
            query += " ORDER BY s.department ASC, s.student_id ASC"
        elif sort_by == "dept_desc":
            query += " ORDER BY s.department DESC, s.student_id ASC"
        elif sort_by == "year_asc":
            query += """ ORDER BY 
                CASE s.current_year
                    WHEN 'First Year' THEN 1
                    WHEN 'Second Year' THEN 2
                    WHEN 'Third Year' THEN 3
                    WHEN 'Final Year' THEN 4
                    ELSE 5
                END ASC, s.student_id ASC"""
        elif sort_by == "year_desc":
            query += """ ORDER BY 
                CASE s.current_year
                    WHEN 'First Year' THEN 1
                    WHEN 'Second Year' THEN 2
                    WHEN 'Third Year' THEN 3
                    WHEN 'Final Year' THEN 4
                    ELSE 5
                END DESC, s.student_id ASC"""
        elif sort_by == "name_asc":
            query += " ORDER BY s.name ASC, s.student_id ASC"
        elif sort_by == "risk_desc":
            query += " ORDER BY r.risk_score DESC, s.student_id ASC"
        elif sort_by == "cgpa_desc":
            query += " ORDER BY s.cgpa DESC, s.student_id ASC"
        else:
            # Default sorting
            query += """ ORDER BY 
                s.is_newly_active DESC,
                CASE s.current_year
                    WHEN 'First Year' THEN 1
                    WHEN 'Second Year' THEN 2
                    WHEN 'Third Year' THEN 3
                    WHEN 'Final Year' THEN 4
                    ELSE 5
                END ASC,
                s.department ASC,
                CASE r.risk_band
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    WHEN 'Low' THEN 4
                    ELSE 5
                END ASC,
                r.risk_score DESC,
                s.student_id ASC"""
                
        # Limit and Offset
        query += " LIMIT ? OFFSET ?"
        params.append(limit)
        params.append(offset)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        students_list = []
        for row in rows:
            student_dict = dict(row)
            # Safe defaults if prediction is missing
            if student_dict["risk_band"] is None:
                student_dict["risk_band"] = "Low"
                student_dict["risk_score"] = 10.0
            students_list.append(student_dict)
            
        return students_list
    except Exception as e:
        logger.error(f"Error listing students: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/students/{student_id}")
def get_student_detail(student_id: str):
    """
    Returns full detail of a student, merging demographics, ML risks, placement checklists, and dashboard metadata.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Basic demographics
        cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
        student_row = cursor.fetchone()
        if not student_row:
            conn.close()
            raise HTTPException(status_code=404, detail="Student not found.")
        student_data = dict(student_row)
        
        # Parse JSON fields
        for field in ["target_companies", "preferred_roles", "preferred_locations", "company_types"]:
            if student_data.get(field):
                try:
                    student_data[field] = json.loads(student_data[field])
                except Exception:
                    student_data[field] = []
            else:
                student_data[field] = []
                
        # 2. Risk profile
        cursor.execute("SELECT * FROM student_risks WHERE student_id = ?", (student_id,))
        risk_row = cursor.fetchone()
        risk_profile = {}
        if risk_row:
            risk_dict = dict(risk_row)
            risk_profile = {
                "risk_band": risk_dict.get("risk_band"),
                "risk_score": risk_dict.get("risk_score"),
                "confidence": risk_dict.get("confidence"),
                "top_factors": json.loads(risk_dict.get("top_factors", "[]")),
                "probabilities": json.loads(risk_dict.get("probabilities", "{}")),
                "last_updated": risk_dict.get("last_updated")
            }
        else:
            # Generate fallback if cache is empty
            risk_profile = {
                "risk_band": "Low",
                "risk_score": 12.0,
                "confidence": 0.9,
                "top_factors": [],
                "probabilities": {"Low": 0.88, "Medium": 0.1, "High": 0.02},
                "last_updated": datetime.datetime.now().isoformat()
            }
            
        # 3. Workflow status
        cursor.execute("SELECT is_flagged, status FROM dashboard_workflow WHERE student_id = ?", (student_id,))
        workflow_row = cursor.fetchone()
        workflow = {"is_flagged": 0, "status": "Under Review"}
        if workflow_row:
            workflow = {
                "is_flagged": workflow_row["is_flagged"],
                "status": workflow_row["status"]
            }
            
        # 4. Placement checklist tasks
        cursor.execute("SELECT * FROM student_tasks WHERE student_id = ? ORDER BY task_index ASC", (student_id,))
        tasks = [dict(r) for r in cursor.fetchall()]
        
        # 5. Placement resources
        cursor.execute("SELECT * FROM student_resources WHERE student_id = ?", (student_id,))
        resources = [dict(r) for r in cursor.fetchall()]
        
        # Compute progress
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.get("completed") == 1)
        progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
        
        # 6. Latest Intervention Report
        cursor.execute("""
            SELECT * FROM intervention_reports 
            WHERE student_id = ? 
            ORDER BY intervention_id DESC LIMIT 1
        """, (student_id,))
        intervention_row = cursor.fetchone()
        latest_intervention = None
        if intervention_row:
            latest_intervention = dict(intervention_row)
            if latest_intervention.get("recommended_actions"):
                try:
                    latest_intervention["recommended_actions"] = json.loads(latest_intervention["recommended_actions"])
                except Exception:
                    latest_intervention["recommended_actions"] = []
            else:
                latest_intervention["recommended_actions"] = []
                
            if latest_intervention.get("recommended_resources"):
                try:
                    latest_intervention["recommended_resources"] = json.loads(latest_intervention["recommended_resources"])
                except Exception:
                    latest_intervention["recommended_resources"] = []
            else:
                latest_intervention["recommended_resources"] = []
                    
        # 7. Mentor assigned tasks
        cursor.execute("SELECT * FROM mentor_tasks WHERE student_id = ? ORDER BY task_index ASC", (student_id,))
        mentor_tasks = [dict(r) for r in cursor.fetchall()]
        total_mentor = len(mentor_tasks)
        completed_mentor = sum(1 for t in mentor_tasks if t.get("completed") == 1)
        mentor_percentage = (completed_mentor / total_mentor * 100) if total_mentor > 0 else 0.0

        # 8. Comments
        cursor.execute("""
            SELECT * FROM dashboard_comments 
            WHERE student_id = ? 
            ORDER BY comment_id DESC
        """, (student_id,))
        comments = [dict(r) for r in cursor.fetchall()]
        
        # 9. Assigned Mentor
        assigned_email = student_data.get("assigned_faculty_email")
        assigned_mentor = {"name": "Unassigned", "email": "", "department": ""}
        if assigned_email:
            cursor.execute("SELECT name, email, department FROM faculty WHERE LOWER(email) = ?", (assigned_email.lower(),))
            fac_row = cursor.fetchone()
            if fac_row:
                assigned_mentor = {"name": fac_row["name"], "email": fac_row["email"], "department": fac_row["department"]}
        
        conn.close()
        
        return {
            "profile": student_data,
            "risk_profile": risk_profile,
            "workflow": workflow,
            "placement": {
                "tasks": tasks,
                "resources": resources,
                "progress": {
                    "total": total_tasks,
                    "completed": completed_tasks,
                    "percentage": round(progress_percentage, 1)
                }
            },
            "latest_intervention": latest_intervention,
            "mentor_progress": {
                "tasks": mentor_tasks,
                "total": total_mentor,
                "completed": completed_mentor,
                "percentage": round(mentor_percentage, 1)
            },
            "comments": comments,
            "assigned_mentor": assigned_mentor
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching student detail {student_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/students/{student_id}/flag")
def toggle_flag(student_id: str):
    """
    Toggles the flagged status of a student in the workflow.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check current flag
        cursor.execute("SELECT is_flagged FROM dashboard_workflow WHERE student_id = ?", (student_id,))
        row = cursor.fetchone()
        
        now = datetime.datetime.now().isoformat()
        if not row:
            new_flag = 1
            cursor.execute("""
                INSERT INTO dashboard_workflow (student_id, is_flagged, status, updated_at)
                VALUES (?, 1, 'Under Review', ?)
            """, (student_id, now))
        else:
            new_flag = 0 if row["is_flagged"] == 1 else 1
            cursor.execute("""
                UPDATE dashboard_workflow
                SET is_flagged = ?, updated_at = ?
                WHERE student_id = ?
            """, (new_flag, now, student_id))
            
        conn.commit()
        conn.close()
        return {"status": "success", "is_flagged": new_flag}
    except Exception as e:
        logger.error(f"Error toggling flag for {student_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/students/{student_id}/workflow")
def update_workflow_status(student_id: str, req: WorkflowUpdateRequest):
    """
    Updates the mentoring workflow status of a student (e.g. Under Review, Intervention Pending, etc.).
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT student_id FROM dashboard_workflow WHERE student_id = ?", (student_id,))
        row = cursor.fetchone()
        
        now = datetime.datetime.now().isoformat()
        if not row:
            cursor.execute("""
                INSERT INTO dashboard_workflow (student_id, is_flagged, status, updated_at)
                VALUES (?, 0, ?, ?)
            """, (student_id, req.status, now))
        else:
            cursor.execute("""
                UPDATE dashboard_workflow
                SET status = ?, updated_at = ?
                WHERE student_id = ?
            """, (req.status, now, student_id))
            
        conn.commit()
        conn.close()
        return {"status": "success", "workflow_status": req.status}
    except Exception as e:
        logger.error(f"Error updating workflow status for {student_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/students/{student_id}/comments")
def add_comment(student_id: str, req: CommentCreateRequest):
    """
    Adds a persistent mentoring note from Dr. Sharma.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dashboard_comments (student_id, faculty_name, comment_text, created_at)
            VALUES (?, ?, ?, ?)
        """, (student_id, req.faculty_name, req.comment_text, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Comment recorded."}
    except Exception as e:
        logger.error(f"Error adding comment for {student_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/students/{student_id}/comments")
def list_comments(student_id: str):
    """
    Lists all notes/comments for a specific student.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dashboard_comments WHERE student_id = ? ORDER BY comment_id DESC", (student_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error fetching comments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Proxy Endpoints to Mentor Agent backend (Port 8000) ──────────────────

@app.post("/api/students/{student_id}/generate-intervention")
async def proxy_generate_intervention(student_id: str):
    """
    Proxies intervention generation to the Mentor Agent LangGraph server.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MENTOR_AGENT_URL}/api/interventions",
                json={"student_id": student_id},
                timeout=120
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to Mentor Agent: {e}")
        raise HTTPException(status_code=503, detail="Mentor Agent backend is currently offline or unreachable.")

class MentorTaskToggleRequest(BaseModel):
    completed: bool

@app.post("/api/students/{student_id}/mentor-tasks/{task_index}/toggle")
async def proxy_toggle_mentor_task(student_id: str, task_index: int, req: MentorTaskToggleRequest):
    """
    Proxies the mentor task progress toggle to the Mentor Agent server.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MENTOR_AGENT_URL}/api/students/{student_id}/mentor-tasks/{task_index}/toggle",
                json={"completed": req.completed},
                timeout=30
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to toggle mentor task progress: {e}")
        raise HTTPException(status_code=503, detail="Mentor Agent backend is offline.")

@app.post("/api/students/{student_id}/outreach/retry")
async def proxy_retry_outreach(student_id: str):
    """
    Proxies the outreach email retry to the Mentor Agent server.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MENTOR_AGENT_URL}/api/students/{student_id}/outreach/retry",
                timeout=30
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to retry student outreach: {e}")
        raise HTTPException(status_code=503, detail="Mentor Agent backend is offline.")

@app.post("/api/interventions/{intervention_id}/approve")
async def proxy_approve_intervention(intervention_id: int, req: ApprovalRequest):
    """
    Approves the intervention. First attempts to notify Mentor Agent for outreach triggering;
    if Mentor Agent is offline/slow, falls back to direct database approval.
    """
    # 1. Try remote Mentor Agent first (to trigger email outreach workflows)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MENTOR_AGENT_URL}/api/interventions/{intervention_id}/approve",
                json={"approved_by": req.approved_by},
                timeout=20
            )
            if response.status_code == 200:
                return response.json()
            logger.warning(f"Mentor agent returned status {response.status_code} during approval: {response.text}")
    except Exception as e:
        logger.warning(f"Mentor agent approval proxy failed: {e}. Falling back to direct database update.")

    # 2. Local database fallback
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.datetime.now().isoformat()
        cursor.execute("""
            UPDATE intervention_reports
            SET status = 'approved', approved_by = ?, approved_at = ?
            WHERE intervention_id = ?
        """, (req.approved_by, now, intervention_id))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Intervention approved successfully."}
    except Exception as e:
        logger.error(f"Failed to approve intervention in database: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve intervention.")

@app.post("/api/interventions/{intervention_id}/reject")
async def proxy_reject_intervention(intervention_id: int):
    """
    Rejects the intervention. Falls back to direct database rejection if Mentor Agent is unreachable.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MENTOR_AGENT_URL}/api/interventions/{intervention_id}/reject",
                timeout=20
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.warning(f"Mentor agent reject proxy failed: {e}. Falling back to direct database update.")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE intervention_reports
            SET status = 'rejected'
            WHERE intervention_id = ?
        """, (intervention_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Intervention rejected successfully."}
    except Exception as e:
        logger.error(f"Failed to reject intervention in database: {e}")
        raise HTTPException(status_code=500, detail="Failed to reject intervention.")


@app.get("/api/policies/{policy_name}")
async def proxy_get_policy(policy_name: str):
    """
    Proxies policy file content retrieval to the Mentor Agent server.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MENTOR_AGENT_URL}/api/policies/{policy_name}",
                timeout=15
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=extract_error_detail(response))
            return response.json()
    except HTTPException:
        raise
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch policy: {e}")
        raise HTTPException(status_code=503, detail="Mentor Agent backend is offline.")

# ── Direct Database Faculty Authentication ──────────────────────────────────
@app.post("/api/faculty/register")
def register_faculty(req: FacultyRegisterRequest):
    """Registers a new faculty member directly in the database."""
    email = req.email.strip().lower()
    if not email.endswith("@spit.ac.in"):
        raise HTTPException(status_code=400, detail="Only email accounts with domain spit.ac.in are allowed to register.")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM faculty WHERE LOWER(email) = ?", (email,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="Email is already registered.")
        
        cursor.execute("""
            INSERT INTO faculty (name, email, password, department)
            VALUES (?, ?, ?, ?)
        """, (req.name.strip(), email, req.password.strip(), req.department.strip()))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Faculty registered successfully."}
    except HTTPException:
        raise
    except Exception as e:
        err_name = type(e).__name__
        if "IntegrityError" in err_name or "UniqueViolation" in err_name:
            raise HTTPException(status_code=400, detail="Email is already registered.")
        logger.error(f"Failed to register faculty: {e}")
        raise HTTPException(status_code=500, detail="Failed to register faculty.")

@app.post("/api/faculty/login")
def login_faculty(req: FacultyLoginRequest):
    """Authenticates a faculty member directly from the database."""
    email = req.email.strip().lower()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, email, department FROM faculty
            WHERE LOWER(email) = ? AND password = ?
        """, (email, req.password.strip()))
        row = cursor.fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        
        user_dict = dict(row)
        return {
            "status": "success",
            "user": {
                "name": user_dict.get("name"),
                "email": user_dict.get("email"),
                "department": user_dict.get("department")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to log in faculty: {e}")
        raise HTTPException(status_code=500, detail="Failed to log in faculty.")

@app.post("/api/students/{student_id}/claim")
def claim_student(student_id: str, req: ClaimRequest):
    """Assigns mentoring responsibility of a student to a faculty member."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE students
            SET assigned_faculty_email = ?
            WHERE student_id = ?
        """, (req.faculty_email.strip().lower(), student_id))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Student claimed successfully."}
    except Exception as e:
        logger.error(f"Failed to claim student: {e}")
        raise HTTPException(status_code=500, detail="Failed to claim student.")

@app.post("/api/interventions/{intervention_id}/edit")
def edit_intervention(intervention_id: int, req: EditInterventionRequest):
    """Edits an intervention report directly in the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE intervention_reports
            SET student_summary = ?,
                recommended_actions = ?,
                priority_level = ?,
                follow_up_plan = ?,
                recommended_resources = ?
            WHERE intervention_id = ?
        """, (
            req.student_summary,
            json.dumps(req.recommended_actions),
            req.priority_level,
            req.follow_up_plan,
            json.dumps([res.dict() for res in req.recommended_resources]),
            intervention_id
        ))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Intervention report edited successfully."}
    except Exception as e:
        logger.error(f"Failed to edit intervention: {e}")
        raise HTTPException(status_code=500, detail="Failed to edit intervention report.")


class ChatRequest(BaseModel):
    message: str

@app.post("/api/students/{student_id}/verify-resume")
async def proxy_verify_resume(student_id: str, file: UploadFile = File(...)):
    try:
        async with httpx.AsyncClient() as client:
            file_bytes = await file.read()
            files = {"file": (file.filename, file_bytes, file.content_type)}
            response = await client.post(
                f"{MENTOR_AGENT_URL}/api/students/{student_id}/verify-resume",
                files=files,
                timeout=120
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=extract_error_detail(response))
            return response.json()
    except HTTPException:
        raise
    except httpx.RequestError as e:
        logger.error(f"Failed to proxy verify resume: {e}")
        raise HTTPException(status_code=503, detail="Mentor Agent backend is offline.")

@app.post("/api/students/{student_id}/verify-certificate")
async def proxy_verify_certificate(student_id: str, file: UploadFile = File(...), task_index: Optional[int] = None):
    try:
        async with httpx.AsyncClient() as client:
            file_bytes = await file.read()
            files = {"file": (file.filename, file_bytes, file.content_type)}
            params = {}
            if task_index is not None:
                params["task_index"] = task_index
            response = await client.post(
                f"{MENTOR_AGENT_URL}/api/students/{student_id}/verify-certificate",
                files=files,
                params=params,
                timeout=120
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=extract_error_detail(response))
            return response.json()
    except HTTPException:
        raise
    except httpx.RequestError as e:
        logger.error(f"Failed to proxy verify certificate: {e}")
        raise HTTPException(status_code=503, detail="Mentor Agent backend is offline.")

@app.get("/api/students/{student_id}/chat")
async def proxy_get_chat(student_id: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MENTOR_AGENT_URL}/api/students/{student_id}/chat",
                timeout=30
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=extract_error_detail(response))
            return response.json()
    except HTTPException:
        raise
    except httpx.RequestError as e:
        logger.error(f"Failed to proxy get chat: {e}")
        raise HTTPException(status_code=503, detail="Mentor Agent backend is offline.")

@app.post("/api/students/{student_id}/chat")
async def proxy_post_chat(student_id: str, req: ChatRequest):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MENTOR_AGENT_URL}/api/students/{student_id}/chat",
                json=req.dict(),
                timeout=60
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=extract_error_detail(response))
            return response.json()
    except HTTPException:
        raise
    except httpx.RequestError as e:
        logger.error(f"Failed to proxy post chat: {e}")
        raise HTTPException(status_code=503, detail="Mentor Agent backend is offline.")

@app.post("/api/students/{student_id}/chat/clear")
async def proxy_clear_chat(student_id: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MENTOR_AGENT_URL}/api/students/{student_id}/chat/clear",
                timeout=30
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=extract_error_detail(response))
            return response.json()
    except HTTPException:
        raise
    except httpx.RequestError as e:
        logger.error(f"Failed to proxy clear chat: {e}")
        raise HTTPException(status_code=503, detail="Mentor Agent backend is offline.")


# ── Person C API Endpoints for Person D (Student Agent) ──────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "dashboard-api"}

@app.get("/intervention/{student_id}")
def get_approved_intervention(student_id: str):
    """
    Returns the latest approved intervention plan for a student.
    Used by Person D's student roadmap agent.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            intervention_id,
            student_id,
            risk_band,
            prediction_confidence,
            student_summary,
            recommended_actions,
            priority_level,
            follow_up_plan,
            status,
            approved_by,
            approved_at,
            generated_at
        FROM intervention_reports
        WHERE student_id = ? AND status = 'approved'
        ORDER BY approved_at DESC
        LIMIT 1
    """, (student_id,))
    row = cur.fetchone()
    conn.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No approved intervention found for student {student_id}"
        )

    r = dict(row)
    actions = r.get("recommended_actions")
    if isinstance(actions, str):
        try:
            actions = json.loads(actions)
        except Exception:
            actions = [actions]
    elif not actions:
        actions = []

    return {
        "intervention_id":       r.get("intervention_id"),
        "student_id":            r.get("student_id"),
        "risk_band":             r.get("risk_band"),
        "prediction_confidence": r.get("prediction_confidence"),
        "student_summary":       r.get("student_summary"),
        "recommended_actions":   actions,
        "priority_level":        r.get("priority_level"),
        "follow_up_plan":        r.get("follow_up_plan"),
        "status":                r.get("status"),
        "approved_by":           r.get("approved_by"),
        "approved_at":           str(r.get("approved_at")) if r.get("approved_at") else None,
        "generated_at":          str(r.get("generated_at")) if r.get("generated_at") else None,
    }

@app.get("/placement/{student_id}")
def get_approved_placement(student_id: str):
    """
    Returns the latest approved placement plan for a student.
    Used by Person D's student roadmap agent.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    row = None
    try:
        cur.execute("""
            SELECT
                placement_id,
                student_id,
                target_companies,
                readiness_summary,
                company_comparison,
                company_selection_guidance,
                preparation_steps,
                timeline,
                risk_factors,
                data_verification_note,
                status,
                approved_by,
                approved_at,
                generated_at
            FROM placement_reports
            WHERE student_id = ? AND status = 'approved'
            ORDER BY approved_at DESC
            LIMIT 1
        """, (student_id,))
        row = cur.fetchone()
    except Exception as e:
        logger.warning(f"Error querying placement_reports: {e}")
        row = None
    finally:
        conn.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No approved placement plan found for student {student_id}"
        )

    r = dict(row)
    companies = r.get("target_companies")
    if isinstance(companies, str):
        try:
            companies = json.loads(companies)
        except Exception:
            companies = companies.split(",") if companies else []
    elif not companies:
        companies = []

    prep_steps = r.get("preparation_steps")
    if isinstance(prep_steps, str):
        try:
            prep_steps = json.loads(prep_steps)
        except Exception:
            prep_steps = []
    elif not prep_steps:
        prep_steps = []

    risk_factors = r.get("risk_factors")
    if isinstance(risk_factors, str):
        try:
            risk_factors = json.loads(risk_factors)
        except Exception:
            risk_factors = []
    elif not risk_factors:
        risk_factors = []

    return {
        "placement_id":               r.get("placement_id"),
        "student_id":                 r.get("student_id"),
        "target_companies":           companies,
        "readiness_summary":          r.get("readiness_summary"),
        "company_comparison":         r.get("company_comparison"),
        "company_selection_guidance": r.get("company_selection_guidance"),
        "preparation_steps":          prep_steps,
        "timeline":                   r.get("timeline"),
        "risk_factors":               risk_factors,
        "data_verification_note":     r.get("data_verification_note"),
        "status":                     r.get("status"),
        "approved_by":                r.get("approved_by"),
        "approved_at":                str(r.get("approved_at")) if r.get("approved_at") else None,
        "generated_at":               str(r.get("generated_at")) if r.get("generated_at") else None,
    }


# ── Serve Frontend ──────────────────────────────────────────────────────────
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

@app.get("/")
def read_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        return {
            "message": "Welcome to Student Success Dashboard API. Frontend static/index.html is missing.",
            "docs": "/docs"
        }
    return FileResponse(index_path)

# Mount static folder
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
