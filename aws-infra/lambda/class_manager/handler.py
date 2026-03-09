"""
Studaxis — Class Manager Lambda (API Gateway → DynamoDB)
══════════════════════════════════════════════════════════
Purpose:
    Multi-class management for teachers. Handles:
    - create_class: Create new class, generate unique 6-char code
    - get_classes_for_teacher: List all classes for a teacher
    - verify_class_code: Validate student join code, return class info

Frontend contract (teacher-dashboard-web teacherApi.ts):
  - POST /classes  body: { teacher_id: string, class_name: string }  → 200 + { class_id, teacher_id, class_name, class_code, created_at }
  - GET  /classes?teacher_id=...  → 200 + { classes: [...] }
  - GET  /classes/verify?code=... → 200 + { class_id, class_name, class_code } or 404

DynamoDB Table: studaxis-classes
  - PK: class_id (UUID)
  - GSI: teacher_id-class_id (teacher_id as PK)
  - GSI: class_code (class_code as PK, for verify)

Trigger: API Gateway REST
IAM: dynamodb:PutItem, dynamodb:GetItem, dynamodb:Query
"""

import os
import json
import random
import string
import logging
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
TABLE_NAME = os.environ.get("CLASSES_TABLE_NAME", "studaxis-classes")

logger = logging.getLogger("studaxis.class_manager")
logger.setLevel(LOG_LEVEL)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def _generate_class_code() -> str:
    """Generate unique 6-character alphanumeric code (uppercase)."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=6))


def _ensure_unique_code(existing_codes: set[str]) -> str:
    """Generate code that doesn't collide. Max 10 attempts."""
    for _ in range(10):
        code = _generate_class_code()
        if code not in existing_codes:
            return code
    return _generate_class_code()  # fallback


def _cors_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST,GET,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(body, default=str),
    }


def create_class(teacher_id: str, class_name: str) -> dict:
    """Create a new class. Returns class object with class_id, class_code, etc."""
    teacher_id = (teacher_id or "").strip()
    class_name = (class_name or "").strip()
    if not teacher_id:
        raise ValueError("teacher_id is required")
    if not class_name:
        raise ValueError("class_name is required")

    # Fetch existing codes to avoid collision (scan by teacher_id)
    existing = set()
    try:
        scan_res = table.scan(
            FilterExpression="teacher_id = :tid",
            ExpressionAttributeValues={":tid": teacher_id},
            ProjectionExpression="class_code",
        )
        for item in scan_res.get("Items", []):
            if item.get("class_code"):
                existing.add(item["class_code"])
    except ClientError:
        pass

    class_id = str(uuid.uuid4())
    class_code = _ensure_unique_code(existing)
    now = datetime.now(timezone.utc).isoformat()

    item = {
        "class_id": class_id,
        "teacher_id": teacher_id,
        "class_name": class_name,
        "class_code": class_code,
        "created_at": now,
    }
    table.put_item(Item=item)

    logger.info("Created class class_id=%s class_code=%s teacher_id=%s", class_id, class_code, teacher_id)
    return item


def get_classes_for_teacher(teacher_id: str) -> list[dict]:
    """Return all classes for a teacher."""
    teacher_id = (teacher_id or "").strip()
    if not teacher_id:
        return []

    try:
        # Table has GSI teacher_id-created_at or we scan by teacher_id
        res = table.scan(
            FilterExpression="teacher_id = :tid",
            ExpressionAttributeValues={":tid": teacher_id},
        )
        items = res.get("Items", [])
        while "LastEvaluatedKey" in res:
            res = table.scan(
                FilterExpression="teacher_id = :tid",
                ExpressionAttributeValues={":tid": teacher_id},
                ExclusiveStartKey=res["LastEvaluatedKey"],
            )
            items.extend(res.get("Items", []))

        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items
    except ClientError as e:
        logger.error("get_classes_for_teacher error: %s", e)
        raise


def verify_class_code(class_code: str) -> dict | None:
    """Verify class code (from student). Returns class_id, class_name, class_code or None."""
    class_code = (class_code or "").strip().upper()
    if len(class_code) < 4:
        return None

    try:
        # Scan for class_code (or use GSI if available)
        res = table.scan(
            FilterExpression="class_code = :cc",
            ExpressionAttributeValues={":cc": class_code},
            Limit=1,
        )
        items = res.get("Items", [])
        if not items:
            return None
        item = items[0]
        return {
            "class_id": item.get("class_id"),
            "class_name": item.get("class_name"),
            "class_code": item.get("class_code"),
        }
    except ClientError as e:
        logger.error("verify_class_code error: %s", e)
        raise


def lambda_handler(event, context):
    """
    API Gateway REST handler (proxy integration).
    Event shape: httpMethod, path (e.g. /prod/classes or /classes), body (JSON string), queryStringParameters.

    Paths:
      POST /classes          — body: { teacher_id, class_name } → create_class
      GET  /classes?teacher_id=X — get_classes_for_teacher
      GET  /classes/verify?code=X — verify_class_code
      OPTIONS * — CORS
    """
    logger.info("Event: %s", json.dumps(event, default=str))

    if event.get("httpMethod") == "OPTIONS":
        return _cors_response(200, {"message": "CORS OK"})

    path = (event.get("path") or event.get("resource") or "").strip()
    method = event.get("httpMethod", "GET")

    # Normalize path: API Gateway may send /prod/classes or /classes
    path_lower = path.lower()
    is_classes_post = (
        method == "POST"
        and ("/classes" in path_lower or path_lower.endswith("/classes"))
        and "/verify" not in path_lower
    )

    try:
        if is_classes_post:
            raw_body = event.get("body") or "{}"
            if isinstance(raw_body, str):
                try:
                    body = json.loads(raw_body)
                except json.JSONDecodeError:
                    body = {}
            else:
                body = raw_body
            # Frontend sends snake_case; allow camelCase for flexibility
            teacher_id = (body.get("teacher_id") or body.get("teacherId") or "").strip()
            class_name = (body.get("class_name") or body.get("className") or "").strip()
            cls = create_class(teacher_id, class_name)
            return _cors_response(200, cls)

        if method == "GET":
            params = event.get("queryStringParameters") or {}
            if "code" in params or "class_code" in params:
                code = (params.get("code") or params.get("class_code") or "").strip().upper()
                result = verify_class_code(code)
                if result is None:
                    return _cors_response(404, {"error": "Class code not found"})
                return _cors_response(200, result)

            teacher_id = (params.get("teacher_id") or params.get("teacherId") or "").strip()
            if teacher_id:
                classes = get_classes_for_teacher(teacher_id)
                return _cors_response(200, {"classes": classes})

        return _cors_response(404, {"error": "Unknown route"})

    except ValueError as e:
        return _cors_response(400, {"error": str(e)})
    except ClientError as e:
        logger.error("DynamoDB error: %s", e)
        return _cors_response(500, {"error": "Database error"})
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return _cors_response(500, {"error": str(e)})
