import asyncio
import json
from typing import Optional, Dict, List
from database import Database


class FileManager:
    def __init__(self, db: Database):
        self.db = db

    async def list_files(self, device_id: str, path: str = "C:\\") -> List[Dict]:
        device = await self.db.get_device(device_id)
        if not device or device["status"] != "online":
            return []

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{device['tailscale_ip']}:9090/command",
                    json={"type": "list_files", "path": path},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("files", [])
        except Exception:
            pass
        return []

    async def upload_file(
        self,
        device_id: str,
        remote_path: str,
        file_data: bytes
    ) -> bool:
        device = await self.db.get_device(device_id)
        if not device or device["status"] != "online":
            return False

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{device['tailscale_ip']}:9090/command",
                    json={
                        "type": "upload_file",
                        "remote_path": remote_path,
                        "data": file_data.hex()
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def download_file(
        self,
        device_id: str,
        remote_path: str
    ) -> Optional[bytes]:
        device = await self.db.get_device(device_id)
        if not device or device["status"] != "online":
            return None

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{device['tailscale_ip']}:9090/command",
                    json={
                        "type": "download_file",
                        "remote_path": remote_path
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "data" in data:
                            return bytes.fromhex(data["data"])
        except Exception:
            pass
        return None

    async def delete_file(self, device_id: str, remote_path: str) -> bool:
        device = await self.db.get_device(device_id)
        if not device or device["status"] != "online":
            return False

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{device['tailscale_ip']}:9090/command",
                    json={
                        "type": "delete_file",
                        "remote_path": remote_path
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False
