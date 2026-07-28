import time
import psutil
from datetime import datetime

try:
    import win32gui
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

_last_entry = None

def get_active_window_info():
    if not HAS_WIN32:
        return None
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return None
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            proc = psutil.Process(pid)
            process_name = proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            process_name = "unknown"
        return {"title": title, "process": process_name, "pid": pid}
    except Exception:
        return None

def poll_activity():
    global _last_entry
    info = get_active_window_info()
    if not info:
        return None
    current = (info["title"], info["process"])
    if current == _last_entry:
        return None
    _last_entry = current
    return {
        "timestamp": datetime.now().isoformat(),
        "title": info["title"],
        "process": info["process"],
    }

def get_uptime_seconds():
    return time.time() - psutil.boot_time()
