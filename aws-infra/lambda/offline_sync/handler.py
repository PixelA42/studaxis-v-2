"""
Studaxis — Offline Sync Lambda (S3 Trigger + AppSync Resolver)
═══════════════════════════════════════════════════════════════
Purpose:
    Dual-mode handler:
    1. S3 TRIGGER: When student stats JSON uploaded to S3, auto-sync to DynamoDB
    2. AppSync API: Handle mutations like `recordQuizAttempt` from GraphQL

Triggers: S3 (sync/ folder, .json files) + AWS AppSync mutations
IAM:      s3:GetObject, dynamodb:PutItem, dynamodb:UpdateItem on studaxis-student-sync
Timeout:  10 seconds
Memory:   256 MB
"""

import os
import json
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# ── Config ──────────────────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE_NAME", "studaxis-student-sync")
S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "studaxis-payloads")

logger = logging.getLogger("studaxis.offline_sync")
logger.setLevel(LOG_LEVEL)

# Initialise outside handler for connection reuse across warm invocations
dynamodb = boto3.resource("dynamodb")
stats_table = dynamodb.Table(DYNAMODB_TABLE)
s3_client = boto3.client("s3")


# ── Helpers ─────────────────────────────────────────────────────────────────

def _correlation_id() -> str:
    """Generate a short correlation ID for CloudWatch tracing."""
    return uuid.uuid4().hex[:12]


def _decimal(value) -> Decimal:
    """DynamoDB requires Decimal for numbers — float is rejected."""
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def _validate_args(args: dict) -> dict | None:
    """
    Validate the AppSync mutation arguments.
    Returns cleaned dict on success, raises ValueError on failure.
    """
    required = ["userId", "quizId", "score", "totalQuestions"]
    missing = [f for f in required if f not in args or args[f] is None]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    total_q = int(args["totalQuestions"])
    score = int(args["score"])

    if total_q <= 0:
        raise ValueError("totalQuestions must be > 0")
    if score < 0:
        raise ValueError("score must be >= 0")
    if score > total_q:
        raise ValueError("score cannot exceed totalQuestions")

    return {
        "userId": str(args["userId"]).strip(),
        "quizId": str(args["quizId"]).strip(),
        "score": score,
        "totalQuestions": total_q,
        "subject": str(args.get("subject", "General")).strip(),
        "difficulty": str(args.get("difficulty", "Medium")).strip(),
        "deviceId": str(args.get("deviceId", "unknown")).strip(),
        "completedAtLocal": args.get("completedAtLocal"),  # ISO timestamp from device
    }


# ── Core Logic ──────────────────────────────────────────────────────────────

def _write_quiz_attempt(data: dict, cid: str) -> dict:
    """
    Write the quiz attempt record AND update the student's
    aggregate sync metadata in a single DynamoDB call (UpdateItem).
    """
    accuracy = round((data["score"] / data["totalQuestions"]) * 100, 2)
    now_iso = datetime.now(timezone.utc).isoformat()

    # ── 1. Write individual quiz attempt record ─────────────────────────
    attempt_id = f"{data['userId']}_{data['quizId']}_{int(datetime.now(timezone.utc).timestamp())}"

    attempt_item = {
        "user_id": attempt_id,          # partition key — composite ID keeps each attempt unique
        "record_type": "quiz_attempt",   # distinguishes from aggregate rows
        "userId": data["userId"],
        "quizId": data["quizId"],
        "score": _decimal(data["score"]),
        "totalQuestions": _decimal(data["totalQuestions"]),
        "accuracyPercentage": _decimal(accuracy),
        "subject": data["subject"],
        "difficulty": data["difficulty"],
        "deviceId": data["deviceId"],
        "completedAtLocal": data.get("completedAtLocal") or now_iso,
        "syncedAt": now_iso,
    }

    logger.info("[%s] Writing quiz attempt %s", cid, attempt_id)
    stats_table.put_item(Item=attempt_item)

    # ── 2. Update student aggregate row (upsert) ───────────────────────
    logger.info("[%s] Updating aggregate metadata for user %s", cid, data["userId"])
    stats_table.update_item(
        Key={"user_id": data["userId"]},
        UpdateExpression=(
            "SET last_sync_timestamp = :ts, "
            "    sync_status         = :synced, "
            "    device_id           = :dev, "
            "    last_quiz_score     = :score "
            "ADD total_sessions :one"
        ),
        ExpressionAttributeValues={
            ":ts": now_iso,
            ":synced": "synced",
            ":dev": data["deviceId"],
            ":score": _decimal(data["score"]),
            ":one": _decimal(1),
        },
    )

    return {
        "attemptId": attempt_id,
        "userId": data["userId"],
        "quizId": data["quizId"],
        "score": data["score"],
        "totalQuestions": data["totalQuestions"],
        "accuracyPercentage": accuracy,
        "syncedAt": now_iso,
    }


