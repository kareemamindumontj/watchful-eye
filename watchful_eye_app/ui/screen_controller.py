import customtkinter as ctk
import asyncio
import threading
from utils.pi_client import pi_client


class ScreenController(ctk.CTkToplevel):
    def __init__(self, parent, device_id, device_name):
        super().__init__(parent)
        self.device_id = device_id
        self.device_name = device_name
        self.running = False
        self.scale_x = 1.0
        self.scale_y = 1.0

        self.title(f"Remote Control - {device_name}")
        self.geometry("1000x700")

        self._create_ui()
        self._start_stream()

    def _create_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        toolbar = ctk.CTkFrame(self, height=50)
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkButton(toolbar, text="Ctrl+Alt+Del", width=100,
                      command=lambda: self._send_combo(["ctrl", "alt", "delete"])).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Alt+Tab", width=80,
                      command=lambda: self._send_combo(["alt", "tab"])).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Alt+F4", width=80,
                      command=lambda: self._send_combo(["alt", "f4"])).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Win", width=60,
                      command=lambda: self._send_combo(["win"])).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Type Text", width=100,
                      command=self._show_type_dialog).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Refresh", width=80,
                      command=self._refresh_screen).pack(side="left", padx=5)

        self.canvas = ctk.CTkCanvas(self, bg="black", cursor="crosshair")
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        self.canvas.bind("<Button-1>", self._on_left_click)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<MouseWheel>", self._on_scroll)
        self.canvas.bind("<Motion>", self._on_move)

        self.status_label = ctk.CTkLabel(self, text="Connecting...", text_color="gray")
        self.status_label.grid(row=2, column=0, pady=5)

        self.image_id = None

    def _start_stream(self):
        self.running = True
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()

    def _stream_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while self.running:
            try:
                img_data = loop.run_until_complete(
                    pi_client.get_screen_image(self.device_id)
                )
                if img_data:
                    self._update_screen(img_data)
            except Exception as e:
                print(f"Stream error: {e}")
            loop.run_until_complete(asyncio.sleep(0.3))

    def _update_screen(self, img_data):
        try:
            from PIL import Image, ImageTk
            import io

            img = Image.open(io.BytesIO(img_data))
            self.original_size = img.size

            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()
            if canvas_w > 1 and canvas_h > 0:
                img = img.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)
                self.scale_x = self.original_size[0] / canvas_w
                self.scale_y = self.original_size[1] / canvas_h

            photo = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.image_id = self.canvas.create_image(0, 0, anchor="nw", image=photo)
            self.canvas._photo = photo

            self.status_label.configure(text="Connected", text_color="green")
        except Exception as e:
            print(f"Display error: {e}")

    def _get_canvas_coords(self, event):
        return int(event.x * self.scale_x), int(event.y * self.scale_y)

    def _on_left_click(self, event):
        x, y = self._get_canvas_coords(event)
        self._send_command("mouse_click", {"x": x, "y": y, "button": "left"})

    def _on_right_click(self, event):
        x, y = self._get_canvas_coords(event)
        self._send_command("mouse_click", {"x": x, "y": y, "button": "right"})

    def _on_double_click(self, event):
        x, y = self._get_canvas_coords(event)
        self._send_command("mouse_click", {"x": x, "y": y, "button": "double"})

    def _on_drag(self, event):
        x, y = self._get_canvas_coords(event)
        self._send_command("mouse_move", {"x": x, "y": y})

    def _on_move(self, event):
        pass

    def _on_scroll(self, event):
        clicks = 1 if event.delta > 0 else -1
        self._send_command("mouse_scroll", {"clicks": clicks})

    def _send_command(self, command_type, params):
        threading.Thread(
            target=self._async_send,
            args=(command_type, params),
            daemon=True
        ).start()

    def _async_send(self, command_type, params):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            session = loop.run_until_complete(pi_client._get_session())
            data = {"type": command_type, **params}
            loop.run_until_complete(
                session.post(
                    f"{pi_client.base_url}/api/devices/{self.device_id}/command",
                    json={"device_id": self.device_id, "command": json.dumps(data)}
                )
            )
        except Exception as e:
            print(f"Command error: {e}")

    def _send_combo(self, keys):
        self._send_command("key_combo", {"keys": keys})

    def _show_type_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Type Text")
        dialog.geometry("400x150")

        ctk.CTkLabel(dialog, text="Enter text to type:").pack(pady=10)
        entry = ctk.CTkEntry(dialog, width=350)
        entry.pack(pady=5)
        entry.focus()

        def send():
            text = entry.get()
            if text:
                self._send_command("key_type", {"text": text})
            dialog.destroy()

        entry.bind("<Return>", lambda e: send())
        ctk.CTkButton(dialog, text="Send", command=send).pack(pady=10)

    def _refresh_screen(self):
        self._send_command("screen_capture", {})

    def _async_send(self, command_type, params):
        import json
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            data = {"type": command_type, **params}
            loop.run_until_complete(
                pi_client.run_command(self.device_id, json.dumps(data))
            )
        except Exception as e:
            print(f"Command error: {e}")

    def on_close(self):
        self.running = False
        self.destroy()
