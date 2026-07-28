import io
import time
import threading
from PIL import ImageGrab, Image
from pathlib import Path
from config import ensure_dirs

_screen_dir = None
_screenshots = []
_recording = False
_capture_thread = None
_lock = threading.Lock()

def get_screenshot_dir():
    global _screen_dir
    if _screen_dir is None:
        d = ensure_dirs() / "screenshots"
        d.mkdir(parents=True, exist_ok=True)
        _screen_dir = d
    return _screen_dir

def capture_screen():
    img = ImageGrab.grab()
    return img

def capture_screen_jpeg(quality=70):
    img = capture_screen()
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()

def save_screenshot():
    img = capture_screen()
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = get_screenshot_dir() / f"screen_{ts}.jpg"
    img.save(path, quality=70)
    with _lock:
        _screenshots.append((time.time(), path))
    return path

def get_recent_screenshots(limit=10):
    with _lock:
        return list(_screenshots[-limit:])

def start_recording(interval=5):
    global _recording, _capture_thread
    if _recording:
        return
    _recording = True
    def _loop():
        while _recording:
            try:
                save_screenshot()
            except Exception:
                pass
            time.sleep(interval)
    _capture_thread = threading.Thread(target=_loop, daemon=True)
    _capture_thread.start()

def stop_recording():
    global _recording
    _recording = False
