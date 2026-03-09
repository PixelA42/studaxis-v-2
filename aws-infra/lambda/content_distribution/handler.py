"""
Studaxis — Content Distribution Lambda (AppSync Resolver)
══════════════════════════════════════════════════════════
Purpose:
    When a student has a brief connectivity window, they hit this
    function to download upcoming curriculum.  It queries the
    studaxis-quiz-index DynamoDB table (lightweight metadata written
    by bedrock-quiz-generator), generates time-limited Pre-signed
    S3 URLs for the full quiz JSONs, and returns a manifest the
    student app can cache locally.

    DynamoDB query = ~10ms.  No S3 file reads needed for discovery.

Trigger:  AWS AppSync GraphQL query  (e.g. `fetchOfflineContent`)
IAM:      dynamodb:GetItem on studaxis-student-sync,
          dynamodb:Query/Scan on studaxis-quiz-index,
          s3:GetObject on studaxis-payloads (pre-signing only)
Timeout:  15 seconds
Memory:   256 MB
"""

import os
import json
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

# ── Config ──────────────────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
SYNC_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "studaxis-student-sync")
QUIZ_INDEX_TABLE = os.environ.get("QUIZ_INDEX_TABLE", "studaxis-quiz-index")
CONTENT_TABLE_NAME = os.environ.get("CONTENT_DISTRIBUTION_TABLE", "studaxis-content-distribution")
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "studaxis-payloads")
PRESIGNED_EXPIRY = int(os.environ.get("PRESIGNED_URL_EXPIRY_SECONDS", "3600"))  # 1 hour

logger = logging.getLogger("studaxis.content_distribution")
logger.setLevel(LOG_LEVEL)

# Initialise outside handler for connection reuse across warm invocations
dynamodb = boto3.resource("dynamodb")
sync_table = dynamodb.Table(SYNC_TABLE_NAME)  # type: ignore
quiz_index = dynamodb.Table(QUIZ_INDEX_TABLE)  # type: ignore
content_table = dynamodb.Table(CONTENT_TABLE_NAME)  # type: ignore
s3_client = boto3.client("s3")


# ── Helpers ─────────────────────────────────────────────────────────────────

def _correlation_id() -> str:
    return uuid.uuid4().hex[:12]


def _presigned_url(s3_key: str) -> str:
    """Generate a time-limited download URL for the student app."""
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET_NAME, "Key": s3_key},
        ExpiresIn=PRESIGNED_EXPIRY,
    )


def _decimal_to_native(obj):
    """Convert DynamoDB Decimal values to int/float for JSON serialisation."""
    if isinstance(obj, Decimal):
        return int(obj) if obj == int(obj) else float(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_native(i) for i in obj]
    return obj


def _list_student_progresses(class_code: str | None, limit: int, next_token: str | None, cid: str) -> dict:
    """
    Scan studaxis-student-sync for student aggregates, filter by class_code.
    Hackathon: Scan + FilterExpression (no GSI). Excludes quiz_attempt rows.
    Solo learners (class_code=SOLO) never appear in teacher view.
    """
    if not class_code or not str(class_code).strip():
        logger.info("[%s] listStudentProgresses: no class_code — returning [] (teacher must provide)", cid)
        return {"items": [], "nextToken": None}

    scan_kwargs = {
        "FilterExpression": Attr("class_code").eq(str(class_code).strip()) & (
            Attr("record_type").not_exists() | Attr("record_type").ne("quiz_attempt")
        ),
        "Limit": min(limit or 100, 200),
    }
    if next_token:
        scan_kwargs["ExclusiveStartKey"] = json.loads(next_token)

    resp = sync_table.scan(**scan_kwargs)
    items = resp.get("Items", [])
    next_key = resp.get("LastEvaluatedKey")

    # Map to StudentProgress shape
    result = []
    for it in items:
        result.append({
            "user_id": it.get("user_id"),
            "current_streak": int(it.get("current_streak", 0)) if it.get("current_streak") is not None else 0,
            "device_id": it.get("device_id"),
            "last_quiz_date": it.get("last_quiz_date"),
            "last_sync_timestamp": it.get("last_sync_timestamp") or "",
            "class_code": it.get("class_code"),
        })
    return {
        "items": [_decimal_to_native(r) for r in result],
        "nextToken": json.dumps(next_key) if next_key else None,
    }


