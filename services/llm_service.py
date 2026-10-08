"""Centralized NVIDIA OpenAI-compatible LLM service with deterministic fallback."""
import json, re
from config.settings import NVIDIA_API_KEY, NVIDIA_MODEL, NVIDIA_BASE_URL

_client = None

def _get_client():
    global _client
    if _client is None and NVIDIA_API_KEY:
        try:
            from openai import OpenAI
            _client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)
        except Exception:
            _client = None
    return _client

def call_llm(system_prompt, user_prompt, max_tokens=800):
    client = _get_client()
    if client:
        try:
            resp = client.chat.completions.create(
                model=NVIDIA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.2,
            )
            return {"text": resp.choices[0].message.content, "mode": "nvidia", "error": None}
        except Exception as e:
            return {"text": None, "mode": "demo", "error": str(e)}
    return {"text": None, "mode": "demo", "error": "No API key - Demo Mode active"}

def parse_json_response(text):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return None

def is_demo_mode():
    return not bool(NVIDIA_API_KEY)
