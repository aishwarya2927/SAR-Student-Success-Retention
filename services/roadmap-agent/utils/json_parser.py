import json
import re


def parse_llm_json(raw_text: str):
    cleaned = raw_text.strip()

    # Remove markdown code fences if Gemini adds them
    cleaned = re.sub(r"^```json", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^```", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "error": "Invalid JSON returned by LLM",
            "raw_response": raw_text
        }