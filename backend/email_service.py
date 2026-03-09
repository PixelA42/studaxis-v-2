"""
Email service for Studaxis — verification emails and OTP via SMTP.

Uses smtplib (stdlib). Configure via env:
  STUDAXIS_SMTP_HOST, STUDAXIS_SMTP_PORT, STUDAXIS_SMTP_USER, STUDAXIS_SMTP_PASSWORD
  Or: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# Config from env — support both STUDAXIS_* and plain SMTP_* names
SMTP_HOST = os.environ.get("STUDAXIS_SMTP_HOST") or os.environ.get("SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("STUDAXIS_SMTP_PORT") or os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("STUDAXIS_SMTP_USER") or os.environ.get("SMTP_USER", "")
# Gmail app passwords may be copied with spaces; strip for login
_raw = (
    os.environ.get("STUDAXIS_SMTP_PASSWORD")
    or os.environ.get("STUDAXIS_SMTP_PASS")
    or os.environ.get("SMTP_PASS", "")
)
SMTP_PASSWORD = _raw.replace(" ", "") if _raw else ""
SMTP_FROM = os.environ.get("STUDAXIS_SMTP_FROM", SMTP_USER or "noreply@studaxis.local")
SMTP_TIMEOUT = int(os.environ.get("STUDAXIS_SMTP_TIMEOUT", "15"))
VERIFY_BASE_URL = os.environ.get("STUDAXIS_VERIFY_BASE_URL", "http://localhost:5173")


def _is_smtp_configured() -> bool:
    """Check if SMTP credentials are set (required for Gmail)."""
    return bool(SMTP_USER and SMTP_PASSWORD)


def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Send a plain-text email via SMTP.

    Uses Gmail SMTP when configured:
      - smtp.gmail.com:587
      - TLS/STARTTLS enabled
      - Authentication required

    Returns True if sent, False on failure (logged).
    """
    if not _is_smtp_configured():
        logger.warning("SMTP not configured (SMTP_USER/SMTP_PASSWORD missing). Email not sent to %s", to_email)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())
        logger.info("Email sent to %s: %s", to_email, subject[:50])
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(
            "SMTP authentication failed for %s. Check STUDAXIS_SMTP_USER and STUDAXIS_SMTP_PASSWORD (use Gmail App Password): %s",
            SMTP_USER,
            str(e),
        )
        return False
    except smtplib.SMTPRecipientsRefused as e:
        logger.error("SMTP recipient refused for %s: %s", to_email, e)
        return False
    except smtplib.SMTPException as e:
        logger.error("SMTP error sending to %s: %s", to_email, e)
        return False
    except (ConnectionError, OSError) as e:
        logger.error("SMTP connection error (host=%s port=%s): %s", SMTP_HOST, SMTP_PORT, e)
        return False
    except TimeoutError:
        logger.error("SMTP timeout connecting to %s:%s", SMTP_HOST, SMTP_PORT)
        return False
    except Exception as e:
        logger.exception("Unexpected error sending email to %s: %s", to_email, e)
        return False


def send_otp_email(to_email: str, otp: str) -> bool:
    """
    Send OTP verification email. Subject: Verify Your Account.
    OTP expires in 5 minutes.
    """
    subject = "Verify Your Account"
    body = f"""Your verification OTP is: {otp}

This OTP will expire in 5 minutes."""
    return send_email(to_email, subject, body)


def send_verification_email(to_email: str, token: str) -> bool:
    """
    Send email verification link to the user.
    Link format: {VERIFY_BASE_URL}/verify-email?token={token}
    Returns True if sent, False if skipped or failed.
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

    # Use send_email for link emails (plain text fallback)
    subject = "Verify your Studaxis email"
    plain_body = f"Verify your Studaxis account by visiting: {verify_url}\n\nThis link expires in 24 hours."
    return send_email(to_email, subject, plain_body)
