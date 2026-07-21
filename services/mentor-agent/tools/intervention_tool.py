import json
import time
import logging

from llm.gemini_client import generate_text

logger = logging.getLogger(__name__)

def draft_intervention_plan(
    risk_profile: dict,
    gathered_info: dict
) -> dict:
    """
    Generates a structured intervention plan using the Gemini LLM.
    """

    # Format top risk factors (if available)
    top_factors = "Not available."

    if risk_profile.get("top_factors"):

        top_factors = "\n".join(
            f"- {factor['feature'].replace('_', ' ').title()}"
            for factor in risk_profile["top_factors"]
        )

    # Format scholarship information
    scholarship_info = ""

    if "scholarship" in gathered_info:

        scholarship = gathered_info["scholarship"]

        status = (
            "Eligible"
            if scholarship["eligible"]
            else "Not Eligible"
        )

        scholarship_info = f"""
Scholarship Assessment

Status:
{status}

Reason:
{scholarship['message']}
"""

    # Format retrieved university resources
    resource_text = ""

    if gathered_info.get("resources"):

        resource_text = "Relevant University Support Resources\n\n"

        for index, resource in enumerate(
            gathered_info["resources"],
            start=1
        ):

            resource_text += (
                f"{index}. {resource}\n\n"
            )

    prompt = f"""
You are an experienced university academic mentor.

Student ID:
{risk_profile["student_id"]}

Predicted Risk Band:
{risk_profile["risk_band"]}

Model Confidence:
{risk_profile["confidence"] * 100:.2f}%

The confidence represents how certain the prediction model is about the assigned risk band. It is NOT a measure of the student's level of risk.

Top Risk Factors

{top_factors}

{scholarship_info}

{resource_text}

Return ONLY a valid JSON object.

Use this exact schema:

{{
  "student_summary": "string",
  "recommended_actions": [
    "string",
    "string"
  ],
  "priority_level": "High | Medium | Low",
  "follow_up_plan": "string",
  "recommended_resources": [
    {{
      "title": "Resource/Course/Playlist Title (e.g. 'Advanced Algebra' or 'Calculus Prep')",
      "type": "Course | Playlist | Documentation | Book",
      "link": "MUST be a specific, direct URL to a real course, video playlist, or documentation. Avoid generic search results pages. Recommending well-known educational courses or playlists from reputable publishers (such as freeCodeCamp, Khan Academy, MIT OpenCourseWare, NPTEL, Coursera, or edX) with direct, valid playlist/course URLs (e.g., 'https://www.youtube.com/playlist?list=PL2_aWCzGMAwI3W_AddcH5UfGRJyfs54g7' for Data Structures, or specific course pages on Coursera/edX) is highly preferred.",
      "description": "Short explanation of why this resource is suggested for the student's academic weaknesses"
    }}
  ]
}}

Requirements:
- Do not include markdown.
- Do not wrap the JSON in ``` blocks.
- Do not include explanations before or after the JSON.
- Recommend only actions supported by the provided information.
- Use the retrieved university resources naturally while generating recommendations.
- Do not mention document names, resource numbers, retrieval results, or internal references in the final response.
- Do not invent student information.
- Provide 2-4 recommended_resources (courses, playlists, or documents) tailored to the student's specific academic or study gaps.
"""

    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

    for attempt in range(MAX_RETRIES):

        try:

            recommendation = generate_text(prompt)

            return json.loads(recommendation)

        except json.JSONDecodeError:

            return {
                "error": "Gemini returned an invalid JSON response.",
                "raw_response": recommendation
            }
        except Exception as e:

            # Retry only if attempts remain
            if attempt < MAX_RETRIES - 1:

                logger.warning(
                    f"Gemini request failed "
                    f"(Attempt {attempt + 1}/{MAX_RETRIES}). "
                    f"Retrying in {RETRY_DELAY} seconds..."
                )

                time.sleep(RETRY_DELAY)

            else:

                return {
                    "error": (
                        "Unable to generate intervention plan "
                        f"after {MAX_RETRIES} attempts: {str(e)}"
                    )
                }


def draft_low_risk_plan(
    student_profile: dict,
    risk_profile: dict
) -> dict:
    """
    Generates a personalized keep-it-up message and optional course suggestions for low-risk students using Gemini.
    """
    name = student_profile.get("name", "Student")
    cgpa = student_profile.get("cgpa", "N/A")
    attendance = student_profile.get("attendance_rate", "N/A")
    backlogs = student_profile.get("backlog_count", 0)
    coding_score = student_profile.get("coding_score", "N/A")
    communication_score = student_profile.get("communication_score", "N/A")
    department = student_profile.get("department", "N/A")

    prompt = f"""
You are an experienced university academic mentor.
Write a personalized supportive note for a student who is doing exceptionally well and has been categorized as Low Risk.

Student Details:
- Name: {name}
- Department: {department}
- CGPA: {cgpa}
- Attendance Rate: {attendance}%
- Active Backlogs: {backlogs}
- Coding Score: {coding_score}
- Communication Score: {communication_score}

Return ONLY a valid JSON object.

Use this exact schema:
{{
  "student_summary": "A positive note congratulating the student on their specific strengths (e.g. high CGPA, attendance, or coding scores) and encouraging them to keep it up and do good at what they are doing well.",
  "recommended_actions": [
    "string",
    "string"
  ],
  "priority_level": "Low",
  "follow_up_plan": "A light monitoring follow-up plan.",
  "recommended_resources": [
    {{
      "title": "Resource/Course/Playlist Title",
      "type": "Course | Playlist | Documentation",
      "link": "MUST be a specific, direct URL to a real course, video playlist, or documentation. e.g. Khan Academy or MIT OpenCourseWare.",
      "description": "Short explanation of the course, explicitly mentioning that completing this is optional and not compulsory (e.g. 'Highly recommended for advanced learning, but not compulsory')."
    }}
  ]
}}

Requirements:
- Do not include markdown.
- Do not wrap the JSON in ``` blocks.
- Do not include explanations before or after the JSON.
- Provide 1-3 recommended_resources (courses or playlists) tailored to their branch/strengths, with a clear note that they are not compulsory.
"""

    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

    for attempt in range(MAX_RETRIES):
        try:
            recommendation = generate_text(prompt)
            # Remove potential markdown wraps if Gemini returns it despite instructions
            cleaned = recommendation.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            return json.loads(cleaned)
        except json.JSONDecodeError:
            if attempt == MAX_RETRIES - 1:
                return {
                    "student_summary": f"Keep up the great work, {name}! Your academic indicators look excellent.",
                    "recommended_actions": ["Maintain current study habits", "Attend all classes"],
                    "priority_level": "Low",
                    "follow_up_plan": "Routine semester tracking.",
                    "recommended_resources": [
                        {
                            "title": "MIT OpenCourseWare Computer Science",
                            "type": "Course",
                            "link": "https://ocw.mit.edu/",
                            "description": "Optional learning resource for advanced topics (Not compulsory)."
                        }
                    ]
                }
            time.sleep(RETRY_DELAY)
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                return {
                    "student_summary": f"Keep up the great work, {name}! Your academic indicators look excellent.",
                    "recommended_actions": ["Maintain current study habits", "Attend all classes"],
                    "priority_level": "Low",
                    "follow_up_plan": "Routine semester tracking.",
                    "recommended_resources": [
                        {
                            "title": "MIT OpenCourseWare Computer Science",
                            "type": "Course",
                            "link": "https://ocw.mit.edu/",
                            "description": "Optional learning resource for advanced topics (Not compulsory)."
                        }
                    ]
                }