import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import customtkinter as ctk
from ui.dashboard import DashboardApp
from utils.config import load_config, save_config


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    config = load_config()

    if not config.get("pi_server"):
        app = ctk.CTk()
        app.withdraw()
        show_setup_wizard(app, config)
        app.destroy()

    app = DashboardApp()
    app.mainloop()


def show_setup_wizard(root, config):
    dialog = ctk.CTkToplevel(root)
    dialog.title("Watchful Eye - Initial Setup")
    dialog.geometry("500x400")
    dialog.transient(root)
    dialog.grab_set()

    ctk.CTkLabel(dialog, text="Watchful Eye Setup", font=("Arial", 24, "bold")).pack(pady=20)

    ctk.CTkLabel(dialog, text="Enter Raspberry Pi Tailscale IP:").pack(pady=(20, 5))
    pi_entry = ctk.CTkEntry(dialog, width=300, placeholder_text="100.x.x.x")
    pi_entry.pack(pady=5)

    ctk.CTkLabel(dialog, text="Enter Gemini API Key:").pack(pady=(20, 5))
    api_entry = ctk.CTkEntry(dialog, width=300, placeholder_text="AIza...", show="*")
    api_entry.pack(pady=5)

    ctk.CTkLabel(dialog, text="Enter Your Wallet Address (for mining):").pack(pady=(20, 5))
    wallet_entry = ctk.CTkEntry(dialog, width=300, placeholder_text="Your BTC/ETC wallet")
    wallet_entry.pack(pady=5)

    def save_setup():
        config["pi_server"] = pi_entry.get()
        config["gemini_api_key"] = api_entry.get()
        config["wallet_address"] = wallet_entry.get()
        save_config(config)
        dialog.destroy()

    ctk.CTkButton(dialog, text="Save & Continue", command=save_setup).pack(pady=30)

    root.mainloop()


if __name__ == "__main__":
    main()
