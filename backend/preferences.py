"""
Studaxis — User Preferences Persistence
════════════════════════════════════════
Load and save user preferences to user_stats.json.
Shared by dashboard and settings pages.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_STATS_FILE = Path(__file__).parent / "data" / "user_stats.json"

_DEFAULT_STATS: dict[str, Any] = {
    "user_id": "student_001",
    "last_sync_timestamp": None,
    "streak": {"current": 0, "longest": 0, "last_activity_date": None},
    "quiz_stats": {
        "total_attempted": 0,
        "total_correct": 0,
        "average_score": 0.0,
        "last_quiz_date": None,
        "by_topic": {}
    },
    "flashcard_stats": {"total_reviewed": 0, "mastered": 0, "due_for_review": 0},
    "chat_history": [],
    "preferences": {
        "difficulty_level": "Beginner",
        "theme": "light",
        "language": "English",
        "sync_enabled": True,
    },
    "hardware_info": {},
}


def load_user_stats() -> dict[str, Any]:
    """Load user_stats.json; return safe defaults on any error."""
    try:
        if _STATS_FILE.exists():
            raw = _STATS_FILE.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
    except (OSError, json.JSONDecodeError):
        pass
    result = _DEFAULT_STATS.copy()
    # Ensure preferences dict has all keys
    prefs = result.get("preferences") or {}
    if not isinstance(prefs, dict):
        prefs = {}
    for key, default in _DEFAULT_STATS["preferences"].items():
        if key not in prefs:
            prefs[key] = default
    result["preferences"] = prefs
    return result


def save_preference(key: str, value: Any) -> None:
    """Persist a single preference to user_stats.json preferences."""
    try:
        stats = load_user_stats()
        if "preferences" not in stats or not isinstance(stats["preferences"], dict):
            stats["preferences"] = {}
        stats["preferences"][key] = value
        tmp = _STATS_FILE.with_suffix(".tmp")
        _STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(_STATS_FILE)
    except OSError:
        pass


def save_theme_preference(theme: str) -> None:
    """Persist theme choice (light/dark) to user_stats.json."""
    save_preference("theme", theme)
