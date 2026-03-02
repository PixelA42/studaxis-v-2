"""
Studaxis — AWS Bedrock Client
Real API calls to Amazon Nova Lite 2 for quiz and lesson content generation.
Uses the Bedrock Converse API — model-agnostic, works with Nova, Claude, Titan, etc.
"""

import boto3
import json
import re
from typing import Optional

# ── Model defaults ────────────────────────────────────────────────────────────
DEFAULT_REGION     = "ap-south-1"
DEFAULT_QUIZ_MODEL = "arn:aws:bedrock:ap-south-1:718980965213:inference-profile/global.amazon.nova-2-lite-v1:0"

# ── Low-level client factory ─────────────────────────────────────────────────

def _bedrock_runtime(region: str = DEFAULT_REGION):
    """Return a Bedrock Runtime boto3 client."""
    return boto3.client("bedrock-runtime", region_name=region)


def _bedrock_control(region: str = DEFAULT_REGION):
    """Return a Bedrock (control plane) boto3 client — for listing models."""
    return boto3.client("bedrock", region_name=region)


# ── Connection test ──────────────────────────────────────────────────────────

def test_bedrock_connection(region: str = DEFAULT_REGION) -> dict:
    """
    Verify AWS credentials and Bedrock model access.
    Returns:
        { "success": bool, "message": str, "models": list[str] }
    """
    try:
        client = _bedrock_control(region)
        resp   = client.list_foundation_models(byOutputModality="TEXT")
        models = [m["modelId"] for m in resp.get("modelSummaries", [])]
        # Show Nova + Claude models relevant to this project
        relevant = [m for m in models if any(k in m.lower() for k in ("nova", "claude", "titan"))]
        return {
            "success": True,
            "message": f"Connected to Bedrock ({region}). {len(relevant)} model(s) available.",
            "models":  relevant,
        }
    except Exception as exc:
        return {"success": False, "message": str(exc), "models": []}


# ── Shared invoke helper (Converse API — model-agnostic) ─────────────────────

def _invoke_model(
    system_prompt: str,
    user_prompt:   str,
    max_tokens:    int   = 2000,
    temperature:   float = 0.4,
    region:        str   = DEFAULT_REGION,
    model_id:      str   = DEFAULT_QUIZ_MODEL,
) -> str:
    """
    Call any Bedrock model via the Converse API and return raw text.
    Works with Amazon Nova, Claude, Titan, and more.
    Raises RuntimeError on API failure.
    """
    client = _bedrock_runtime(region)
    response = client.converse(
        modelId=model_id,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": user_prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
    return response["output"]["message"]["content"][0]["text"].strip()


def _parse_json_response(raw: str) -> dict:
    """
    Robustly extract and parse JSON from a model response.
    Strategy:
      1. Look for a ```json ... ``` or ``` ... ``` fence anywhere in the text.
      2. If no fence found, slice from the first '{' to the last '}'.
      3. Parse the extracted substring as JSON.
    """
    # Strategy 1: markdown code fence (```json or ```)
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence_match:
        text = fence_match.group(1).strip()
        return json.loads(text)

    # Strategy 2: find outermost JSON object braces
    start = raw.find("{")
    end   = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(raw[start:end + 1])

    # Last resort: try the whole string
    return json.loads(raw)


# ── Quiz generation ──────────────────────────────────────────────────────────

def generate_quiz(
    topic:         str,
    difficulty:    str = "medium",
    num_questions: int = 3,
    region:        str = DEFAULT_REGION,
    model_id:      str = DEFAULT_QUIZ_MODEL,
) -> dict:
    """
    Generate a multiple-choice quiz using Claude 3 Haiku.

    Args:
        topic:         Subject matter for the quiz.
        difficulty:    "easy" | "medium" | "hard"
        num_questions: Number of questions (1–10).
        region:        AWS region where model is available.
        model_id:      Bedrock model ID.

    Returns:
        Parsed JSON dict:
        {
            "quiz_title": str,
            "topic": str,
            "difficulty": str,
            "questions": [
                {
                    "question":    str,
                    "options":     ["A. ...", "B. ...", "C. ...", "D. ..."],
                    "answer":      "A. ...",
                    "explanation": str
                }, ...
            ]
        }

    Raises:
        RuntimeError on API failure.
        ValueError   if response is not valid JSON.
    """
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
            "question":    "string",
            "options":     ["A. ...", "B. ...", "C. ...", "D. ..."],
            "answer":      "A. ...",
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

    try:
        raw = _invoke_model(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=2000,
            temperature=0.4,
            region=region,
            model_id=model_id,
        )
        return _parse_json_response(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Bedrock returned non-JSON output: {exc}\nPreview: {raw[:400]}") from exc
    except Exception as exc:
        raise RuntimeError(f"Bedrock API error: {exc}") from exc


# ── Lesson summary generation ────────────────────────────────────────────────

def generate_lesson_summary(
    topic:       str,
    grade_level: str = "Grade 10",
    region:      str = DEFAULT_REGION,
    model_id:    str = DEFAULT_QUIZ_MODEL,
) -> dict:
    """
    Generate concise study notes / lesson summary for students.

    Returns:
        Parsed JSON dict:
        {
            "title":        str,
            "grade_level":  str,
            "key_concepts": [str, ...],
            "summary":      str,
            "fun_fact":     str
        }

    Raises:
        RuntimeError on API failure.
        ValueError   if response is not valid JSON.
    """
    system_prompt = """You are an expert educator writing concise study notes for students.
Output ONLY a raw JSON object. Do NOT use markdown, code fences, backticks, or any explanation.
Start your response with { and end with }.
Required format:
{
    "title":        "string",
    "grade_level":  "string",
    "key_concepts": ["concept1", "concept2", "concept3"],
    "summary":      "string (2-3 short paragraphs)",
    "fun_fact":     "string"
}"""

    user_prompt = (
        f"Create concise study notes about '{topic}' for {grade_level} students. "
        f"Include 4-6 key concepts, a 2-3 paragraph summary, and one interesting fun fact."
    )

    try:
        raw = _invoke_model(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=1500,
            temperature=0.5,
            region=region,
            model_id=model_id,
        )
        return _parse_json_response(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Bedrock returned non-JSON output: {exc}\nPreview: {raw[:400]}") from exc
    except Exception as exc:
        raise RuntimeError(f"Bedrock API error: {exc}") from exc
