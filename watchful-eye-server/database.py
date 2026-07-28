import aiosqlite
import json
from datetime import datetime
from typing import Optional, List, Dict


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db: Optional[aiosqlite.Connection] = None

    async def init(self):
        self.db = await aiosqlite.connect(self.db_path)
        await self.db.execute("PRAGMA journal_mode=WAL")
        await self._create_tables()

    async def _create_tables(self):
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                hostname TEXT NOT NULL,
                ip TEXT,
                tailscale_ip TEXT,
                os TEXT,
                status TEXT DEFAULT 'offline',
                last_seen TIMESTAMP,
                has_gpu INTEGER DEFAULT 0,
                gpu_name TEXT,
                admin INTEGER DEFAULT 0,
                mining_enabled INTEGER DEFAULT 0,
                mining_intensity INTEGER DEFAULT 50,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS recordings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                duration_seconds INTEGER,
                file_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(id)
            )
        """)

        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS command_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                command TEXT NOT NULL,
                result TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(id)
            )
        """)

        await self.db.commit()

    async def get_all_devices(self) -> List[Dict]:
        cursor = await self.db.execute(
            "SELECT * FROM devices ORDER BY hostname"
        )
        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    async def get_device(self, device_id: str) -> Optional[Dict]:
        cursor = await self.db.execute(
            "SELECT * FROM devices WHERE id = ?", (device_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))

    async def update_device_status(
        self,
        device_id: str,
        hostname: str,
        ip: str,
        tailscale_ip: str,
        os: str,
        has_gpu: bool,
        gpu_name: str,
        admin: bool = False
    ):
        now = datetime.utcnow().isoformat()
        await self.db.execute("""
            INSERT INTO devices (id, hostname, ip, tailscale_ip, os, status, last_seen, has_gpu, gpu_name, admin)
            VALUES (?, ?, ?, ?, ?, 'online', ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                hostname = excluded.hostname,
                ip = excluded.ip,
                tailscale_ip = excluded.tailscale_ip,
                os = excluded.os,
                status = 'online',
                last_seen = excluded.last_seen,
                has_gpu = excluded.has_gpu,
                gpu_name = excluded.gpu_name,
                admin = excluded.admin
        """, (device_id, hostname, ip, tailscale_ip, os, now, int(has_gpu), gpu_name, int(admin)))
        await self.db.commit()

    async def set_device_offline(self, device_id: str):
        await self.db.execute(
            "UPDATE devices SET status = 'offline' WHERE id = ?",
            (device_id,)
        )
        await self.db.commit()

    async def update_mining_status(self, device_id: str, enabled: bool, intensity: int):
        await self.db.execute(
            "UPDATE devices SET mining_enabled = ?, mining_intensity = ? WHERE id = ?",
            (int(enabled), intensity, device_id)
        )
        await self.db.commit()

    async def add_recording(
        self,
        device_id: str,
        filename: str,
        filepath: str,
        duration_seconds: int,
        file_size: int
    ):
        await self.db.execute("""
            INSERT INTO recordings (device_id, filename, filepath, duration_seconds, file_size)
            VALUES (?, ?, ?, ?, ?)
        """, (device_id, filename, filepath, duration_seconds, file_size))
        await self.db.commit()

    async def get_recordings(self, device_id: Optional[str] = None) -> List[Dict]:
        if device_id:
            cursor = await self.db.execute(
                "SELECT * FROM recordings WHERE device_id = ? ORDER BY created_at DESC",
                (device_id,)
            )
        else:
            cursor = await self.db.execute(
                "SELECT * FROM recordings ORDER BY created_at DESC"
            )
        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    async def log_command(self, device_id: str, command: str, result: str, status: str):
        await self.db.execute("""
            INSERT INTO command_log (device_id, command, result, status)
            VALUES (?, ?, ?, ?)
        """, (device_id, command, result, status))
        await self.db.commit()

    async def close(self):
        if self.db:
            await self.db.close()
