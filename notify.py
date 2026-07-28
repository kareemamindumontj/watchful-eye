import smtplib
import ssl
from email.message import EmailMessage
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from config import load_config

CARRIER_GATEWAYS = {
    "verizon": "vtext.com",
    "tmobile": "tmomail.net",
    "att": "txt.att.net",
    "sprint": "messaging.sprintpcs.com",
    "cricket": "sms.cricketwireless.net",
    "google-fi": "msg.fi.google.com",
    "us-cellular": "email.uscc.net",
    "mint": "tmomail.net",
    "boost": "sms.myboostmobile.com",
    "tracfone": "mmst5.tracfone.com",
    "consumer-cellular": "mailmymobile.com",
    "republic": "text.republicwireless.com",
}

def _send_email(to_addr, subject, body, smtp_host, smtp_port, smtp_user, smtp_pass, use_tls=True, attachment_path=None):
    if attachment_path and Path(attachment_path).exists():
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to_addr
        msg.attach(MIMEText(body, "plain"))
        with open(attachment_path, "rb") as f:
            img = MIMEImage(f.read())
            img.add_header("Content-Disposition", "attachment", filename=Path(attachment_path).name)
            msg.attach(img)
    else:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to_addr
        msg.set_content(body)

    try:
        if use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.starttls(context=context)
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) as server:
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
        return True
    except Exception:
        return False

def send_sms(body, subject="Watchful Eye", attachment_path=None):
    cfg = load_config()
    phone = cfg.get("sms_phone", "").strip()
    carrier = cfg.get("sms_carrier", "").strip()
    smtp_host = cfg.get("smtp_host", "").strip()
    smtp_port = cfg.get("smtp_port", 587)
    smtp_user = cfg.get("smtp_user", "").strip()
    smtp_pass = cfg.get("smtp_pass", "").strip()

    if not phone or not carrier or not smtp_host or not smtp_user or not smtp_pass:
        return False, "SMS not configured."

    gateway = CARRIER_GATEWAYS.get(carrier)
    if not gateway:
        return False, f"Unknown carrier: {carrier}"

    to_addr = f"{phone}@{gateway}"
    ok = _send_email(to_addr, subject, body, smtp_host, smtp_port, smtp_user, smtp_pass, attachment_path=attachment_path)
    if ok:
        return True, "Sent."
    return False, "SMTP send failed."

def send_email(subject, body, attachment_path=None):
    cfg = load_config()
    smtp_host = cfg.get("smtp_host", "").strip()
    smtp_port = cfg.get("smtp_port", 587)
    smtp_user = cfg.get("smtp_user", "").strip()
    smtp_pass = cfg.get("smtp_pass", "").strip()
    to_email = cfg.get("email_to", "").strip()

    if not smtp_host or not smtp_user or not smtp_pass or not to_email:
        return False, "Email not configured."

    ok = _send_email(to_email, subject, body, smtp_host, smtp_port, smtp_user, smtp_pass, attachment_path=attachment_path)
    if ok:
        return True, "Sent."
    return False, "SMTP send failed."

def send_notification(body, subject="Watchful Eye Summary", attachment_path=None):
    ok_sms, _ = send_sms("Photo taken at boot." if attachment_path else body, subject)
    ok_email, _ = send_email(subject, body, attachment_path)
    if ok_sms or ok_email:
        return True, "Sent."
    return False, "No notification method configured."
