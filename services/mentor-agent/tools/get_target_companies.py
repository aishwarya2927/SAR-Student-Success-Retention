import os
import sys
import requests

# Ensure parent directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_student

PERSON_D_API_BASE = os.environ.get("PLACEMENT_API_BASE_URL", "https://sar-roadmap-agent.onrender.com")
USE_MOCK = os.environ.get("USE_MOCK_TARGET_COMPANY", "false").lower() == "true"

MOCK_COMPANY_MAP = {
    "STU202600011": ["Google", "Microsoft"],
    "STU202600033": ["TCS"],
    "STU202600099": [],
}


def get_target_companies(student_id: str):
    """
    Fetches the student's currently selected target companies. Checks the local
    database first. If not found, falls back to mock data or Person D's roadmap agent API.
    Returns a list of company name strings (possibly empty).
    """
    local_student = get_student(student_id)
    if local_student:
        return local_student.get("target_companies", [])

    if USE_MOCK:
        return MOCK_COMPANY_MAP.get(student_id, [])

    try:
        response = requests.get(
            f"{PERSON_D_API_BASE}/student-target-companies/{student_id}",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get("target_companies", [])

    except Exception as e:
        print(f"Target Companies Fetch Error: {e}")
        return []