from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from path_config import get_data_dir

PROFILE_FILE = get_data_dir() / "profile.json"


@dataclass
class UserProfile:
    profile_name: Optional[str] = None
    profile_mode: Optional[str] = None  # "solo" | "teacher_linked" | "teacher_linked_provisional"
    class_code: Optional[str] = None
    class_id: Optional[str] = None
    user_role: Optional[str] = None  # "student" | "teacher"
    onboarding_complete: bool = False


def load_profile() -> Optional[UserProfile]:
    """
    Load the persisted user profile from disk, if it exists.

    Returns None when no profile is present or the file is invalid.
    """
    try:
        if not PROFILE_FILE.exists():
            return None

        raw = PROFILE_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        # Treat empty {} or missing profile_name as no profile — do not auto-login or auto-populate
        if not data or not data.get("profile_name"):
            return None

        return UserProfile(
            profile_name=data.get("profile_name"),
            profile_mode=data.get("profile_mode"),
            class_code=data.get("class_code"),
            class_id=data.get("class_id"),
            user_role=data.get("user_role"),
            onboarding_complete=data.get("onboarding_complete", False),
        )
    except (OSError, json.JSONDecodeError):
        return None


def get_onboarding_complete() -> bool:
    """Return onboarding_complete from profile file. Used by auth routes."""
    try:
        if not PROFILE_FILE.exists():
            return False
        data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return bool(data.get("onboarding_complete", False))
    except (OSError, json.JSONDecodeError):
        pass
    return False


def get_onboarding_complete() -> bool:
    """Read onboarding_complete from profile file. Returns False if no profile or missing."""
    try:
        if not PROFILE_FILE.exists():
            return False
        data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return bool(data.get("onboarding_complete", False))
    except (OSError, json.JSONDecodeError):
        pass
    return False


def save_profile(profile: UserProfile) -> None:
    """
    Persist the given profile to disk using an atomic write.
    """
    PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)

    data = asdict(profile)
    tmp_path = PROFILE_FILE.with_suffix(".tmp")

    tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(PROFILE_FILE)


def _user_profile_file(user_id: str) -> Path:
    """Return per-user profile.json path."""
    return PROFILE_FILE.parent / "users" / user_id / "profile.json"


def load_profile_for_user(user_id: str) -> Optional[UserProfile]:
    """Load profile from per-user directory."""
    path = _user_profile_file(user_id)
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not data.get("profile_name"):
            return None
        return UserProfile(
            profile_name=data.get("profile_name"),
            profile_mode=data.get("profile_mode"),
            class_code=data.get("class_code"),
            class_id=data.get("class_id"),
            user_role=data.get("user_role"),
            onboarding_complete=data.get("onboarding_complete", False),
        )
    except (OSError, json.JSONDecodeError):
        return None


def save_profile_for_user(user_id: str, profile: UserProfile) -> None:
    """Persist profile to per-user directory."""
    path = _user_profile_file(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(profile)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)

