import requests
import os
import sys

# Ensure parent directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_student, get_connection

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


def get_local_risk_profile(student_id: str) -> dict:
    import json
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM student_risks WHERE student_id = ?", (student_id,))
        row = cursor.fetchone()
        conn.close()
    except Exception as e:
        print(f"Error fetching local risk profile from DB: {e}")
        return None
    
    if row:
        risk_dict = dict(row)
        try:
            top_factors = json.loads(risk_dict.get("top_factors", "[]"))
        except Exception:
            top_factors = []
        try:
            probabilities = json.loads(risk_dict.get("probabilities", "{}"))
        except Exception:
            probabilities = {}
            
        local_student = get_student(student_id) or {}
        target_cos = local_student.get("target_companies", [])
        target_company = target_cos[0] if target_cos else ""
        
        return {
            "student_id": student_id,
            "risk_band": risk_dict.get("risk_band", "Low"),
            "risk_score": risk_dict.get("risk_score", 15.0),
            "confidence": risk_dict.get("confidence", 0.9),
            "top_factors": filter_actual_risk_factors(top_factors),
            "probabilities": probabilities,
            "last_updated": risk_dict.get("last_updated"),
            "fee_delay_days": local_student.get("fee_delay_days", 0),
            "target_company": target_company,
            "placement_profile": {
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
        }
    return None


def calculate_heuristic_risk_profile(student_id: str) -> dict:
    import datetime
    local_student = get_student(student_id)
    
    risk_band = "Low"
    risk_score = 15.0
    confidence = 0.9
    top_factors = []
    
    if local_student:
        cgpa = local_student.get("cgpa") or 8.0
        attendance = local_student.get("attendance_rate") or 90.0
        backlogs = local_student.get("backlog_count") or 0
        fee_delay = local_student.get("fee_delay_days") or 0
        
        # Heuristic scoring
        factors_list = []
        score_sum = 0.0
        if cgpa < 6.0:
            score_sum += 40.0
            factors_list.append({"feature": "cgpa", "value": str(cgpa), "importance": 0.4})
        elif cgpa < 7.0:
            score_sum += 20.0
        
        if attendance < 65.0:
            score_sum += 40.0
            factors_list.append({"feature": "attendance_rate", "value": str(attendance), "importance": 0.4})
        elif attendance < 75.0:
            score_sum += 20.0
            
        if backlogs > 1:
            score_sum += 15.0
            factors_list.append({"feature": "backlog_count", "value": str(backlogs), "importance": 0.2})
        
        if fee_delay > 15:
            score_sum += 15.0
            factors_list.append({"feature": "fee_delay_days", "value": str(fee_delay), "importance": 0.15})
            
        risk_score = max(5.0, min(98.0, score_sum + (100.0 - attendance) * 0.2))
        if risk_score > 60.0:
            risk_band = "High"
        elif risk_score > 30.0:
            risk_band = "Medium"
        
        top_factors = factors_list
        
    probabilities = {
        "Critical": 0.01 if risk_band == "High" else 0.001,
        "High": 0.8 if risk_band == "High" else 0.05,
        "Medium": 0.7 if risk_band == "Medium" else 0.1,
        "Low": 0.9 if risk_band == "Low" else 0.05
    }
    
    target_cos = local_student.get("target_companies", []) if local_student else []
    target_company = target_cos[0] if target_cos else ""
    
    return {
        "student_id": student_id,
        "risk_band": risk_band,
        "risk_score": risk_score,
        "confidence": confidence,
        "top_factors": filter_actual_risk_factors(top_factors),
        "probabilities": probabilities,
        "last_updated": datetime.datetime.now().isoformat(),
        "fee_delay_days": local_student.get("fee_delay_days", 0) if local_student else 0,
        "target_company": target_company,
        "placement_profile": {
            "weekly_study_hours": local_student.get("weekly_study_hours") if local_student else None,
            "lms_login_frequency": local_student.get("lms_login_frequency") if local_student else None,
            "time_management_score": local_student.get("time_management_score") if local_student else None,
            "technical_skills": {
                "coding_score": local_student.get("coding_score") if local_student else None,
                "ai_ml_score": local_student.get("ai_ml_score") if local_student else None
            },
            "soft_skills": {
                "communication_skill_score": local_student.get("communication_score") if local_student else None,
                "teamwork_score": local_student.get("teamwork_score") if local_student else None,
                "presentation_score": local_student.get("presentation_score") if local_student else None
            },
            "portfolio_metrics": {
                "internship_count": local_student.get("internship_count") if local_student else None,
                "completed_certifications": local_student.get("completed_certifications") if local_student else None
            }
        }
    }


def save_local_risk_profile(profile: dict):
    import json
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO student_risks (
            student_id, risk_band, risk_score, confidence, top_factors, probabilities, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            profile["student_id"],
            profile["risk_band"],
            profile["risk_score"],
            profile["confidence"],
            json.dumps(profile["top_factors"]),
            json.dumps(profile["probabilities"]),
            profile["last_updated"]
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: Failed to save local risk profile cache: {e}")


def get_risk_profile(student_id: str) -> dict:
    """
    Fetches a student's risk profile. Checks the local database first;
    if a local record exists, sends a POST prediction request to the remote Risk Engine.
    Otherwise, falls back to a GET lookup on the remote database.
    If the remote Risk Engine fails, falls back to the local database cache or heuristic.
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
                timeout=10
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
            save_local_risk_profile(result)
            return result

        except Exception as e:
            print(f"Risk Engine prediction POST failed: {e}. Checking local cache/heuristic.")
            local_profile = get_local_risk_profile(student_id)
            if local_profile:
                return local_profile
            heuristic_profile = calculate_heuristic_risk_profile(student_id)
            save_local_risk_profile(heuristic_profile)
            return heuristic_profile

    # Fallback to GET lookup for legacy/synthetic students not stored locally
    try:
        response = requests.get(
            f"{RISK_ENGINE_URL}/predict/{student_id}",
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        result["top_factors"] = filter_actual_risk_factors(result.get("top_factors", []))
        save_local_risk_profile(result)
        return result

    except Exception as e:
        print(f"Risk Engine prediction GET failed: {e}. Checking local cache/heuristic.")
        local_profile = get_local_risk_profile(student_id)
        if local_profile:
            return local_profile
        heuristic_profile = calculate_heuristic_risk_profile(student_id)
        save_local_risk_profile(heuristic_profile)
        return heuristic_profile