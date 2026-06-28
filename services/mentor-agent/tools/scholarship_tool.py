def check_scholarship_eligibility(
    student_id: str,
    fee_delay_days: int
):

    if fee_delay_days >= 30:

        return {
            "eligible": True,
            "message":
            "Student may qualify for financial assistance."
        }

    return {
        "eligible": False,
        "message":
        "Fee delay is below scholarship review threshold."
    }

