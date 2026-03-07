from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


PROFILE_FILE = Path(__file__).parent / "data" / "profile.json"


@dataclass
class UserProfile:
    profile_name: Optional[str] = None
    profile_mode: Optional[str] = None  # "solo" | "teacher_linked" | "teacher_linked_provisional"
    class_code: Optional[str] = None
    user_role: Optional[str] = None  # "student" | "teacher"


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

        return UserProfile(
            profile_name=data.get("profile_name"),
            profile_mode=data.get("profile_mode"),
            class_code=data.get("class_code"),
            user_role=data.get("user_role"),
        )
    except (OSError, json.JSONDecodeError):
        return None


def save_profile(profile: UserProfile) -> None:
    """
    Persist the given profile to disk using an atomic write.
    """
    PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)

    data = asdict(profile)
    tmp_path = PROFILE_FILE.with_suffix(".tmp")

    tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(PROFILE_FILE)

