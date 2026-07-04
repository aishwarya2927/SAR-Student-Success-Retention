import requests

RISK_ENGINE_URL = "http://127.0.0.1:8000"


def get_risk_profile(student_id: str) -> dict:
    """
    Fetches a student's risk profile from the Risk Engine API.
    """

    try:

        response = requests.get(
            f"{RISK_ENGINE_URL}/predict/{student_id}",
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as e:

        raise Exception(
            f"Risk Engine API Error: {str(e)}"
        )