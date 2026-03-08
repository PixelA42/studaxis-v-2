"""
Studaxis — AWS Sync (AppSync + S3 only, NO DynamoDB)

Architecture: SyncManager MUST NOT talk directly to DynamoDB.
- Lightweight deltas → AppSync GraphQL (recordQuizAttempt, updateStreak) → Lambda → DynamoDB
- Heavy payloads (>4KB) → boto3 upload to S3 → S3 event triggers offline_sync Lambda (if configured)

Flow:
  1. Lightweight: SyncManager sends GraphQL mutations to AppSync
  2. Heavy: Upload user_stats/chat logs to S3; include S3 key in metadata sync via AppSync where applicable
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("studaxis.aws_sync")

HEAVY_PAYLOAD_THRESHOLD_BYTES = 4096  # 4KB — use S3 for larger payloads


def _load_dotenv() -> None:
    """Load .env if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        base = Path(__file__).resolve().parent
        env_path = base / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass


def upload_heavy_payload_to_s3(
    base_path: Path,
    user_id: str,
    stats: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """
    Upload heavy payload (user_stats) to S3. S3 event triggers offline_sync Lambda.
    Returns S3 key on success, None on failure. Never raises.

    - base_path: backend root
    - user_id: student user id
    - stats: full user_stats dict; if None, loaded from data/users/{user_id}/user_stats.json
    """
    _load_dotenv()
    bucket = (os.getenv("S3_BUCKET_NAME") or os.getenv("AWS_S3_SYNC_BUCKET") or "").strip()
    region = os.getenv("AWS_REGION", "ap-south-1")

    if not bucket:
        logger.debug("S3 upload skipped: S3_BUCKET_NAME not set")
        return None

    if not user_id or user_id == "anonymous":
        logger.debug("S3 upload skipped: no user_id")
        return None

    try:
        import boto3
    except ImportError:
        logger.warning("boto3 not installed; S3 payload sync disabled")
        return None

    if stats is None:
        stats_path = base_path / "data" / "users" / user_id / "user_stats.json"
        if not stats_path.exists():
            logger.debug("No user_stats.json at %s", stats_path)
            return None
        try:
            with open(stats_path, encoding="utf-8") as f:
                stats = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to load user_stats: %s", e)
            return None

    if not isinstance(stats, dict):
        logger.warning("user_stats is not a dict")
        return None

    now = datetime.now(timezone.utc)

    # Lambda _write_student_aggregate_stats expects this format for S3 payload
    streak = 0
    if isinstance(stats.get("streak"), dict):
        streak = int(stats["streak"].get("current", 0) or 0)
    elif isinstance(stats.get("streak"), (int, float)):
        streak = int(stats["streak"])

    qs = stats.get("quiz_stats") or {}
    quiz_attempts = int(qs.get("total_attempted", 0)) if isinstance(qs, dict) else 0
    total_score = float(qs.get("total_score_sum", 0) or qs.get("average_score", 0) * quiz_attempts) if isinstance(qs, dict) else 0.0

    device_id = ""
    try:
        from device_id import get_or_generate_device_id
        device_id = get_or_generate_device_id() or ""
    except Exception:
        pass

    # Lambda-compatible payload for S3 trigger
    lambda_payload = {
        "student_id": user_id,
        "device_id": device_id or "unknown",
        "quiz_attempts": quiz_attempts,
        "total_score": total_score,
        "streak": streak,
        "last_sync": now.isoformat(),
    }
    # Also include full user_stats for downstream use (chat logs, etc.)
    lambda_payload["_full_user_stats"] = stats

    payload_bytes = json.dumps(lambda_payload, indent=2, ensure_ascii=False).encode("utf-8")

    # S3 key under sync/ prefix — Lambda S3 trigger listens here (if configured)
    s3_key = f"sync/students/{user_id}/user_stats_{now.strftime('%Y%m%d_%H%M%S')}.json"

    try:
        s3 = boto3.client("s3", region_name=region)
        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=payload_bytes,
            ContentType="application/json",
        )
        logger.info("Uploaded heavy payload to s3://%s/%s (%d bytes)", bucket, s3_key, len(payload_bytes))
        _update_local_last_sync(base_path, user_id, now.isoformat())
        return s3_key
    except Exception as e:
        logger.warning("S3 upload failed: %s", e)
        return None


def _update_local_last_sync(base_path: Path, user_id: str, timestamp: str) -> None:
    """Update last_sync_timestamp in user_stats.json. Never raises."""
    try:
        stats_path = base_path / "data" / "users" / user_id / "user_stats.json"
        if not stats_path.exists():
            return
        with open(stats_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data["last_sync_timestamp"] = timestamp
            tmp = stats_path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            tmp.replace(stats_path)
            logger.debug("Updated last_sync_timestamp for %s", user_id)
    except Exception as e:
        logger.debug("Could not update last_sync_timestamp: %s", e)


def is_payload_heavy(stats: dict[str, Any]) -> bool:
    """Return True if payload (e.g. chat_history) exceeds 4KB."""
    size = len(json.dumps(stats, ensure_ascii=False).encode("utf-8"))
    return size > HEAVY_PAYLOAD_THRESHOLD_BYTES
