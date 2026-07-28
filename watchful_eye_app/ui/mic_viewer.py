import customtkinter as ctk
import asyncio
import threading
import wave
import io
import pyaudio
from utils.pi_client import pi_client


class MicrophoneViewer(ctk.CTkToplevel):
    def __init__(self, parent, device_id, device_name):
        super().__init__(parent)
        self.device_id = device_id
        self.device_name = device_name
        self.running = False
        self.recording = False
        self.audio_stream = None
        self.pyaudio_instance = None

        self.title(f"Microphone - {device_name}")
        self.geometry("500x400")

        self._create_ui()

    def _create_ui(self):
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(self, text=f"Microphone: {self.device_name}",
                              font=("Arial", 18, "bold"))
        header.grid(row=0, column=0, pady=20)

        status_frame = ctk.CTkFrame(self)
        status_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.status_label = ctk.CTkLabel(status_frame, text="Status: Disconnected",
                                          text_color="gray")
        self.status_label.pack(pady=10)

        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.listen_btn = ctk.CTkButton(control_frame, text="Start Listening",
                                         command=self._toggle_listen,
                                         width=200, height=40)
        self.listen_btn.pack(pady=10)

        self.record_btn = ctk.CTkButton(control_frame, text="Record (10 sec)",
                                         command=self._start_recording,
                                         width=200, height=40,
                                         fg_color="#444444")
        self.record_btn.pack(pady=5)

        vol_frame = ctk.CTkFrame(self)
        vol_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(vol_frame, text="Volume:").pack(pady=(10, 0))
        self.volume_bar = ctk.CTkProgressBar(vol_frame, width=400, height=20)
        self.volume_bar.pack(pady=10)
        self.volume_bar.set(0)

        record_frame = ctk.CTkFrame(self)
        record_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(record_frame, text="Custom Recording Duration:").pack(pady=(10, 0))

        dur_frame = ctk.CTkFrame(record_frame, fg_color="transparent")
        dur_frame.pack(pady=5)

        self.duration_entry = ctk.CTkEntry(dur_frame, width=100, placeholder_text="Seconds")
        self.duration_entry.pack(side="left", padx=5)
        self.duration_entry.insert(0, "30")

        ctk.CTkButton(dur_frame, text="Record", width=80,
                      command=self._start_custom_recording).pack(side="left", padx=5)

        self.recordings_label = ctk.CTkLabel(self, text="Recordings saved on device",
                                              text_color="gray")
        self.recordings_label.grid(row=5, column=0, pady=10)

    def _toggle_listen(self):
        if self.running:
            self._stop_listen()
        else:
            self._start_listen()

    def _start_listen(self):
        self.running = True
        self.listen_btn.configure(text="Stop Listening", fg_color="#cc4444")
        self.status_label.configure(text="Status: Listening...", text_color="green")

        self.stream_thread = threading.Thread(target=self._stream_audio, daemon=True)
        self.stream_thread.start()

    def _stop_listen(self):
        self.running = False
        self.listen_btn.configure(text="Start Listening", fg_color=["#3B8ED0", "#1F6AA5"])
        self.status_label.configure(text="Status: Disconnected", text_color="gray")
        self.volume_bar.set(0)

        if self.audio_stream:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except Exception:
                pass
            self.audio_stream = None

        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except Exception:
                pass
            self.pyaudio_instance = None

    def _stream_audio(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            self.audio_stream = self.pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                output=True,
                frames_per_buffer=1024
            )

            while self.running:
                result = loop.run_until_complete(
                    pi_client.run_command(
                        self.device_id,
                        '{"type": "audio_read"}'
                    )
                )

                if isinstance(result, dict) and "audio" in result:
                    import base64
                    audio_data = base64.b64decode(result["audio"])
                    self.audio_stream.write(audio_data)

                    volume = sum(abs(b) for b in audio_data[:1024]) / 1024 / 128
                    self.after(0, lambda v=min(volume, 1.0): self.volume_bar.set(v))
                else:
                    self.after(0, lambda: self.volume_bar.set(0))

        except Exception as e:
            print(f"Audio stream error: {e}")
        finally:
            self.after(0, lambda: self.status_label.configure(
                text="Status: Disconnected", text_color="gray"))

    def _start_recording(self):
        self._record_audio(10)

    def _start_custom_recording(self):
        try:
            duration = int(self.duration_entry.get())
            self._record_audio(duration)
        except ValueError:
            pass

    def _record_audio(self, duration):
        self.recording = True
        self.record_btn.configure(text="Recording...", fg_color="#cc4444")
        self.status_label.configure(text=f"Status: Recording {duration}s...",
                                     text_color="orange")

        threading.Thread(
            target=self._do_recording,
            args=(duration,),
            daemon=True
        ).start()

    def _do_recording(self, duration):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                pi_client.run_command(
                    self.device_id,
                    f'{{"type": "audio_record", "duration": {duration}}}'
                )
            )

            self.after(0, lambda: self.status_label.configure(
                text="Status: Recording saved!", text_color="green"))
            self.after(2000, lambda: self.status_label.configure(
                text="Status: Listening...", text_color="green"))

        except Exception as e:
            self.after(0, lambda: self.status_label.configure(
                text=f"Status: Error - {str(e)}", text_color="red"))
        finally:
            self.after(0, lambda: self.record_btn.configure(
                text="Record (10 sec)", fg_color="#444444"))
            self.recording = False

    def on_close(self):
        self._stop_listen()
        self.destroy()
