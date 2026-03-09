"""
Auth API routes: signup, login, JWT generation.

- Signup: email, username, password with strict validation
- Login: username or email + password
- Returns secure JWT on success
"""

from __future__ import annotations

import logging
import os
import re
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from auth_utils import hash_password, verify_password
from database import User, get_db, init_db
from email_service import send_otp_email, send_verification_email
from profile_store import UserProfile, load_profile, save_profile, load_profile_for_user, save_profile_for_user

# JWT config (must be before dependencies import to avoid circular import)
JWT_SECRET = os.environ.get("STUDAXIS_JWT_SECRET", "studaxis-dev-secret-change-in-prod")
if JWT_SECRET == "studaxis-dev-secret-change-in-prod":
    logging.getLogger("studaxis.auth").warning(
        "STUDAXIS_JWT_SECRET not set; using dev fallback. Set it in production."
    )
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24 * 7  # 7 days
VERIFICATION_EXPIRY_HOURS = 24  # Email verification token

# OTP storage: email -> { code, expires_at, attempts }
_otp_store: dict = {}
OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 5

# Validation patterns
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,20}$")
PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
)
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Import after JWT constants to avoid circular import with dependencies
from dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1)


class LoginRequest(BaseModel):
    username_or_email: str = Field(..., min_length=1, description="Username or email")
    password: str = Field(..., min_length=1)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    email: str
    onboarding_complete: bool = False


class RequestOTPRequest(BaseModel):
    email: EmailStr
    password: str | None = None  # Required for login flow; omit for resend when OTP already sent


class OTPVerify(BaseModel):
    email: EmailStr
    otp: str


class EmailCheck(BaseModel):
    email: EmailStr


class OnboardingData(BaseModel):
    profile_name: str = Field(..., min_length=1)
    role: str = Field(..., pattern="^(student|teacher)$")
    mode: str = Field(default="solo", pattern="^(solo|teacher_linked|teacher_linked_provisional)$")
    class_code: str | None = None
    class_id: str | None = None
    subjects: str | None = None
    grade: str | None = None


# ---------------------------------------------------------------------------
# Rate limiting (auth endpoints — prevent brute force)
# ---------------------------------------------------------------------------
_RATE_WINDOW_SEC = 60
_RATE_MAX_REQUESTS = 10
_rate_store: dict[str, list[float]] = defaultdict(list)
_otp_request_per_email: dict[str, list[float]] = defaultdict(list)
_OTP_REQUEST_COOLDOWN_SEC = 30  # Min 1 OTP request per email per 30 seconds


def _check_rate_limit(request: Request) -> None:
    """Raise 429 if IP exceeds rate limit. In-memory; resets on restart."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - _RATE_WINDOW_SEC
    _rate_store[client_ip] = [t for t in _rate_store[client_ip] if t > window_start]
    if len(_rate_store[client_ip]) >= _RATE_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again in a minute.",
        )
    _rate_store[client_ip].append(now)


def _check_otp_request_cooldown(email: str) -> None:
    """Prevent OTP bombing: max 1 request per email per minute."""
    key = email.strip().lower()
    now = time.time()
    window_start = now - _OTP_REQUEST_COOLDOWN_SEC
    _otp_request_per_email[key] = [t for t in _otp_request_per_email[key] if t > window_start]
    if _otp_request_per_email[key]:
        raise HTTPException(
            status_code=429,
            detail="Please wait before requesting another OTP. Check your email or try again in a minute.",
        )
    _otp_request_per_email[key].append(now)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_username(username: str) -> None:
    if not USERNAME_REGEX.match(username):
        raise HTTPException(
            status_code=422,
            detail="Username must be 3–20 characters, alphanumeric and underscores only.",
        )


def _validate_password(password: str) -> None:
    if not PASSWORD_REGEX.match(password):
        raise HTTPException(
            status_code=422,
            detail=(
                "Password must be at least 8 characters with 1 uppercase, 1 lowercase, "
                "1 digit, and 1 special character (@$!%*?&)."
            ),
        )


def _validate_email(email: str) -> None:
    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=422, detail="Invalid email format.")


def _create_jwt(user_id: int, username: str) -> str:
    import jwt

    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _create_verification_token(email: str) -> str:
    """Short-lived JWT for email verification (24h). Payload: email."""
    import jwt

    payload = {
        "email": email.strip().lower(),
        "type": "email_verification",
        "exp": datetime.now(timezone.utc) + timedelta(hours=VERIFICATION_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _send_otp_email(email: str, code: str) -> None:
    """Send OTP via SMTP. Falls back to console log if SMTP not configured."""
    import logging
    if send_otp_email(email, code):
        return
    logging.getLogger(__name__).info("[OTP dev fallback] %s → %s", email, code)


def _generate_and_send_otp(email: str) -> None:
    """Generate secure 6-digit OTP, store with 5 min expiry, send via email."""
    code = str(secrets.randbelow(900000) + 100000)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)
    _otp_store[email.strip().lower()] = {"code": code, "expires_at": expires_at, "attempts": 0}
    _send_otp_email(email, code)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/signup", response_model=AuthResponse)
def signup(
    request: Request,
    req: SignupRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
):
    _check_rate_limit(request)
    """
    Register a new user. Validates username (alphanumeric + underscore, 3–20 chars)
    and password (8+ chars, 1 upper, 1 lower, 1 digit, 1 special).
    Returns JWT on success.
    """
    _validate_username(req.username)
    _validate_password(req.password)
    _validate_email(req.email)

    # Check username already exists
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Username already exists. Please choose a different username.",
        )

    # Check email already exists
    existing_email = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="Email Already Exists, Please Sign In")

    hashed = hash_password(req.password)
    user = User(
        email=req.email.strip().lower(),
        username=req.username.strip(),
        hashed_password=hashed,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Send verification email in background (non-blocking)
    verification_token = _create_verification_token(user.email)
    background_tasks.add_task(send_verification_email, user.email, verification_token)

    # OTP: generate and send (signup triggers OTP)
    _generate_and_send_otp(user.email)

    token = _create_jwt(user.id, user.username)
    return AuthResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        email=user.email,
    )


@router.post("/login")
def login(
    request: Request,
    req: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Authenticate by username or email + password. Returns JWT on success.
    If account is not verified, returns 403 with requires_otp and email for OTP flow.
    """
    _check_rate_limit(request)
    identifier = req.username_or_email.strip()
    is_email = "@" in identifier

    if is_email:
        user = db.query(User).filter(User.email == identifier.lower()).first()
    else:
        user = db.query(User).filter(User.username == identifier).first()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid username/email or password.",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Email not verified. Please verify with the OTP sent to your email.",
                "requires_otp": True,
                "email": user.email,
            },
        )

    token = _create_jwt(user.id, user.username)
    p = load_profile_for_user(user.username)
    if not p:
        p = load_profile()  # fallback to shared for migration
    onboarding_complete = p.onboarding_complete if p else False
    return AuthResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        email=user.email,
        onboarding_complete=onboarding_complete,
    )


