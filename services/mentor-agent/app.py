from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import logging
from dotenv import load_dotenv

load_dotenv(override=True)

from graph import graph
from tools.get_risk_profile import get_risk_profile
from tools.get_target_companies import get_target_companies
from tools.search_company_resources import search_multiple_company_resources, KNOWN_COMPANIES
from tools.placement_tool import draft_placement_plan
from database import (
    get_connection,
    save_student,
    get_student,
    save_generated_tasks,
    save_generated_resources,
    toggle_task_completion,
    get_student_tasks,
    get_student_resources,
    insert_intervention,
    approve_intervention,
    reject_intervention,
    get_latest_intervention
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    return get_connection()

app = FastAPI(
    title="Mentor & Student Agent API",
    version="1.0.0",
    description="AI Success & Placement Agent for Students and Mentors"
)


# ── Pydantic Request Models ───────────────────────────────────────────────────

class StudentRequest(BaseModel):
    student_id: str


class PlacementRequest(BaseModel):
    student_id: str


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



class StudentProfileModel(BaseModel):
    student_id: str = Field(..., description="Unique Student Identifier")
    name: str = Field(..., description="Full Name of the Student")
    
    # Academics
    cgpa: Optional[float] = None
    backlog_count: Optional[int] = 0
    attendance_rate: Optional[float] = 100.0
    internal_marks_avg: Optional[float] = None
    gpa_trend: Optional[str] = "Stable"
    assignment_submission_rate: Optional[float] = 100.0
    lms_login_frequency: Optional[int] = None
    
    # Skills & Study
    hackathon_count: Optional[int] = 0
    weekly_study_hours: Optional[float] = None
    time_management_score: Optional[int] = None
    coding_score: Optional[int] = None
    ai_ml_score: Optional[int] = None
    communication_score: Optional[int] = None
    teamwork_score: Optional[int] = None
    presentation_score: Optional[int] = None
    internship_count: Optional[int] = 0
    completed_certifications: Optional[int] = 0
    
    # Financial & Stress
    fee_delay_days: Optional[int] = 0
    financial_stress_score: Optional[float] = None
    
    # Career Preferences
    target_companies: Optional[List[str]] = []
    preferred_roles: Optional[List[str]] = []
    preferred_locations: Optional[List[str]] = []
    min_ctc: Optional[str] = None
    company_types: Optional[List[str]] = []
    max_bond_years: Optional[str] = None
    work_mode: Optional[str] = None
    
    # Added fields
    department: Optional[str] = None
    current_year: Optional[str] = None
    added_by_mentor: Optional[bool] = False


# ── Expose Static Files & Dashboard Root ──────────────────────────────────────

# Ensure static directory exists
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

@app.get("/")
def read_index():
    """
    Serves the Student Dashboard frontend.
    """
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        return {
            "message": "Welcome to Student Agent API. Frontend is not created yet.",
            "docs": "/docs",
            "health": "/health"
        }
    return FileResponse(index_path)


# ── Health & Diagnostics ──────────────────────────────────────────────────────

@app.get("/health")
def health():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy"
    }


# ── Student Data Management APIs ──────────────────────────────────────────────

@app.post("/api/students")
def create_or_update_student(profile: StudentProfileModel):
    """
    Saves or updates a student profile in the local SQLite database.
    """
    try:
        # Compatibility helper to support dump on pydantic v1 / v2
        data = profile.model_dump() if hasattr(profile, "model_dump") else profile.dict()
        data["is_newly_active"] = 1
        data["added_by_mentor"] = 1 if data.get("added_by_mentor") else 0
        save_student(data)
        return {"status": "success", "message": f"Student profile {profile.student_id} saved successfully."}
    except Exception as e:
        logger.error(f"Error saving student: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/students")
