from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import json
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
    get_latest_intervention,
    save_chat_log,
    get_chat_logs,
    clear_chat_logs
)
from tools.chat_agent import process_student_chat


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
    email: Optional[str] = None
    phone: Optional[str] = None


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
        "email": student.get("email"),
        "phone": student.get("phone"),
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


class ChatRequest(BaseModel):
    message: str

@app.get("/api/students/{student_id}/chat")
def get_chat_history_endpoint(student_id: str):
    """
    Returns the student chat history.
    """
    try:
        logs = get_chat_logs(student_id)
        return logs
    except Exception as e:
        logger.error(f"Error fetching chat logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/students/{student_id}/chat")
async def chat_with_agent_endpoint(student_id: str, req: ChatRequest):
    """
    Submits a student message to the AI agent and returns the reply.
    """
    try:
        history = get_chat_logs(student_id)
        save_chat_log(student_id, "student", req.message)
        reply = process_student_chat(student_id, req.message, history)
        save_chat_log(student_id, "agent", reply)
        return {"response": reply}
    except Exception as e:
        logger.error(f"Error in chat agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/students/{student_id}/chat/clear")
def clear_chat_history_endpoint(student_id: str):
    """
    Clears the student chat history.
    """
    try:
        clear_chat_logs(student_id)
        return {"status": "success", "message": "Chat history cleared."}
    except Exception as e:
        logger.error(f"Error clearing chat logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/students/{student_id}/verify-resume")
async def verify_resume_endpoint(student_id: str, file: UploadFile = File(...)):
    """
    Upload and parse student CV using Gemini, audit it, and tick off the corresponding task.
    """
    try:
        from google import genai
        from google.genai import types
        file_bytes = await file.read()
        mime = file.content_type or "application/pdf"
        
        from llm.gemini_client import get_gemini_client
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY_PLACEMENT")
        client = get_gemini_client(api_key=api_key)
        
        prompt = """
        You are an expert resume checker.
        Audit this student resume. Check if it is well-formatted, lists clear skills (technical and soft),
        and highlights appropriate project experiences.
        Provide:
        1. An overall score (out of 10)
        2. Strong parts of the resume
        3. Specific gaps or formatting issues that need to be corrected.
        Return your analysis in clear markdown.
        """
        
        resp = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=[
                types.Part.from_bytes(
                    data=file_bytes,
                    mime_type=mime
                ),
                prompt
            ]
        )
        feedback = resp.text.strip()
        
        # Toggle the resume preparation task on the student checklist
        tasks = get_student_tasks(student_id)
        t_index_to_toggle = None
        for t in tasks:
            t_title = t["title"].lower()
            if "resume" in t_title or "cv" in t_title or "portfolio" in t_title:
                t_index_to_toggle = t["task_index"]
                toggle_task_completion(student_id, t["task_index"], True)
                break
                
        # Add feedback comment to the database so mentor can see it
        from database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        comment_text = f"[AUTOMATED CV VERIFICATION REPORT]\nScore: Audit Completed.\n{feedback[:800]}"
        cursor.execute("""
            INSERT INTO dashboard_comments (student_id, faculty_name, comment_text)
            VALUES (?, 'AI Resume Auditor', ?)
        """, (student_id, comment_text))
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "feedback": feedback,
            "task_toggled": t_index_to_toggle is not None,
            "task_index": t_index_to_toggle
        }
    except Exception as e:
        logger.error(f"Error verifying resume: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/students/{student_id}/verify-certificate")
