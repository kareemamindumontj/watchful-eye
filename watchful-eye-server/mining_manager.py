import asyncio
from typing import Optional, Dict
from database import Database


class MiningManager:
    def __init__(self, db: Database):
        self.db = db

    async def configure_mining(
        self,
        device_id: str,
        enabled: bool,
        intensity: int = 50
    ) -> Dict:
        device = await self.db.get_device(device_id)
        if not device or device["status"] != "online":
            return {"error": "Device offline"}

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{device['tailscale_ip']}:9090/command",
                    json={
                        "type": "mining_config",
                        "enabled": enabled,
                        "intensity": intensity
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    result = await resp.json()
                    await self.db.update_mining_status(device_id, enabled, intensity)
                    return result
        except Exception as e:
            return {"error": str(e)}

    async def get_mining_stats(self, device_id: str) -> Dict:
        device = await self.db.get_device(device_id)
        if not device or device["status"] != "online":
            return {"error": "Device offline"}

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{device['tailscale_ip']}:9090/command",
                    json={"type": "mining_stats"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    return await resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def configure_all(
        self,
        enabled: bool,
        intensity: int = 50
    ) -> Dict:
        devices = await self.db.get_all_devices()
        results = {}
        for device in devices:
            if device["status"] == "online":
                result = await self.configure_mining(
                    device["id"],
                    enabled,
                    intensity
                )
                results[device["hostname"]] = result
        return results
