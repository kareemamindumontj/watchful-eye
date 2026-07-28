import asyncio
import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from database import Database


class StreamManager:
    def __init__(self):
        self.active_streams: Dict[str, bool] = {}
        self.recordings_dir = Path(__file__).parent / "data" / "recordings"
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

    async def start_stream(self, device_id: str, db: Database):
        self.active_streams[device_id] = True
        while self.active_streams.get(device_id, False):
            try:
                device = await db.get_device(device_id)
                if not device or device["status"] != "online":
                    break

                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"http://{device['tailscale_ip']}:9090/screen",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if "image" in data:
                                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                                filename = f"{device_id}_{timestamp}.jpg"
                                filepath = self.recordings_dir / filename
                                image_data = base64.b64decode(data["image"])
                                filepath.write_bytes(image_data)
            except Exception as e:
                print(f"Stream error for {device_id}: {e}")

            await asyncio.sleep(1)

    def stop_stream(self, device_id: str):
        self.active_streams[device_id] = False

    async def capture_screen(self, device_id: str, db: Database) -> Optional[str]:
        device = await db.get_device(device_id)
        if not device or device["status"] != "online":
            return None

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://{device['tailscale_ip']}:9090/screen",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("image")
        except Exception:
            pass
        return None
