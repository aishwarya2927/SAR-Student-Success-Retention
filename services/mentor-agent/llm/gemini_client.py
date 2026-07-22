import os
import time
import logging
from dotenv import load_dotenv
from google import genai

load_dotenv()

logger = logging.getLogger(__name__)

class ModelsWrapper:
    def __init__(self, client_wrapper):
        self.client_wrapper = client_wrapper
        
    def generate_content(self, model, contents, **kwargs):
        return self.client_wrapper._call_with_fallback('generate_content', model, contents, **kwargs)
        
    def embed_content(self, model, contents, **kwargs):
        return self.client_wrapper._call_with_fallback('embed_content', model, contents, **kwargs)

class FallbackGeminiClient:
    # Class-level dictionary to cache failure timestamps for each API key
    # key -> float (timestamp until which it should be skipped)
    _failed_keys_until = {}

    def __init__(self, api_key=None):
        self.api_key_override = api_key
        self.keys = []
        
        # If an override key is provided, try it first
        if api_key:
            self.keys.append(api_key)
            
        # Collect keys from env variables (supporting multiple backup keys)
        env_vars = ["GEMINI_API_KEY", "GEMINI_API_KEY_PLACEMENT", "GEMINI_API_KEY_3", "GEMINI_API_KEY_4", "GEMINI_API_KEY_5"]
        for var in env_vars:
            val = os.getenv(var)
            if val and val not in self.keys:
                self.keys.append(val)
                
        # Cache of initialized clients: key -> genai.Client
        self._clients = {}
        self.models = ModelsWrapper(self)

    def _get_client(self, key):
        if key not in self._clients:
            self._clients[key] = genai.Client(api_key=key)
        return self._clients[key]

    def _call_with_fallback(self, method_name, model, contents, **kwargs):
        now = time.time()
        
        # Filter keys: try to find keys that haven't failed recently
        available_keys = [k for k in self.keys if now >= FallbackGeminiClient._failed_keys_until.get(k, 0.0)]
        
        # If all keys have failed recently, reset cooldowns to prevent complete lockout
        if not available_keys:
            logger.info("All Gemini API keys are in cooldown. Resetting cooldowns to retry.")
            available_keys = self.keys
            
        if not available_keys:
            raise ValueError("No Gemini API keys are configured in the environment.")

        last_error = None
        for key in available_keys:
            try:
                client = self._get_client(key)
                method = getattr(client.models, method_name)
                return method(model=model, contents=contents, **kwargs)
            except Exception as e:
                last_error = e
                # Check if it's a rate-limit/quota error (429)
                is_quota_error = False
                if hasattr(e, 'code') and e.code == 429:
                    is_quota_error = True
                elif "429" in str(e) or "quota" in str(e).lower() or "exhausted" in str(e).lower():
                    is_quota_error = True
                
                if is_quota_error:
                    # Cooldown for 2 minutes (sufficient to clear RPM limits, and flags daily limits too)
                    FallbackGeminiClient._failed_keys_until[key] = now + 120.0
                    key_hint = key[:8] if key else "Unknown"
                    logger.warning(
                        f"Gemini API key ending in/matching '{key_hint}' failed with 429. "
                        f"Cooldowned for 2 minutes. Trying next key. Error: {e}"
                    )
                    continue
                # For non-429 errors (like invalid model name, bad payload), raise immediately
                raise e
                
        # If we exhausted all available keys and all failed, raise the last encountered error
        raise last_error

def get_gemini_client(api_key=None):
    return FallbackGeminiClient(api_key=api_key)

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = FallbackGeminiClient()
    return _client

def generate_text(prompt: str):
    client = _get_client()
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )
    return response.text