"""
Studaxis — Teacher Generate Notes Lambda (API Gateway → Bedrock → S3 → DynamoDB)
═══════════════════════════════════════════════════════════════════════════════
Purpose:
    Handles notes generation from the Teacher Dashboard. On request:
    1. Checks S3 for existing notes (s3://studaxis-payloads/notes/{class_id}/{topic}.json)
    2. If exists → returns existing URL (saves Bedrock costs)
    3. If not → invokes Bedrock, saves to S3, creates DynamoDB assignment record
    4. Returns S3 URL and generated markdown to the frontend

Payload: subject, topic, source_material, note_style, target_class_id

Trigger:  API Gateway REST (POST /generateNotes or POST /teacher/generateNotes)
IAM:      bedrock:InvokeModel, s3:GetObject, s3:PutObject, s3:HeadObject,
          dynamodb:PutItem on studaxis-content-distribution
Timeout:  60 seconds (Bedrock inference can be slow)
Memory:   512 MB
"""

import os
import json
import re
import logging
from datetime import datetime, timezone
from urllib.parse import quote

import boto3
from botocore.exceptions import ClientError

# ── Config ──────────────────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "studaxis-payloads")
CONTENT_TABLE = os.environ.get("CONTENT_DISTRIBUTION_TABLE", "studaxis-content-distribution")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "ap-south-1")
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "arn:aws:bedrock:ap-south-1:718980965213:inference-profile/global.amazon.nova-2-lite-v1:0",
)
PRESIGNED_EXPIRY = int(os.environ.get("PRESIGNED_URL_EXPIRY_SECONDS", "86400"))  # 24h

logger = logging.getLogger("studaxis.teacher_generate_notes")
logger.setLevel(LOG_LEVEL)

s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
bedrock_runtime = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _slugify(topic: str) -> str:
    """Convert topic to safe S3 key segment (alphanumeric, hyphens)."""
    s = re.sub(r"[^\w\s-]", "", topic)
    s = re.sub(r"[-\s]+", "-", s).strip().lower()
    return s or "notes"


def _s3_key(target_class_id: str, topic: str) -> str:
    """S3 key for notes: notes/{class_id}/{topic}.json"""
    slug = _slugify(topic)
    return f"notes/{target_class_id}/{slug}.json"


def _s3_exists(bucket: str, key: str) -> bool:
    """Check if object exists in S3."""
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise


def _presigned_url(key: str) -> str:
    """Generate pre-signed download URL."""
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET_NAME, "Key": key},
        ExpiresIn=PRESIGNED_EXPIRY,
    )


def _invoke_bedrock(system_prompt: str, user_prompt: str, max_tokens: int = 4000, temperature: float = 0.5) -> str:
    """Call Bedrock Converse API and return raw text."""
    response = bedrock_runtime.converse(
        modelId=BEDROCK_MODEL_ID,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": user_prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
    return response["output"]["message"]["content"][0]["text"].strip()


def _generate_notes_bedrock(subject: str, topic: str, source_material: str, note_style: str) -> str:
    """Generate structured study notes via Bedrock. Returns Markdown string."""
    style_instructions = {
        "summary": "Write concise summary notes with bullet points. Include key definitions and 2–3 main takeaways.",
        "detailed": "Write a detailed explanation with sections, subheadings, and step-by-step reasoning where applicable.",
        "revision": "Write a revision sheet format: short headings, bullet points, key formulas and facts. Optimize for quick review.",
        "flashcard": "Write in flashcard-style format: each concept as a Q&A pair. Use clear 'Q:' and 'A:' labels.",
        "mindmap": "Write a mind map outline with a central topic, main branches, and sub-branches. Use indentation to show hierarchy.",
    }
    style_guide = style_instructions.get(note_style, style_instructions["summary"])

    system_prompt = """You are an expert educator creating study notes for students.
Output ONLY valid Markdown. Do NOT wrap in code fences or backticks.
Use clear headings (##), bullet points, and structured sections.
Be accurate and syllabus-aligned. Include key formulas and definitions where relevant."""

    context = f"Subject: {subject}\nTopic: {topic}\nFormat: {style_guide}"
    if source_material and source_material.strip():
        context += f"\n\nSource material (use this to ground your content):\n{source_material[:8000]}"
    else:
        context += "\n\nNo source material provided — generate comprehensive notes from your knowledge."

    user_prompt = f"Create study notes with this context:\n\n{context}"

    raw = _invoke_bedrock(system_prompt, user_prompt, max_tokens=4000, temperature=0.5)
    # Ensure we have valid markdown (Bedrock sometimes wraps in fences)
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:markdown|md)?\s*\n?", "", raw)
        raw = re.sub(r"\n?```\s*$", "", raw)
    return raw.strip()


