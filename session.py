import json
import time
from datetime import datetime
from pathlib import Path
from config import SESSIONS_DIR, load_config

class Session:
    def __init__(self):
        self.boot_time = datetime.now()
        self.boot_timestamp = time.time()
        self.shutdown_time = None
        self.activities = []
        self.webcam_image = None
        self.summary = None
        self.session_id = self.boot_time.strftime("%Y%m%d_%H%M%S")
        self.path = SESSIONS_DIR / f"session_{self.session_id}.json"

    def add_activity(self, entry):
        self.activities.append(entry)

    def set_webcam_image(self, path):
        self.webcam_image = path

    def save(self):
        data = {
            "session_id": self.session_id,
            "boot_time": self.boot_time.isoformat(),
            "shutdown_time": self.shutdown_time.isoformat() if self.shutdown_time else None,
            "duration_minutes": self._duration(),
            "activity_count": len(self.activities),
            "activities": self.activities,
            "webcam_image": str(self.webcam_image) if self.webcam_image else None,
            "summary": self.summary,
        }
        self.path.write_text(json.dumps(data, indent=2))

    def _duration(self):
        end = self.shutdown_time or datetime.now()
        return (end - self.boot_time).total_seconds() / 60

    def end(self):
        self.shutdown_time = datetime.now()

    @property
    def duration_minutes(self):
        return self._duration()

def last_session_path():
    sessions = sorted(SESSIONS_DIR.glob("session_*.json"))
    return sessions[-1] if sessions else None

def last_summary_text():
    path = last_session_path()
    if not path:
        return None
    try:
        data = json.loads(path.read_text())
        return data.get("summary")
    except (json.JSONDecodeError, OSError):
        return None

def get_all_sessions():
    sessions = sorted(SESSIONS_DIR.glob("session_*.json"))
    result = []
    for p in sessions:
        try:
            data = json.loads(p.read_text())
            result.append({
                "id": data.get("session_id", p.stem.replace("session_", "")),
                "boot_time": data.get("boot_time", ""),
                "duration": data.get("duration_minutes", 0),
                "activity_count": data.get("activity_count", 0),
                "summary": data.get("summary", ""),
                "webcam": data.get("webcam_image"),
            })
        except (json.JSONDecodeError, OSError):
            pass
    return result
