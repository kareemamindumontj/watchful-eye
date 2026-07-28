import sys
import os
import json
import time
import socket
import platform
import subprocess
import win32serviceutil
import win32service
import win32event
import servicemanager
from pathlib import Path


class WatchfulEyeService(win32serviceutil.ServiceFramework):
    _svc_name_ = "WatchfulEyeAgent"
    _svc_display_name_ = "Watchful Eye Agent"
    _svc_description_ = "Watchful Eye Remote Management Agent - Runs as SYSTEM with full admin privileges"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.running = False
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, "")
        )
        self.main()

    def main(self):
        try:
            import agent_server
            agent_server.start_agent(port=9090)
        except Exception as e:
            servicemanager.LogErrorMsg(f"Watchful Eye Agent error: {str(e)}")


def get_device_id():
    device_id_file = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "WatchfulEye" / "device_id"
    if device_id_file.exists():
        return device_id_file.read_text().strip()
    import uuid
    device_id = uuid.uuid4().hex[:12]
    device_id_file.parent.mkdir(parents=True, exist_ok=True)
    device_id_file.write_text(device_id)
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


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        print("Installing Watchful Eye Agent as SYSTEM service...")
        win32serviceutil.HandleCommandLine(WatchfulEyeService)
    elif len(sys.argv) > 1 and sys.argv[1] == "remove":
        print("Removing Watchful Eye Agent service...")
        win32serviceutil.HandleCommandLine(WatchfulEyeService)
    else:
        win32serviceutil.HandleCommandLine(WatchfulEyeService)