def _get_last_sync_timestamp(user_id: str, cid: str) -> str | None:
    """Look up when this student last synced so we can send only new content."""
    try:
        resp = sync_table.get_item(Key={"user_id": user_id})
        item = resp.get("Item")
        if item:
            return item.get("last_sync_timestamp")
    except ClientError as e:
        logger.warning("[%s] Could not read sync table: %s", cid, e)
    return None


# ── Core: DynamoDB-Based Quiz Discovery ────────────────────────────────────

def _fetch_quizzes(subject: str, cid: str, class_id: str | None = None, class_code: str | None = None) -> list:
    """
    Query the quiz index table.  Filters by subject at the DB layer
    so we never pull unnecessary data.
    """
    logger.info("[%s] Querying quiz index — subject=%s", cid, subject)

    scan_kwargs = {}
    if subject and subject.lower() != "all":
        scan_kwargs["FilterExpression"] = Attr("subject").eq(subject)

    response = quiz_index.scan(**scan_kwargs)
    items = response.get("Items", [])

    # Handle pagination
    while "LastEvaluatedKey" in response:
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        response = quiz_index.scan(**scan_kwargs)
        items.extend(response.get("Items", []))

    logger.info("[%s] Found %d quizzes in index", cid, len(items))
    return items


def _enrich_with_urls(quizzes: list, cid: str) -> list:
    """
    Attach a pre-signed S3 download URL to each quiz entry.
    No file reads — just signing the key that's already in the index row.
    """
    enriched = []
    for quiz in quizzes:
        s3_key = quiz.get("s3_key", "")
        if not s3_key:
            logger.warning("[%s] Quiz %s has no s3_key, skipping", cid, quiz.get("quiz_id"))
            continue

        try:
            quiz["offlineQuizUrl"] = _presigned_url(s3_key)
        except ClientError:
            quiz["offlineQuizUrl"] = None

        enriched.append(_decimal_to_native(quiz))

    return enriched


def _fetch_notes_for_class(class_id_or_code: str | None, cid: str) -> list:
    """
    Query studaxis-content-distribution for notes assigned to this class.
    Uses class_id (or class_code for legacy) as partition key.
    """
    if not class_id_or_code or not str(class_id_or_code).strip():
        return []
    key = str(class_id_or_code).strip()
    try:
        resp = content_table.query(KeyConditionExpression=Key("class_id").eq(key))
        items = resp.get("Items", [])
        while "LastEvaluatedKey" in resp:
            resp = content_table.query(
                KeyConditionExpression=Key("class_id").eq(key),
                ExclusiveStartKey=resp["LastEvaluatedKey"],
            )
            items.extend(resp.get("Items", []))
        out = []
        for it in items:
            s3_uri = it.get("s3_uri", "")
            if s3_uri:
                try:
                    # s3_uri may be s3://bucket/key or full URL
                    if s3_uri.startswith("s3://"):
                        parts = s3_uri.replace("s3://", "").split("/", 1)
                        bucket = parts[0] if len(parts) > 0 else BUCKET_NAME
                        key_path = parts[1] if len(parts) > 1 else ""
                    else:
                        bucket, key_path = BUCKET_NAME, s3_uri
                    presigned = s3_client.generate_presigned_url(
                        "get_object",
                        Params={"Bucket": bucket, "Key": key_path},
                        ExpiresIn=PRESIGNED_EXPIRY,
                    )
                except ClientError:
                    presigned = None
            else:
                presigned = None
            out.append(_decimal_to_native({
                "content_id": it.get("content_id"),
                "content_type": it.get("content_type", "notes"),
                "topic": it.get("topic"),
                "subject": it.get("subject"),
                "s3_uri": s3_uri,
                "presigned_url": presigned,
            }))
        logger.info("[%s] Found %d notes for class %s", cid, len(out), key)
        return out
    except ClientError as e:
        logger.warning("[%s] Content-distribution query failed: %s", cid, e)
        return []


def _build_manifest(quizzes: list, user_id: str, cid: str, notes: list | None = None) -> dict:
    """
    Build a lightweight content manifest the student app caches locally.
    Heavy payloads are referenced by pre-signed URL, not inlined.
    """
    notes_list = notes if notes is not None else []
    manifest = {
        "manifestId": uuid.uuid4().hex[:16],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "userId": user_id,
        "totalItems": len(quizzes) + len(notes_list),
        "presignedUrlExpirySeconds": PRESIGNED_EXPIRY,
        "quizzes": quizzes,
        "notes": notes_list,
    }

    logger.info(
        "[%s] Manifest built — %d quizzes, %d notes, ~%.1f KB",
        cid,
        len(quizzes),
        len(notes_list),
        len(json.dumps(manifest, default=str)) / 1024,
    )
    return manifest