async def verify_certificate_endpoint(student_id: str, file: UploadFile = File(...), task_index: Optional[int] = None):
    """
    Verify external certificates using Gemini Vision and check off tasks.
    """
    try:
        from google import genai
        from google.genai import types
        file_bytes = await file.read()
        mime = file.content_type or "image/png"
        
        from llm.gemini_client import get_gemini_client
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY_PLACEMENT")
        client = get_gemini_client(api_key=api_key)
        
        prompt = """
        You are an academic credential verifier.
        Check if this uploaded document is a valid certificate of completion or achievement.
        Extract:
        1. Recipient student name
        2. Certification subject / course title
        3. Validating platform (e.g. Coursera, Udemy, NPTEL)
        
        Return ONLY a valid JSON block containing:
        - "is_valid": boolean
        - "subject": string
        - "platform": string
        - "recipient": string
        - "reason": string
        Do not wrap in markdown or include extra text.
        """
        
        resp = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=[
                types.Part.from_bytes(
                    data=file_bytes,
                    mime_type=mime
                ),
                prompt
            ]
        )
        
        raw_text = resp.text.strip()
        logger.info(f"Certificate raw output from Gemini: {raw_text}")
        
        cleaned_text = raw_text
        if "```" in cleaned_text:
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[-1].split("```")[0].strip()
            else:
                parts = cleaned_text.split("```")
                if len(parts) >= 3:
                    cleaned_text = parts[1].strip()
                else:
                    cleaned_text = parts[-1].strip()
        
        # Strip potential leading/trailing markdown labels
        if cleaned_text.startswith("json"):
            cleaned_text = cleaned_text[4:].strip()
            
        result = json.loads(cleaned_text)
        
        is_valid = result.get("is_valid", False)
        subject = result.get("subject", "External Course")
        platform = result.get("platform", "Online Platform")
        recipient = result.get("recipient", "Student")
        
        toggled = False
        t_index = task_index
        
        if is_valid:
            if t_index is not None:
                toggle_task_completion(student_id, t_index, True)
                toggled = True
            else:
                tasks = get_student_tasks(student_id)
                for t in tasks:
                    t_title = t["title"].lower()
                    if "certif" in t_title or "course" in t_title or "nptel" in t_title:
                        toggle_task_completion(student_id, t["task_index"], True)
                        toggled = True
                        t_index = t["task_index"]
                        break
                        
            from database import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            comment_text = f"[AUTOMATED CERTIFICATE VERIFICATION]\nPlatform: {platform}\nTopic: {subject}\nRecipient: {recipient}\nStatus: Verified and Toggled Checklist."
            cursor.execute("""
                INSERT INTO dashboard_comments (student_id, faculty_name, comment_text)
                VALUES (?, 'AI Certificate Verifier', ?)
            """, (student_id, comment_text))
            conn.commit()
            conn.close()
            
        return {
            "status": "success",
            "is_valid": is_valid,
            "extracted_data": result,
            "task_toggled": toggled,
            "task_index": t_index
        }
    except Exception as e:
        import datetime
        import traceback
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_errors.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- Certificate Error: {datetime.datetime.now().isoformat()} ---\n")
            f.write(f"Student ID: {student_id}\n")
            f.write(f"Exception: {e}\n")
            f.write(traceback.format_exc())
            f.write("-----------------------------------------\n")
        logger.error(f"Error verifying certificate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_continuous_risk_monitor():
    """
    Background worker that runs periodically, scans for students crossing risk criteria,
    and automatically triggers the LangGraph intervention generation workflow.
    """
    import asyncio
    import datetime
    
    # Wait a few seconds for database and servers to boot
    await asyncio.sleep(5)
    logger.info("Continuous Risk Monitor background worker started.")
    
    while True:
        try:
            from database import get_connection, insert_intervention
            from graph import graph
            
            conn = get_connection()
            cursor = conn.cursor()
            
            # Select students with critical indicators who DO NOT have any intervention reports in intervention_reports (limit to 3 per cycle to preserve LLM API quota)
            cursor.execute("""
                SELECT s.student_id, s.name, s.cgpa, s.attendance_rate, s.backlog_count, s.fee_delay_days, s.financial_stress_score
                FROM students s
                LEFT JOIN intervention_reports i ON s.student_id = i.student_id
                WHERE i.student_id IS NULL AND (
                    s.cgpa < 7.0 OR 
                    s.attendance_rate < 75.0 OR 
                    s.backlog_count > 0 OR 
                    s.fee_delay_days > 30 OR 
                    s.financial_stress_score > 7.0
                )
                LIMIT 3
            """)
            at_risk_students = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            for student in at_risk_students:
                student_id = student["student_id"]
                logger.info(f"[MONITOR] Auto-escalating student {student_id} ({student['name']}) due to risk metrics.")
                
                state = {
                    "student_id": student_id,
                    "risk_profile": {},
                    "gathered_info": {},
                    "tools_called": [],
                    "status": "",
                    "response": {}
                }
                
                try:
                    result = graph.invoke(state)
                    plan = result["response"]
                    
                    # Insert the draft intervention
                    intervention_id = insert_intervention(student_id, plan)
                    
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    # Flag the student workflow
                    now = datetime.datetime.now().isoformat()
                    cursor.execute("""
                        INSERT INTO dashboard_workflow (student_id, is_flagged, status, updated_at)
                        VALUES (?, 1, 'Intervention Pending', ?)
                        ON CONFLICT(student_id) DO UPDATE SET
                            is_flagged = 1,
                            status = 'Intervention Pending',
                            updated_at = excluded.updated_at
                    """, (student_id, now))
                    
                    # Set is_newly_active in students table
                    cursor.execute("""
                        UPDATE students SET is_newly_active = 1 WHERE student_id = ?
                    """, (student_id,))
                    
                    # Add comment explaining auto-trigger
                    alert_comment = (
                        f"[SYSTEM ALERT] Student automatically flagged due to: "
                        f"CGPA: {student['cgpa']}, Attendance: {student['attendance_rate']}%, "
                        f"Backlogs: {student['backlog_count']}, Fee Delay: {student['fee_delay_days']} days. "
                        f"Draft intervention generated (ID: {intervention_id})."
                    )
                    cursor.execute("""
                        INSERT INTO dashboard_comments (student_id, faculty_name, comment_text)
                        VALUES (?, 'Risk Engine Monitor', ?)
                    """, (student_id, alert_comment))
                    
                    conn.commit()
                    conn.close()
                    logger.info(f"[MONITOR] Successfully generated draft intervention for {student_id}")
                    
                except Exception as ex:
                    logger.error(f"[MONITOR] Failed to auto-generate intervention for {student_id}: {ex}")
                    
        except Exception as e:
            logger.error(f"Error in Continuous Risk Monitor loop: {e}")
            
        # Poll every 60 seconds
        await asyncio.sleep(60)

@app.on_event("startup")
def start_background_monitor():
    import asyncio
    asyncio.create_task(run_continuous_risk_monitor())


# ── Mount Static Directory ────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")