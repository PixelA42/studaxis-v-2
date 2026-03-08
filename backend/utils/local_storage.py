"""
Local storage for flashcards and user stats.

Compatible with flashcards_system (add_flashcards, get_due_cards, load_user_stats, save_user_stats).
Data paths: {base_path}/data/user_stats.json, {base_path}/data/flashcards.json.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _default_base_path() -> Path:
    return Path(__file__).resolve().parent.parent


class LocalStorage:
    """Persistence for user stats and flashcards (flashcards_system interface)."""

    def __init__(self, base_path: str | Path | None = None, *, user_id: str) -> None:
        self._base = Path(base_path) if base_path else _default_base_path()
        self._data_dir = self._base / "data"
        self._user_id = user_id
        # Per-user directory: data/users/{user_id}/
        self._user_dir = self._data_dir / "users" / user_id
        self._stats_file = self._user_dir / "user_stats.json"
        self._flashcards_file = self._user_dir / "flashcards.json"

    def _ensure_data_dir(self) -> None:
        self._user_dir.mkdir(parents=True, exist_ok=True)

    def load_user_stats(self) -> dict[str, Any]:
        """Load user_stats.json; return dict with defaults on missing/error."""
        try:
            if self._stats_file.exists():
                raw = self._stats_file.read_text(encoding="utf-8")
                data = json.loads(raw)
                if isinstance(data, dict):
                    return data
        except (OSError, json.JSONDecodeError):
            pass
        return {
            "user_id": "student_001",
            "topic_performance": {},
            "flashcard_stats": {"total_reviewed": 0, "mastered": 0, "due_for_review": 0},
        }

    def save_user_stats(self, stats: dict[str, Any]) -> None:
        """Persist user stats to user_stats.json."""
        try:
            self._ensure_data_dir()
            self._stats_file.write_text(
                json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except OSError:
            pass

    def add_flashcards(self, cards: list[dict[str, Any]]) -> None:
        """Append flashcards to flashcards.json. Each card must have keys expected by spaced_repetition."""
        if not cards:
            return
        try:
            self._ensure_data_dir()
            existing: list[dict[str, Any]] = []
            if self._flashcards_file.exists():
                raw = self._flashcards_file.read_text(encoding="utf-8")
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    existing = parsed
            existing.extend(cards)
            self._flashcards_file.write_text(
                json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except (OSError, json.JSONDecodeError):
            pass

    def get_all_flashcards(self) -> list[dict[str, Any]]:
        """Load all stored flashcards."""
        try:
            if self._flashcards_file.exists():
                raw = self._flashcards_file.read_text(encoding="utf-8")
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return parsed
        except (OSError, json.JSONDecodeError):
            pass
        return []

    def get_due_cards(self) -> list[dict[str, Any]]:
        """Return cards where next_review <= now (ISO string comparison or missing next_review)."""
        now = datetime.now(timezone.utc).isoformat()
        all_cards = self.get_all_flashcards()
        due = []
        for c in all_cards:
            next_review = c.get("next_review") or ""
            if not next_review or next_review <= now:
                due.append(c)
        return due

    def save_flashcards(self, cards: list[dict[str, Any]]) -> None:
        """Overwrite flashcards.json with the given list (e.g. after updating intervals)."""
        try:
            self._ensure_data_dir()
            self._flashcards_file.write_text(
                json.dumps(cards, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except OSError:
            pass

    def initialize_user_stats(self, user_id: str | None = None) -> dict[str, Any]:
        """Create and persist a fresh user-stats dict, then return it."""
        stats: dict[str, Any] = {
            "user_id": user_id,
            "topic_performance": {},
            "flashcard_stats": or self._user_id {"total_reviewed": 0, "mastered": 0, "due_for_review": 0},
            "chat_history": [],
        }
        self.save_user_stats(stats)
        return stats

    def add_chat_message(self, role: str, content: str, subject: str = "General") -> None:
        """Append a chat message to the chat_history list in user stats."""
        stats = self.load_user_stats()
        history = stats.setdefault("chat_history", [])
        history.append({
            "role": role,
            "content": content,
            "subject": subject,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Cap history at 100 entries
        if len(history) > 100:
            stats["chat_history"] = history[-100:]
        self.save_user_stats(stats)
