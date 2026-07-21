SCHOLARSHIP_THRESHOLD = 30


def check_scholarship_eligibility(
    student_id: str,
    fee_delay_days: int
) -> dict:
    """
    Determines whether a student is eligible for scholarship review
    based on fee payment delay.
    """

    fee_delay_days = fee_delay_days or 0

    eligible = fee_delay_days >= SCHOLARSHIP_THRESHOLD

    return {
        "student_id": student_id,
        "eligible": eligible,
        "fee_delay_days": fee_delay_days,
        "message": (
            "Student may qualify for financial assistance."
            if eligible
            else "Fee delay is below scholarship review threshold."
        )
    }