import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from utils.json_parser import parse_llm_json

load_dotenv(".env")


def get_llm():
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in .env")

    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.3,
    )


def ask_gemini(prompt: str):
    """
    Use this only when Gemini must return JSON.
    Example: roadmap generation.
    """
    llm = get_llm()
    response = llm.invoke(prompt)
    return parse_llm_json(response.content)


def ask_gemini_text(prompt: str):
    """
    Use this when Gemini can return normal text.
    Example: career guidance.
    """
    llm = get_llm()
    response = llm.invoke(prompt)
    return response.content