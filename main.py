import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import time
import threading
from config import load_config, ensure_dirs
from activity_tracker import poll_activity
from session import Session
from webcam_capture import capture_photo
from summarizer import build_summary_prompt, call_ai_api
from notify import send_notification
from screen_capture import start_recording, stop_recording
from server import start_server
from github_sync import start_sync

try:
    import pystray
    from PIL import Image
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

_session = None
_running = True
_last_summary_time = 0

def on_summary(summary_text):
    global _session
    if _session:
        _session.summary = summary_text
        _session.save()
    cfg = load_config()
    if cfg.get("sms_enabled") and cfg.get("sms_on_summary"):
        send_notification(summary_text)

def get_webcam_image():
    img = capture_photo()
    if img and img.exists():
        return img
    return None

def summarizer_loop(language="english"):
    global _last_summary_time
    cfg = load_config()
    interval = cfg.get("summary_interval_minutes", 60) * 60
    while _running:
        elapsed = time.time() - _last_summary_time
        if _last_summary_time > 0 and elapsed < interval:
            time.sleep(30)
            continue
        _last_summary_time = time.time()
        try:
            data = {
                "boot_time": _session.boot_time.isoformat(),
                "shutdown_time": None,
                "duration_minutes": _session.duration_minutes,
                "activities": _session.activities[-100:],
            }
            prompt = build_summary_prompt(data, _session.webcam_image, language)
            summary = call_ai_api(prompt, _session.webcam_image, language)
            on_summary(summary)
        except Exception:
            pass
        time.sleep(30)

def activity_loop(poll_interval):
    while _running:
        entry = poll_activity()
        if entry and _session:
            _session.add_activity(entry)
        time.sleep(poll_interval)

def send_person_description(image_path, language="english"):
    send_notification("Photo taken at boot.", "Watchful Eye — Boot Photo", attachment_path=image_path)

def run():
    global _session, _running
    ensure_dirs()
    cfg = load_config()

    _session = Session()
    language = cfg.get("language", "english")
    webcam_image = None

    if cfg.get("capture_webcam_on_boot", True):
        img = get_webcam_image()
        if img:
            webcam_image = img
            _session.set_webcam_image(img)

    if webcam_image:
        send_person_description(webcam_image, language)

    start_recording(interval=cfg.get("screenshot_interval", 5))

    poll_interval = cfg.get("poll_interval_seconds", 10)
    act_thread = threading.Thread(target=activity_loop, args=(poll_interval,), daemon=True)
    act_thread.start()

    summ_thread = threading.Thread(target=summarizer_loop, args=(language,), daemon=True)
    summ_thread.start()
    _last_summary_time = time.time()

    server, ip, port = start_server(port=cfg.get("server_port", 8080))
    start_sync()
    print(f"Open Safari on iPhone: http://{ip}:{port}")
    print(f"Or visit GitHub Pages: https://kareemamindumontj.github.io/watchful-eye/ (password: watchful)")

    try:
        while _running:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        shutdown()

def shutdown():
    global _running, _session
    _running = False
    stop_recording()
    if _session:
        _session.end()
        if not _session.summary:
            data = {
                "boot_time": _session.boot_time.isoformat(),
                "shutdown_time": _session.shutdown_time.isoformat(),
                "duration_minutes": _session.duration_minutes,
                "activities": _session.activities,
            }
            cfg = load_config()
            language = cfg.get("language", "english")
            summary = call_ai_api(
                build_summary_prompt(data, _session.webcam_image, language),
                _session.webcam_image, language
            )
            on_summary(summary)
        else:
            _session.save()

def tray_icon():
    if not HAS_TRAY:
        return
    img = Image.new("RGB", (64, 64), (0, 120, 255))
    icon = pystray.Icon(
        "watchful-eye",
        img,
        "Watchful Eye",
        menu=pystray.Menu(
            pystray.MenuItem("View Last Summary", lambda: _show_summary()),
            pystray.MenuItem("Quit", lambda: (_shutdown_tray(), shutdown())),
        ),
    )
    icon.run()

def _show_summary():
    from session import last_summary_text
    text = last_summary_text()
    if text:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, text, "Watchful Eye Summary", 0)
        except Exception:
            print(text)
        return text
    return "No summary available yet."

def _shutdown_tray():
    global _running
    _running = False

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--install":
        from install import install_startup
        install_startup()
        print("Watchful Eye installed to startup.")
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        from install import uninstall_startup
        uninstall_startup()
        print("Watchful Eye removed from startup.")
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--configure":
        import configure
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--summary":
        print(_show_summary())
        return
    if HAS_TRAY:
        t = threading.Thread(target=tray_icon, daemon=True)
        t.start()
    run()

if __name__ == "__main__":
    main()
