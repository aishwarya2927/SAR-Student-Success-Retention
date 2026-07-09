import os
import requests

PERSON_D_API_BASE = os.environ.get("PLACEMENT_API_BASE_URL")
USE_MOCK = os.environ.get("USE_MOCK_TARGET_COMPANY", "false").lower() == "true"

MOCK_COMPANY_MAP = {
    "STU202600011": ["Google", "Microsoft"],
    "STU202600033": ["TCS"],
    "STU202600099": [],  # simulates a student who hasn't picked any company
}


def get_target_companies(student_id: str):
    """
    Fetches the student's currently selected target companies live from Person D's endpoint.
    Returns a list of company name strings (possibly empty).
    """
    if USE_MOCK:
        return MOCK_COMPANY_MAP.get(student_id, [])

    try:
        response = requests.get(
            f"{PERSON_D_API_BASE}/students/{student_id}/target-companies",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get("target_companies", [])

    except Exception as e:
        print(f"Target Companies Fetch Error: {e}")
        return []