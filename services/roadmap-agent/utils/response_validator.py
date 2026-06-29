REQUIRED_ROADMAP_KEYS = [
    "risk_summary",
    "risk_reasons",
    "priority_ranking",
    "four_week_plan",
    "support_needed",
    "risk_reduction_estimate",
    "encouraging_note"
]


def validate_roadmap_response(response) -> dict:
    if not isinstance(response, dict):
        return {
            "is_valid": False,
            "missing_keys": REQUIRED_ROADMAP_KEYS,
            "quality_note": "Response is not a dictionary/JSON object."
        }

    missing_keys = []

    for key in REQUIRED_ROADMAP_KEYS:
        if key not in response:
            missing_keys.append(key)

    is_valid = len(missing_keys) == 0

    return {
        "is_valid": is_valid,
        "missing_keys": missing_keys,
        "quality_note": "Response follows expected JSON structure." if is_valid else "Response is missing required JSON keys."
    }