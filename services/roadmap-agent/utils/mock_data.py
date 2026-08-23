def get_mock_risk_profile(student_id: str) -> dict:
    return {
        "student_id": student_id,
        "risk_score": 78,
        "risk_band": "high",
        "top_factors": [
            {
                "feature": "attendance_drop",
                "value": -18,
                "shap_contribution": 0.31
            },
            {
                "feature": "backlog_count",
                "value": 2,
                "shap_contribution": 0.24
            },
            {
                "feature": "fee_delay",
                "value": 45,
                "shap_contribution": 0.19
            }
        ],
        "last_updated": "2026-06-20T10:00:00Z"
    }