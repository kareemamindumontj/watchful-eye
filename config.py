import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local")) / "WatchfulEye"
CONFIG_FILE = CONFIG_DIR / "config.json"
DATA_DIR = CONFIG_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
WEBCAM_DIR = DATA_DIR / "webcam"

DEFAULT_CONFIG = {
    "api_key": "",
    "api_url": "",
    "model": "",
    "poll_interval_seconds": 10,
    "summary_interval_minutes": 60,
    "capture_webcam_on_boot": True,
    "startup_enabled": True,
    "log_keystrokes": False,
    "language": "english",
    "sms_enabled": False,
    "sms_phone": "",
    "sms_carrier": "",
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_pass": "",
    "sms_on_summary": True,
    "email_to": "",
}

def ensure_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    WEBCAM_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR

def load_config():
    ensure_dirs()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except (json.JSONDecodeError, OSError):
            return dict(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)

def save_config(cfg):
    ensure_dirs()
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
