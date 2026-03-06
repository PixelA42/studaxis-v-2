"""
Studaxis — Quiz Generation Lambda (API Gateway → Bedrock)
═══════════════════════════════════════════════════════════
Purpose:
    REST API backend for teacher quiz generation.
    Receives requests from API Gateway, invokes Amazon Bedrock,
    returns structured quiz JSON.

Trigger:  API Gateway REST (POST /generateQuiz, POST /generateNotes)
IAM:      bedrock:InvokeModel
Timeout:  30 seconds (Bedrock inference can be slow)
Memory:   512 MB
"""

import os
import json
import re
import logging
from datetime import datetime, timezone

import boto3

# ── Config ──────────────────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "ap-south-1")
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "arn:aws:bedrock:ap-south-1:718980965213:inference-profile/global.amazon.nova-2-lite-v1:0",
)

logger = logging.getLogger("studaxis.quiz_generation")
logger.setLevel(LOG_LEVEL)

# Reuse client across warm invocations
bedrock_runtime = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _invoke_bedrock(system_prompt: str, user_prompt: str, max_tokens: int = 2000, temperature: float = 0.4) -> str:
    """Call Bedrock via Converse API and return raw text."""
    response = bedrock_runtime.converse(
        modelId=BEDROCK_MODEL_ID,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": user_prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
    return response["output"]["message"]["content"][0]["text"].strip()


def _parse_json(raw: str) -> dict:
    """Extract JSON from model response (handles code fences)."""
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        return json.loads(fence.group(1).strip())
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        return json.loads(raw[start : end + 1])
    return json.loads(raw)


def _cors_response(status_code: int, body: dict) -> dict:
    """Return API Gateway-compatible response with CORS headers."""
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


# ── Quiz Generation ────────────────────────────────────────────────────────

def _generate_quiz(topic: str, difficulty: str, num_questions: int) -> dict:
    """Generate a structured quiz via Bedrock."""
    system_prompt = """You are an expert educator creating quizzes for students.
Output ONLY a raw JSON object. Do NOT use markdown, code fences, backticks, or any explanation.
Start your response with { and end with }.
Required format:
{
    "quiz_title": "string",
    "topic": "string",
    "difficulty": "string",
    "questions": [
        {
            "question": "string",
            "question_type": "mcq",
            "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
            "correct_answer": "A. ...",
            "answer": "A. ...",
            "explanation": "string"
        }
    ]
}"""

    user_prompt = (
        f"Create a {difficulty} difficulty {num_questions}-question multiple-choice quiz about: {topic}. "
        f"Each question must have exactly 4 options labeled A, B, C, D. "
        f"The 'answer' field must be the full correct option text (e.g. 'A. Paris'). "
        f"Include a one-sentence explanation for each correct answer."
    )

    raw = _invoke_bedrock(system_prompt, user_prompt, max_tokens=2000, temperature=0.4)
    return _parse_json(raw)


# ── Lesson Summary Generation ──────────────────────────────────────────────

def _generate_notes(topic: str, grade_level: str) -> dict:
    """Generate study notes via Bedrock."""
    system_prompt = """You are an expert educator writing concise study notes for students.
Output ONLY a raw JSON object. Do NOT use markdown, code fences, backticks, or any explanation.
Start your response with { and end with }.
Required format:
{
    "title": "string",
    "grade_level": "string",
    "key_concepts": ["concept1", "concept2", "concept3"],
    "summary": "string (2-3 short paragraphs)",
    "fun_fact": "string"
}"""

    user_prompt = (
        f"Create concise study notes about '{topic}' for {grade_level} students. "
        f"Include 4-6 key concepts, a 2-3 paragraph summary, and one interesting fun fact."
    )

    raw = _invoke_bedrock(system_prompt, user_prompt, max_tokens=1500, temperature=0.5)
    return _parse_json(raw)


# ── Lambda Entry Point ─────────────────────────────────────────────────────

def lambda_handler(event, context):
    """
    API Gateway REST handler. Routes by path:
      POST /generateQuiz   → quiz generation
      POST /generateNotes  → lesson summary generation
      OPTIONS /*           → CORS preflight

    Request body (JSON):
      /generateQuiz:  { "topic": str, "difficulty": str, "num_questions": int }
      /generateNotes: { "topic": str, "grade_level": str }
    """
    logger.info("Event: %s", json.dumps(event, default=str))

    # Handle CORS preflight
    http_method = event.get("httpMethod", "")
    if http_method == "OPTIONS":
        return _cors_response(200, {"message": "CORS OK"})

    # Parse path
    path = event.get("path", event.get("resource", ""))
    logger.info("Path: %s, Method: %s", path, http_method)

    # Parse body
    try:
        body = json.loads(event.get("body", "{}") or "{}")
    except json.JSONDecodeError:
        return _cors_response(400, {"error": "Invalid JSON body"})

    try:
        if path.endswith("/generateQuiz"):
            topic = body.get("topic", "").strip()
            difficulty = body.get("difficulty", "medium").strip()
            num_questions = int(body.get("num_questions", 3))

            if not topic:
                return _cors_response(400, {"error": "Missing required field: topic"})
            if num_questions < 1 or num_questions > 10:
                return _cors_response(400, {"error": "num_questions must be 1-10"})

            logger.info("Generating quiz: topic=%s, difficulty=%s, n=%d", topic, difficulty, num_questions)
            quiz = _generate_quiz(topic, difficulty, num_questions)
            quiz["generated_at"] = datetime.now(timezone.utc).isoformat()
            quiz["model"] = BEDROCK_MODEL_ID

            return _cors_response(200, quiz)

        elif path.endswith("/generateNotes"):
            topic = body.get("topic", "").strip()
            grade_level = body.get("grade_level", "Grade 10").strip()

            if not topic:
                return _cors_response(400, {"error": "Missing required field: topic"})

            logger.info("Generating notes: topic=%s, grade=%s", topic, grade_level)
            notes = _generate_notes(topic, grade_level)
            notes["generated_at"] = datetime.now(timezone.utc).isoformat()

            return _cors_response(200, notes)

        else:
            return _cors_response(404, {"error": f"Unknown path: {path}"})

    except json.JSONDecodeError as e:
        logger.error("Bedrock returned non-JSON: %s", e)
        return _cors_response(502, {"error": f"AI model returned invalid response: {e}"})
    except Exception as e:
        logger.error("Generation error: %s", e, exc_info=True)
        return _cors_response(500, {"error": f"Internal error: {str(e)}"})
