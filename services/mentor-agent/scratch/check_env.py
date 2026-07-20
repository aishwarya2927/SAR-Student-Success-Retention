import os
from dotenv import load_dotenv
from google import genai

load_dotenv(override=True)

key1 = os.getenv("GEMINI_API_KEY")
key2 = os.getenv("GEMINI_API_KEY_PLACEMENT")

def mask(key):
    if not key:
        return "Not Set"
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]} (len={len(key)})"

print("--- Loaded Keys (with override=True) ---")
print(f"GEMINI_API_KEY: {mask(key1)}")
print(f"GEMINI_API_KEY_PLACEMENT: {mask(key2)}")

print("\nTesting connection to Gemini API...")
try:
    client = genai.Client(api_key=key1)
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents="Say hello in one word."
    )
    print(f"Success! Response: {response.text.strip()}")
except Exception as e:
    print(f"Failed: {e}")
