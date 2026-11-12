"""
LLM Client Wrapper.

Handles communication with Google Gemini API.
Features:
- Strict JSON parsing
- Retries
- Threading timeout to prevent hanging the QIS pipeline
"""
import os
import json
import re
import threading
from typing import Optional, Any

# Timeout configuration
LLM_TIMEOUT_SECONDS = int(os.environ.get("LLM_TIMEOUT_SECONDS", "3"))


def get_gemini_client():
    try:
        import google.generativeai as genai
        from config import Config
        api_key = Config.GEMINI_API_KEY or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("[llm_client] Gemini API key is missing.")
            return None
        genai.configure(api_key=api_key)
        print("[llm_client] Gemini API key configured successfully.")
        return genai
    except ImportError:
        return None


def generate_json(prompt: str, model_name: str = "gemini-1.5-flash", temperature: float = 0.2) -> Optional[dict]:
    """
    Wrapper for LLM calls expecting JSON output.
    Implements retries, robust JSON parsing, and strict timeouts.
    """
    genai = get_gemini_client()
    if not genai:
        raise Exception("Google Generative AI SDK not configured or API key missing.")
        
    def _do_generation(model, p_prompt, result_container):
        try:
            response = model.generate_content(p_prompt)
            result_container["text"] = response.text.strip()
            result_container["success"] = True
        except Exception as e:
            result_container["error"] = e
            result_container["success"] = False

    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config={
            "temperature": temperature,
            "response_mime_type": "application/json",
        }
    )
    
    last_error = None
    for attempt in range(2):
        result_container = {"success": False, "text": None, "error": None}
        
        # Run generation in a thread to enforce timeout
        t = threading.Thread(target=_do_generation, args=(model, prompt, result_container))
        t.start()
        t.join(timeout=LLM_TIMEOUT_SECONDS)
        
        if t.is_alive():
            print(f"[llm_client] Timeout after {LLM_TIMEOUT_SECONDS}s on attempt {attempt+1}")
            continue
            
        if not result_container["success"]:
            last_error = result_container.get('error')
            print(f"[llm_client] LLM Generation Error on attempt {attempt+1}: {last_error}")
            # Remove response_mime_type requirement for retry just in case it caused issues
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config={"temperature": temperature}
            )
            continue
            
        text = result_container["text"]
        
        try:
            # Robust JSON extraction
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                text = match.group(0)
                
            data = json.loads(text)
            
            # Simple validation: ensure it's a dict
            if isinstance(data, dict):
                print(f"[llm_client] Generation successful.")
                return data
            else:
                print(f"[llm_client] Generation failed: Expected dict, got {type(data)}.")
                
        except json.JSONDecodeError as e:
            last_error = f"JSON Parse Error: {e}. Text: {text}"
            print(f"[llm_client] {last_error}")
            
    raise Exception(last_error or "LLM Generation failed for unknown reasons.")
