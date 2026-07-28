import json
from datetime import datetime
from config import load_config
from pathlib import Path

def _encode_image(image_path):
    import base64
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def build_summary_prompt(session_data, webcam_image=None, language="english"):
    boot_time = session_data.get("boot_time", "unknown")
    shutdown_time = session_data.get("shutdown_time", "unknown")
    activities = session_data.get("activities", [])
    duration = session_data.get("duration_minutes", 0)

    activity_lines = []
    for a in activities:
        ts = a.get("timestamp", "")[11:19]
        activity_lines.append(f"  [{ts}] {a.get('process', '?')} - {a.get('title', '?')}")

    activity_text = "\n".join(activity_lines) if activity_lines else "  (no activity logged)"

    lines = [
        "Summarize this computer session in a few concise sentences.",
        f"Duration: {duration:.0f} minutes, {len(activities)} activities tracked.",
        "",
        "Activities:",
        activity_text,
        "",
        f"Write in {language}.",
    ]

    if webcam_image and webcam_image.exists():
        lines.insert(0, "A webcam photo was taken at the start of this session. Describe the person in the photo (appearance, expression, setting), then summarize their activity.")

    return "\n".join(lines)

def _call_ollama_native(prompt, image_path, model):
    import requests
    b64 = _encode_image(image_path) if image_path and Path(image_path).exists() else None
    body = {"model": model, "prompt": prompt, "stream": False}
    if b64:
        body["images"] = [b64]
    try:
        resp = requests.post("http://localhost:11434/api/generate", json=body, timeout=120)
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except Exception:
        pass
    return None

def _try_providers(prompt, image_path=None):
    cfg = load_config()
    providers = []

    api_key = cfg.get("api_key", "")
    api_url = cfg.get("api_url", "").strip()
    model = cfg.get("model", "")

    if api_key and api_url:
        providers.append(("configured", api_url, api_key, model))

    if image_path:
        result = _call_ollama_native(prompt, image_path, "moondream")
        if result:
            return result

    providers.append(("ollama-text", "http://localhost:11434/v1", "", "llama3.2"))
    providers.append(("ollama-small", "http://localhost:11434/v1", "", "qwen2.5:1.5b"))

    for name, url, key, mdl in providers:
        result = _call_api(prompt, image_path, url, key, mdl)
        if result:
            return result
    return "AI summary not available. Install Ollama (ollama.com) or configure an API key."

def _call_api(prompt, image_path, api_url, api_key, model):
    import requests
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    messages = [{"role": "user", "content": []}]
    if image_path and Path(image_path).exists():
        b64 = _encode_image(image_path)
        messages[0]["content"].append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })
    messages[0]["content"].append({"type": "text", "text": prompt})
    body = {"model": model, "messages": messages, "max_tokens": 1024, "stream": False}

    try:
        resp = requests.post(f"{api_url}/chat/completions", headers=headers, json=body, timeout=60)
        if resp.status_code == 404 or resp.status_code >= 500:
            return None
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except requests.ConnectionError:
        return None
    except Exception as e:
        return None

def call_ai_api(prompt, image_path=None, language="english"):
    return _try_providers(prompt, image_path)