# ── Lambda Entry Point ─────────────────────────────────────────────────────

def lambda_handler(event, context):
    """
    AppSync resolver entry point.

    Supported field names (event['info']['fieldName']):
      • fetchOfflineContent  — query quiz index + pre-signed URLs

    AppSync event shape:
    {
      "info": { "fieldName": "fetchOfflineContent" },
      "arguments": {
        "userId":  "student_001",
        "subject": "Mathematics",   // optional, defaults to "All"
        "class_id": "uuid-...",     // optional, filters content for student's class
        "class_code": "ABC123"      // optional, fallback when class_id not set (legacy)
      }
    }
    """
    cid = _correlation_id()
    logger.info("[%s] Content Distribution Lambda invoked", cid)
    logger.info("[%s] Event: %s", cid, json.dumps(event, default=str))

    try:
        field = event.get("info", {}).get("fieldName", "fetchOfflineContent")
        args = event.get("arguments", {})
        user_id = str(args.get("userId", "anonymous")).strip()
        subject = str(args.get("subject", "All")).strip()
        class_id = (args.get("class_id") or "").strip() or None
        class_code = (args.get("class_code") or args.get("classCode") or "").strip() or None

        if field == "fetchOfflineContent":
            # Check last sync to log delta info
            last_sync = _get_last_sync_timestamp(user_id, cid)
            if last_sync:
                logger.info("[%s] Last sync for %s: %s", cid, user_id, last_sync)

            # Query DynamoDB index (fast, filtered) then pre-sign URLs
            # class_id/class_code passed for future per-class filtering; quiz index may not have class yet
            quizzes = _fetch_quizzes(subject, cid, class_id=class_id, class_code=class_code)
            # Fetch notes for this class from content-distribution table
            notes = _fetch_notes_for_class(class_id or class_code, cid)
            enriched = _enrich_with_urls(quizzes, cid)
            manifest = _build_manifest(enriched, user_id, cid, notes=notes)

        elif field == "getQuizPresignedUrl":
            # Single quiz presigned URL lookup
            quiz_id = str(args.get("quizId", args.get("quiz_id", ""))).strip()
            logger.info("[%s] Looking up presigned URL for quiz_id=%s", cid, quiz_id)

            try:
                resp = quiz_index.get_item(Key={"quiz_id": quiz_id})
                item = resp.get("Item")
                if not item:
                    raise ValueError(f"Quiz not found: {quiz_id}")

                s3_key = item.get("s3_key", "")
                if not s3_key:
                    raise ValueError(f"Quiz {quiz_id} has no s3_key")

                presigned = _presigned_url(s3_key)
                return {
                    "quiz_id": quiz_id,
                    "presigned_url": presigned,
                    "expires_at": datetime.now(timezone.utc).isoformat(),
                }
            except ClientError as e:
                logger.error("[%s] DynamoDB error looking up %s: %s", cid, quiz_id, e)
                raise

        elif field == "listQuizzes":
            # List all quizzes in the index
            logger.info("[%s] Listing all quizzes for teacher dashboard", cid)
            quizzes = _fetch_quizzes("All", cid)
            return [_decimal_to_native(q) for q in quizzes]

        elif field == "listStudentProgresses":
            # Teacher dashboard: students filtered by class_code (Scan + FilterExpression)
            class_code = args.get("class_code") or args.get("classCode")
            limit = int(args.get("limit", 100))
            next_token = args.get("nextToken")
            logger.info("[%s] listStudentProgresses: class_code=%s", cid, class_code)
            return _list_student_progresses(class_code, limit, next_token, cid)

        else:
            raise ValueError(f"Unknown fieldName: {field}")

        logger.info("[%s] Returning manifest with %d items", cid, manifest["totalItems"])
        return manifest

    except ValueError as ve:
        logger.warning("[%s] Validation error: %s", cid, ve)
        raise Exception(f"ValidationError: {ve}")

    except ClientError as ce:
        error_code = ce.response["Error"]["Code"]
        logger.error("[%s] AWS error [%s]: %s", cid, error_code, ce)
        raise Exception(f"AWSError: {error_code}")

    except Exception as exc:
        logger.error("[%s] Unexpected error: %s", cid, exc, exc_info=True)
        raise