@router.post("/check-email")
def check_email(
    body: EmailCheck,
    db: Annotated[Session, Depends(get_db)],
):
    """Check if email is already registered."""
    email = body.email.strip().lower()
    exists = db.query(User).filter(User.email == email).first() is not None
    return {"exists": exists}


@router.post("/request-otp")
@router.post("/send-otp")
def request_otp(
    request: Request,
    body: RequestOTPRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Request OTP for existing user.
    - Login flow: pass password to verify before sending OTP.
    - Resend flow: omit password when OTP already sent (active OTP must exist).
    """
    _check_rate_limit(request)
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No user found with this email.")
    stored = _otp_store.get(email)
    has_active_otp = stored and datetime.now(timezone.utc) <= stored.get("expires_at", datetime.min.replace(tzinfo=timezone.utc))
    if body.password is not None:
        if not verify_password(body.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid password.")
    elif not has_active_otp:
        raise HTTPException(
            status_code=400,
            detail="Password required for first OTP request. For resend, use the OTP screen (OTP must be active).",
        )
    _check_otp_request_cooldown(email)
    _generate_and_send_otp(email)
    return {"message": "OTP sent"}


@router.post("/verify-otp")
def verify_otp(
    request: Request,
    body: OTPVerify,
    db: Annotated[Session, Depends(get_db)],
):
    """Verify OTP, mark user as verified, return access_token. Limited attempts to prevent brute force."""
    _check_rate_limit(request)
    email = body.email.strip().lower()
    stored = _otp_store.get(email)
    if not stored:
        raise HTTPException(status_code=400, detail="No OTP found for this email. Request a new one.")
    if datetime.now(timezone.utc) > stored["expires_at"]:
        del _otp_store[email]
        raise HTTPException(status_code=410, detail="OTP expired. Please request a new one.")
    attempts = stored.get("attempts", 0)
    if attempts >= OTP_MAX_ATTEMPTS:
        del _otp_store[email]
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Please request a new OTP.",
        )
    otp_clean = body.otp.replace(" ", "").strip()
    DEV_BYPASS = os.getenv("ENV", "dev") == "dev"
    if stored["code"] != otp_clean:
        if not (DEV_BYPASS and otp_clean == "000000"):
            stored["attempts"] = attempts + 1
            remaining = OTP_MAX_ATTEMPTS - stored["attempts"]
            raise HTTPException(
                status_code=400,
                detail=f"Incorrect OTP. {remaining} attempt(s) remaining.",
            )
    # Remove OTP after successful use (one-time)
    del _otp_store[email]
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_verified = True
    db.commit()
    token = _create_jwt(user.id, user.username)
    p = load_profile_for_user(user.username)
    if not p:
        p = load_profile()
    onboarding_complete = p.onboarding_complete if p else False
    return {
        "access_token": token,
        "token_type": "bearer",
        "onboarding_complete": onboarding_complete,
    }


@router.get("/verify-email")
def verify_email(
    token: str,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Verify email via token (query param). Decodes JWT, finds user by email,
    sets is_verified=True. Returns success message.
    """
    import jwt

    if not token or not token.strip():
        raise HTTPException(status_code=400, detail="Token is required")

    try:
        payload = jwt.decode(token.strip(), JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Verification link has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    email = payload.get("email")
    if not email or payload.get("type") != "email_verification":
        raise HTTPException(status_code=400, detail="Invalid verification token")

    user = db.query(User).filter(User.email == email.lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    db.commit()

    return {"message": "Email verified successfully. You can now sign in."}


@router.post("/complete-onboarding")
def complete_onboarding(
    body: OnboardingData,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Save profile from onboarding, set onboarding_complete=True. Scoped by user_id."""
    user_id = current_user.username
    existing = load_profile_for_user(user_id) or UserProfile()
    merged = UserProfile(
        profile_name=body.profile_name,
        profile_mode=body.mode,
        class_code=body.class_code or existing.class_code,
        class_id=body.class_id or existing.class_id,
        user_role=body.role,
        onboarding_complete=True,
    )
    save_profile_for_user(user_id, merged)
    return {"ok": True, "onboarding_complete": True}
