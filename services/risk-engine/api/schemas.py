# services/risk-engine/api/schemas.py
from pydantic import BaseModel, Field
from typing import Dict, Optional
import datetime

class StudentInput(BaseModel):
    student_id: Optional[str] = Field(None, description="Unique Student Identifier")
    department: Optional[str] = Field(None, description="Engineering Department Name")
    specialization: Optional[str] = Field(None, description="Domain Specialization Track")
    current_year: Optional[str] = Field(None, description="Current Academic Year (e.g., First Year)")
    gender: Optional[str] = Field(None, description="Gender Identity Indicator")
    cgpa_trend: Optional[str] = Field(None, description="CGPA Direction: Stable, Upward, Downward")
    attendance_trend: Optional[str] = Field(None, description="Attendance Direction: Stable, Improving, Declining")
    scholarship_status: Optional[str] = Field(None, description="Scholarship Bracket Placement")

    # Numeric Matrix Values
    semester: Optional[float] = None
    cgpa: Optional[float] = None
    semester_gpa: Optional[float] = None
    backlog_count: Optional[float] = None
    internal_marks_avg: Optional[float] = None
    assignment_submission_rate: Optional[float] = None
    lab_performance_score: Optional[float] = None
    project_score: Optional[float] = None
    attendance_percentage: Optional[float] = None
    classes_missed: Optional[float] = None
    lms_login_frequency: Optional[float] = None
    course_completion_rate: Optional[float] = None
    video_watch_percentage: Optional[float] = None
    quiz_attempt_rate: Optional[float] = None
    study_hours_per_week: Optional[float] = None
    club_participation_score: Optional[float] = None
    hackathon_count: Optional[float] = None
    technical_event_participation: Optional[float] = None
    leadership_score: Optional[float] = None
    extracurricular_score: Optional[float] = None
    fee_delay_days: Optional[float] = Field(None, description="Crucial cross-cutting parameter for scholarship monitoring logic")
    financial_stress_score: Optional[float] = None
    mentor_meetings_count: Optional[float] = None
    mentor_feedback_score: Optional[float] = None
    intervention_history_count: Optional[float] = None
    counseling_sessions: Optional[float] = None
    communication_score: Optional[float] = None
    presentation_score: Optional[float] = None
    teamwork_score: Optional[float] = None
    coding_score: Optional[float] = None
    aptitude_score: Optional[float] = None
    problem_solving_score: Optional[float] = None
    database_score: Optional[float] = None
    web_development_score: Optional[float] = None
    ai_ml_score: Optional[float] = None
    cloud_score: Optional[float] = None
    cybersecurity_score: Optional[float] = None
    linkedin_profile_score: Optional[float] = None
    resume_score: Optional[float] = None
    github_activity_score: Optional[float] = None
    portfolio_score: Optional[float] = None
    certification_count: Optional[float] = None
    mock_interview_score: Optional[float] = None
    group_discussion_score: Optional[float] = None
    internship_count: Optional[float] = None
    industry_project_count: Optional[float] = None
    open_source_contributions: Optional[float] = None
    stress_score: Optional[float] = None
    time_management_score: Optional[float] = None
    motivation_score: Optional[float] = None
    consistency_score: Optional[float] = None

    class Config:
        extra = "allow"

class PredictionResponse(BaseModel):
    student_id: Optional[str]
    risk_band: str
    risk_score: float
    confidence: float
    fee_delay_days: Optional[float] = Field(None, description="Echoed back to caller to feed the scholarship agent system pipeline")
    probabilities: Dict[str, float]
    last_updated: str

# ---------------------------------------------------------------------------
# RESPONSES
# ---------------------------------------------------------------------------

class TopFactor(BaseModel):
    feature: str
    importance: float
    value: str

class PredictionResponse(BaseModel):
    student_id: Optional[str]
    risk_band: str              # Critical | High | Medium | Low
    risk_score: float            # confidence * 100
    confidence: float            # raw probability
    fee_delay_days: Optional[float] = None
    top_factors: list[TopFactor] = []  # Added this field for dashboard & research use
    probabilities: Dict[str, float]
    last_updated: str

# ── ADD THIS MISSING CLASS BACK ──
class ProbabilityResponse(BaseModel):
    probabilities: Dict[str, float]


class HealthResponse(BaseModel):
    status:         str
    model_loaded:   bool
    encoder_loaded: bool
    n_features:     int
    classes:        list


class ErrorResponse(BaseModel):
    error:   str
    detail:  str    