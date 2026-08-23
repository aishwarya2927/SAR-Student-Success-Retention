import os
import sys
from dotenv import load_dotenv

# Load env variables
load_dotenv(override=True)

# Add mentor-agent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from google.genai import types

def test():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY_PLACEMENT")
    print(f"API Key loaded (first 8 chars): {api_key[:8] if api_key else 'None'}")
    
    if not api_key:
        print("Error: No API key found.")
        return
        
    client = genai.Client(api_key=api_key)
    
    # 1. Test basic text generation
    print("Testing basic text generation...")
    try:
        resp = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents="Say hello!"
        )
        print(f"Success! Response: {resp.text.strip()}")
    except Exception as e:
        print(f"Text generation failed: {e}")
        
    # 2. Test inline bytes generation (dummy PDF bytes)
    print("\nTesting inline PDF bytes generation...")
    dummy_pdf_bytes = b"%PDF-1.4 ... dummy content ..."
    try:
        resp = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=[
                types.Part.from_bytes(
                    data=dummy_pdf_bytes,
                    mime_type="application/pdf"
                ),
                "Is this a valid PDF? Answer yes or no."
            ]
        )
        print(f"Success! PDF Response: {resp.text.strip()}")
    except Exception as e:
        print(f"Inline PDF generation failed: {e}")

if __name__ == "__main__":
    test()
