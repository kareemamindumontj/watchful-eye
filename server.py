import io
import json
import time
import socket
import ssl
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
HTTPServer = ThreadingHTTPServer
from PIL import ImageGrab, Image

from config import load_config, ensure_dirs, DATA_DIR
from screen_capture import capture_screen_jpeg, get_recent_screenshots, save_screenshot
from webcam_capture import capture_photo
from session import Session, get_all_sessions, last_summary_text
from summarizer import call_ai_api, build_summary_prompt

FRONTEND_DIR = Path(__file__).parent / "frontend"
MIME_TYPES = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".ico": "image/x-icon",
    ".svg": "image/svg+xml",
}

class WatchfulHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path):
        ext = path.suffix.lower()
        mime = MIME_TYPES.get(ext, "application/octet-stream")
        try:
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self._send_error(404)

    def _send_error(self, code=500, msg="Error"):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(msg.encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")

        if path == "/ca.pem":
            ca_path = FRONTEND_DIR / "ca.pem"
            if ca_path.exists():
                self._send_file(ca_path)
            else:
                self._send_error(404)
            return

        if path == "/api/screen":
            jpeg = capture_screen_jpeg(quality=60)
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(jpeg)))
            self.end_headers()
            self.wfile.write(jpeg)
            return

        if path == "/api/webcam":
            img_path = capture_photo()
            if img_path and img_path.exists():
                data = img_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self._send_error(500, "No webcam")
            return

        if path == "/api/sessions":
            sessions = get_all_sessions()
            summary = last_summary_text()
            self._send_json({"sessions": sessions, "latest_summary": summary})
            return

        if path.startswith("/api/session/") and "/summary" in path:
            sid = path.split("/")[3]
            data_dir = ensure_dirs() / "sessions"
            session_file = data_dir / f"{sid}.json"
            if session_file.exists():
                with open(session_file) as f:
                    data = json.load(f)
                prompt = build_summary_prompt(data, language="english")
                s = call_ai_api(prompt, language="english")
                self._send_json({"summary": s or "No summary available."})
            else:
                self._send_error(404, "Session not found")
            return

        if path == "/api/screenshots":
            shots = get_recent_screenshots(20)
            items = []
            for ts, p in shots:
                items.append({"time": ts, "path": p.name})
            self._send_json({"screenshots": items})
            return

        if path == "/api/status":
            cfg = load_config()
            self._send_json({
                "running": True,
                "interval": cfg.get("screenshot_interval", 5),
                "session_active": True,
            })
            return

        if path == "/api/screenshot":
            idx = self.path.split("?idx=")
            idx = int(idx[1]) if len(idx) > 1 else -1
            shots = get_recent_screenshots(50)
            if idx >= 0 and idx < len(shots):
                data = shots[len(shots) - 1 - idx][1].read_bytes()
            elif shots:
                data = shots[-1][1].read_bytes()
            else:
                self._send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if path == "/" or path == "":
            path = FRONTEND_DIR / "index.html"
        else:
            path = FRONTEND_DIR / path.lstrip("/")

        path = path.resolve()
        if not str(path).startswith(str(FRONTEND_DIR.resolve())):
            self._send_error(403)
            return
        if path.is_file():
            self._send_file(path)
        else:
            self._send_error(404)

    def log_message(self, format, *args):
        pass

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def start_server(port=8080):
    ip = get_local_ip()
    cert_path = DATA_DIR / "server.crt"
    key_path = DATA_DIR / "server.key"

    server = HTTPServer(("0.0.0.0", port), WatchfulHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.set_ciphers("HIGH:!aNULL:!eNULL:!MD5")
    server.socket = context.wrap_socket(server.socket, server_side=True)

    print(f"Watchful Eye server running at https://{ip}:{port}")
    print(f"Open Safari on iPhone and go to: https://{ip}:{port}")
    print("")
    print("=== FIRST-TIME SETUP ON iPHONE ===")
    print("1. Open Safari and download: https://{0}:{1}/ca.pem".format(ip, port))
    print("2. Go to Settings > General > VPN & Device Management")
    print("3. Tap the 'mkcert' profile and Install")
    print("4. Go to Settings > General > About > Certificate Trust Settings")
    print("5. Enable 'mkcert' (toggle ON)")
    print("6. Then open: https://{0}:{1}/".format(ip, port))
    print("===================================")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, ip, port