def _put_dynamodb_assignment(class_id: str, topic: str, s3_uri: str, subject: str, note_style: str) -> None:
    """Create record in studaxis-content-distribution for AppSync to notify student devices."""
    table = dynamodb.Table(CONTENT_TABLE)
    now = datetime.now(timezone.utc).isoformat()
    topic_slug = _slugify(topic)
    content_id = f"notes#{topic_slug}#{now.replace(':', '-').replace('.', '-')}"

    item = {
        "class_id": class_id,
        "content_id": content_id,
        "content_type": "notes",
        "topic": topic,
        "subject": subject,
        "note_style": note_style,
        "s3_uri": s3_uri,
        "created_at": now,
    }
    table.put_item(Item=item)
    logger.info("Created DynamoDB assignment: class_id=%s, content_id=%s", class_id, content_id)


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


# ── Main Handler ──────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    """
    API Gateway REST handler for notes generation.

    Path: POST /generateNotes or POST /teacher/generateNotes

    Request body (JSON):
    {
        "subject": "Physics",
        "topic": "Laws of Thermodynamics",
        "source_material": "Pasted text or empty",
        "note_style": "summary|detailed|revision|flashcard|mindmap",
        "target_class_id": "ABC123"
    }

    Response:
    {
        "s3_url": "https://...",
        "generated_text": "## Notes...",
        "from_cache": false
    }
    """
    logger.info("Event: %s", json.dumps(event, default=str))

    # CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return _cors_response(200, {"message": "CORS OK"})

    try:
        body = json.loads(event.get("body", "{}") or "{}")
    except json.JSONDecodeError:
        return _cors_response(400, {"error": "Invalid JSON body"})

    subject = (body.get("subject") or "General").strip()
    topic = (body.get("topic") or "").strip()
    source_material = (body.get("source_material") or "").strip()
    note_style = (body.get("note_style") or "summary").strip()
    target_class_id = (body.get("target_class_id") or "").strip()

    if not topic:
        return _cors_response(400, {"error": "Missing required field: topic"})
    if not target_class_id:
        return _cors_response(400, {"error": "Missing required field: target_class_id"})

    key = _s3_key(target_class_id, topic)
    from_cache = False

    # ── S3 Check: return existing if present ──────────────────────────────────
    if _s3_exists(BUCKET_NAME, key):
        logger.info("Notes already exist at s3://%s/%s — returning URL", BUCKET_NAME, key)
        s3_url = _presigned_url(key)
        try:
            obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
            data = json.loads(obj["Body"].read().decode())
            generated_text = data.get("generated_text", data.get("content", ""))
        except Exception as e:
            logger.warning("Could not read existing notes content: %s", e)
            generated_text = ""
        return _cors_response(200, {
            "s3_url": s3_url,
            "generated_text": generated_text,
            "from_cache": True,
        })

    # ── Bedrock Generation ───────────────────────────────────────────────────
    logger.info("Generating notes via Bedrock: topic=%s, style=%s", topic, note_style)
    generated_text = _generate_notes_bedrock(subject, topic, source_material, note_style)

    # ── S3 Storage ───────────────────────────────────────────────────────────
    payload = {
        "subject": subject,
        "topic": topic,
        "note_style": note_style,
        "generated_text": generated_text,
        "target_class_id": target_class_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=json.dumps(payload, indent=2),
        ContentType="application/json",
    )
    s3_uri = f"s3://{BUCKET_NAME}/{key}"
    s3_url = _presigned_url(key)

    # ── DynamoDB Assignment ──────────────────────────────────────────────────
    try:
        _put_dynamodb_assignment(target_class_id, topic, s3_uri, subject, note_style)
    except ClientError as e:
        logger.warning("DynamoDB PutItem failed (assignment record): %s", e)
        # Do not fail the request — notes are in S3, assignment can be retried

    return _cors_response(200, {
        "s3_url": s3_url,
        "generated_text": generated_text,
        "from_cache": False,
    })