def list_students():
    """
    Lists all students in the database with their risk predictions, sorted as:
    1. Newly active (added/registered/logged in) students at the top.
    2. Year (First Year, Second Year, Third Year, Final Year).
    3. Department (Alphabetically).
    4. Risk band (Critical, High, Medium, Low).
    """
    try:
        from database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
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
                r.risk_band, 
                r.risk_score
            FROM students s
            LEFT JOIN student_risks r ON s.student_id = r.student_id
            ORDER BY 
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
                s.student_id ASC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        students_list = []
        for row in rows:
            student_dict = dict(row)
            if student_dict["risk_band"] is None:
                student_dict["risk_band"] = "Low"
                student_dict["risk_score"] = 10.0
            students_list.append(student_dict)
            
        return students_list
    except Exception as e:
        logger.error(f"Error listing students: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/students/{student_id}")
def read_student(student_id: str):
    """
    Fetches a student profile from the local SQLite database.
    """
    student = get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student profile {student_id} not found in database.")
    return student


@app.post("/api/faculty/register")
def register_faculty_endpoint(req: FacultyRegisterRequest):
    email = req.email.strip().lower()
    if not email.endswith("@spit.ac.in"):
        raise HTTPException(status_code=400, detail="Only email accounts with domain spit.ac.in are allowed to register.")
    
    from database import register_faculty
    success = register_faculty(req.name, email, req.password, req.department)
    if not success:
        raise HTTPException(status_code=400, detail="Email is already registered.")
    
    return {"status": "success", "message": "Faculty registered successfully."}

@app.post("/api/faculty/login")
def login_faculty_endpoint(req: FacultyLoginRequest):
    from database import authenticate_faculty
    user = authenticate_faculty(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return {"status": "success", "user": user}

@app.post("/api/students/{student_id}/claim")
def claim_student_endpoint(student_id: str, req: ClaimRequest):
    from database import claim_student
    success = claim_student(student_id, req.faculty_email)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to claim student.")
    return {"status": "success", "message": "Student claimed successfully."}

@app.post("/api/interventions/{intervention_id}/edit")
def edit_intervention_endpoint(intervention_id: int, req: EditInterventionRequest):
    from database import update_intervention
    plan = {
        "student_summary": req.student_summary,
        "recommended_actions": req.recommended_actions,
        "priority_level": req.priority_level,
        "follow_up_plan": req.follow_up_plan,
        "recommended_resources": [res.dict() for res in req.recommended_resources]
    }
    update_intervention(intervention_id, plan)
    return {"status": "success", "message": "Intervention report edited successfully."}



@app.get("/api/companies")
def list_companies():
    """
    Returns a sorted list of supported target companies for frontend dropdowns.
    """
    special_cases = {
        "tcs": "TCS",
        "ibm": "IBM",
        "isro": "ISRO",
        "drdo": "DRDO",
        "nic": "NIC",
        "rbi": "RBI"
    }
    
    formatted_companies = []
    for c in sorted(KNOWN_COMPANIES):
        name = special_cases.get(c) or c.replace("_", " ").title()
        formatted_companies.append({
            "key": c,
            "name": name
        })
    return formatted_companies


# ── AI Intervention Planner Endpoint ──────────────────────────────────────────

@app.post("/generate-intervention")
def generate_intervention(data: StudentRequest):
    """
    Generates a personalized intervention plan using the LangGraph workflow.
    """
    try:
        state = {
            "student_id": data.student_id,
            "risk_profile": {},
            "gathered_info": {},
            "tools_called": [],
            "status": "",
            "response": {}
        }

        result = graph.invoke(state)
        return result["response"]

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error generating intervention: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Mentor Agent Error: {str(e)}"
        )


class ApprovalRequest(BaseModel):
    approved_by: str


