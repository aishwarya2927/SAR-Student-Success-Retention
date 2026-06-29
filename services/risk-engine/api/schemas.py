"""
schemas.py — Pydantic request / response models for the Risk Engine API.

StudentInput covers all 62 columns the pipeline was trained on, including
the leakage columns that are still present in the saved model.
Every field has a default of None so callers can omit unknown columns;
missing fields are filled by the pipeline's own imputer.

NOTE: recommended_* columns are leakage and will be removed in the next
retrain.  They are kept here so the current saved pipeline runs correctly.
"""

from pydantic import BaseModel, Field
from typing import Dict, Optional
import datetime


# ---------------------------------------------------------------------------
# REQUEST
# ---------------------------------------------------------------------------

class StudentInput(BaseModel):

    # ── Identity (used for display, not fed to model) ───────────────────────
    student_id: Optional[str] = Field(None, description="Student identifier — display only, not a model feature")

    # ── Categorical features ─────────────────────────────────────────────────
    department:          Optional[str]   = None
    specialization:      Optional[str]   = None
    current_year:        Optional[str]   = None
    gender:              Optional[str]   = None
    cgpa_trend:          Optional[str]   = None
    attendance_trend:    Optional[str]   = None
    scholarship_status:  Optional[str]   = None

    # ── Academic performance ─────────────────────────────────────────────────
    semester:                    Optional[float] = None
    cgpa:                        Optional[float] = None
    semester_gpa:                Optional[float] = None
    backlog_count:               Optional[float] = None
    internal_marks_avg:          Optional[float] = None
    assignment_submission_rate:  Optional[float] = None
    lab_performance_score:       Optional[float] = None
    project_score:               Optional[float] = None

    # ── Attendance ───────────────────────────────────────────────────────────
    attendance_percentage: Optional[float] = None
    classes_missed:        Optional[float] = None

    # ── LMS / engagement ─────────────────────────────────────────────────────
    lms_login_frequency:    Optional[float] = None
    course_completion_rate: Optional[float] = None
    video_watch_percentage: Optional[float] = None
    quiz_attempt_rate:      Optional[float] = None
    study_hours_per_week:   Optional[float] = None

    # ── Extracurricular ──────────────────────────────────────────────────────
    club_participation_score:      Optional[float] = None
    hackathon_count:               Optional[float] = None
    technical_event_participation: Optional[float] = None
    leadership_score:              Optional[float] = None
    extracurricular_score:         Optional[float] = None

    # ── Financial ────────────────────────────────────────────────────────────
    fee_delay_days:        Optional[float] = None
    financial_stress_score:Optional[float] = None

    # ── Mentoring ────────────────────────────────────────────────────────────
    mentor_meetings_count:       Optional[float] = None
    mentor_feedback_score:       Optional[float] = None
    intervention_history_count:  Optional[float] = None
    counseling_sessions:         Optional[float] = None

    # ── Soft skills ──────────────────────────────────────────────────────────
    communication_score:   Optional[float] = None
    presentation_score:    Optional[float] = None
    teamwork_score:        Optional[float] = None

    # ── Technical skills ─────────────────────────────────────────────────────
    coding_score:           Optional[float] = None
    aptitude_score:         Optional[float] = None
    problem_solving_score:  Optional[float] = None
    database_score:         Optional[float] = None
    web_development_score:  Optional[float] = None
    ai_ml_score:            Optional[float] = None
    cloud_score:            Optional[float] = None
    cybersecurity_score:    Optional[float] = None

    # ── Career readiness ─────────────────────────────────────────────────────
    linkedin_profile_score:   Optional[float] = None
    resume_score:             Optional[float] = None
    github_activity_score:    Optional[float] = None
    portfolio_score:          Optional[float] = None
    certification_count:      Optional[float] = None
    mock_interview_score:     Optional[float] = None
    group_discussion_score:   Optional[float] = None
    internship_count:         Optional[float] = None
    industry_project_count:   Optional[float] = None
    open_source_contributions:Optional[float] = None

    # ── Wellbeing ─────────────────────────────────────────────────────────────
    stress_score:           Optional[float] = None
    time_management_score:  Optional[float] = None
    motivation_score:       Optional[float] = None
    consistency_score:      Optional[float] = None

    # ── Leakage columns (present in current saved pipeline — remove on retrain)
    recommended_intervention:  Optional[str]   = None
    recommended_career_path:   Optional[str]   = None
    recommended_certification: Optional[str]   = None
    recommended_course_track:  Optional[str]   = None

    class Config:
        # Allow extra fields — they are silently ignored by the predictor
        extra = "allow"


# ---------------------------------------------------------------------------
# RESPONSES
# ---------------------------------------------------------------------------

class TopFactor(BaseModel):
    feature:    str
    shap_value: float
    direction:  str   # "↑ increases risk" | "↓ decreases risk"


class PredictionResponse(BaseModel):
    student_id:           Optional[str]
    risk_band:            str              # Critical | High | Medium | Low
    risk_score:           float            # confidence × 100, range 0–100
    confidence:           float            # raw probability of predicted class
    probabilities:        Dict[str, float] # all 4 class probabilities
    last_updated:         str              # ISO 8601 UTC timestamp


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
