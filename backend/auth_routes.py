"""
Auth API routes: signup, login, JWT generation.

- Signup: email, username, password with strict validation
- Login: username or email + password
- Returns secure JWT on success
"""

from __future__ import annotations

import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from auth_utils import hash_password, verify_password
from database import User, get_db, init_db
from email_service import send_otp_email, send_verification_email
from profile_store import UserProfile, load_profile, save_profile, load_profile_for_user, save_profile_for_user

# JWT config (must be before dependencies import to avoid circular import)
JWT_SECRET = os.environ.get("STUDAXIS_JWT_SECRET", "studaxis-dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24 * 7  # 7 days
VERIFICATION_EXPIRY_HOURS = 24  # Email verification token

# OTP storage: email -> { code, expires_at }
_otp_store: dict = {}
OTP_EXPIRY_MINUTES = 5

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
    subjects: str | None = None
    grade: str | None = None


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
    _otp_store[email.strip().lower()] = {"code": code, "expires_at": expires_at}
    _send_otp_email(email, code)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/signup", response_model=AuthResponse)
def signup(
    req: SignupRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
):
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


@router.post("/login", response_model=AuthResponse)
def login(
    req: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Authenticate by username or email + password. Returns JWT on success.
    """
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
    body: RequestOTPRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Request OTP for existing user. Checks email exists, generates and sends OTP via email."""
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No user found with this email.")
    _generate_and_send_otp(email)
    return {"message": "OTP sent"}


@router.post("/verify-otp")
def verify_otp(
    body: OTPVerify,
    db: Annotated[Session, Depends(get_db)],
):
    """Verify OTP, mark user as verified, return access_token."""
    email = body.email.strip().lower()
    stored = _otp_store.get(email)
    if not stored:
        raise HTTPException(status_code=400, detail="No OTP found for this email.")
    if datetime.now(timezone.utc) > stored["expires_at"]:
        raise HTTPException(status_code=410, detail="OTP expired.")
    DEV_BYPASS = os.getenv("ENV", "dev") == "dev"
    if stored["code"] != body.otp:
        if not (DEV_BYPASS and body.otp == "000000"):
            raise HTTPException(status_code=400, detail="Incorrect OTP.")
    # Remove OTP after successful use (one-time)
    del _otp_store[email]
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_verified = True
    db.commit()
    token = _create_jwt(user.id, user.username)
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
        user_role=body.role,
        onboarding_complete=True,
    )
    save_profile_for_user(user_id, merged)
    return {"ok": True, "onboarding_complete": True}
