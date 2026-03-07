"""
Auth API routes: signup, login, JWT generation.

- Signup: email, username, password with strict validation
- Login: username or email + password
- Returns secure JWT on success
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth_utils import hash_password, verify_password
from database import User, get_db, init_db

# Validation patterns
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,20}$")
PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
)
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# JWT config (use env in prod)
JWT_SECRET = os.environ.get("STUDAXIS_JWT_SECRET", "studaxis-dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24 * 7  # 7 days

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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/signup", response_model=AuthResponse)
def signup(
    req: SignupRequest,
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
    existing_email = db.query(User).filter(User.email == req.email).first()
    if existing_email:
        raise HTTPException(
            status_code=409,
            detail="Email already registered. Please sign in or use a different email.",
        )

    hashed = hash_password(req.password)
    user = User(
        email=req.email.strip().lower(),
        username=req.username.strip(),
        hashed_password=hashed,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

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
    return AuthResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        email=user.email,
    )
