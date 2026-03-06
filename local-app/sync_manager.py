"""
Studaxis — Sync Manager (Student Device)
═════════════════════════════════════════
Manages the offline-first sync queue:
  1. Queue mutations locally when offline (quiz attempts, streaks)
  2. Detect connectivity to AppSync
  3. Flush queue → AppSync GraphQL mutations when online
  4. Track sync status and last-sync timestamps

Flow:
  Student completes quiz → record_quiz_attempt() saves locally
  → enqueue_quiz_sync() adds to offline queue
  → try_sync() checks connectivity and flushes pending mutations
  → AppSync → Lambda → DynamoDB
  → Teacher Dashboard sees updated data
"""

import json
import os
import logging
import requests
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger("studaxis.sync_manager")


@dataclass
class SyncItem:
    """A single pending sync mutation."""
    mutation_type: str       # "recordQuizAttempt" | "updateStreak"
    payload: Dict            # GraphQL variables
    queued_at: str           # ISO timestamp
    retry_count: int = 0
    last_error: str = ""


class SyncManager:
    """
    Offline-first sync manager.
    Queues mutations locally and flushes to AppSync when online.
    """

    QUEUE_FILE = "data/sync_queue.json"
    MAX_RETRIES = 5
    CONNECTIVITY_TIMEOUT = 5  # seconds

    def __init__(
        self,
        appsync_endpoint: Optional[str] = None,
        appsync_api_key: Optional[str] = None,
        base_path: str = ".",
    ):
        self.appsync_endpoint = appsync_endpoint or os.getenv("APPSYNC_ENDPOINT", "")
        self.appsync_api_key = appsync_api_key or os.getenv("APPSYNC_API_KEY", "")
        self.base_path = Path(base_path)
        self.queue_path = self.base_path / self.QUEUE_FILE
        self.session = requests.Session()

        # Ensure data directory exists
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing queue
        self._queue: List[Dict] = self._load_queue()

    # ═══════════════════════════════════════════════════════════════════════
    # PUBLIC API — Queue Mutations
    # ═══════════════════════════════════════════════════════════════════════

    def enqueue_quiz_sync(
        self,
        user_id: str,
        quiz_id: str,
        score: int,
        total_questions: int,
        subject: str = "General",
        difficulty: str = "Medium",
        device_id: str = None,
    ) -> bool:
        """
        Queue a quiz attempt for sync to AppSync.
        Called after record_quiz_attempt() saves locally.
        If device_id is None, generates/retrieves persistent device ID.
        """
        # Use persistent device ID if not provided
        if device_id is None:
            from device_id import get_or_generate_device_id
            device_id = get_or_generate_device_id()
        item = SyncItem(
            mutation_type="recordQuizAttempt",
            payload={
                "userId": user_id,
                "quizId": quiz_id,
                "score": score,
                "totalQuestions": total_questions,
                "subject": subject,
                "difficulty": difficulty,
                "deviceId": device_id,
                "completedAtLocal": datetime.now(timezone.utc).isoformat(),
            },
            queued_at=datetime.now(timezone.utc).isoformat(),
        )
        self._queue.append(asdict(item))
        self._save_queue()
        logger.info("Queued quiz sync: %s (queue size: %d)", quiz_id, len(self._queue))
        return True

    def enqueue_streak_sync(
        self,
        user_id: str,
        current_streak: int,
    ) -> bool:
        """Queue a streak update for sync to AppSync."""
        item = SyncItem(
            mutation_type="updateStreak",
            payload={
                "userId": user_id,
                "currentStreak": current_streak,
            },
            queued_at=datetime.now(timezone.utc).isoformat(),
        )
        self._queue.append(asdict(item))
        self._save_queue()
        logger.info("Queued streak sync: %s → %d", user_id, current_streak)
        return True

    # ═══════════════════════════════════════════════════════════════════════
    # PUBLIC API — Sync Execution
    # ═══════════════════════════════════════════════════════════════════════

    def try_sync(self) -> Dict:
        """
        Attempt to flush all pending mutations to AppSync.
        Returns sync result summary.

        This is the main entry point — call on page load, after quiz
        completion, or on a timer.
        """
        result = {
            "synced": 0,
            "failed": 0,
            "pending": 0,
            "online": False,
            "errors": [],
        }

        # Respect user opt-out from Settings (Privacy Controls)
        try:
            from preferences import load_user_stats
            prefs = load_user_stats().get("preferences") or {}
            if not prefs.get("sync_enabled", True):
                result["pending"] = len(self._queue)
                result["online"] = self.check_connectivity()
                result["errors"] = ["Cloud sync disabled in Settings"]
                logger.info("Sync skipped — user has disabled cloud sync")
                return result
        except ImportError:
            pass

        if not self._queue:
            result["online"] = self.check_connectivity()
            return result

        # Check connectivity first
        if not self.check_connectivity():
            result["pending"] = len(self._queue)
            logger.info("Offline — %d items queued for later", len(self._queue))
            return result

        result["online"] = True

        # Flush queue (process in order, oldest first)
        remaining = []
        for item in self._queue:
            mutation_type = item["mutation_type"]
            payload = item["payload"]
            retry_count = item.get("retry_count", 0)

            if retry_count >= self.MAX_RETRIES:
                logger.warning("Dropping item after %d retries: %s", retry_count, mutation_type)
                result["failed"] += 1
                result["errors"].append(f"Max retries exceeded for {mutation_type}")
                continue

            success, error = self._execute_mutation(mutation_type, payload)
            if success:
                result["synced"] += 1
                logger.info("Synced: %s", mutation_type)
            else:
                item["retry_count"] = retry_count + 1
                item["last_error"] = error
                remaining.append(item)
                result["failed"] += 1
                result["errors"].append(error)
                logger.warning("Sync failed for %s: %s", mutation_type, error)

        self._queue = remaining
        self._save_queue()
        result["pending"] = len(remaining)

        logger.info(
            "Sync complete: %d synced, %d failed, %d pending",
            result["synced"], result["failed"], result["pending"],
        )
        return result

    def check_connectivity(self) -> bool:
        """
        Check if AppSync endpoint is reachable.
        Returns True if online, False if offline.
        """
        if not self.appsync_endpoint or "your-appsync" in self.appsync_endpoint:
            logger.debug("AppSync endpoint not configured")
            return False

        try:
            # Simple POST with empty query to test connectivity
            resp = self.session.post(
                self.appsync_endpoint,
                json={"query": "{ __typename }"},
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.appsync_api_key,
                },
                timeout=self.CONNECTIVITY_TIMEOUT,
            )
            # Any response (even GraphQL errors) means we're connected
            return resp.status_code in (200, 400, 401, 403)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return False
        except Exception as e:
            logger.debug("Connectivity check failed: %s", e)
            return False

    @property
    def queue_size(self) -> int:
        """Number of pending sync items."""
        return len(self._queue)

    @property
    def sync_status(self) -> str:
        """Human-readable sync status."""
        if not self._queue:
            return "synced"
        return f"{len(self._queue)} pending"

    def get_queue_summary(self) -> Dict:
        """Return summary of pending sync items."""
        quiz_count = sum(1 for i in self._queue if i["mutation_type"] == "recordQuizAttempt")
        streak_count = sum(1 for i in self._queue if i["mutation_type"] == "updateStreak")
        oldest = self._queue[0]["queued_at"] if self._queue else None
        return {
            "total": len(self._queue),
            "quiz_attempts": quiz_count,
            "streak_updates": streak_count,
            "oldest_item": oldest,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # INTERNAL — GraphQL Mutations
    # ═══════════════════════════════════════════════════════════════════════

    def _execute_mutation(self, mutation_type: str, variables: Dict) -> tuple:
        """
        Execute a single GraphQL mutation against AppSync.
        Returns (success: bool, error_message: str).
        """
        if mutation_type == "recordQuizAttempt":
            mutation = """
            mutation RecordQuizAttempt(
              $userId: String!,
              $quizId: String!,
              $score: Int!,
              $totalQuestions: Int!,
              $subject: String,
              $difficulty: String,
              $deviceId: String,
              $completedAtLocal: String
            ) {
              recordQuizAttempt(
                userId: $userId,
                quizId: $quizId,
                score: $score,
                totalQuestions: $totalQuestions,
                subject: $subject,
                difficulty: $difficulty,
                deviceId: $deviceId,
                completedAtLocal: $completedAtLocal
              ) {
                attemptId
                userId
                quizId
                score
                totalQuestions
                accuracyPercentage
                syncedAt
              }
            }
            """
        elif mutation_type == "updateStreak":
            mutation = """
            mutation UpdateStreak($userId: String!, $currentStreak: Int!) {
              updateStreak(userId: $userId, currentStreak: $currentStreak) {
                userId
                currentStreak
                syncedAt
              }
            }
            """
        else:
            return False, f"Unknown mutation type: {mutation_type}"

        try:
            resp = self.session.post(
                self.appsync_endpoint,
                json={"query": mutation, "variables": variables},
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.appsync_api_key,
                },
                timeout=15,
            )

            if resp.status_code == 200:
                body = resp.json()
                if "errors" in body:
                    error_msg = body["errors"][0].get("message", "Unknown GraphQL error")
                    return False, f"GraphQL error: {error_msg}"
                return True, ""
            else:
                return False, f"HTTP {resp.status_code}: {resp.text[:200]}"

        except requests.exceptions.Timeout:
            return False, "Request timed out (15s)"
        except requests.exceptions.ConnectionError:
            return False, "Connection lost during sync"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    # ═══════════════════════════════════════════════════════════════════════
    # INTERNAL — Queue Persistence
    # ═══════════════════════════════════════════════════════════════════════

    def _load_queue(self) -> List[Dict]:
        """Load sync queue from disk."""
        if not self.queue_path.exists():
            return []
        try:
            with open(self.queue_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("Failed to load sync queue: %s", e)
            return []

    def _save_queue(self):
        """Persist sync queue to disk (atomic write)."""
        try:
            tmp = self.queue_path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._queue, f, indent=2, ensure_ascii=False)
            tmp.replace(self.queue_path)
        except IOError as e:
            logger.error("Failed to save sync queue: %s", e)


# ── Standalone test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print("Testing SyncManager...")

    sm = SyncManager(base_path=".")

    # Queue some test mutations
    sm.enqueue_quiz_sync(
        user_id="student_001",
        quiz_id="quiz_test_001",
        score=8,
        total_questions=10,
        subject="Mathematics",
    )
    sm.enqueue_streak_sync(user_id="student_001", current_streak=5)

    print(f"Queue size: {sm.queue_size}")
    print(f"Queue summary: {sm.get_queue_summary()}")
    print(f"Connectivity: {sm.check_connectivity()}")

    # Try sync (will fail if no endpoint configured)
    result = sm.try_sync()
    print(f"Sync result: {result}")
