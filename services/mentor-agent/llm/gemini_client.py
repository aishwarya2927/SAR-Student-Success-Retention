import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set. Please add it to your environment or .env file.")
        _client = genai.Client(api_key=api_key)
    return _client


def generate_text(prompt: str):
    client = _get_client()
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )
    return response.text


if __name__ == "__main__":
    prompt = "Say hello in one sentence."
    try:
        print(generate_text(prompt))
    except Exception as e:
        print(f"Error: {e}")