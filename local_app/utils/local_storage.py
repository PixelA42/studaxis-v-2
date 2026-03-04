"""
Local Storage Manager

Handles JSON persistence for:
- user stats
- chat history
- flashcards
"""

import json
import shutil
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any, Dict, List, Optional


class LocalStorage:

    def __init__(self, base_path: str = "./data"):

        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.user_stats_path = self.base_path / "user_stats.json"
        self.flashcards_path = self.base_path / "flashcards.json"

        self.backup_dir = self.base_path / "backups"
        self.backup_dir.mkdir(exist_ok=True)

        self._ensure_files()

    # ======================================================
    # File Initialization
    # ======================================================

    def _ensure_files(self):

        if not self.user_stats_path.exists():
            self._write_json(self.user_stats_path, {})

        if not self.flashcards_path.exists():
            self._write_json(self.flashcards_path, [])

    # ======================================================
    # JSON Helpers
    # ======================================================

    def _read_json(self, path: Path):

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None

    def _write_json(self, path: Path, data):

        # atomic write
        temp = path.with_suffix(".tmp")

        with open(temp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        temp.replace(path)

    # ======================================================
    # USER STATS
    # ======================================================

    def initialize_user_stats(self, user_id: str) -> Dict[str, Any]:

        now = datetime.now(timezone.utc)

        stats = {
            "user_id": user_id,
            "last_sync_timestamp": now.isoformat(),
            "streak": {
                "current": 0,
                "longest": 0,
                "last_activity_date": now.date().isoformat(),
            },
            "quiz_stats": {
                "total_attempted": 0,
                "total_correct": 0,
                "average_score": 0.0,
                "by_topic": {},
            },
            "flashcard_stats": {
                "total_reviewed": 0,
                "mastered": 0,
                "due_for_review": 0,
            },
            "chat_history": [],
            "preferences": {
                "difficulty_level": "Beginner",
                "theme": "light",
                "language": "English",
            },
            "hardware_info": {},
        }

        self.save_user_stats(stats)

        return stats

    def load_user_stats(self) -> Optional[Dict[str, Any]]:

        if not self.user_stats_path.exists():
            return None

        try:
            return self._read_json(self.user_stats_path)

        except json.JSONDecodeError:

            print("⚠️ Corrupted user stats, restoring backup")

            return self._restore_from_backup()

    def save_user_stats(self, stats: Dict[str, Any]) -> bool:

        try:
            self._create_backup()
            self._write_json(self.user_stats_path, stats)
            return True

        except Exception as e:

            print("❌ Failed to save stats:", e)

            return False

    def update_user_stats(self, updates: Dict[str, Any]):

        stats = self.load_user_stats()

        if stats is None:
            return False

        self._deep_merge(stats, updates)

        stats["last_sync_timestamp"] = datetime.now(timezone.utc).isoformat()

        return self.save_user_stats(stats)

    def _deep_merge(self, base: Dict[str, Any], updates: Dict[str, Any]):

        for key, value in updates.items():

            if key in base and isinstance(base[key], dict) and isinstance(value, dict):

                self._deep_merge(base[key], value)

            else:

                base[key] = value

    # ======================================================
    # CHAT HISTORY
    # ======================================================

    def add_chat_message(self, role: str, content: str, topic: str = "General"):

        stats = self.load_user_stats()

        if not stats:
            return False

        message = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "content": content,
            "topic": topic,
        }

        stats["chat_history"].append(message)

        stats["chat_history"] = stats["chat_history"][-50:]

        return self.save_user_stats(stats)

    # ======================================================
    # FLASHCARDS
    # ======================================================

    def load_flashcards(self) -> List[Dict[str, Any]]:

        cards = self._read_json(self.flashcards_path)

        return cards if cards else []

    def add_flashcards(self, cards: List[Dict[str, Any]]):

        existing = self.load_flashcards()

        existing.extend(cards)

        self._write_json(self.flashcards_path, existing)

    def update_flashcard(self, updated_card: Dict[str, Any]):

        cards = self.load_flashcards()

        for i, card in enumerate(cards):

            if card["card_id"] == updated_card["card_id"]:

                cards[i] = updated_card
                break

        self._write_json(self.flashcards_path, cards)

    def delete_flashcard(self, card_id: str):

        cards = self.load_flashcards()

        cards = [c for c in cards if c["card_id"] != card_id]

        self._write_json(self.flashcards_path, cards)

    def get_due_flashcards(self):

        cards = self.load_flashcards()

        today = datetime.now(timezone.utc).date()

        due = []

        for card in cards:

            try:
                review_date = datetime.fromisoformat(card["next_review"]).date()

                if review_date <= today:
                    due.append(card)

            except:
                continue

        return due

    # ======================================================
    # STREAK SYSTEM
    # ======================================================

    def update_streak(self):

        stats = self.load_user_stats()

        if not stats:
            return False

        today = datetime.now(timezone.utc).date()

        last = date.fromisoformat(stats["streak"]["last_activity_date"])

        if today == last:
            return True
        diff = (today - last)

        if diff.days == 1:
            stats["streak"]["current"] += 1
        else:
            stats["streak"]["current"] = 1

        stats["streak"]["longest"] = max(
            stats["streak"]["longest"],
            stats["streak"]["current"],
        )

        stats["streak"]["last_activity_date"] = today.isoformat()

        return self.save_user_stats(stats)

    # ======================================================
    # BACKUPS
    # ======================================================

    def _create_backup(self):

        if not self.user_stats_path.exists():
            return

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        backup = self.backup_dir / f"user_stats_{timestamp}.json"

        shutil.copy2(self.user_stats_path, backup)

        self._cleanup_old_backups()

    def _cleanup_old_backups(self, keep: int = 7):

        backups = sorted(self.backup_dir.glob("user_stats_*.json"))

        for old in backups[:-keep]:
            old.unlink()

    def _restore_from_backup(self):

        backups = sorted(self.backup_dir.glob("user_stats_*.json"))

        if not backups:
            return None

        latest = backups[-1]

        stats = self._read_json(latest)

        self._write_json(self.user_stats_path, stats)

        return stats