def _write_streak_update(args: dict, cid: str) -> dict:
    """
    Handle a dedicated streak sync mutation (e.g., student just logged in
    today, incrementing their streak without a quiz).
    """
    user_id = str(args.get("userId", "")).strip()
    streak = int(args.get("currentStreak", 0))
    if not user_id:
        raise ValueError("userId is required for streak update")

    now_iso = datetime.now(timezone.utc).isoformat()

    logger.info("[%s] Streak update for %s → %d", cid, user_id, streak)
    stats_table.update_item(
        Key={"user_id": user_id},
        UpdateExpression=(
            "SET current_streak       = :streak, "
            "    last_sync_timestamp  = :ts, "
            "    sync_status          = :synced"
        ),
        ExpressionAttributeValues={
            ":streak": _decimal(streak),
            ":ts": now_iso,
            ":synced": "synced",
        },
    )

    return {
        "userId": user_id,
        "currentStreak": streak,
        "syncedAt": now_iso,
    }


# ── S3 Trigger Handlers ─────────────────────────────────────────────────────

def _is_s3_event(event: dict) -> bool:
    """Check if event is an S3 trigger (has Records.s3 structure)."""
    return bool(event.get("Records") and event["Records"][0].get("s3"))


def _read_s3_object(bucket: str, key: str, cid: str) -> dict:
    """Read and parse JSON object from S3."""
    logger.info("[%s] Reading S3 object: s3://%s/%s", cid, bucket, key)
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        body = response["Body"].read().decode("utf-8")
        payload = json.loads(body)
        logger.info("[%s] S3 payload parsed successfully", cid)
        return payload
    except ClientError as e:
        logger.error("[%s] Failed to read S3 object: %s", cid, e)
        raise Exception(f"S3Error: Failed to read {key}")


