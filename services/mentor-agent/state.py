from typing import TypedDict

class MentorState(TypedDict):
    student_id: str

    risk_profile: dict

    gathered_info: dict

    tools_called: list

    status: str

    response: dict