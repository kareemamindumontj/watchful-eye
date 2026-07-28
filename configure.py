import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import tkinter as tk
from tkinter import ttk, messagebox
from config import load_config, save_config
from notify import CARRIER_GATEWAYS

cfg = load_config()

def save_and_close():
    cfg["api_key"] = api_key_var.get()
    cfg["api_url"] = api_url_var.get()
    cfg["model"] = model_var.get()
    cfg["language"] = lang_var.get()
    cfg["poll_interval_seconds"] = int(poll_var.get())
    cfg["summary_interval_minutes"] = int(summary_var.get())
    cfg["sms_enabled"] = sms_enabled_var.get()
    cfg["sms_phone"] = sms_phone_var.get()
    cfg["sms_carrier"] = sms_carrier_var.get()
    cfg["smtp_host"] = smtp_host_var.get()
    cfg["smtp_port"] = int(smtp_port_var.get())
    cfg["smtp_user"] = smtp_user_var.get()
    cfg["smtp_pass"] = smtp_pass_var.get()
    cfg["email_to"] = email_to_var.get()
    save_config(cfg)
    messagebox.showinfo("Saved", "Configuration saved.")
    root.destroy()

carriers = sorted(CARRIER_GATEWAYS.keys())

root = tk.Tk()
root.title("Watchful Eye Configuration")
root.geometry("560x620")
root.resizable(False, False)

main = ttk.Frame(root, padding=16)
main.pack(fill="both", expand=True)

ttk.Label(main, text="Watchful Eye", font=("Segoe UI", 16, "bold")).pack(anchor="w")
ttk.Label(main, text="AI activity tracking & phone notifications", foreground="gray").pack(anchor="w", pady=(0, 12))

notebook = ttk.Notebook(main)
notebook.pack(fill="both", expand=True)

page_ai = ttk.Frame(notebook, padding=12)
notebook.add(page_ai, text="AI Provider")

page_sms = ttk.Frame(notebook, padding=12)
notebook.add(page_sms, text="SMS / Notifications")

page_general = ttk.Frame(notebook, padding=12)
notebook.add(page_general, text="General")

def add_row(parent, label, var, show=None, row=0, col_span=1):
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
    w = ttk.Entry(parent, textvariable=var, width=55, show=show)
    w.grid(row=row, column=1, columnspan=col_span, sticky="ew", pady=3, padx=(8, 0))
    return w

ttk.Label(page_ai, text="Leave blank to use local Ollama (free, run: ollama pull llama3.2-vision)", foreground="gray", wraplength=480).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

api_key_var = tk.StringVar(value=cfg.get("api_key", ""))
api_url_var = tk.StringVar(value=cfg.get("api_url", ""))
model_var = tk.StringVar(value=cfg.get("model", ""))

add_row(page_ai, "API Key:", api_key_var, show="*", row=1)
add_row(page_ai, "API URL:", api_url_var, row=2)
add_row(page_ai, "Model:", model_var, row=3)

page_ai.columnconfigure(1, weight=1)

row = 0
ttk.Label(page_sms, text="Send summaries to your phone via email-to-SMS.", foreground="gray", wraplength=480).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))

row += 1
sms_enabled_var = tk.BooleanVar(value=cfg.get("sms_enabled", False))
ttk.Checkbutton(page_sms, text="Enable SMS notifications", variable=sms_enabled_var).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)

row += 1
sms_phone_var = tk.StringVar(value=cfg.get("sms_phone", ""))
add_row(page_sms, "Phone number:", sms_phone_var, row=row)

row += 1
sms_carrier_var = tk.StringVar(value=cfg.get("sms_carrier", ""))
ttk.Label(page_sms, text="Carrier:").grid(row=row, column=0, sticky="w", pady=3)
carrier_menu = ttk.Combobox(page_sms, textvariable=sms_carrier_var, values=carriers, width=52)
carrier_menu.grid(row=row, column=1, sticky="ew", pady=3, padx=(8, 0))

row += 1
ttk.Separator(page_sms).grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)

row += 1
ttk.Label(page_sms, text="SMTP settings (for sending SMS via email gateway):", font=("Segoe UI", 9, "bold")).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))

row += 1
smtp_host_var = tk.StringVar(value=cfg.get("smtp_host", ""))
add_row(page_sms, "SMTP Host:", smtp_host_var, row=row)

row += 1
smtp_port_var = tk.StringVar(value=str(cfg.get("smtp_port", 587)))
add_row(page_sms, "SMTP Port:", smtp_port_var, row=row)

row += 1
smtp_user_var = tk.StringVar(value=cfg.get("smtp_user", ""))
add_row(page_sms, "SMTP User:", smtp_user_var, row=row)

row += 1
smtp_pass_var = tk.StringVar(value=cfg.get("smtp_pass", ""))
add_row(page_sms, "SMTP Password:", smtp_pass_var, show="*", row=row)

row += 1
ttk.Separator(page_sms).grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)

row += 1
ttk.Label(page_sms, text="Or send to email instead of SMS:", font=("Segoe UI", 9, "bold")).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))

row += 1
email_to_var = tk.StringVar(value=cfg.get("email_to", ""))
add_row(page_sms, "Email To:", email_to_var, row=row)

page_sms.columnconfigure(1, weight=1)

row = 0
lang_var = tk.StringVar(value=cfg.get("language", "english"))
poll_var = tk.StringVar(value=str(cfg.get("poll_interval_seconds", 10)))
summary_var = tk.StringVar(value=str(cfg.get("summary_interval_minutes", 60)))

add_row(page_general, "Language:", lang_var, row=0)
add_row(page_general, "Poll Interval (sec):", poll_var, row=1)
add_row(page_general, "Summary Interval (min):", summary_var, row=2)

page_general.columnconfigure(1, weight=1)

btn_frame = ttk.Frame(main)
btn_frame.pack(fill="x", pady=(12, 0))
ttk.Button(btn_frame, text="Save", command=save_and_close).pack(side="right", padx=(8, 0))
ttk.Button(btn_frame, text="Cancel", command=root.destroy).pack(side="right")

root.mainloop()
