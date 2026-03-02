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
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

# ── Config ──────────────────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
SYNC_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "studaxis-student-sync")
QUIZ_INDEX_TABLE = os.environ.get("QUIZ_INDEX_TABLE", "studaxis-quiz-index")
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "studaxis-payloads")
PRESIGNED_EXPIRY = int(os.environ.get("PRESIGNED_URL_EXPIRY_SECONDS", "3600"))  # 1 hour

logger = logging.getLogger("studaxis.content_distribution")
logger.setLevel(LOG_LEVEL)

# Initialise outside handler for connection reuse across warm invocations
dynamodb = boto3.resource("dynamodb")
sync_table = dynamodb.Table(SYNC_TABLE_NAME)
quiz_index = dynamodb.Table(QUIZ_INDEX_TABLE)
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

def _fetch_quizzes(subject: str, cid: str) -> list:
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


def _build_manifest(quizzes: list, user_id: str, cid: str) -> dict:
    """
    Build a lightweight content manifest the student app caches locally.
    Heavy payloads are referenced by pre-signed URL, not inlined.
    """
    manifest = {
        "manifestId": uuid.uuid4().hex[:16],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "userId": user_id,
        "totalItems": len(quizzes),
        "presignedUrlExpirySeconds": PRESIGNED_EXPIRY,
        "quizzes": quizzes,
    }

    logger.info(
        "[%s] Manifest built — %d items, ~%.1f KB",
        cid,
        len(quizzes),
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
        "subject": "Mathematics"   // optional, defaults to "All"
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

        if field == "fetchOfflineContent":
            # Check last sync to log delta info
            last_sync = _get_last_sync_timestamp(user_id, cid)
            if last_sync:
                logger.info("[%s] Last sync for %s: %s", cid, user_id, last_sync)

            # Query DynamoDB index (fast, filtered) then pre-sign URLs
            quizzes = _fetch_quizzes(subject, cid)
            enriched = _enrich_with_urls(quizzes, cid)
            manifest = _build_manifest(enriched, user_id, cid)

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
