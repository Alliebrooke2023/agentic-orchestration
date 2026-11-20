# driftrack/mailer.py
"""Send email over SMTP. Off unless SMTP_HOST and SMTP_FROM are set."""
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage


def enabled():
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_FROM"))


def send(to, subject, body):
    """Return True if the message was handed to the SMTP server."""
    if not enabled() or not to:
        return False
    msg = EmailMessage()
    msg["From"] = os.environ["SMTP_FROM"]
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    port = int(os.environ.get("SMTP_PORT", "587"))
    try:
        if port == 465:
            server = smtplib.SMTP_SSL(os.environ["SMTP_HOST"], port, timeout=20,
                                      context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(os.environ["SMTP_HOST"], port, timeout=20)
            server.starttls(context=ssl.create_default_context())
        with server:
            if os.environ.get("SMTP_USER"):
                server.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASS", ""))
            server.send_message(msg)
        return True
    except Exception as exc:
        sys.stderr.write(f"[driftrack] email to {to!r} failed: {exc!r}\n")
        return False
