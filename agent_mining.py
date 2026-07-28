import json
import os
import time
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

MINING_CONFIG_FILE = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "WatchfulEye" / "mining_config.json"
MINING_LOG_FILE = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "WatchfulEye" / "mining_log.json"

mining_process = None
mining_active = False

DEFAULT_CONFIG = {
    "enabled": False,
    "intensity": 50,
    "max_temp": 75,
    "schedule_enabled": False,
    "schedule_start": "22:00",
    "schedule_end": "06:00",
    "idle_only": True,
    "min_profit_usd": 0.01
}


def load_config():
    if MINING_CONFIG_FILE.exists():
        try:
            return {**DEFAULT_CONFIG, **json.loads(MINING_CONFIG_FILE.read_text())}
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config):
    MINING_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    MINING_CONFIG_FILE.write_text(json.dumps(config, indent=2))


def log_mining(event, data=None):
    MINING_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logs = []
    if MINING_LOG_FILE.exists():
        try:
            logs = json.loads(MINING_LOG_FILE.read_text())
        except Exception:
            logs = []

    logs.append({
        "timestamp": datetime.utcnow().isoformat(),
        "event": event,
        "data": data
    })

    logs = logs[-1000:]
    MINING_LOG_FILE.write_text(json.dumps(logs, indent=2))


def get_cpu_temp():
    if not HAS_PSUTIL:
        return 0
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                for entry in entries:
                    if entry.current > 0:
                        return entry.current
    except Exception:
        pass
    return 0


def get_cpu_usage():
    if not HAS_PSUTIL:
        return 0
    try:
        return psutil.cpu_percent(interval=1)
    except Exception:
        return 0


def is_system_idle(threshold=10):
    if not HAS_PSUTIL:
        return True
    try:
        cpu_usage = psutil.cpu_percent(interval=0.1)
        return cpu_usage < threshold
    except Exception:
        return True


def is_in_schedule(config):
    if not config.get("schedule_enabled"):
        return True

    now = datetime.now()
    current_time = now.strftime("%H:%M")

    start = config.get("schedule_start", "22:00")
    end = config.get("schedule_end", "06:00")

    if start <= end:
        return start <= current_time <= end
    else:
        return current_time >= start or current_time <= end


def start_nicehash_mining(intensity=50):
    global mining_process, mining_active

    try:
        nicehash_path = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "NiceHash" / "NiceHash QuickMiner" / "excavator.exe"
        if not nicehash_path.exists():
            nicehash_path = Path("C:\\Program Files\\NiceHash\\NiceHash QuickMiner\\excavator.exe")

        if not nicehash_path.exists():
            return {"success": False, "message": "NiceHash not installed"}

        cmd = [
            str(nicehash_path),
            "-login", "YOUR_WALLET_ADDRESS",
            "-worker", f"watchful-{socket.gethostname()}",
            "-intensity", str(intensity)
        ]

        mining_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        mining_active = True
        log_mining("started", {"intensity": intensity})
        return {"success": True, "message": "Mining started"}

    except Exception as e:
        return {"success": False, "message": str(e)}


def stop_nicehash_mining():
    global mining_process, mining_active

    if mining_process:
        try:
            mining_process.terminate()
            mining_process.wait(timeout=10)
        except Exception:
            try:
                mining_process.kill()
            except Exception:
                pass
        mining_process = None

    mining_active = False
    log_mining("stopped")
    return {"success": True, "message": "Mining stopped"}


def get_mining_stats():
    config = load_config()
    stats = {
        "enabled": config.get("enabled", False),
        "intensity": config.get("intensity", 50),
        "active": mining_active,
        "cpu_temp": get_cpu_temp(),
        "cpu_usage": get_cpu_usage(),
        "max_temp": config.get("max_temp", 75),
        "schedule_enabled": config.get("schedule_enabled", False)
    }

    if mining_active and HAS_PSUTIL:
        try:
            process = psutil.Process(mining_process.pid) if mining_process else None
            if process:
                stats["memory_mb"] = process.memory_info().rss / 1024 / 1024
                stats["cpu_percent"] = process.cpu_percent()
        except Exception:
            pass

    return stats


def mining_safety_loop():
    global mining_active

    while True:
        config = load_config()

        if not config.get("enabled"):
            if mining_active:
                stop_nicehash_mining()
            time.sleep(30)
            continue

        if config.get("idle_only") and not is_system_idle():
            if mining_active:
                stop_nicehash_mining()
                log_mining("paused_idle")
            time.sleep(30)
            continue

        if not is_in_schedule(config):
            if mining_active:
                stop_nicehash_mining()
                log_mining("paused_schedule")
            time.sleep(30)
            continue

        temp = get_cpu_temp()
        if temp > config.get("max_temp", 75):
            if mining_active:
                stop_nicehash_mining()
                log_mining("stopped_overheat", {"temp": temp})
            time.sleep(60)
            continue

        if not mining_active:
            result = start_nicehash_mining(config.get("intensity", 50))
            if not result.get("success"):
                log_mining("failed_start", result)

        time.sleep(30)


def configure_mining(enabled, intensity=50):
    config = load_config()
    config["enabled"] = enabled
    config["intensity"] = max(1, min(100, intensity))
    save_config(config)

    if enabled:
        return {"success": True, "message": f"Mining enabled at {intensity}% intensity"}
    else:
        stop_nicehash_mining()
        return {"success": True, "message": "Mining disabled"}


def init_mining():
    config = load_config()
    if config.get("enabled"):
        safety_thread = threading.Thread(target=mining_safety_loop, daemon=True)
        safety_thread.start()