def _write_student_aggregate_stats(payload: dict, cid: str) -> dict:
    """
    Process student stats from S3 and write aggregate record to DynamoDB.
    
    Expected S3 payload:
    {
      "student_id": "STU-001",
      "device_id": "DEV-001",
      "quiz_attempts": 5,
      "total_score": 85.5,
      "streak": 3,
      "last_sync": "2026-03-02T15:30:00Z"
    }
    """
    # Extract and validate fields
    student_id = str(payload.get("student_id", "")).strip()
    if not student_id:
        raise ValueError("student_id is required in S3 payload")

    device_id = str(payload.get("device_id", "unknown")).strip()
    quiz_attempts = int(payload.get("quiz_attempts", 0))
    total_score = float(payload.get("total_score", 0))
    streak = int(payload.get("streak", 0))
    last_sync = payload.get("last_sync") or datetime.now(timezone.utc).isoformat()

    now_iso = datetime.now(timezone.utc).isoformat()

    logger.info(
        "[%s] Writing student aggregate: student_id=%s, score=%.1f, streak=%d",
        cid, student_id, total_score, streak
    )

    # Write/update student aggregate record
    stats_table.put_item(
        Item={
            "user_id": student_id,              # partition key
            "record_type": "student_aggregate",   # distinguishes from quiz attempts
            "studentId": student_id,
            "deviceId": device_id,
            "quizAttempts": _decimal(quiz_attempts),
            "totalScore": _decimal(total_score),
            "currentStreak": _decimal(streak),
            "lastSyncDevice": last_sync,
            "syncedAt": now_iso,
            "syncStatus": "synced",
        }
    )

    # Also update aggregate metadata (for quick lookups)
    stats_table.update_item(
        Key={"user_id": student_id},
        UpdateExpression=(
            "SET sync_status           = :synced, "
            "    last_sync_timestamp   = :ts, "
            "    device_id             = :dev, "
            "    current_streak        = :streak, "
            "    total_quiz_attempts   = :attempts, "
            "    total_score           = :score "
        ),
        ExpressionAttributeValues={
            ":synced": "synced",
            ":ts": now_iso,
            ":dev": device_id,
            ":streak": _decimal(streak),
            ":attempts": _decimal(quiz_attempts),
            ":score": _decimal(total_score),
        },
    )

    return {
        "studentId": student_id,
        "deviceId": device_id,
        "quizAttempts": quiz_attempts,
        "totalScore": float(total_score),
        "currentStreak": streak,
        "syncedAt": now_iso,
        "syncStatus": "synced",
    }


# ── Lambda Entry Point ─────────────────────────────────────────────────────

def lambda_handler(event, context):
    """
    Dual-mode entry point: Handles S3 triggers AND AppSync mutations.

    TRIGGER 1: S3 Event (automatic)
      When student_stats.json uploaded to s3://bucket/sync/
      Event structure: {"Records": [{"s3": {"bucket": {...}, "object": {"key": "..."}}}]}

    TRIGGER 2: AppSync Mutation (API call)
      Supported field names (event['info']['fieldName']):
        • recordQuizAttempt  — sync a completed quiz from offline queue
        • updateStreak       — sync streak metadata only

      AppSync event shape:
      {
        "info": { "fieldName": "recordQuizAttempt" },
        "arguments": { "userId": "...", "quizId": "...", ... }
      }
    """
    cid = _correlation_id()
    logger.info("[%s] Offline Sync Lambda invoked", cid)
    logger.info("[%s] Event: %s", cid, json.dumps(event, default=str))

    try:
        # ── Detect S3 trigger ───────────────────────────────────────────────
        if _is_s3_event(event):
            logger.info("[%s] Detected S3 trigger", cid)
            record = event["Records"][0]
            bucket = record["s3"]["bucket"]["name"]
            key = record["s3"]["object"]["key"]
            
            # Read S3 object
            payload = _read_s3_object(bucket, key, cid)
            
            # Write to DynamoDB
            result = _write_student_aggregate_stats(payload, cid)
            
            logger.info("[%s] S3 sync complete: %s", cid, json.dumps(result, default=str))
            return result

        # ── Detect AppSync mutation ───────────────────────────────────────
        logger.info("[%s] Detected AppSync mutation", cid)
        field = event.get("info", {}).get("fieldName", "recordQuizAttempt")
        args = event.get("arguments", {})

        if field == "recordQuizAttempt":
            validated = _validate_args(args)
            result = _write_quiz_attempt(validated, cid)

        elif field == "updateStreak":
            result = _write_streak_update(args, cid)

        else:
            raise ValueError(f"Unknown fieldName: {field}")

        logger.info("[%s] AppSync mutation complete: %s", cid, json.dumps(result, default=str))
        return result

    except ValueError as ve:
        logger.warning("[%s] Validation error: %s", cid, ve)
        raise Exception(f"ValidationError: {ve}")

    except ClientError as ce:
        error_code = ce.response["Error"]["Code"]
        logger.error("[%s] DynamoDB error [%s]: %s", cid, error_code, ce)
        raise Exception(f"DatabaseError: {error_code}")

    except Exception as exc:
        logger.error("[%s] Unexpected error: %s", cid, exc, exc_info=True)
        raise