@app.post("/api/interventions")
def create_intervention(data: StudentRequest):
    """
    Triggers LangGraph to generate an academic intervention plan and saves it in the database.
    """
    try:
        state = {
            "student_id": data.student_id,
            "risk_profile": {},
            "gathered_info": {},
            "tools_called": [],
            "status": "",
            "response": {}
        }
        result = graph.invoke(state)
        plan = result["response"]
        
        # Save to database
        intervention_id = insert_intervention(data.student_id, plan)
        plan["intervention_id"] = intervention_id
        return plan
    except Exception as e:
        logger.error(f"Error generating and saving intervention: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/interventions/{intervention_id}/approve")
def api_approve_intervention(intervention_id: int, req: ApprovalRequest):
    """
    Approves an academic intervention plan.
    """
    try:
        approve_intervention(intervention_id, req.approved_by)
        return {"status": "success", "message": f"Intervention {intervention_id} approved."}
    except Exception as e:
        logger.error(f"Error approving intervention: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/interventions/{intervention_id}/reject")
def api_reject_intervention(intervention_id: int):
    """
    Rejects an academic intervention plan.
    """
    try:
        reject_intervention(intervention_id)
        return {"status": "success", "message": f"Intervention {intervention_id} rejected."}
    except Exception as e:
        logger.error(f"Error rejecting intervention: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/students/{student_id}/interventions/latest")
