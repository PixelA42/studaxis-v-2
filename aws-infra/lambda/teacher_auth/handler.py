"""
Studaxis — Teacher Auth Lambda (API Gateway → DynamoDB)
═══════════════════════════════════════════════════════════
Purpose:
    POST /auth — authenticates teacher by classCode (+ optional teacherId).
    Looks up teacher in DynamoDB, returns JWT + teacher object.
    Matches exact Login UI fields: classCode (required), teacherId (optional).

Trigger:  API Gateway REST POST /auth
IAM:      dynamodb:GetItem on studaxis-teachers
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone

import boto3
import jwt

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
TEACHERS_TABLE = os.environ.get("TEACHERS_TABLE_NAME", "studaxis-teachers")
JWT_SECRET = os.environ.get("STUDAXIS_JWT_SECRET", "studaxis-dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24 * 7  # 7 days

logger = logging.getLogger("studaxis.teacher_auth")
logger.setLevel(LOG_LEVEL)

dynamodb = boto3.resource("dynamodb")


def _cors_response(status_code: int, body: dict) -> dict:
    """API Gateway-compatible response with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(body, default=str),
    }


def _get_teacher(class_code: str) -> dict | None:
    """Look up teacher by classCode in DynamoDB. PK = classCode."""
    try:
        table = dynamodb.Table(TEACHERS_TABLE)
        cc = (class_code or "").strip().upper()
        resp = table.get_item(Key={"classCode": cc})
        return resp.get("Item")
    except Exception as e:
        logger.error("DynamoDB get_item error: %s", e)
        return None


def _create_teacher_jwt(class_code: str, teacher_id: str) -> str:
    """Create JWT for authenticated teacher."""
    payload = {
        "sub": class_code,
        "classCode": class_code,
        "teacherId": teacher_id,
        "role": "teacher",
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def lambda_handler(event, context):
    """
    POST /auth — body: { classCode: str, teacherId?: str }
    Returns: { access_token, token_type, teacher }
    """
    logger.info("Event: %s", json.dumps(event, default=str))

    if event.get("httpMethod") == "OPTIONS":
        return _cors_response(200, {"message": "CORS OK"})

    if event.get("httpMethod") != "POST":
        return _cors_response(405, {"error": "Method not allowed"})

    try:
        body = json.loads(event.get("body", "{}") or "{}")
    except json.JSONDecodeError:
        return _cors_response(400, {"error": "Invalid JSON body"})

    cc = (body.get("classCode") or "").strip().upper()
    teacher_id_input = (body.get("teacherId") or "").strip() or None

    if len(cc) < 3:
        return _cors_response(400, {"error": "classCode is required (min 3 chars)"})

    teacher = _get_teacher(cc)
    if not teacher:
        return _cors_response(401, {"error": "Class code not found"})

    teacher_id = teacher.get("teacherId") or teacher.get("classCode") or cc
    if teacher_id_input:
        if teacher.get("email", "").lower() == teacher_id_input.lower():
            teacher_id = teacher_id_input
        elif teacher.get("teacherId") == teacher_id_input:
            teacher_id = teacher_id_input
        else:
            teacher_id = teacher_id_input

    token = _create_teacher_jwt(cc, teacher_id)
    teacher_response = {
        "teacherId": teacher_id,
        "name": teacher.get("name", ""),
        "email": teacher.get("email", ""),
        "subject": teacher.get("subject", ""),
        "grade": teacher.get("grade", ""),
        "school": teacher.get("school", ""),
        "city": teacher.get("city", ""),
        "board": teacher.get("board", ""),
        "className": teacher.get("className", ""),
        "classCode": teacher.get("classCode", cc),
        "numStudents": teacher.get("numStudents", ""),
    }

    return _cors_response(
        200,
        {"access_token": token, "token_type": "bearer", "teacher": teacher_response},
    )
