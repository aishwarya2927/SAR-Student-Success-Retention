# services/risk-engine/api/schemas.py
from pydantic import BaseModel, Field
from typing import Dict, Optional, List

class StudentInput(BaseModel):
    # Categorical Attributes
    student_id: Optional[str] = Field(None, description="Unique Student Identifier")
    department: Optional[str] = Field(None, description="Engineering Department Name")
    specialization: Optional[str] = Field(None, description="Domain Specialization Track")
    current_year: Optional[str] = Field(None, description="Current Academic Year (e.g., First Year)")
    gender: Optional[str] = Field(None, description="Gender Identity Indicator")
    cgpa_trend: Optional[str] = Field(None, description="CGPA Direction: Stable, Upward, Downward")
    attendance_trend: Optional[str] = Field(None, description="Attendance Direction: Stable, Improving, Declining")
    scholarship_status: Optional[str] = Field(None, description="Scholarship Bracket Placement")

    # Numeric Matrix Values with Hardened Validation Guardrails
    semester: Optional[float] = Field(None, ge=1.0, le=8.0)
    cgpa: Optional[float] = Field(None, ge=0.0, le=10.0, description="CGPA on a 10-point scale")
    semester_gpa: Optional[float] = Field(None, ge=0.0, le=10.0)
    backlog_count: Optional[float] = Field(None, ge=0.0, description="Active backlogs")
    internal_marks_avg: Optional[float] = Field(None, ge=0.0, le=100.0)
    assignment_submission_rate: Optional[float] = Field(None, ge=0.0, le=100.0)
    lab_performance_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    project_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    attendance_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    classes_missed: Optional[float] = Field(None, ge=0.0)
    lms_login_frequency: Optional[float] = Field(None, ge=0.0)
    course_completion_rate: Optional[float] = Field(None, ge=0.0, le=100.0)
    video_watch_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    quiz_attempt_rate: Optional[float] = Field(None, ge=0.0, le=100.0)
    study_hours_per_week: Optional[float] = Field(None, ge=0.0, le=168.0)
    club_participation_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    hackathon_count: Optional[float] = Field(None, ge=0.0)
    technical_event_participation: Optional[float] = Field(None, ge=0.0)
    leadership_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    extracurricular_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    
    # Scholarship cross-cutting dependency
    fee_delay_days: Optional[float] = Field(None, ge=0.0, description="Crucial cross-cutting parameter for scholarship monitoring logic")
    
    financial_stress_score: Optional[float] = Field(None, ge=1.0, le=10.0)
    mentor_meetings_count: Optional[float] = Field(None, ge=0.0)
    mentor_feedback_score: Optional[float] = Field(None, ge=0.0, le=10.0)
    intervention_history_count: Optional[float] = Field(None, ge=0.0)
    counseling_sessions: Optional[float] = Field(None, ge=0.0)
    communication_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    presentation_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    teamwork_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    coding_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    aptitude_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    problem_solving_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    database_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    web_development_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    ai_ml_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    cloud_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    cybersecurity_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    linkedin_profile_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    resume_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    github_activity_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    portfolio_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    certification_count: Optional[float] = Field(None, ge=0.0)
    mock_interview_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    group_discussion_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    internship_count: Optional[float] = Field(None, ge=0.0)
    industry_project_count: Optional[float] = Field(None, ge=0.0)
    open_source_contributions: Optional[float] = Field(None, ge=0.0)
    stress_score: Optional[float] = Field(None, ge=1.0, le=10.0)
    time_management_score: Optional[float] = Field(None, ge=1.0, le=10.0)
    motivation_score: Optional[float] = Field(None, ge=1.0, le=10.0)
    consistency_score: Optional[float] = Field(None, ge=1.0, le=10.0)

    class Config:
        extra = "allow"

# ---------------------------------------------------------------------------
# RESPONSES & COMPONENT SCHEMAS
# ---------------------------------------------------------------------------

class TopFactor(BaseModel):
    feature: str
    importance: float
    value: str

class PredictionResponse(BaseModel):
    student_id: Optional[str]
    risk_band: str              # Critical | High | Medium | Low
    risk_score: float           # confidence * 100 (kept for frozen sub-team contract alignment)
    confidence_score: float     # Explicit percentage indicator for Gemini LLM context
    confidence: float           # Raw decimal probability
    fee_delay_days: Optional[float] = None # Echoed back for scholarship agent support
    top_factors: List[TopFactor] = []  # Injected dynamic SHAP feature importance tracking lists
    probabilities: Dict[str, float]
    last_updated: str

class ProbabilityResponse(BaseModel):
    probabilities: Dict[str, float]

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    encoder_loaded: bool
    n_features: int
    classes: List[str]

class ErrorResponse(BaseModel):
    error: str
    detail: str