def api_get_latest_intervention(student_id: str):
    """
    Retrieves the latest academic student intervention report from the database.
    """
    try:
        plan = get_latest_intervention(student_id)
        return plan
    except Exception as e:
        logger.error(f"Error retrieving latest intervention: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ── AI Placement Plan Endpoint ────────────────────────────────────────────────

@app.post("/generate-placement-plan")
def generate_placement_plan(data: PlacementRequest):
    """
    Generates a personalized placement roadmap for a student.
    """
    try:
        tools_called = []

        # Step 1: Fetch risk profile (will query local DB first, then POST to remote Risk Engine)
        risk_profile = get_risk_profile(data.student_id)
        tools_called.append("get_risk_profile")

        # Step 2: Fetch target companies (will read from local DB first)
        target_companies = get_target_companies(data.student_id)
        tools_called.append("get_target_companies")

        # Step 3: Retrieve company context documents (RAG)
        company_data = {}
        if target_companies:
            company_data = search_multiple_company_resources(target_companies)
            tools_called.append("search_company_resources")

        # Step 4: Draft the placement plan
        placement_plan = draft_placement_plan(
            student_id=data.student_id,
            target_companies=target_companies,
            risk_band=risk_profile.get("risk_band"),
            risk_factors=risk_profile.get("top_factors", []),
            company_data=company_data,
            placement_profile=risk_profile.get("placement_profile", {})
        )
        tools_called.append("draft_placement_plan")

        # Save to SQLite database for task and progress tracking
        if placement_plan.get("generation_status") == "ok":
            plan_data = placement_plan.get("placement_plan")
            if plan_data:
                save_generated_tasks(data.student_id, plan_data.get("preparation_steps", []))
                save_generated_resources(data.student_id, plan_data.get("recommended_resources", []))

        # Build data source tracking metadata
        if company_data:
            data_source = {
                company: ("curated" if info["is_curated"] else "general_knowledge")
                for company, info in company_data.items()
            }
        else:
            data_source = "general_readiness"

        return {
            "student_id": data.student_id,
            "target_companies": target_companies,
            "placement_plan": placement_plan,
            "placement_data_source": data_source,
            "tools_called": tools_called,
            "status": "pending_approval",
            "risk_profile": {
                "risk_band": risk_profile.get("risk_band"),
                "risk_score": risk_profile.get("risk_score"),
                "top_factors": risk_profile.get("top_factors", [])
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating placement plan: {e}")
        raise HTTPException(status_code=500, detail=f"Placement Plan Error: {str(e)}")


# ── Progress & Task Tracking APIs ──────────────────────────────────────────────

class TaskToggleRequest(BaseModel):
    completed: bool


@app.post("/api/students/{student_id}/tasks/{task_index}/toggle")
def toggle_task(student_id: str, task_index: int, data: TaskToggleRequest):
    """
    Updates the completion status of a specific task.
    """
    try:
        toggle_task_completion(student_id, task_index, data.completed)
        return {"status": "success", "message": f"Task {task_index} completion updated to {data.completed}."}
    except Exception as e:
        logger.error(f"Error toggling task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class MentorTaskToggleRequest(BaseModel):
    completed: bool

@app.post("/api/students/{student_id}/mentor-tasks/{task_index}/toggle")
def toggle_mentor_task(student_id: str, task_index: int, data: MentorTaskToggleRequest):
    """
    Updates the completion status of a specific mentor-assigned task.
    """
    try:
        from database import toggle_mentor_task_completion
        toggle_mentor_task_completion(student_id, task_index, data.completed)
        return {"status": "success", "message": f"Mentor task {task_index} completion updated to {data.completed}."}
    except Exception as e:
        logger.error(f"Error toggling mentor task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/students/{student_id}/progress")
def get_student_progress(student_id: str):
    """
    Retrieves the student's saved placement checklist, resources, and progress percentage.
    """
    student = get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student profile {student_id} not found.")

    tasks = get_student_tasks(student_id)
    resources = get_student_resources(student_id)

    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.get("completed") == 1)
    progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Also fetch the current academic risk profile details to mirror dashboard
    try:
        risk_profile = get_risk_profile(student_id)
    except Exception:
        risk_profile = {}

    # Fetch mentor assigned tasks and progress
    from database import get_mentor_tasks, get_faculty, get_connection
    mentor_tasks = get_mentor_tasks(student_id)
    total_mentor = len(mentor_tasks)
    completed_mentor = sum(1 for t in mentor_tasks if t.get("completed") == 1)
    mentor_percentage = (completed_mentor / total_mentor * 100) if total_mentor > 0 else 0.0

    # Fetch assigned mentor
    assigned_email = student.get("assigned_faculty_email")
    mentor_info = {"name": "Dr. Sharma", "email": "sharma@spit.ac.in", "department": student.get("department") or "Computer Engineering"}
    if assigned_email:
        fac = get_faculty(assigned_email)
        if fac:
            mentor_info = {"name": fac["name"], "email": fac["email"], "department": fac["department"]}
    else:
        # Default to a faculty in the same department if registered
        dept = student.get("department")
        if dept:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name, email, department FROM faculty WHERE department = ? LIMIT 1", (dept,))
            row = cursor.fetchone()
            conn.close()
            if row:
                mentor_info = {"name": row["name"], "email": row["email"], "department": row["department"]}

    # Fetch mentor comments on student progress
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dashboard_comments WHERE student_id = ? ORDER BY comment_id DESC", (student_id,))
    comments = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "student_id": student_id,
        "name": student.get("name"),
        "target_companies": student.get("target_companies", []),
        "preferred_roles": student.get("preferred_roles", []),
        "tasks": tasks,
        "resources": resources,
        "risk_profile": {
            "risk_band": risk_profile.get("risk_band", "Low"),
            "risk_score": risk_profile.get("risk_score", 99.0)
        },
        "progress": {
            "total": total_tasks,
            "completed": completed_tasks,
            "percentage": round(progress_percentage, 1)
        },
        "mentor_tasks": mentor_tasks,
        "mentor_progress": {
            "total": total_mentor,
            "completed": completed_mentor,
            "percentage": round(mentor_percentage, 1)
        },
        "assigned_mentor": mentor_info,
        "comments": comments
    }



@app.get("/api/policies/{policy_name}")
def get_policy(policy_name: str):
    """
    Retrieves the raw content of university RAG markdown policies from resources/
    """
    import os
    safe_name = os.path.basename(policy_name)
    if not safe_name.endswith('.md'):
        safe_name += '.md'
    filepath = os.path.join("resources", safe_name)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Policy file not found.")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return {"policy_name": safe_name, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Mount Static Directory ────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")