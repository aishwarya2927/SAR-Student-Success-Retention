def get_risk_profile(student_id: str) -> dict:
    """
    Gets a student's risk profile.

    For now this returns mock data.
    Later it will call Person A's API.
    """

    mock_students = {
        "S1001": {
            "student_id": "S1001",
            "risk_score": 85,
            "risk_band": "high",
            "fee_delay_days": 45,
            "top_factors": [
                {"feature": "fee_delay"},
                {"feature": "backlog_count"}
            ]
        },

        "S1002": {
            "student_id": "S1002",
            "risk_score": 55,
            "risk_band": "medium",
            "fee_delay_days": 12,
            "top_factors": [
                {"feature": "attendance_drop"}
            ]
        }
    }

    return mock_students.get(student_id)