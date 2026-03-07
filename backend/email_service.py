"""
Email service for Studaxis — verification emails via SMTP.
Uses smtplib (stdlib). Configure via env: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, etc.
"""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Config from env (optional — if not set, send_verification_email logs and skips)
SMTP_HOST = os.environ.get("STUDAXIS_SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("STUDAXIS_SMTP_PORT", "1025"))
SMTP_USER = os.environ.get("STUDAXIS_SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("STUDAXIS_SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("STUDAXIS_SMTP_FROM", "noreply@studaxis.local")
# Frontend base URL for verification link
VERIFY_BASE_URL = os.environ.get("STUDAXIS_VERIFY_BASE_URL", "http://localhost:5173")


def send_verification_email(to_email: str, token: str) -> bool:
    """
    Send email verification link to the user.
    Link format: {VERIFY_BASE_URL}/verify-email?token={token}
    Returns True if sent, False if skipped (e.g. SMTP not configured).
    """
    verify_url = f"{VERIFY_BASE_URL.rstrip('/')}/verify-email?token={token}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: system-ui, sans-serif; line-height: 1.6; color: #333;">
        <h2>Verify your Studaxis account</h2>
        <p>Thanks for signing up! Please verify your email by clicking the link below:</p>
        <p><a href="{verify_url}" style="color: #FA5C5C; font-weight: bold;">Verify my email</a></p>
        <p>Or copy this link into your browser:</p>
        <p style="word-break: break-all; font-size: 12px;">{verify_url}</p>
        <p>This link expires in 24 hours.</p>
        <p>If you didn't create an account, you can ignore this email.</p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your Studaxis email"
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            if SMTP_USER and SMTP_PASSWORD:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())
        return True
    except Exception as e:
        # Log but don't fail signup — user can request resend later
        import logging
        logging.getLogger(__name__).warning("Verification email failed: %s", e)
        return False
