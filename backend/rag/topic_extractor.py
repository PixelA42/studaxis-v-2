"""
Topic extraction from educational content using LLM.
Used before chunking to identify dominant concepts for topic-aware RAG and flashcard generation.
"""

from __future__ import annotations

import json
import os
import re
import requests
from typing import Any

_ollama_base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_API_URL = f"{_ollama_base}/api/generate"
DEFAULT_MODEL = "llama3.2"
DEFAULT_TIMEOUT = 90


def ollama_generate(prompt: str, model: str = DEFAULT_MODEL, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Call Ollama API for completion. Returns raw response text."""
    payload = {"model": model, "prompt": prompt, "stream": False}
    resp = requests.post(OLLAMA_API_URL, json=payload, timeout=timeout)
    resp.raise_for_status()
    return (resp.json().get("response") or "").strip()


def parse_ai_json(raw: str) -> list[str]:
    """Parse AI response as JSON array of strings. Handles markdown, trailing commas."""
    cleaned = re.sub(r"```json|```", "", raw).strip()
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if not match:
        return []
    try:
        parsed = json.loads(match.group())
    except json.JSONDecodeError:
        fixed = re.sub(r",\s*([}\]])", r"\1", match.group())
        try:
            parsed = json.loads(fixed)
        except json.JSONDecodeError:
            return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if item and str(item).strip()]


def extract_dominant_topics(
    text: str,
    num_topics: int = 10,
    model: str = DEFAULT_MODEL,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[str]:
    """
    Extract dominant educational concepts from content using an LLM.
    Run BEFORE chunking; store results in ChromaDB metadata as dominant_topics.

    Args:
        text: Raw document text (will use first 6000 chars)
        num_topics: Max number of topics to extract
        model: Ollama model name
        timeout: Request timeout in seconds

    Returns:
        List of topic strings (actual concepts, not chapter titles or objectives).
    """
    if not text or not text.strip():
        return []
    sample = text[:6000] if len(text) > 6000 else text
    prompt = f"""Read this educational content and identify the {num_topics} most important concepts a student must understand.

Do NOT list chapter titles, goals, objectives, or section headers.

List only ACTUAL CONCEPTS that appear in the content — things that would appear on an exam.

Examples of good topics: "Newton's Second Law", "Mitosis vs Meiosis", "Demand curve shifts"
Examples of bad topics: "Chapter 3 Goals", "Learning Objectives", "Summary"

Content:
{sample}

Return ONLY a JSON array of topic strings.
No markdown. No backticks. Start with [ end with ]"""
    try:
        raw = ollama_generate(prompt, model=model, timeout=timeout)
        topics = parse_ai_json(raw)
        return topics[:num_topics] if topics else []
    except Exception as e:
        print(f"[topic_extractor] Ollama extraction failed: {e}")
        return []


def map_question_to_topics(
    user_question: str,
    doc_topics: list[str],
    model: str = DEFAULT_MODEL,
    timeout: int = 60,
) -> list[str]:
    """
    Map a user question to the 2-3 most relevant topics from a document's topic list.

    Args:
        user_question: The user's question
        doc_topics: List of dominant topics from the textbook
        model: Ollama model
        timeout: Request timeout

    Returns:
        List of 2-3 topic strings from doc_topics that best match the question.
    """
    if not user_question or not doc_topics:
        return []
    topics_str = json.dumps(doc_topics)
    prompt = f'''Given this question: "{user_question}"

And these topics from the textbook: {topics_str}

Which 2-3 topics are most relevant to answering this question?
Return ONLY a JSON array of topic strings (subset of the given topics).
No markdown. No backticks. Start with [ end with ]'''
    try:
        raw = ollama_generate(prompt, model=model, timeout=timeout)
        return parse_ai_json(raw)[:3]
    except Exception as e:
        print(f"[topic_extractor] map_question_to_topics failed: {e}")
        return []
