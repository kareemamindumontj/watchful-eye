import asyncio
import socket
import struct
from datetime import datetime
from typing import Optional
from database import Database


class DeviceDiscovery:
    def __init__(self, db: Database):
        self.db = db
        self.scanning = False
        self.scan_interval = 60

    async def start_scanning(self):
        self.scanning = True
        while self.scanning:
            try:
                await self._scan_network()
                await self._check_device_health()
            except Exception as e:
                print(f"Scan error: {e}")
            await asyncio.sleep(self.scan_interval)

    async def _scan_network(self):
        try:
            import subprocess
            result = subprocess.run(
                ["tailscale", "status", "--json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                peers = data.get("Peer", {})
                for peer_id, peer in peers.items():
                    if peer.get("Online"):
                        tailscale_ip = peer.get("TailscaleIPs", [None])[0]
                        hostname = peer.get("HostName", "Unknown")
                        if tailscale_ip:
                            await self._probe_device(tailscale_ip, hostname)
        except FileNotFoundError:
            await self._scan_local_network()

    async def _scan_local_network(self):
        try:
            import netifaces
            gateways = netifaces.gateways()
            default_gw = gateways.get('default', {}).get(netifaces.AF_INET)
            if default_gw:
                interface = default_gw[1]
                addrs = netifaces.ifaddresses(interface)
                ipinfo = addrs.get(netifaces.AF_INET, [{}])[0]
                ip = ipinfo.get('addr', '192.168.1.1')
                base_ip = '.'.join(ip.split('.')[:3])

                for i in range(1, 255):
                    ip = f"{base_ip}.{i}"
                    asyncio.create_task(self._probe_device(ip))
        except Exception:
            pass

    async def _probe_device(self, ip: str, hostname: str = None):
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, 9090),
                timeout=2
            )
            writer.close()
            await writer.wait_closed()

            if not hostname:
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                except Exception:
                    hostname = f"Device-{ip.split('.')[-1]}"

            device_id = self._generate_device_id(ip)
            await self.db.update_device_status(
                device_id=device_id,
                hostname=hostname,
                ip=ip,
                tailscale_ip=ip,
                os="Windows",
                has_gpu=False,
                gpu_name="Unknown"
            )
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            pass

    async def _check_device_health(self):
        devices = await self.db.get_all_devices()
        now = datetime.utcnow()
        for device in devices:
            if device["status"] == "online" and device["last_seen"]:
                last_seen = datetime.fromisoformat(device["last_seen"])
                diff = (now - last_seen).total_seconds()
                if diff > 180:
                    await self.db.set_device_offline(device["id"])

    def _generate_device_id(self, ip: str) -> str:
        import hashlib
        return hashlib.md5(f"watchful-{ip}".encode()).hexdigest()[:12]
