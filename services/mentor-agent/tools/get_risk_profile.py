import requests

RISK_ENGINE_URL = "http://127.0.0.1:8000"


def get_risk_profile(student_id: str) -> dict:
    """
    Fetch student's risk profile from Person A's Risk Engine.
    """

    response = requests.get(
        f"{RISK_ENGINE_URL}/predict/{student_id}"
    )

    response.raise_for_status()

    return response.json()