def check_scholarship_eligibility(
    student_id: str,
    fee_delay_days: int
) -> dict:
    """
    Determines whether a student is eligible for scholarship review
    based on fee payment delay.
    """

    SCHOLARSHIP_THRESHOLD = 30

    if fee_delay_days >= SCHOLARSHIP_THRESHOLD:

        return {
            "student_id": student_id,
            "eligible": True,
            "fee_delay_days": fee_delay_days,
            "message": (
                "Student may qualify for financial assistance."
            )
        }

    return {
        "student_id": student_id,
        "eligible": False,
        "fee_delay_days": fee_delay_days,
        "message": (
            "Fee delay is below scholarship review threshold."
        )
    }