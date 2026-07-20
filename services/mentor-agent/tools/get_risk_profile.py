import requests
import os
import sys

# Ensure parent directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_student

RISK_ENGINE_URL = "https://sar-student-success-retention.onrender.com"


def filter_actual_risk_factors(factors: list) -> list:
    if not factors:
        return []
    
    actual_risks = []
    for f in factors:
        if not isinstance(f, dict):
            # If it's a string, keep it unless it contains keywords indicating it's not a risk
            f_str = str(f).lower()
            if "nan" in f_str or "none" in f_str:
                continue
            actual_risks.append(f)
            continue
            
        feature = str(f.get("feature") or f.get("factor") or f.get("name") or "").strip().lower()
        val = f.get("value")
        
        # If value is None or NaN, it is not a risk
        if val is None:
            continue
        try:
            val_str = str(val).lower()
            if "nan" in val_str or "none" in val_str:
                continue
            val_float = float(val)
        except ValueError:
            actual_risks.append(f)
            continue
            
        # Filter out false risk factors (healthy values)
        if "backlog" in feature and val_float <= 0:
            continue
        if "assignment" in feature and val_float >= 80.0:
            continue
        if "attendance" in feature and val_float >= 75.0:
            continue
        if "stress" in feature and val_float <= 4.0:  # Stress score out of 10
            continue
        if "stress" in feature and val_float <= 40.0 and val_float > 10.0: # Stress score out of 100
            continue
        if "cgpa" in feature and val_float >= 7.0:
            continue
        if "marks" in feature and val_float >= 70.0:
            continue
        if "login" in feature and val_float >= 5.0: # LMS login frequency
            continue
        if "study_hours" in feature and val_float >= 15.0:
            continue
        if "delay" in feature and val_float <= 0: # Fee delay days
            continue
            
        actual_risks.append(f)
        
    return actual_risks


def get_risk_profile(student_id: str) -> dict:
    """
    Fetches a student's risk profile. Checks the local database first;
    if a local record exists, sends a POST prediction request to the remote Risk Engine.
    Otherwise, falls back to a GET lookup on the remote database.
    """

    local_student = get_student(student_id)

    if local_student:
        financial_stress = local_student.get("financial_stress_score")
        if financial_stress is not None and financial_stress > 10.0:
            financial_stress = financial_stress / 10.0

        # Construct the payload of academic/behavioral/financial features for the ML model
        payload = {
            "student_id": local_student.get("student_id"),
            "cgpa": local_student.get("cgpa"),
            "backlog_count": float(local_student.get("backlog_count", 0)) if local_student.get("backlog_count") is not None else None,
            "attendance_percentage": local_student.get("attendance_rate"),
            "internal_marks_avg": local_student.get("internal_marks_avg"),
            "cgpa_trend": local_student.get("gpa_trend"),
            "assignment_submission_rate": local_student.get("assignment_submission_rate"),
            "lms_login_frequency": float(local_student.get("lms_login_frequency")) if local_student.get("lms_login_frequency") is not None else None,
            "hackathon_count": float(local_student.get("hackathon_count", 0)) if local_student.get("hackathon_count") is not None else None,
            "study_hours_per_week": local_student.get("weekly_study_hours"),
            "time_management_score": float(local_student.get("time_management_score") / 10.0) if local_student.get("time_management_score") is not None else None,
            "coding_score": local_student.get("coding_score"),
            "ai_ml_score": local_student.get("ai_ml_score"),
            "communication_score": local_student.get("communication_score"),
            "teamwork_score": local_student.get("teamwork_score"),
            "presentation_score": local_student.get("presentation_score"),
            "internship_count": float(local_student.get("internship_count", 0)) if local_student.get("internship_count") is not None else None,
            "certification_count": float(local_student.get("completed_certifications", 0)) if local_student.get("completed_certifications") is not None else None,
            "fee_delay_days": float(local_student.get("fee_delay_days", 0)) if local_student.get("fee_delay_days") is not None else None,
            "financial_stress_score": financial_stress
        }

        # Filter out None values to let the Risk Engine handle missing inputs gracefully
        cleaned_payload = {k: v for k, v in payload.items() if v is not None}

        try:
            response = requests.post(
                f"{RISK_ENGINE_URL}/predict",
                json=cleaned_payload,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()

            # Inject the required local placement metadata and contract fields
            result["student_id"] = student_id
            result["fee_delay_days"] = local_student.get("fee_delay_days", 0)
            
            target_cos = local_student.get("target_companies", [])
            result["target_company"] = target_cos[0] if target_cos else ""
            
            result["placement_profile"] = {
                "weekly_study_hours": local_student.get("weekly_study_hours"),
                "lms_login_frequency": local_student.get("lms_login_frequency"),
                "time_management_score": local_student.get("time_management_score"),
                "technical_skills": {
                    "coding_score": local_student.get("coding_score"),
                    "ai_ml_score": local_student.get("ai_ml_score")
                },
                "soft_skills": {
                    "communication_skill_score": local_student.get("communication_score"),
                    "teamwork_score": local_student.get("teamwork_score"),
                    "presentation_score": local_student.get("presentation_score")
                },
                "portfolio_metrics": {
                    "internship_count": local_student.get("internship_count"),
                    "completed_certifications": local_student.get("completed_certifications")
                }
            }

            result["top_factors"] = filter_actual_risk_factors(result.get("top_factors", []))
            return result

        except requests.exceptions.Timeout:
            raise Exception("The Risk Engine API on Render timed out (cold-starting). Please click Generate again.")
        except requests.exceptions.HTTPError as e:
            try:
                detail = e.response.json().get("detail")
                raise Exception(f"Risk Engine Validation Error: {detail}")
            except Exception:
                raise Exception(f"Risk Engine Prediction HTTP Error: {e.response.status_code}")
        except requests.RequestException as e:
            raise Exception(f"Risk Engine POST Prediction Error: {str(e)}")

    # Fallback to GET lookup for legacy/synthetic students not stored locally
    try:
        response = requests.get(
            f"{RISK_ENGINE_URL}/predict/{student_id}",
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        result["top_factors"] = filter_actual_risk_factors(result.get("top_factors", []))
        return result

    except requests.exceptions.Timeout:
        raise Exception("The Risk Engine API on Render timed out (cold-starting). Please try again.")
    except requests.RequestException as e:
        raise Exception(f"Risk Engine API Error: {str(e)}")