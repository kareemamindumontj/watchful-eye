import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "WatchfulEye"
CONFIG_FILE = CONFIG_DIR / "app_config.json"

DEFAULT_CONFIG = {
    "pi_server": "",
    "pi_port": 8000,
    "gemini_api_key": "",
    "wallet_address": "",
    "appearance": "dark",
    "mining_max_temp": 75,
    "mining_default_intensity": 50
}


def ensure_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config():
    ensure_dirs()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    ensure_dirs()
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def get_pi_url(config):
    server = config.get("pi_server", "")
    port = config.get("pi_port", 8000)
    return f"http://{server}:{port}"
