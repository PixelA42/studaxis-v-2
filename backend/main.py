"""
Studaxis FastAPI Backend — API Bridge

Serves as the bridge between the React frontend and the local AI engine (Ollama),
flashcards system, and optional cloud. CORS is configured for local React development.

When frontend/dist exists (e.g. repo root frontend/dist), serves the compiled React SPA
at / with fallback to index.html for client-side routes. API routes are under /api.

Run: uvicorn main:app --reload --host 0.0.0.0 --port 6782
(from the backend directory)

Or from repo root: uvicorn backend.main:app --reload --host 0.0.0.0 --port 6782
Or: python main.py  (root main.py mounts SPA and runs uvicorn)
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure backend is on path for imports when run from repo root
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_APP_DIR))

from ai_integration_layer import AIEngine, AIState, AITaskType
from grading.grader import Grader
from grading.red_pen_feedback import RedPenFeedback
from auth_routes import router as auth_router
from database import User, init_db
from dependencies import get_current_user, get_user_id
from profile_store import UserProfile, load_profile, save_profile, load_profile_for_user, save_profile_for_user
from recommendation_service import (
    _has_flashcard_topic,
    _has_quiz_data,
    _get_quiz_profile,
    build_flashcard_based_prompt,
    build_quiz_only_prompt,
    parse_ai_response,
)
from stats_algorithms import (
    ensure_flashcard_structure,
    ensure_streak_structure,
    update_flashcard_entry,
    update_flashcard_stats_from_cards,
    update_quiz_stats as _update_quiz_stats,
    update_streak as _update_streak,
)

# ---------------------------------------------------------------------------
# Base path for AI engine and data (user_stats, profile, etc.)
# When run as "uvicorn main:app", cwd is backend; when "uvicorn backend.main:app", cwd is repo root.
BASE_PATH = Path(os.environ.get("STUDAXIS_BASE_PATH", str(_APP_DIR)))
DATA_DIR = BASE_PATH / "data"
STATS_FILE = DATA_DIR / "user_stats.json"
FLASHCARDS_FILE = DATA_DIR / "flashcards.json"
SAMPLE_TEXTBOOKS_DIR = DATA_DIR / "sample_textbooks"


def _user_dir(user_id: str) -> Path:
    """Return per-user data directory, creating it if needed."""
    d = DATA_DIR / "users" / user_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _stats_file(user_id: str) -> Path:
    """Return path to per-user user_stats.json."""
    return _user_dir(user_id) / "user_stats.json"


def _flashcards_file(user_id: str) -> Path:
    """Return path to per-user flashcards.json (legacy)."""
    return _user_dir(user_id) / "flashcards.json"


# New deck-based flashcard storage: data/flashcards/{user_id}.json
def _flashcard_decks_file(user_id: str) -> Path:
    """Return path to per-user flashcard decks JSON."""
    d = DATA_DIR / "flashcards"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{user_id}.json"


def _load_flashcard_decks(user_id: str) -> list[dict[str, Any]]:
    """Load decks from new structure. Migrates from legacy if needed."""
    decks_path = _flashcard_decks_file(user_id)
    legacy_path = _flashcards_file(user_id)

    # Migrate legacy flat cards to deck format if new file missing
    if not decks_path.exists() and legacy_path.exists():
        try:
            raw = legacy_path.read_text(encoding="utf-8")
            legacy = json.loads(raw)
            cards = legacy if isinstance(legacy, list) else []
            if cards:
                by_topic: dict[str, list] = {}
                for c in cards:
                    topic = str(c.get("topic") or "General")
                    by_topic.setdefault(topic, []).append(c)
                decks = []
                for topic, topic_cards in by_topic.items():
                    deck_id = f"deck_{uuid.uuid4().hex[:12]}"
                    created = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    decks.append({
                        "id": deck_id,
                        "title": topic,
                        "subject": topic,
                        "created_at": created,
                        "cards": [_normalize_card_for_deck(c) for c in topic_cards],
                    })
                data = {"decks": decks}
                decks_path.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
        except (OSError, json.JSONDecodeError):
            pass

    if not decks_path.exists():
        return []

    try:
        raw = decks_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return data.get("decks", []) if isinstance(data, dict) else []
    except (OSError, json.JSONDecodeError):
        return []


def _normalize_card_for_deck(c: dict[str, Any]) -> dict[str, Any]:
    """Ensure card has required deck fields; preserve extra fields."""
    base = {
        "id": str(c.get("id") or uuid.uuid4().hex),
        "front": str(c.get("front") or c.get("question") or ""),
        "back": str(c.get("back") or c.get("answer") or ""),
        "ease": str(c.get("ease") or "medium"),
        "next_review": str(c.get("next_review") or datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "review_count": int(c.get("review_count", 0)),
        "mastered": bool(c.get("mastered", False)),
    }
    for k, v in c.items():
        if k not in base and v is not None:
            base[k] = v
    return base


def _save_flashcard_decks(decks: list[dict[str, Any]], user_id: str) -> None:
    """Save decks to new structure."""
    try:
        path = _flashcard_decks_file(user_id)
        path.write_text(
            json.dumps({"decks": decks}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def _enqueue_sync(base_path: Path, user_id: str, sync_type: str, payload: dict[str, Any]) -> None:
    """Add item to sync queue for AWS when online."""
    try:
        from sync_manager import SyncManager
        sm = SyncManager(base_path=str(base_path), user_id=user_id)
        if sync_type == "flashcard_review":
            sm._enqueue_generic("flashcard_review", payload)
        elif sync_type == "quiz_result":
            sm._enqueue_generic("quiz_result", payload)
        elif sync_type == "flashcard_create":
            sm._enqueue_generic("flashcard_create", payload)
        elif sync_type == "assignment_complete":
            sm._enqueue_generic("assignment_complete", payload)
    except Exception:
        pass


def _chat_history_file(user_id: str) -> Path:
    """Return path to per-user chat_history.json."""
    return _user_dir(user_id) / "chat_history.json"


def _notifications_file(user_id: str) -> Path:
    """Return path to per-user notifications.json."""
    d = DATA_DIR / "notifications"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{user_id}.json"


def _assignments_dir() -> Path:
    d = DATA_DIR / "assignments"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _assignments_file(class_code: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", class_code or "default")[:64]
    return _assignments_dir() / f"{safe}.json"


def _load_assignments(class_code: str) -> list[dict[str, Any]]:
    try:
        path = _assignments_file(class_code)
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        pass
    return []


def _save_assignments(class_code: str, items: list[dict[str, Any]]) -> None:
    try:
        _assignments_file(class_code).write_text(
            json.dumps(items, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def _load_notifications(user_id: str) -> list[dict[str, Any]]:
    """Load notifications from JSON file; return [] on missing/error."""
    try:
        f = _notifications_file(user_id)
        if f.exists():
            raw = f.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "notifications" in data:
                return data["notifications"]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def _save_notifications(notifications: list[dict[str, Any]], user_id: str) -> None:
    """Persist notifications to JSON file."""
    try:
        f = _notifications_file(user_id)
        f.write_text(
            json.dumps(notifications, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


app = FastAPI(
    title="Studaxis API",
    description="Offline-first AI tutoring backend — flashcards, explain, study recommendation",
    version="1.0.0",
)

# Auth routes: /api/auth/signup, /api/auth/login
app.include_router(auth_router)


@app.on_event("startup")
def _startup():
    """Ensure auth DB tables exist on startup."""
    init_db()


# CORS: allow local React (Vite 5173), same-origin (6782, 6783)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:6782",
        "http://127.0.0.1:6782",
        "http://localhost:6783",
        "http://127.0.0.1:6783",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single AI engine instance (lazy init to avoid import-time side effects)
_ai_engine: Optional[AIEngine] = None


def get_ai_engine() -> AIEngine:
    global _ai_engine
    if _ai_engine is None:
        _ai_engine = AIEngine(base_path=str(BASE_PATH))
    return _ai_engine



# ---------------------------------------------------------------------------
# User stats persistence (same schema as preferences.py / Streamlit)
# ---------------------------------------------------------------------------

_DEFAULT_STATS: dict[str, Any] = {
    "user_id": "",
    "last_sync_timestamp": None,
    "streak": {"current": 0, "longest": 0, "last_active_date": None, "milestone_next": 7},
    "quiz_stats": {
        "total_attempted": 0,
        "total_correct": 0,
        "average_score": 0.0,
        "last_quiz_date": None,
        "by_topic": {},
        "total_score_sum": 0,
        "total_max_sum": 0,
        "average_percent": 0,
        "last_score": None,
    },
    "flashcard_stats": {"total_reviewed": 0, "mastered": 0, "due_for_review": 0, "cards": {}},
    "chat_history": [],
    "preferences": {
        "difficulty_level": "Beginner",
        "theme": "light",
        "language": "English",
        "sync_enabled": True,
    },
    "hardware_info": {},
}


def _load_user_stats(user_id: str) -> dict[str, Any]:
    """Load user_stats.json for given user; return defaults on missing/error."""
    try:
        f = _stats_file(user_id)
        if f.exists():
            raw = f.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
    except (OSError, json.JSONDecodeError):
        pass
    result = dict(_DEFAULT_STATS)
    prefs = result.get("preferences") or {}
    if not isinstance(prefs, dict):
        prefs = {}
    for key, default in _DEFAULT_STATS["preferences"].items():
        prefs.setdefault(key, default)
    result["preferences"] = prefs
    return result



def _save_user_stats(stats: dict[str, Any], user_id: str) -> None:
    """Persist user stats to per-user directory (atomic write)."""
    try:
        f = _stats_file(user_id)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(f)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class FlashcardGenerateRequest(BaseModel):
    topic_or_chapter: str = Field(..., min_length=1, description="Topic or textbook chapter name")
    input_type: str = Field(default="Topic Name", description="'Topic Name' or 'Textbook Chapter'")
    count: int = Field(default=10, ge=5, le=35, description="Number of flashcards to generate")
    offline_mode: bool = Field(default=True, description="Force local inference")
    user_id: Optional[str] = Field(default=None, description="Optional user identifier")


class FlashcardItem(BaseModel):
    id: str
    topic: str
    front: str
    back: str
    sourceType: Optional[str | list[str]] = None


class FlashcardGenerateResponse(BaseModel):
    cards: list[FlashcardItem]
    topic: str


class FlashcardExplainRequest(BaseModel):
    front: str = Field(..., description="Card question/front")
    back: str = Field(..., description="Card answer/back")
    subject: str = Field(default="General", description="Deck/subject of the card")
    difficulty: str = Field(default="Beginner", description="User profile difficulty level")


class FlashcardExplainResponse(BaseModel):
    text: str
    confidence_score: float = 0.0


class StudyRecommendationRequest(BaseModel):
    topic: str = Field(..., description="Topic or subject for the plan")
    time_budget_minutes: int = Field(default=15, ge=1, le=240, description="Available study time in minutes")
    review_mode: Optional[str] = Field(default="flashcards", description="Context: flashcards, quiz, etc.")
    user_id: Optional[str] = Field(default=None)
    offline_mode: bool = Field(default=True)


class FlashcardRecommendRequest(BaseModel):
    deck_id: str = Field(default="", description="Current deck id (optional for quiz-only mode)")
    subject: str = Field(default="", description="Current subject/topic (optional for quiz-only mode)")
    hard_cards: list[str] = Field(default_factory=list, description="Card fronts marked Hard")
    easy_count: int = Field(default=0)
    hard_count: int = Field(default=0)
    difficulty: str = Field(default="Beginner")
    insights: Optional[dict[str, Any]] = Field(default=None, description="weak_subjects, avg_quiz_score, streak")


class StudyRecommendationResponse(BaseModel):
    text: str
    confidence_score: float = 0.0


class AdaptiveRecommendationResponse(BaseModel):
    """Structured adaptive recommendation (weak topic, action, difficulty)."""
    weak_topic: str = Field(..., description="Weak area to focus on")
    suggested_action: str = Field(..., description="Specific recommendation")
    difficulty_adjustment: str = Field(..., description="Easier / medium / harder")
    text: str = Field(default="", description="Full human-readable summary")
    confidence_score: float = 0.0
    has_data: bool = Field(default=True, description="False when no flashcard or quiz data")


# --- Chat ---
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    is_clarification: bool = Field(default=False, description="True if this is a follow-up clarification")
    task_type: Optional[str] = Field(
        default="chat",
        description="Task type: chat, clarify, explain_topic, quiz_me, flashcards, step_by_step",
    )
    context: Optional[dict[str, Any]] = Field(default=None, description="Optional: difficulty, chat_history, subject, etc.")
    subject: Optional[str] = Field(default=None, description="Selected subject (e.g. General, Maths)")
    textbook_id: Optional[str] = Field(default=None, description="Attached textbook id (filename) for RAG")


class ChatResponse(BaseModel):
    text: str
    confidence_score: float = 0.0
    metadata: Optional[dict[str, Any]] = None


# --- Grade ---
class GradeRequest(BaseModel):
    question_id: str = Field(..., description="Question identifier")
    question: str = Field(..., description="Question text")
    expected_answer: Optional[str] = Field(default=None)
    topic: str = Field(default="General")
    answer: str = Field(..., description="Student answer to grade")
    difficulty: str = Field(default="Beginner")
    rubric: Optional[str] = Field(default=None)
    user_id: Optional[str] = None
    offline_mode: bool = True


class GradeResponse(BaseModel):
    text: str
    confidence_score: float = 0.0
    score: Optional[float] = None
    errors: list[Any] = []
    strengths: list[Any] = []
    remarks: str = ""
    metadata: Optional[dict[str, Any]] = None


# --- Quiz (stub content from Streamlit quiz page) ---
QUIZ_ITEMS: list[dict[str, Any]] = [
    {
        "id": "q1",
        "topic": "Physics",
        "question": "State Newton's second law and explain what each term means.",
        "expected_answer": "Force equals mass times acceleration. F = m * a.",
    },
    {
        "id": "q2",
        "topic": "Biology",
        "question": "What is osmosis in simple terms?",
        "expected_answer": "Movement of water molecules from high concentration to low concentration through a semipermeable membrane.",
    },
    {
        "id": "q3",
        "topic": "Mathematics",
        "question": "Differentiate x^2 and explain the rule used.",
        "expected_answer": "Derivative of x squared is 2x using the power rule.",
    },
]

# Panic Mode exam (Streamlit panic_mode.py)
PANIC_ITEMS: list[dict[str, Any]] = [
    {"id": "p1", "topic": "Physics", "question": "Define momentum and explain one real-world example.", "expected_answer": "Momentum is mass multiplied by velocity."},
    {"id": "p2", "topic": "Biology", "question": "Explain why osmosis is important in plant cells.", "expected_answer": "It helps maintain turgor pressure and water balance."},
    {"id": "p3", "topic": "Mathematics", "question": "What is the derivative of x^3 and which rule applies?", "expected_answer": "3x^2 using the power rule."},
    {"id": "p4", "topic": "Chemistry", "question": "What is pH and what does pH 7 indicate?", "expected_answer": "pH measures acidity/basicity; pH 7 is neutral."},
    {"id": "p5", "topic": "Physics", "question": "State one difference between speed and velocity.", "expected_answer": "Speed is scalar; velocity includes direction."},
]


class QuizSubmitRequest(BaseModel):
    answers: list[dict[str, Any]] = Field(..., description="List of {question_id, answer}")
    items: Optional[list[dict[str, Any]]] = Field(default=None, description="Custom quiz items for panic mode grading (when generated from material)")


class QuizSubmitResponse(BaseModel):
    score: float = Field(default=0, description="Total score")
    max_score: float = Field(default=0, description="Max possible score")
    percent: int = Field(default=0, description="Percentage score")
    results: list[dict[str, Any]] = Field(default_factory=list, description="Per-question: question_id, correct, correct_answer, explanation")
    weak_topics_text: Optional[str] = Field(default=None, description="AI weak-topic summary (panic mode only)")
    recommendation_text: Optional[str] = Field(default=None, description="AI study recommendation (panic mode only)")


# ---------------------------------------------------------------------------
# Helpers (mirror Streamlit flashcards.py logic)
# ---------------------------------------------------------------------------


def _extract_json_array(text: str) -> str:
    """Extract a JSON array from model output (strip markdown code blocks)."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _parse_ai_json(raw: str) -> list:
    """Robustly parse AI response as JSON array. Handles markdown, trailing commas."""
    cleaned = re.sub(r"```json|```", "", raw).strip()
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if not match:
        raise ValueError("No JSON array found in AI response")
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        fixed = re.sub(r",\s*([}\]])", r"\1", match.group())
        return json.loads(fixed)


def _normalize_cards(raw: list[Any]) -> list[dict[str, Any]]:
    """Convert LLM output to list of cards with id, topic, front, back."""
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        front = str(item.get("front", item.get("question", ""))).strip() or "?"
        back = str(item.get("back", item.get("answer", ""))).strip() or "—"
        topic = str(item.get("topic", "")).strip() or "General"
        card_id = str(item.get("id", item.get("card_id", str(uuid.uuid4()))))
        out.append({
            "id": card_id,
            "topic": topic,
            "front": front,
            "back": back,
        })
    return out


def _normalize_quiz_items(raw: list[Any], subject: str) -> list[dict[str, Any]]:
    """Convert LLM output to list of quiz items with id, topic, question, expected_answer."""
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip() or "?"
        expected = str(item.get("expected_answer", item.get("answer", ""))).strip() or ""
        topic = str(item.get("topic", subject)).strip() or subject
        item_id = str(item.get("id", f"pq{i+1}_{uuid.uuid4().hex[:8]}"))
        out.append({
            "id": item_id,
            "topic": topic,
            "question": question,
            "expected_answer": expected,
        })
    return out


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health():
    """Liveness/readiness; includes Ollama availability when possible."""
    payload: dict[str, Any] = {"status": "ok", "service": "studaxis-api"}
    try:
        engine = get_ai_engine()
        # Lightweight check: we don't call Ollama here to avoid latency; optional future: ping Ollama
        payload["ollama_available"] = getattr(engine, "config", None) is not None
    except Exception:
        payload["ollama_available"] = False
    return payload


@app.get("/api/ollama/ping")
def ollama_ping():
    """Ping Ollama at localhost:11434. Used by loading screen to wait until local AI is ready."""
    import requests
    url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    base = url.rstrip("/")
    try:
        r = requests.get(f"{base}/", timeout=3)
        return {"ok": r.status_code == 200}
    except Exception:
        return {"ok": False}


# ---------------------------------------------------------------------------
# Hardware (Phase 8 — HardwareValidator)
# ---------------------------------------------------------------------------

def _get_hardware_result() -> dict[str, Any]:
    """Run HardwareValidator and return status, message, specs, tips. Safe if psutil missing or validator fails."""
    try:
        from pages.hardware_validator import HardwareValidator
        v = HardwareValidator()
        is_valid, message, specs = v.validate()
        tips = v.get_optimization_tips()
        quantization = v.get_quantization_recommendation()
        status = "block" if not is_valid else ("warn" if tips else "ok")
        return {
            "status": status,
            "message": message,
            "specs": specs,
            "tips": tips,
            "quantization_recommendation": quantization,
            "min_ram_gb": HardwareValidator.MIN_RAM_GB,
            "min_disk_gb": HardwareValidator.MIN_DISK_GB,
            "recommended_ram_gb": HardwareValidator.RECOMMENDED_RAM_GB,
        }
    except Exception as e:
        return {
            "status": "ok",
            "message": "Hardware check unavailable.",
            "specs": {},
            "tips": [],
            "quantization_recommendation": "Q2_K",
            "min_ram_gb": 4.0,
            "min_disk_gb": 2.0,
            "recommended_ram_gb": 6.0,
            "error": str(e),
        }


@app.get("/api/hardware")
def hardware():
    """Hardware check for boot flow: ok / warn / block + specs + tips."""
    return _get_hardware_result()


# ---------------------------------------------------------------------------
# Diagnostics (Settings: Deployment Readiness)
# ---------------------------------------------------------------------------

def _get_sync_readiness(user_id: str) -> tuple[str, str]:
    """Return (sync_state, sync_readiness) from user stats and SyncManager."""
    stats = _load_user_stats(user_id)
    prefs = stats.get("preferences") or {}
    sync_enabled = prefs.get("sync_enabled", True)
    last_sync = stats.get("last_sync_timestamp")

    if not sync_enabled:
        return "Disabled", "Cloud sync is disabled in Settings"

    try:
        from sync_manager import SyncManager
        sm = SyncManager(base_path=str(BASE_PATH), user_id=user_id)
        pending = sm.queue_size
        online = sm.check_connectivity()
        if pending > 0 and online:
            return "Pending", f"{pending} item(s) queued — ready to sync"
        if pending > 0 and not online:
            return "Pending", f"{pending} item(s) queued — waiting for connection"
        if online:
            return "Idle", "Ready to sync"
        return "Offline", "Waiting for connection"
    except Exception:
        pass

    if last_sync:
        return "Idle", "Ready to sync"
    return "Idle", "Ready to sync"


@app.get("/api/diagnostics")
def diagnostics(user_id: str = Depends(get_user_id)):
    """
    Deployment readiness: app version, environment, sync state, last sync.
    Used by Settings Deployment Readiness panel.
    """
    stats = _load_user_stats(user_id)
    prefs = stats.get("preferences") or {}
    sync_enabled = prefs.get("sync_enabled", True)
    last_sync = stats.get("last_sync_timestamp")
    sync_state, sync_readiness = _get_sync_readiness(user_id)

    return {
        "app_version": getattr(app, "version", "1.0.0"),
        "environment": os.environ.get("STUDAXIS_ENV", "Local"),
        "sync_enabled": sync_enabled,
        "sync_state": sync_state,
        "sync_readiness": sync_readiness,
        "last_sync_timestamp": last_sync,
    }


# ---------------------------------------------------------------------------
# Storage file list (Settings: Storage)
# ---------------------------------------------------------------------------

def _format_size(n: int) -> str:
    """Format byte count as human-readable string."""
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def _get_storage_files(user_id: str) -> list[dict[str, Any]]:
    """List storage files for a user (per-user dir) plus shared files."""
    files: list[dict[str, Any]] = []
    user_dir = _user_dir(user_id)

    # Per-user files
    per_user_known = {
        "user_stats.json": "Progress, streaks, quiz stats, chat history, preferences",
        "flashcards.json": "Flashcard decks and SRS data",
        "profile.json": "User profile (name, mode, class code)",
        "users.db": "Auth database (accounts)",
        "sync_queue.json": "Pending sync items",
    }
    for name, desc in per_user_known.items():
        path = user_dir / name
        if path.exists():
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            extra = ""
            if name == "flashcards.json":
                cards = _load_flashcards(user_id)
                extra = f" — {len(cards)} cards" if cards else ""
            elif name == "user_stats.json":
                stats = _load_user_stats(user_id)
                chat_len = len(stats.get("chat_history") or [])
                if chat_len:
                    extra = f" — {chat_len} chat messages"
            files.append({
                "name": name,
                "size_bytes": size,
                "size_human": _format_size(size),
                "description": desc + extra,
            })

    # Shared files (not per-user)
    shared_known = {
        "profile.json": "User profile (name, mode, class code)",
        "users.db": "Auth database (accounts)",
        "sync_queue.json": "Pending sync items",
    }
    for name, desc in shared_known.items():
        path = DATA_DIR / name
        if path.exists():
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            files.append({
                "name": name,
                "size_bytes": size,
                "size_human": _format_size(size),
                "description": desc,
            })
        elif name == "sync_queue.json":
            files.append({
                "name": name,
                "size_bytes": 0,
                "size_human": "0 B",
                "description": desc + " — not created yet",
            })

    backups = DATA_DIR / "backups"
    if backups.is_dir():
        try:
            count = sum(1 for _ in backups.iterdir() if _.is_file())
            total = sum(_.stat().st_size for _ in backups.iterdir() if _.is_file())
            files.append({
                "name": "backups/",
                "size_bytes": total,
                "size_human": _format_size(total),
                "description": f"Backup files ({count} file(s))",
            })
        except OSError:
            pass

    return files


@app.get("/api/storage/files")
def storage_files(user_id: str = Depends(get_user_id)):
    """List local storage files for Settings Storage panel."""
    return {"files": _get_storage_files(user_id)}


# ---------------------------------------------------------------------------
# Textbooks (sample_textbooks)
# ---------------------------------------------------------------------------


def _list_textbooks() -> list[dict[str, Any]]:
    """List *.pdf, *.txt, and *.pptx files in sample_textbooks."""
    from datetime import datetime, timezone
    out: list[dict[str, Any]] = []
    if not SAMPLE_TEXTBOOKS_DIR.is_dir():
        return out
    for p in sorted(SAMPLE_TEXTBOOKS_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() in (".pdf", ".txt", ".pptx"):
            subject = p.stem.split("_")[0] if "_" in p.stem else p.stem
            try:
                mtime = p.stat().st_mtime
                uploaded_at = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
            except OSError:
                uploaded_at = ""
            out.append({
                "id": p.name,
                "filename": p.name,
                "name": p.stem,
                "subject": subject,
                "uploaded_at": uploaded_at,
            })
    return out


@app.get("/api/textbooks")
def textbooks_list():
    """List textbooks from data/sample_textbooks (*.pdf, *.txt)."""
    return {"textbooks": _list_textbooks()}


@app.post("/api/textbooks/upload")
def textbooks_upload(file: UploadFile = File(...)):
    """Multipart file upload; save PDF or PPTX to sample_textbooks (shared with Flashcards and AI Chat)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    suf = Path(file.filename).suffix.lower()
    if suf not in (".pdf", ".pptx"):
        raise HTTPException(status_code=400, detail="Only PDF and PPTX files are accepted")
    SAMPLE_TEXTBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    dest = SAMPLE_TEXTBOOKS_DIR / file.filename
    try:
        content = file.file.read()
        dest.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
    return {"id": file.filename, "name": Path(file.filename).stem}


def _extract_text_from_pdf(path: Path) -> str:
    """Extract text from PDF using PyPDF2 or PyPDFLoader."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(str(path))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    except ImportError:
        try:
            from langchain_community.document_loaders import PyPDFLoader
            docs = PyPDFLoader(str(path)).load()
            return "\n".join(d.page_content for d in docs)
        except ImportError:
            raise HTTPException(status_code=501, detail="Install PyPDF2 or langchain-community for PDF extraction")


def _extract_text_from_file(path: Path) -> str:
    """Extract text from txt, pdf, or ppt/pptx."""
    suf = path.suffix.lower()
    if suf == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")
    if suf == ".pdf":
        return _extract_text_from_pdf(path)
    if suf in (".ppt", ".pptx"):
        try:
            from langchain_community.document_loaders import UnstructuredPowerPointLoader
            docs = UnstructuredPowerPointLoader(str(path)).load()
            return "\n".join(d.page_content for d in docs)
        except ImportError:
            raise HTTPException(status_code=501, detail="PPT support requires UnstructuredPowerPointLoader (pip install unstructured)")
    return ""


def _chunks_from_text(text: str, chunk_size: int = 800, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks for finding relevant content per topic."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start += chunk_size - overlap
    return [c for c in chunks if len(c) > 50]


def _find_relevant_chunk_for_topic(content: str, topic: str) -> str:
    """Find the chunk that best matches the topic (contains topic or has high overlap)."""
    chunks = _chunks_from_text(content)
    if not chunks:
        return content[:600] if len(content) > 600 else content
    topic_lower = topic.lower()
    topic_words = set(topic_lower.split())
    best_chunk = chunks[0]
    best_score = 0
    for c in chunks:
        c_lower = c.lower()
        if topic_lower in c_lower or any(w in c_lower for w in topic_words if len(w) > 2):
            overlap = sum(1 for w in topic_words if len(w) > 2 and w in c_lower)
            if overlap > best_score:
                best_score = overlap
                best_chunk = c
    return best_chunk[:800] if len(best_chunk) > 800 else best_chunk


def _generate_single_flashcard_via_ollama(
    topic: str, relevant_chunk: str, subject: str, difficulty: str = "Beginner"
) -> dict[str, Any] | None:
    """Generate one flashcard for a topic using Ollama. Returns {front, back} or None."""
    import requests
    if not relevant_chunk or not str(relevant_chunk).strip():
        context_chunk = (
            f"""Use your knowledge as a {subject} expert to generate questions about: {topic}"""
        )
        no_context_note = (
            f"Since no source material was provided, generate questions based on standard {subject} "
            f"curriculum for {difficulty} level students. "
        )
    else:
        context_chunk = str(relevant_chunk).strip()
        no_context_note = ""

    prompt = f"""You are creating exam-style flashcards for a {difficulty} level {subject} student.

Topic: {topic}
Context from source material: {context_chunk}

Generate 1 flashcard about this topic.
{no_context_note}
RULES:
- Front must be a QUESTION, never just the topic name
- Questions must be specific and testable
- Back must be a direct answer, max 2 sentences
- Each card must test a DIFFERENT aspect of the topic
- Do NOT write "What is {{topic}}?" as the only question

Good question types to use:
  "What causes...?"
  "How does X differ from Y?"
  "What are the main components of...?"
  "Why does...?"
  "Give an example of..."
  "What happens when...?"

Source content to base questions on:
{context_chunk}

Return ONLY a valid JSON array.
No markdown. No backticks. Start with [ end with ]

Each item:
{{
  "front": "specific question about the topic",
  "back": "concise direct answer"
}}"""
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.2", "prompt": prompt, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        raw = (resp.json().get("response") or "").strip()
        cleaned = re.sub(r"```json|```", "", raw).strip()
        obj = {}
        arr_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if arr_match:
            try:
                parsed = json.loads(arr_match.group())
                if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                    obj = parsed[0]
                elif isinstance(parsed, dict):
                    obj = parsed
            except json.JSONDecodeError:
                pass
        if not obj:
            match = re.search(r"\{[^{}]*\"front\"[^{}]*\"back\"[^{}]*\}", cleaned, re.DOTALL)
            if not match:
                match = re.search(r"\{.*?\}", cleaned, re.DOTALL)
            if match:
                try:
                    obj = json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        if obj:
            front = str(obj.get("front", "")).strip() or "?"
            back = str(obj.get("back", "")).strip() or "—"
            return {"front": front, "back": back, "topic": topic}
    except Exception as e:
        print(f"[flashcard] Ollama failed for topic {topic}: {e}")
    return None


def _generate_cards_from_textbook(
    content: str, count: int, textbook_id: str
) -> FlashcardGenerateResponse:
    """Topic-based flashcard generation from textbook: extract topics, 1-2 cards per topic."""
    from rag.topic_extractor import extract_dominant_topics

    truncated = content[:12000] if len(content) > 12000 else content
    subject = Path(textbook_id).stem.split("_")[0] if "_" in Path(textbook_id).stem else Path(textbook_id).stem
    if not subject:
        subject = "General"

    topics = extract_dominant_topics(truncated, num_topics=max(5, count // 2))
    if not topics:
        return _generate_cards_from_content(content, count, "textbook", subject, "Beginner")

    cards: list[dict[str, Any]] = []
    for topic in topics:
        if len(cards) >= count:
            break
        relevant = _find_relevant_chunk_for_topic(truncated, topic)
        for _ in range(2):
            if len(cards) >= count:
                break
            card = _generate_single_flashcard_via_ollama(topic, relevant, subject, "Beginner")
            if card:
                card["id"] = str(uuid.uuid4())[:8]
                card["topic"] = topic
                cards.append(card)

    if not cards:
        return _generate_cards_from_content(content, count, "textbook", subject, "Beginner")

    normalized = _normalize_cards([{"id": c.get("id"), "topic": c.get("topic"), "front": c.get("front"), "back": c.get("back")} for c in cards])
    for c in normalized:
        c["sourceType"] = "textbook"
    return FlashcardGenerateResponse(
        cards=[FlashcardItem(**c) for c in normalized],
        topic=subject or "Textbook",
    )


def _generate_cards_topic_aware(
    content: str, count: int, subject: str, source_type: str, difficulty: str = "Beginner"
) -> FlashcardGenerateResponse:
    """Topic extraction + per-topic flashcard generation for URL/file/paste sources."""
    from rag.topic_extractor import extract_dominant_topics

    truncated = content[:8000] if len(content) > 8000 else content
    subj = (subject or "General").strip()
    topics = extract_dominant_topics(truncated, num_topics=max(5, count // 2))
    if not topics:
        return _generate_cards_from_content(content, count, source_type, subj, difficulty)

    cards: list[dict[str, Any]] = []
    for topic in topics:
        if len(cards) >= count:
            break
        relevant = _find_relevant_chunk_for_topic(truncated, topic)
        for _ in range(2):
            if len(cards) >= count:
                break
            card = _generate_single_flashcard_via_ollama(topic, relevant, subj, difficulty)
            if card:
                card["id"] = str(uuid.uuid4())[:8]
                card["topic"] = topic
                cards.append(card)

    if not cards:
        return _generate_cards_from_content(content, count, source_type, subj, difficulty)

    normalized = _normalize_cards([{"id": c.get("id"), "topic": c.get("topic"), "front": c.get("front"), "back": c.get("back")} for c in cards])
    for c in normalized:
        c["sourceType"] = source_type
    return FlashcardGenerateResponse(
        cards=[FlashcardItem(**c) for c in normalized],
        topic=subj or "General",
    )


def _generate_cards_from_content(
    content: str, count: int, source_type: str, subject: str = "General", difficulty: str = "Beginner"
) -> FlashcardGenerateResponse:
    """Generate flashcards from extracted text via AI."""
    if not content or not content.strip():
        raise HTTPException(status_code=422, detail="No extractable text from source")
    engine = get_ai_engine()
    truncated = content[:12000] if len(content) > 12000 else content
    try:
        response = engine.request(
            task_type=AITaskType.FLASHCARD_GENERATION,
            user_input="",
            context_data={
                "input_type": "Textbook Chapter",
                "topic_or_chapter": "Content-based",
                "count": count,
                "source_content": truncated,
                "subject": subject,
                "difficulty": difficulty,
            },
            offline_mode=True,
            privacy_sensitive=True,
            user_id=None,
        )
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=503, detail=str(e))
    if response.state in (AIState.FALLBACK_RESPONSE, AIState.ERROR):
        raise HTTPException(status_code=503, detail=response.error_message or response.text or "AI unavailable.")
    raw_text = _extract_json_array(response.text)
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"AI returned invalid JSON: {e}")
    if not isinstance(parsed, list):
        raise HTTPException(status_code=422, detail="AI response was not a JSON array")
    cards = _normalize_cards(parsed)
    for c in cards:
        c["sourceType"] = source_type
    return FlashcardGenerateResponse(cards=[FlashcardItem(**c) for c in cards], topic="Content-based")


def _generate_mcq_questions_via_ai(topic: str, subject: str, difficulty: str, count: int) -> list[dict[str, Any]]:
    """Generate MCQ questions via AI. Returns list of {id, text, options, correct, explanation}."""
    engine = get_ai_engine()
    prompt = f"""Generate exactly {count} multiple choice questions about {topic} for a {difficulty} level {subject} student.

Return ONLY a valid JSON array. No markdown. No backticks. Start with [ end with ]

Each item:
{{
  "id": "q1",
  "text": "question text",
  "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
  "correct": 0,
  "explanation": "why this answer is correct"
}}

Use correct index 0-3 for the right option. Ensure exactly 4 options per question."""
    try:
        response = engine.request(
            task_type=AITaskType.QUIZ_GENERATION,
            user_input=prompt,
            context_data={"subject": subject, "count": count, "difficulty": difficulty},
            offline_mode=True,
            privacy_sensitive=True,
            user_id=None,
        )
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=503, detail=str(e))
    try:
        parsed = _parse_ai_json(response.text)
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=422, detail="AI could not generate valid MCQ questions.")
    out: list[dict[str, Any]] = []
    for i, item in enumerate(parsed) if isinstance(parsed, list) else []:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("id", f"q{i+1}_{uuid.uuid4().hex[:6]}"))
        text = str(item.get("text", item.get("question", ""))).strip() or "?"
        opts = item.get("options", [])
        if not isinstance(opts, list):
            opts = []
        options = [str(o) for o in opts[:4]]
        while len(options) < 4:
            options.append("(No option)")
        correct = int(item.get("correct", 0))
        if correct < 0 or correct >= 4:
            correct = 0
        explanation = str(item.get("explanation", "")).strip() or ""
        out.append({
            "id": qid,
            "text": text,
            "options": options,
            "correct": correct,
            "explanation": explanation,
        })
    return out[:count]


def _generate_open_ended_questions_via_ai(topic: str, subject: str, difficulty: str, count: int) -> list[dict[str, Any]]:
    """Generate open-ended questions via AI. Returns list of {id, text, sample_answer, rubric}."""
    engine = get_ai_engine()
    prompt = f"""Generate exactly {count} open-ended questions about {topic} for a {difficulty} level {subject} student.

Return ONLY a valid JSON array. No markdown. Start with [ end with ]

Each item:
{{
  "id": "q1",
  "text": "question text",
  "sample_answer": "ideal answer",
  "rubric": "what to look for when grading"
}}"""
    try:
        response = engine.request(
            task_type=AITaskType.QUIZ_GENERATION,
            user_input=prompt,
            context_data={"subject": subject, "count": count, "difficulty": difficulty},
            offline_mode=True,
            privacy_sensitive=True,
            user_id=None,
        )
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=503, detail=str(e))
    try:
        parsed = _parse_ai_json(response.text)
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=422, detail="AI could not generate valid open-ended questions.")
    out: list[dict[str, Any]] = []
    for i, item in enumerate(parsed) if isinstance(parsed, list) else []:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("id", f"q{i+1}_{uuid.uuid4().hex[:6]}"))
        text = str(item.get("text", item.get("question", ""))).strip() or "?"
        sample = str(item.get("sample_answer", item.get("expected_answer", ""))).strip() or ""
        rubric = str(item.get("rubric", "")).strip() or "Assess comprehension and accuracy."
        out.append({
            "id": qid,
            "text": text,
            "sample_answer": sample,
            "rubric": rubric,
        })
    return out[:count]


def _generate_quiz_from_content(content: str, subject: str, count: int = 5) -> list[dict[str, Any]]:
    """Generate panic-mode quiz items from extracted text via AI."""
    if not content or not content.strip():
        raise HTTPException(status_code=422, detail="No extractable text from source")
    engine = get_ai_engine()
    truncated = content[:12000] if len(content) > 12000 else content
    try:
        response = engine.request(
            task_type=AITaskType.QUIZ_GENERATION,
            user_input=f"Generate {count} open-ended exam questions for {subject}.",
            context_data={
                "subject": subject,
                "count": count,
                "source_content": truncated,
            },
            offline_mode=True,
            privacy_sensitive=True,
            user_id=None,
        )
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=503, detail=str(e))
    if response.state in (AIState.FALLBACK_RESPONSE, AIState.ERROR):
        raise HTTPException(status_code=503, detail=response.error_message or response.text or "AI unavailable.")
    try:
        parsed = _parse_ai_json(response.text)
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(
            status_code=422,
            detail="AI could not generate valid questions from this material. Try a shorter PDF or use default questions.",
        )
    if not isinstance(parsed, list):
        raise HTTPException(
            status_code=422,
            detail="AI could not generate valid questions from this material. Try a shorter PDF or use default questions.",
        )
    return _normalize_quiz_items(parsed, subject)


class TextbookGenerateRequest(BaseModel):
    textbook_id: str = Field(..., description="Filename in sample_textbooks")
    chapter: Optional[str] = Field(default=None)
    count: int = Field(default=10, ge=5, le=35)


@app.post("/api/flashcards/generate/textbook", response_model=FlashcardGenerateResponse)
def flashcards_generate_textbook(req: TextbookGenerateRequest):
    """Generate flashcards from a textbook file. Uses topic-aware extraction when possible."""
    path = SAMPLE_TEXTBOOKS_DIR / req.textbook_id
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Textbook '{req.textbook_id}' not found")
    try:
        content = _extract_text_from_file(path)
        if not content.strip():
            raise HTTPException(status_code=422, detail="Could not extract text from textbook")
        return _generate_cards_from_textbook(content, req.count, req.textbook_id)
    except HTTPException:
        raise
    except Exception:
        # Fallback to topic-based generation
        topic = req.chapter or Path(req.textbook_id).stem
        return flashcards_generate(FlashcardGenerateRequest(
            topic_or_chapter=topic,
            input_type="Textbook Chapter",
            count=req.count,
            offline_mode=True,
            user_id=None,
        ))


class WeblinkGenerateRequest(BaseModel):
    url: str = Field(..., min_length=1)
    count: int = Field(default=10, ge=5, le=35)


@app.post("/api/flashcards/generate/weblink", response_model=FlashcardGenerateResponse)
def flashcards_generate_weblink(req: WeblinkGenerateRequest):
    """Fetch URL content, strip HTML, generate flashcards via AI."""
    import requests
    try:
        r = requests.get(req.url.strip(), timeout=15, headers={"User-Agent": "Studaxis/1.0"})
        r.raise_for_status()
        html = r.text
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not fetch URL: {e}")
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return _generate_cards_from_content(text, req.count, "weblink")


class GenerateFromUrlRequest(BaseModel):
    url: str = Field(..., min_length=1)
    subject: str = Field(default="General")
    num_cards: int = Field(default=10, ge=5, le=20)
    difficulty: str = Field(default="Beginner")


@app.post("/api/flashcards/generate-from-url", response_model=FlashcardGenerateResponse)
def flashcards_generate_from_url(req: GenerateFromUrlRequest):
    """Scrape URL with BeautifulSoup, topic extraction, smart flashcard generation."""
    url = req.url.strip()
    text = ""
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError:
        httpx = None
        BeautifulSoup = None

    if httpx is not None and BeautifulSoup is not None:
        try:
            response = httpx.get(
                url,
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"},
            )
            if response.status_code in (401, 403):
                raise HTTPException(
                    status_code=422,
                    detail="This website blocked access. Try pasting the article text directly.",
                )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)[:8000]
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise HTTPException(
                    status_code=422,
                    detail="This website blocked access. Try pasting the article text directly.",
                ) from e
            raise HTTPException(
                status_code=422,
                detail="Could not fetch that URL. Try another link or paste the text directly instead.",
            ) from e
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError):
            raise HTTPException(
                status_code=422,
                detail="Could not fetch that URL. Try another link or paste the text directly instead.",
            )
    else:
        import requests
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code in (401, 403):
                raise HTTPException(
                    status_code=422,
                    detail="This website blocked access. Try pasting the article text directly.",
                )
            r.raise_for_status()
            text = re.sub(r"<[^>]+>", " ", r.text)
            text = re.sub(r"\s+", " ", text).strip()[:8000]
        except requests.exceptions.RequestException:
            raise HTTPException(
                status_code=422,
                detail="Could not fetch that URL. Try another link or paste the text directly instead.",
            )

    if len(text) < 200:
        raise HTTPException(
            status_code=422,
            detail="Not enough content found at that URL. Try a different link.",
        )

    cnt = max(5, min(20, req.num_cards))
    return _generate_cards_topic_aware(text, cnt, req.subject, "weblink", req.difficulty)


class GenerateFromTextRequest(BaseModel):
    text: str = Field(..., min_length=1)
    subject: str = Field(default="General")
    num_cards: int = Field(default=10, ge=5, le=20)
    difficulty: str = Field(default="Beginner")


@app.post("/api/flashcards/generate-from-text", response_model=FlashcardGenerateResponse)
def flashcards_generate_from_text(req: GenerateFromTextRequest):
    """Paste text: topic extraction + smart flashcard generation."""
    text = req.text.strip()
    if len(text) < 150:
        raise HTTPException(
            status_code=422,
            detail="Please paste at least a paragraph of text to generate flashcards from",
        )
    cnt = max(5, min(20, req.num_cards))
    return _generate_cards_topic_aware(text[:3000], cnt, req.subject, "paste", req.difficulty)


@app.post("/api/flashcards/generate-from-file", response_model=FlashcardGenerateResponse)
def flashcards_generate_from_file(
    file: UploadFile = File(...),
    subject: str = Form("General"),
    num_cards: int = Form(10, ge=5, le=20),
):
    """Multipart: PDF or PPT only. Topic extraction + smart flashcard generation."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    suf = Path(file.filename).suffix.lower()
    if suf not in (".pdf", ".ppt", ".pptx"):
        raise HTTPException(status_code=422, detail="Only PDF and PPT files are supported")

    tmp_path = DATA_DIR / "tmp_upload" / Path(file.filename).name
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        content = file.file.read()
        tmp_path.write_bytes(content)
        if suf == ".pdf":
            text = _extract_text_from_pdf(tmp_path)
        elif suf in (".ppt", ".pptx"):
            try:
                from pptx import Presentation
                prs = Presentation(str(tmp_path))
                parts = []
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text") and shape.text:
                            parts.append(shape.text)
                text = "\n".join(parts) if parts else ""
            except ImportError:
                try:
                    from langchain_community.document_loaders import UnstructuredPowerPointLoader
                    docs = UnstructuredPowerPointLoader(str(tmp_path)).load()
                    text = "\n".join(d.page_content for d in docs)
                except ImportError:
                    raise HTTPException(
                        status_code=501,
                        detail="PPT support requires python-pptx or unstructured (pip install python-pptx)",
                    )
        else:
            text = ""
        if not text or len(text.strip()) < 100:
            raise HTTPException(status_code=422, detail="Could not extract enough text from the file")
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass

    cnt = max(5, min(20, num_cards))
    return _generate_cards_topic_aware(text[:12000], cnt, subject or "General", "file", "Beginner")


@app.post("/api/flashcards/generate/files", response_model=FlashcardGenerateResponse)
def flashcards_generate_files(files: list[UploadFile] = File(...), count: int = Form(10)):
    """Multipart file upload; extract text from txt/pdf/ppt, generate via AI."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    texts: list[str] = []
    ppt_skipped: list[str] = []
    for uf in files:
        if not uf.filename:
            continue
        suf = Path(uf.filename).suffix.lower()
        if suf not in (".txt", ".pdf", ".ppt", ".pptx"):
            continue
        tmp = Path(uf.filename).name
        try:
            content = uf.file.read()
            tmp_path = DATA_DIR / "tmp_upload" / tmp
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_bytes(content)
            try:
                if suf in (".ppt", ".pptx"):
                    try:
                        from langchain_community.document_loaders import UnstructuredPowerPointLoader
                        docs = UnstructuredPowerPointLoader(str(tmp_path)).load()
                        texts.append("\n".join(d.page_content for d in docs))
                    except ImportError:
                        ppt_skipped.append(uf.filename)
                else:
                    texts.append(_extract_text_from_file(tmp_path))
            finally:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Failed to process {uf.filename}: {e}")
    if ppt_skipped:
        pass  # Already recorded
    combined = "\n\n".join(texts)
    if not combined.strip():
        msg = "No extractable text."
        if ppt_skipped:
            msg += f" PPT support unavailable; skipped: {', '.join(ppt_skipped)}"
        raise HTTPException(status_code=422, detail=msg)
    cnt = max(5, min(35, count))
    return _generate_cards_from_content(combined, cnt, "file")


@app.post("/api/flashcards/generate", response_model=FlashcardGenerateResponse)
def flashcards_generate(req: FlashcardGenerateRequest):
    """
    Generate a deck of flashcards from a topic or chapter name using local AI.
    Returns a list of cards (id, topic, front, back) for the React UI to store or display.
    """
    engine = get_ai_engine()
    try:
        response = engine.request(
            task_type=AITaskType.FLASHCARD_GENERATION,
            user_input=req.topic_or_chapter.strip(),
            context_data={
                "input_type": req.input_type,
                "topic_or_chapter": req.topic_or_chapter.strip(),
                "count": req.count,
                "subject": "General",
                "difficulty": "Beginner",
                "source_content": None,
            },
            offline_mode=req.offline_mode,
            privacy_sensitive=True,
            user_id=req.user_id,
        )
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=503, detail=str(e))

    # AI fallback/error (e.g. Ollama not running) returns plain text, not JSON
    if response.state in (AIState.FALLBACK_RESPONSE, AIState.ERROR):
        raise HTTPException(
            status_code=503,
            detail=response.error_message or response.text or "AI unavailable.",
        )

    raw_text = _extract_json_array(response.text)
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=422,
            detail=f"AI returned invalid JSON: {e}. Model may have added extra text.",
        )
    if not isinstance(parsed, list):
        raise HTTPException(status_code=422, detail="AI response was not a JSON array of cards.")

    cards = _normalize_cards(parsed)
    if not cards:
        raise HTTPException(
            status_code=422,
            detail="AI returned no valid flashcards. Try a different topic or count.",
        )

    return FlashcardGenerateResponse(
        cards=[FlashcardItem(**c) for c in cards],
        topic=req.topic_or_chapter.strip(),
    )


# ---------------------------------------------------------------------------
# Flashcards storage (mirror LocalStorage: flashcards.json)
# ---------------------------------------------------------------------------

def _all_cards_from_decks(decks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten all cards from all decks (for backward compat)."""
    cards = []
    for d in decks:
        deck_cards = d.get("cards") or []
        for c in deck_cards:
            c2 = dict(c)
            c2["topic"] = c2.get("topic") or d.get("subject") or d.get("title") or "General"
            cards.append(c2)
    return cards


def _load_flashcards(user_id: str) -> list[dict[str, Any]]:
    """Load all cards by flattening from deck structure."""
    decks = _load_flashcard_decks(user_id)
    return _all_cards_from_decks(decks)


def _save_flashcards(cards: list[dict[str, Any]], user_id: str) -> None:
    """Overwrite by saving as single deck (legacy compat)."""
    deck_id = f"deck_{uuid.uuid4().hex[:12]}"
    normalized = [_normalize_card_for_deck(c) for c in cards]
    deck = {
        "id": deck_id,
        "title": "All Cards",
        "subject": "General",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "cards": normalized,
    }
    _save_flashcard_decks([deck], user_id)


def _recompute_deck_counts(deck: dict[str, Any]) -> None:
    """Update easy_count, hard_count, mastered from cards."""
    cards = deck.get("cards") or []
    easy_count = sum(1 for c in cards if (c.get("ease") or "").lower() == "easy")
    hard_count = sum(1 for c in cards if (c.get("ease") or "").lower() == "hard")
    deck["easy_count"] = easy_count
    deck["hard_count"] = hard_count
    deck["mastered"] = easy_count == len(cards) and len(cards) > 0


def _merge_flashcards(new_cards: list[dict[str, Any]], user_id: str) -> int:
    """
    Merge new cards into decks. Cards with matching id update; new ids append to first deck.
    """
    decks = _load_flashcard_decks(user_id)
    if not decks:
        deck_id = f"deck_{uuid.uuid4().hex[:12]}"
        decks = [{
            "id": deck_id,
            "title": "Imported",
            "subject": "General",
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "cards": [],
        }]
    first_deck = decks[0]
    first_cards = first_deck.get("cards") or []
    merged_count = 0
    for c in new_cards:
        cid = c.get("id")
        norm = _normalize_card_for_deck(c)
        if not cid:
            first_cards.append(norm)
            merged_count += 1
            continue
        idx = next((i for i, x in enumerate(first_cards) if (x.get("id") or "") == cid), None)
        if idx is not None:
            first_cards[idx] = {**first_cards[idx], **norm}
            merged_count += 1
        else:
            first_cards.append(norm)
            merged_count += 1
    first_deck["cards"] = first_cards
    _save_flashcard_decks(decks, user_id)
    return merged_count


def _get_due_cards(user_id: str) -> list[dict[str, Any]]:
    """Return cards where next_review <= now or missing."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    all_cards = _load_flashcards(user_id)
    due = []
    for c in all_cards:
        next_review = c.get("next_review") or ""
        if not next_review or next_review <= now:
            due.append(c)
    return due


@app.get("/api/flashcards")
def flashcards_list(user_id: str = Depends(get_user_id)):
    """Return all decks for the authenticated user."""
    return {"decks": _load_flashcard_decks(user_id)}


@app.get("/api/flashcards/cards")
def flashcards_list_cards(user_id: str = Depends(get_user_id)):
    """Return all cards flattened (backward compat for frontend)."""
    return {"cards": _load_flashcards(user_id)}


def _dashboard_flashcards(user_id: str) -> list[dict[str, Any]]:
    """Transform stored flashcards to dashboard format (id, conceptTitle, content, sourceType)."""
    raw = _load_flashcards(user_id)
    out = []
    for c in raw:
        cid = c.get("id") or str(uuid.uuid4())
        topic = c.get("topic") or "General"
        front = c.get("front") or c.get("question") or ""
        back = c.get("back") or c.get("answer") or ""
        # conceptTitle = topic; content = back (answer). Front is the question.
        concept_title = topic
        content = back or front
        source = c.get("sourceType")
        if source is None:
            source = ["textbook"]
        elif isinstance(source, str):
            source = [source]
        out.append({
            "id": cid,
            "conceptTitle": concept_title,
            "content": content,
            "sourceType": source,
        })
    return out


@app.get("/api/dashboard/flashcards")
def dashboard_flashcards(user_id: str = Depends(get_user_id)):
    """Return flashcards in dashboard format for the authenticated user."""
    return {"cards": _dashboard_flashcards(user_id)}


@app.get("/api/flashcards/due")
def flashcards_due(user_id: str = Depends(get_user_id)):
    """Return cards due for review for the authenticated user."""
    return {"cards": _get_due_cards(user_id)}


class FlashcardsAppendRequest(BaseModel):
    cards: list[dict[str, Any]] = Field(..., description="Cards to append (id, topic, front, back, next_review, etc.)")
    deck_id: Optional[str] = Field(default=None, description="If provided, create/update deck with this id")
    deck_title: Optional[str] = Field(default=None)
    deck_subject: Optional[str] = Field(default=None)


@app.post("/api/flashcards")
def flashcards_append(req: FlashcardsAppendRequest, user_id: str = Depends(get_user_id)):
    """Merge generated cards into storage. If deck_id provided, create/update that deck."""
    if not req.cards:
        return {"ok": True, "appended": 0}
    if req.deck_id:
        decks = _load_flashcard_decks(user_id)
        existing = next((d for d in decks if (d.get("id") or "") == req.deck_id), None)
        normalized = [_normalize_card_for_deck(c) for c in req.cards]
        title = req.deck_title or (req.cards[0].get("topic") if req.cards else "General")
        subject = req.deck_subject or title
        if existing:
            by_id = {c.get("id"): c for c in (existing.get("cards") or [])}
            for c in normalized:
                by_id[c.get("id", "")] = c
            existing["cards"] = list(by_id.values())
            _recompute_deck_counts(existing)
        else:
            decks.insert(0, {
                "id": req.deck_id,
                "title": title,
                "subject": subject,
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "cards": normalized,
            })
            _recompute_deck_counts(decks[0])
        _save_flashcard_decks(decks, user_id)
        return {"ok": True, "appended": len(req.cards)}
    n = _merge_flashcards(req.cards, user_id)
    return {"ok": True, "appended": n}


class FlashcardsReplaceRequest(BaseModel):
    cards: list[dict[str, Any]] = Field(..., description="Full list to replace storage with")


@app.put("/api/flashcards")
def flashcards_replace(req: FlashcardsReplaceRequest, user_id: str = Depends(get_user_id)):
    """Replace stored flashcards for the authenticated user."""
    _save_flashcards(req.cards, user_id)
    stats = _load_user_stats(user_id)
    ensure_streak_structure(stats)
    ensure_flashcard_structure(stats)
    update_flashcard_stats_from_cards(stats, req.cards)
    _update_streak(stats)
    _save_user_stats(stats, user_id)
    return {"ok": True, "count": len(req.cards)}


class FlashcardReviewRequest(BaseModel):
    card_id: str = Field(..., description="Card identifier")
    ease: str = Field(..., description="'hard' | 'medium' | 'easy'")
    next_review: str = Field(..., description="Next review date (YYYY-MM-DD)")


@app.post("/api/flashcards/review")
def flashcards_review(req: FlashcardReviewRequest, user_id: str = Depends(get_user_id)):
    """Record a single flashcard review; updates streak and flashcard stats."""
    stats = _load_user_stats(user_id)
    ensure_streak_structure(stats)
    ensure_flashcard_structure(stats)
    mastered = req.ease == "easy"
    update_flashcard_entry(stats, req.card_id, req.ease, req.next_review, mastered=mastered)
    decks = _load_flashcard_decks(user_id)
    for d in decks:
        for c in d.get("cards") or []:
            if (c.get("id") or "") == req.card_id:
                c["ease"] = req.ease
                c["next_review"] = req.next_review
                c["review_count"] = int(c.get("review_count", 0)) + 1
                c["mastered"] = mastered
                _save_flashcard_decks(decks, user_id)
                update_flashcard_stats_from_cards(stats, _all_cards_from_decks(decks))
                _update_streak(stats)
                _save_user_stats(stats, user_id)
                _enqueue_sync(BASE_PATH, user_id, "flashcard_review", {
                    "userId": user_id,
                    "cardId": req.card_id,
                    "ease": req.ease,
                    "nextReview": req.next_review,
                })
                return {"ok": True}
    return {"ok": True}


class FlashcardDeckCreateRequest(BaseModel):
    """Create empty deck. Also accepts full deck save when 'cards' is provided."""
    id: Optional[str] = Field(default=None)
    title: str = Field(..., min_length=1)
    subject: str = Field(default="General")
    source: Optional[str] = Field(default=None)
    card_count: Optional[int] = Field(default=None)
    easy_count: Optional[int] = Field(default=None)
    hard_count: Optional[int] = Field(default=None)
    cards: Optional[list[dict[str, Any]]] = Field(default=None)
    created_at: Optional[str] = Field(default=None)
    last_studied: Optional[str] = Field(default=None)


class FlashcardCardAddRequest(BaseModel):
    deck_id: str = Field(...)
    front: str = Field(..., min_length=1)
    back: str = Field(..., min_length=1)


class FlashcardReviewPatchRequest(BaseModel):
    deck_id: Optional[str] = Field(default=None, description="Deck identifier (required for deck progress)")
    card_id: str = Field(...)
    ease: str = Field(..., description="'hard' | 'medium' | 'easy'")
    next_review: Optional[str] = Field(default=None, description="Next review date (computed if omitted)")


class FlashcardsFromQuizRequest(BaseModel):
    wrong_questions: list[dict[str, Any]] = Field(default_factory=list, description="List of {question_id, text, correct_answer, explanation}")


@app.post("/api/flashcards/from-quiz")
def flashcards_from_quiz(req: FlashcardsFromQuizRequest, user_id: str = Depends(get_user_id)):
    """Create a flashcard deck from wrong quiz questions. Front=question, back=correct_answer."""
    if not req.wrong_questions:
        return {"ok": True, "deck_id": None, "card_count": 0}
    decks = _load_flashcard_decks(user_id)
    deck_id = f"quiz_{uuid.uuid4().hex[:12]}"
    cards: list[dict[str, Any]] = []
    for i, wq in enumerate(req.wrong_questions):
        text = str(wq.get("text", wq.get("question", ""))).strip() or "?"
        correct = str(wq.get("correct_answer", "")).strip() or "—"
        expl = str(wq.get("explanation", "")).strip()
        back = correct
        if expl:
            back = f"{correct}\n\n{expl}"
        cards.append({
            "id": str(wq.get("question_id", f"fc_{uuid.uuid4().hex[:8]}")),
            "front": text,
            "back": back,
            "ease": "medium",
            "next_review": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "review_count": 0,
            "mastered": False,
        })
    decks.insert(0, {
        "id": deck_id,
        "title": "Quiz Review — Wrong Answers",
        "subject": "General",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "cards": cards,
        "easy_count": 0,
        "hard_count": len(cards),
        "mastered_count": 0,
    })
    _save_flashcard_decks(decks, user_id)
    return {"ok": True, "deck_id": deck_id, "card_count": len(cards)}


@app.post("/api/flashcards/deck")
def flashcard_create_deck(req: FlashcardDeckCreateRequest, user_id: str = Depends(get_user_id)):
    """Create empty deck or save full deck (when cards provided)."""
    decks = _load_flashcard_decks(user_id)
    # Handle full deck save (cards provided)
    if req.cards and len(req.cards) > 0:
        deck_id = req.id or f"deck_{uuid.uuid4().hex[:12]}"
        normalized = [_normalize_card_for_deck(c) for c in req.cards]
        deck = {
            "id": deck_id,
            "title": req.title,
            "subject": req.subject,
            "source": req.source,
            "card_count": req.card_count or len(normalized),
            "easy_count": req.easy_count or 0,
            "hard_count": req.hard_count or 0,
            "created_at": req.created_at or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "last_studied": req.last_studied or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "cards": normalized,
        }
        _recompute_deck_counts(deck)
        decks = [d for d in decks if (d.get("id") or "") != deck_id]
        decks.insert(0, deck)
        _save_flashcard_decks(decks, user_id)
        _enqueue_sync(BASE_PATH, user_id, "flashcard_create", {
            "userId": user_id,
            "deckId": deck_id,
            "title": req.title,
            "subject": req.subject,
        })
        return {"ok": True}
    # Create empty deck (legacy)
    deck_id = f"deck_{uuid.uuid4().hex[:12]}"
    deck = {
        "id": deck_id,
        "title": req.title,
        "subject": req.subject,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "cards": [],
    }
    decks.append(deck)
    _save_flashcard_decks(decks, user_id)
    _enqueue_sync(BASE_PATH, user_id, "flashcard_create", {
        "userId": user_id,
        "deckId": deck_id,
        "title": req.title,
        "subject": req.subject,
    })
    return deck


@app.post("/api/flashcards/card")
def flashcard_add_card(req: FlashcardCardAddRequest, user_id: str = Depends(get_user_id)):
    """Add a card to a deck."""
    decks = _load_flashcard_decks(user_id)
    card_id = f"card_{uuid.uuid4().hex[:12]}"
    card = {
        "id": card_id,
        "front": req.front,
        "back": req.back,
        "ease": "medium",
        "next_review": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "review_count": 0,
        "mastered": False,
    }
    for d in decks:
        if d.get("id") == req.deck_id:
            d.setdefault("cards", []).append(card)
            _save_flashcard_decks(decks, user_id)
            return card
    raise HTTPException(status_code=404, detail="Deck not found")


@app.patch("/api/flashcards/review")
def flashcard_patch_review(req: FlashcardReviewPatchRequest, user_id: str = Depends(get_user_id)):
    """Update card ease and next_review; update deck easy_count, hard_count, mastered when deck_id provided."""
    stats = _load_user_stats(user_id)
    ensure_streak_structure(stats)
    ensure_flashcard_structure(stats)
    mastered = req.ease == "easy"
    next_review = req.next_review or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    update_flashcard_entry(stats, req.card_id, req.ease, next_review, mastered=mastered)
    decks = _load_flashcard_decks(user_id)
    if req.deck_id:
        deck = next((d for d in decks if (d.get("id") or "") == req.deck_id), None)
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")
        target_decks = [deck]
    else:
        target_decks = [d for d in decks if any((c.get("id") or "") == req.card_id for c in (d.get("cards") or []))]
    for deck in target_decks:
        for c in deck.get("cards") or []:
            if (c.get("id") or "") == req.card_id:
                c["ease"] = req.ease
                c["next_review"] = next_review
                c["review_count"] = int(c.get("review_count", 0)) + 1
                c["mastered"] = mastered
                _recompute_deck_counts(deck)
                _save_flashcard_decks(decks, user_id)
                update_flashcard_stats_from_cards(stats, _all_cards_from_decks(decks))
                _update_streak(stats)
                _save_user_stats(stats, user_id)
                _enqueue_sync(BASE_PATH, user_id, "flashcard_review", {
                    "userId": user_id,
                    "deckId": req.deck_id or deck.get("id"),
                    "cardId": req.card_id,
                    "ease": req.ease,
                    "nextReview": next_review,
                })
                return {"ok": True}
    raise HTTPException(status_code=404, detail="Card not found")


@app.delete("/api/flashcards/{card_id}")
def flashcard_delete_card(card_id: str, user_id: str = Depends(get_user_id)):
    """Delete a card by id."""
    decks = _load_flashcard_decks(user_id)
    for d in decks:
        cards = d.get("cards") or []
        for i, c in enumerate(cards):
            if (c.get("id") or "") == card_id:
                cards.pop(i)
                d["cards"] = cards
                _save_flashcard_decks(decks, user_id)
                return {"ok": True}
    raise HTTPException(status_code=404, detail="Card not found")


@app.post("/api/flashcards/explain", response_model=FlashcardExplainResponse)
def flashcards_explain(req: FlashcardExplainRequest):
    """
    Get an AI explanation for a flashcard (front/back). Uses local LLM (Ollama).
    """
    engine = get_ai_engine()
    prompt = (
        f"You are a {req.subject} tutor explaining a flashcard concept to a {req.difficulty} student.\n\n"
        f"Concept: {req.front}\n"
        f"Answer: {req.back}\n\n"
        "Give a clear, concise explanation in 3-4 sentences. Use a simple analogy if helpful. "
        "Do not repeat the question. Just explain why the answer is correct and help the student truly understand it."
    )
    try:
        response = engine.request(
            task_type=AITaskType.FLASHCARD_EXPLANATION,
            user_input=prompt,
            context_data={
                "subject": req.subject,
                "front": req.front,
                "back": req.back,
                "difficulty": req.difficulty,
            },
            offline_mode=True,
            privacy_sensitive=True,
            user_id=None,
        )
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=503, detail=str(e))

    return FlashcardExplainResponse(
        text=response.text,
        confidence_score=response.confidence_score,
    )


_NO_DATA_MESSAGE = "Complete a quiz or create flashcards to receive personalized recommendations."


@app.post("/api/flashcards/recommend", response_model=AdaptiveRecommendationResponse)
def flashcards_recommend(req: FlashcardRecommendRequest, user_id: str = Depends(get_user_id)):
    """
    Adaptive study recommendation. NEVER generic plans.
    - If flashcard topic exists: use it (+ quiz data if available)
    - Else if quiz history exists: use quiz avg score, weak topics
    - Else: return has_data=False for UI to show empty message
    """
    stats = _load_user_stats(user_id)
    has_fc = _has_flashcard_topic(req.subject, req.hard_cards)
    has_quiz = _has_quiz_data(stats)

    if not has_fc and not has_quiz:
        return AdaptiveRecommendationResponse(
            weak_topic="",
            suggested_action="",
            difficulty_adjustment="",
            text=_NO_DATA_MESSAGE,
            confidence_score=0.0,
            has_data=False,
        )

    quiz_profile = _get_quiz_profile(stats) if has_quiz else None
    difficulty = req.difficulty or (stats.get("preferences") or {}).get("difficulty_level") or "Beginner"

    if has_fc:
        subject = req.subject.strip() or "General"
        prompt = build_flashcard_based_prompt(
            subject=subject,
            difficulty=difficulty,
            hard_cards=req.hard_cards or [],
            easy_count=req.easy_count or 0,
            hard_count=req.hard_count or 0,
            quiz_profile=quiz_profile,
        )
        fallback_weak = subject
    else:
        prompt = build_quiz_only_prompt(difficulty=difficulty, quiz_profile=quiz_profile)
        weak_list = quiz_profile.get("weak_topics") or []
        fallback_weak = weak_list[0][0] if weak_list else "Your weakest topic"

    engine = get_ai_engine()
    try:
        response = engine.request(
            task_type=AITaskType.STUDY_RECOMMENDATION,
            user_input=prompt,
            context_data={
                "deck_id": req.deck_id,
                "subject": req.subject,
                "hard_cards": req.hard_cards,
                "easy_count": req.easy_count,
                "hard_count": req.hard_count,
                "difficulty": difficulty,
            },
            offline_mode=True,
            privacy_sensitive=True,
            user_id=user_id,
        )
        rec = parse_ai_response(response.text, fallback_weak=fallback_weak)
        return AdaptiveRecommendationResponse(
            weak_topic=rec.weak_topic,
            suggested_action=rec.suggested_action,
            difficulty_adjustment=rec.difficulty_adjustment,
            text=rec.text,
            confidence_score=response.confidence_score,
            has_data=True,
        )
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/api/study/recommendation", response_model=StudyRecommendationResponse)
def study_recommendation(req: StudyRecommendationRequest):
    """
    Get a study plan / recommendation for a topic and time budget (local AI).
    """
    engine = get_ai_engine()
    user_input = f"Suggest a review plan for topic {req.topic}."
    try:
        response = engine.request(
            task_type=AITaskType.STUDY_RECOMMENDATION,
            user_input=user_input,
            context_data={
                "topic": req.topic,
                "time_budget_minutes": req.time_budget_minutes,
                "review_mode": req.review_mode or "flashcards",
            },
            offline_mode=req.offline_mode,
            privacy_sensitive=True,
            user_id=req.user_id,
        )
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=503, detail=str(e))

    return StudyRecommendationResponse(
        text=response.text,
        confidence_score=response.confidence_score,
    )


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


def _resolve_chat_task_type(req: ChatRequest) -> AITaskType:
    """Map ChatRequest fields to AITaskType."""
    if req.is_clarification:
        return AITaskType.CLARIFY
    raw = (req.task_type or "chat").strip().lower()
    mapping = {
        "chat": AITaskType.CHAT,
        "clarify": AITaskType.CLARIFY,
        "explain_topic": AITaskType.EXPLAIN_TOPIC,
        "quiz_me": AITaskType.QUIZ_ME,
        "flashcards": AITaskType.FLASHCARDS,
        "step_by_step": AITaskType.STEP_BY_STEP,
    }
    return mapping.get(raw, AITaskType.CHAT)


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, user_id: str = Depends(get_user_id)):
    """Turn-based chat with local LLM. Supports clarification, Explain, Quiz, Flashcards, Step-by-Step."""
    stats = _load_user_stats(user_id)
    ensure_streak_structure(stats)
    _update_streak(stats)
    _save_user_stats(stats, user_id)
    engine = get_ai_engine()
    ctx: dict[str, Any] = dict(req.context) if req.context else {}
    ctx["is_clarification"] = req.is_clarification
    if req.subject is not None:
        ctx["subject"] = req.subject
    if req.textbook_id is not None:
        ctx["textbook_id"] = req.textbook_id
    task_type = _resolve_chat_task_type(req)
    try:
        response = engine.request(
            task_type=task_type,
            user_input=req.message,
            context_data=ctx,
            offline_mode=True,
            privacy_sensitive=True,
            user_id=user_id,
        )
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=503, detail=str(e))

    return ChatResponse(
        text=response.text,
        confidence_score=response.confidence_score,
        metadata=response.metadata,
    )


# ---------------------------------------------------------------------------
# Chat history (Layer 2 persistence — backend JSON, restores when localStorage cleared)
# ---------------------------------------------------------------------------


class ChatHistorySession(BaseModel):
    """A saved chat session for history persistence."""
    id: str
    title: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str
    subject: str = "General"


def _load_chat_history(user_id: str) -> list[dict[str, Any]]:
    """Load chat history for user from JSON file."""
    path = _chat_history_file(user_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_chat_history(sessions: list[dict[str, Any]], user_id: str) -> None:
    """Save chat history for user to JSON file."""
    path = _chat_history_file(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sessions, ensure_ascii=False, indent=2), encoding="utf-8")


@app.post("/api/chat/history/save")
def chat_history_save(session: ChatHistorySession, user_id: str = Depends(get_user_id)):
    """Append a saved chat session to the user's chat_history.json."""
    sessions = _load_chat_history(user_id)
    sessions.insert(0, session.model_dump())
    _save_chat_history(sessions, user_id)
    return {"ok": True}


@app.get("/api/chat/history")
def chat_history_get(user_id: str = Depends(get_user_id)):
    """Return array of saved chat sessions for restore when localStorage is empty."""
    sessions = _load_chat_history(user_id)
    return sessions


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


class NotificationPushRequest(BaseModel):
    type: Optional[str] = Field(default="info")
    title: str = Field(..., min_length=1)
    message: Optional[str] = None
    tag: Optional[str] = None
    pinned: Optional[bool] = False
    action: Optional[dict[str, str]] = None


@app.get("/api/notifications")
def notifications_get(user_id: str = Depends(get_user_id)):
    """Return notifications from backend/data/notifications/{user_id}.json."""
    notifs = _load_notifications(user_id)
    return {"notifications": notifs}


@app.post("/api/notifications/push")
def notifications_push(
    req: NotificationPushRequest, user_id: str = Depends(get_user_id)
):
    """Add a notification and return the created item."""
    notifs = _load_notifications(user_id)
    nid = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat()
    notif: dict[str, Any] = {
        "id": nid,
        "type": req.type or "info",
        "title": req.title,
        "message": req.message,
        "tag": req.tag,
        "pinned": req.pinned or False,
        "read": False,
        "timestamp": ts,
        "action": req.action,
    }
    notifs.insert(0, notif)
    _save_notifications(notifs, user_id)
    return notif


@app.patch("/api/notifications/{notif_id}/read")
def notifications_mark_read(
    notif_id: str, user_id: str = Depends(get_user_id)
):
    """Mark one notification as read."""
    notifs = _load_notifications(user_id)
    for n in notifs:
        if n.get("id") == notif_id:
            n["read"] = True
            _save_notifications(notifs, user_id)
            return {"ok": True}
    raise HTTPException(status_code=404, detail="Notification not found")


@app.delete("/api/notifications/{notif_id}")
def notifications_delete(notif_id: str, user_id: str = Depends(get_user_id)):
    """Remove one notification."""
    notifs = _load_notifications(user_id)
    prev_len = len(notifs)
    notifs[:] = [n for n in notifs if n.get("id") != notif_id]
    if len(notifs) == prev_len:
        raise HTTPException(status_code=404, detail="Notification not found")
    _save_notifications(notifs, user_id)
    return {"ok": True}


@app.delete("/api/notifications/all")
@app.delete("/api/notifications/clear")
def notifications_clear_all(user_id: str = Depends(get_user_id)):
    """Clear all non-pinned notifications. Supports /all and /clear."""
    notifs = _load_notifications(user_id)
    notifs[:] = [n for n in notifs if n.get("pinned")]
    _save_notifications(notifs, user_id)
    return {"ok": True}


@app.post("/api/grade", response_model=GradeResponse)
def grade(req: GradeRequest):
    """Grade subjective/objective answers using AI engine with Red Pen–style feedback."""
    engine = get_ai_engine()
    try:
        response = engine.request(
            task_type=AITaskType.GRADING,
            user_input=req.answer,
            context_data={
                "question_id": req.question_id,
                "question": req.question,
                "expected_answer": req.expected_answer,
                "topic": req.topic,
                "difficulty": req.difficulty,
                "rubric": req.rubric or "[GRADING_RUBRIC_PLACEHOLDER]",
            },
            offline_mode=req.offline_mode,
            privacy_sensitive=True,
            user_id=req.user_id,
        )
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Parse "Score: X/10" from AI response for structured output
    score = None
    import re
    match = re.search(r"Score:\s*(\d+(?:\.\d+)?)\s*/\s*10", response.text, re.IGNORECASE)
    if match:
        score = float(match.group(1))

    return GradeResponse(
        text=response.text,
        confidence_score=response.confidence_score,
        score=score,
        errors=[],  # AI engine returns freeform; optional: parse if needed
        strengths=[],
        remarks="",
        metadata=response.metadata,
    )


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------


@app.get("/api/quiz/history")
def quiz_history(user_id: str = Depends(get_user_id)):
    """Return all past quiz results for the authenticated user."""
    return {"results": _load_quiz_history(user_id)}


@app.get("/api/quiz/{quiz_id}")
def quiz_get(quiz_id: str, user_id: str = Depends(get_user_id)):
    """Get quiz content by id. Loads from user file first, then static stubs."""
    loaded = _load_quiz_from_file(user_id, quiz_id)
    if loaded:
        return loaded
    if quiz_id == "default" or quiz_id == "quick":
        return {"id": quiz_id, "items": QUIZ_ITEMS, "title": "Quick Quiz"}
    if quiz_id == "panic":
        return {"id": quiz_id, "items": PANIC_ITEMS, "title": "Panic Mode Exam"}
    for item in QUIZ_ITEMS + PANIC_ITEMS:
        if item["id"] == quiz_id:
            return {"id": quiz_id, "items": [item], "title": f"Quiz: {item['topic']}"}
    raise HTTPException(status_code=404, detail=f"Quiz {quiz_id} not found")


@app.post("/api/quiz/generate")
def quiz_generate(req: QuizGenerateRequest, user_id: str = Depends(get_user_id)):
    """Generate quiz from materials or topic. Saves to data/quizzes/{user_id}/{quiz_id}.json."""
    topic = (req.topic_text or "").strip()
    if req.source == "materials" and req.source_ids:
        texts: list[str] = []
        for tid in req.source_ids[:5]:
            path = SAMPLE_TEXTBOOKS_DIR / tid
            if path.is_file():
                try:
                    texts.append(_extract_text_from_file(path))
                except Exception:
                    pass
        if texts:
            topic = "\n\n".join(texts)[:15000]
        if not topic.strip():
            topic = req.subject
    if not topic.strip():
        topic = req.subject or "General Knowledge"
    count = max(1, min(20, req.num_questions))
    difficulty = req.difficulty or "Beginner"
    subject = req.subject or "General"
    if req.question_type == "open_ended":
        items = _generate_open_ended_questions_via_ai(topic, subject, difficulty, count)
        question_type = "open_ended"
    else:
        items = _generate_mcq_questions_via_ai(topic, subject, difficulty, count)
        question_type = "mcq"
    quiz_id = f"gen_{uuid.uuid4().hex[:12]}"
    payload: dict[str, Any] = {
        "id": quiz_id,
        "title": f"Quiz — {subject}",
        "subject": subject,
        "difficulty": difficulty,
        "question_type": question_type,
        "items": items,
    }
    path = _quiz_file(user_id, quiz_id)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"id": quiz_id, "title": payload["title"], "items": items, "subject": subject, "difficulty": difficulty, "question_type": question_type}


class GradeAnswerRequest(BaseModel):
    question: str = Field(...)
    user_answer: str = Field(default="")
    sample_answer: str = Field(default="")
    rubric: str = Field(default="")
    difficulty: str = Field(default="Beginner")


@app.post("/api/quiz/grade-answer")
def quiz_grade_answer(req: GradeAnswerRequest):
    """Grade a single open-ended answer. Returns { score: float, feedback: string }."""
    engine = get_ai_engine()
    try:
        response = engine.request(
            task_type=AITaskType.GRADING,
            user_input=req.user_answer,
            context_data={
                "question": req.question,
                "expected_answer": req.sample_answer,
                "rubric": req.rubric or "Assess comprehension and accuracy.",
                "difficulty": req.difficulty,
            },
            offline_mode=True,
            privacy_sensitive=True,
            user_id=None,
        )
        text = response.text or ""
        score = 5.0
        match = re.search(r"Score:\s*(\d+(?:\.\d+)?)\s*/\s*10", text, re.IGNORECASE)
        if match:
            score = float(match.group(1))
        return {"score": min(10.0, max(0.0, score)), "feedback": text}
    except (ConnectionError, TimeoutError) as e:
        fallback = _local_score(req.user_answer, req.sample_answer)
        return {"score": fallback, "feedback": "AI grading unavailable; scored locally."}


def _local_score(answer: str, expected: str) -> float:
    """Simple deterministic score for progress stats (mirror Streamlit quiz.py)."""
    if not (answer or "").strip():
        return 0.0
    at = set((answer or "").lower().split())
    et = set((expected or "").lower().split())
    if not et:
        return 0.0
    overlap = len(at & et) / len(et)
    return round(min(10.0, max(0.0, overlap * 10)), 1)


class PanicGenerateTextbookRequest(BaseModel):
    subject: str = Field(..., min_length=1)
    textbook_id: str = Field(...)
    chapter: Optional[str] = Field(default=None)
    count: int = Field(default=5, ge=3, le=15)


class PanicGenerateWeblinkRequest(BaseModel):
    subject: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    count: int = Field(default=5, ge=3, le=15)


class QuizGenerateRequest(BaseModel):
    source: str = Field(..., description="materials | topic")
    subject: str = Field(default="General")
    source_ids: Optional[list[str]] = Field(default=None, description="Textbook ids when source=materials")
    topic_text: Optional[str] = Field(default=None, description="Topic or pasted text when source=topic")
    question_type: str = Field(default="mcq", description="mcq | open_ended")
    num_questions: int = Field(default=10, ge=1, le=20)
    difficulty: str = Field(default="Beginner")


@app.post("/api/quiz/panic/generate/textbook")
def panic_generate_textbook(req: PanicGenerateTextbookRequest):
    """Generate panic-mode questions from a textbook. One subject only."""
    path = SAMPLE_TEXTBOOKS_DIR / req.textbook_id
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Textbook '{req.textbook_id}' not found")
    try:
        content = _extract_text_from_file(path)
        if not content.strip():
            raise HTTPException(status_code=422, detail="Could not extract text from textbook")
        items = _generate_quiz_from_content(content, req.subject, req.count)
        return {"id": "panic", "title": f"Panic Mode — {req.subject}", "items": items}
    except HTTPException:
        raise
    except Exception:
        items = _normalize_quiz_items([], req.subject)
        for i, q in enumerate(PANIC_ITEMS):
            if q.get("topic", "").lower() == req.subject.lower():
                items.append(q)
        if not items:
            items = [q for q in PANIC_ITEMS][:req.count]
        return {"id": "panic", "title": f"Panic Mode — {req.subject}", "items": items}


@app.post("/api/quiz/panic/generate/weblink")
def panic_generate_weblink(req: PanicGenerateWeblinkRequest):
    """Generate panic-mode questions from a web URL. One subject only."""
    import requests as req_lib
    try:
        r = req_lib.get(req.url.strip(), timeout=15, headers={"User-Agent": "Studaxis/1.0"})
        r.raise_for_status()
        html = r.text
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not fetch URL: {e}")
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    items = _generate_quiz_from_content(text, req.subject, req.count)
    return {"id": "panic", "title": f"Panic Mode — {req.subject}", "items": items}


class QuizGenerateFromUrlRequest(BaseModel):
    url: str = Field(..., min_length=1)
    subject: str = Field(default="General")
    num_questions: int = Field(default=10, ge=1, le=20)
    question_type: str = Field(default="mcq", description="mcq | open_ended")
    difficulty: str = Field(default="Beginner")


@app.post("/api/quiz/generate-from-url")
def quiz_generate_from_url(req: QuizGenerateFromUrlRequest, user_id: str = Depends(get_user_id)):
    """Scrape URL, extract content, generate quiz. Returns same format as /api/quiz/generate."""
    url = req.url.strip()
    text = ""
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError:
        httpx = None
        BeautifulSoup = None
    if httpx is not None and BeautifulSoup is not None:
        try:
            response = httpx.get(
                url, timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"},
            )
            if response.status_code in (401, 403):
                raise HTTPException(
                    status_code=422,
                    detail="This website blocked access. Try pasting the article text directly.",
                )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)[:8000]
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise HTTPException(
                    status_code=422,
                    detail="This website blocked access. Try pasting the article text directly.",
                ) from e
            raise HTTPException(
                status_code=422,
                detail="Could not fetch that URL. Try another link or paste the text directly.",
            ) from e
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError):
            raise HTTPException(
                status_code=422,
                detail="Could not fetch that URL. Try another link or paste the text directly.",
            )
    else:
        import requests as req_lib
        try:
            r = req_lib.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code in (401, 403):
                raise HTTPException(
                    status_code=422,
                    detail="This website blocked access. Try pasting the article text directly.",
                )
            r.raise_for_status()
            text = re.sub(r"<[^>]+>", " ", r.text)
            text = re.sub(r"\s+", " ", text).strip()[:8000]
        except Exception:
            raise HTTPException(
                status_code=422,
                detail="Could not fetch that URL. Try another link or paste the text directly.",
            )
    if len(text) < 200:
        raise HTTPException(
            status_code=422,
            detail="Not enough content found at that URL. Try a different link.",
        )
    return _save_and_return_quiz(user_id, text, req.subject, req.num_questions, req.question_type, req.difficulty)


class QuizGenerateFromTextRequest(BaseModel):
    text: str = Field(..., min_length=1)
    subject: str = Field(default="General")
    num_questions: int = Field(default=10, ge=1, le=20)
    question_type: str = Field(default="mcq", description="mcq | open_ended")
    difficulty: str = Field(default="Beginner")


@app.post("/api/quiz/generate-from-text")
def quiz_generate_from_text(req: QuizGenerateFromTextRequest, user_id: str = Depends(get_user_id)):
    """Generate quiz from pasted text. Returns same format as /api/quiz/generate."""
    text = req.text.strip()
    if len(text) < 150:
        raise HTTPException(
            status_code=422,
            detail="Please paste at least a paragraph of text to generate a quiz from.",
        )
    return _save_and_return_quiz(user_id, text[:3000], req.subject, req.num_questions, req.question_type, req.difficulty)


@app.post("/api/quiz/generate-from-file")
def quiz_generate_from_file(
    file: UploadFile = File(...),
    subject: str = Form("General"),
    num_questions: int = Form(10, ge=1, le=20),
    question_type: str = Form("mcq"),
    difficulty: str = Form("Beginner"),
    user_id: str = Depends(get_user_id),
):
    """Generate quiz from uploaded PDF or PPT. Returns same format as /api/quiz/generate."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    suf = Path(file.filename).suffix.lower()
    if suf not in (".pdf", ".ppt", ".pptx"):
        raise HTTPException(status_code=422, detail="Only PDF and PPT files are supported")
    tmp_path = DATA_DIR / "tmp_upload" / Path(file.filename).name
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        content = file.file.read()
        tmp_path.write_bytes(content)
        if suf == ".pdf":
            text = _extract_text_from_pdf(tmp_path)
        elif suf in (".ppt", ".pptx"):
            try:
                from pptx import Presentation
                prs = Presentation(str(tmp_path))
                parts = []
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text") and shape.text:
                            parts.append(shape.text)
                text = "\n".join(parts) if parts else ""
            except ImportError:
                try:
                    from langchain_community.document_loaders import UnstructuredPowerPointLoader
                    docs = UnstructuredPowerPointLoader(str(tmp_path)).load()
                    text = "\n".join(d.page_content for d in docs)
                except ImportError:
                    raise HTTPException(
                        status_code=501,
                        detail="PPT support requires python-pptx (pip install python-pptx)",
                    )
        else:
            text = ""
        if not text or len(text.strip()) < 100:
            raise HTTPException(status_code=422, detail="Could not extract enough text from the file")
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
    return _save_and_return_quiz(user_id, text[:12000], subject, num_questions, question_type, difficulty)


def _save_and_return_quiz(
    user_id: str,
    content: str,
    subject: str,
    num_questions: int,
    question_type: str,
    difficulty: str,
) -> Any:
    """Extract content, generate questions, save to quizzes dir, return API response."""
    count = max(1, min(20, num_questions))
    subj = subject or "General"
    if question_type == "open_ended":
        items = _generate_open_ended_questions_via_ai(content, subj, difficulty, count)
    else:
        items = _generate_mcq_questions_via_ai(content, subj, difficulty, count)
    quiz_id = f"gen_{uuid.uuid4().hex[:12]}"
    payload: dict[str, Any] = {
        "id": quiz_id,
        "title": f"Quiz — {subj}",
        "subject": subj,
        "difficulty": difficulty,
        "question_type": question_type,
        "items": items,
    }
    path = _quiz_file(user_id, quiz_id)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"id": quiz_id, "title": payload["title"], "items": items, "subject": subj, "difficulty": difficulty, "question_type": question_type}


@app.post("/api/quiz/panic/generate/files")
def panic_generate_files(
    files: list[UploadFile] = File(...),
    subject: str = Form(...),
    count: int = Form(5),
):
    """Generate panic-mode questions from uploaded files. One subject only."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    texts: list[str] = []
    for uf in files:
        if not uf.filename:
            continue
        suf = Path(uf.filename).suffix.lower()
        if suf not in (".txt", ".pdf", ".ppt", ".pptx"):
            continue
        tmp = Path(uf.filename).name
        try:
            content = uf.file.read()
            tmp_path = DATA_DIR / "tmp_upload" / tmp
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_bytes(content)
            try:
                texts.append(_extract_text_from_file(tmp_path))
            finally:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Failed to process {uf.filename}: {e}")
    combined = "\n\n".join(texts)
    if not combined.strip():
        raise HTTPException(status_code=422, detail="No extractable text from files")
    cnt = max(3, min(15, count))
    items = _generate_quiz_from_content(combined, subject, cnt)
    return {"id": "panic", "title": f"Panic Mode — {subject}", "items": items}


def _quizzes_dir(user_id: str) -> Path:
    """Return per-user quiz directory: data/quizzes/{user_id}/"""
    d = DATA_DIR / "quizzes" / user_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _quiz_file(user_id: str, quiz_id: str) -> Path:
    """Path for a saved quiz: data/quizzes/{user_id}/{quiz_id}.json"""
    return _quizzes_dir(user_id) / f"{quiz_id}.json"


def _load_quiz_from_file(user_id: str, quiz_id: str) -> dict[str, Any] | None:
    """Load quiz from user's quiz directory if exists."""
    path = _quiz_file(user_id, quiz_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _quiz_result_file(user_id: str, quiz_id: str, attempt_id: str) -> Path:
    """Path for a single quiz result file."""
    return _quizzes_dir(user_id) / f"{quiz_id}_{attempt_id}_result.json"


def _save_quiz_result(user_id: str, quiz_id: str, result: dict[str, Any]) -> str:
    """Save quiz result to JSON; returns attempt_id."""
    attempt_id = f"{int(datetime.now(timezone.utc).timestamp())}_{uuid.uuid4().hex[:8]}"
    path = _quiz_result_file(user_id, quiz_id, attempt_id)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return attempt_id


def _load_quiz_history(user_id: str) -> list[dict[str, Any]]:
    """Load all quiz results from user's quiz directory."""
    d = _quizzes_dir(user_id)
    results = []
    for p in sorted(d.iterdir(), reverse=True):
        if p.is_file() and p.suffix == ".json" and "_result" in p.stem:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                results.append(data)
            except (OSError, json.JSONDecodeError):
                pass
    return results


def _resolve_quiz_items(quiz_id: str, items_list: list[dict[str, Any]] | None, user_id: str | None = None) -> list[dict[str, Any]]:
    """Resolve quiz items for grading (from req.items, user file, or static)."""
    if items_list:
        return items_list
    if user_id:
        loaded = _load_quiz_from_file(user_id, quiz_id)
        if loaded and loaded.get("items"):
            return loaded["items"]
    if quiz_id in ("quick", "default"):
        return QUIZ_ITEMS
    if quiz_id == "panic":
        return PANIC_ITEMS
    for item in QUIZ_ITEMS + PANIC_ITEMS:
        if item.get("id") == quiz_id:
            return [item]
    return []


def _score_mcq_answer(user_answer: str, item: dict[str, Any]) -> float:
    """Score MCQ: user_answer can be index (0-3) or option text."""
    opts = item.get("options") or []
    correct_idx = int(item.get("correct", 0))
    correct_text = opts[correct_idx] if correct_idx < len(opts) else ""
    try:
        idx = int(user_answer.strip())
        return 10.0 if 0 <= idx < len(opts) and idx == correct_idx else 0.0
    except (ValueError, TypeError):
        pass
    ua = (user_answer or "").strip().lower()
    ct = (correct_text or "").strip().lower()
    return 10.0 if ua and ct and ua in ct else _local_score(user_answer, correct_text)


@app.post("/api/quiz/{quiz_id}/submit", response_model=QuizSubmitResponse)
def quiz_submit(quiz_id: str, req: QuizSubmitRequest, user_id: str = Depends(get_user_id)):
    """Submit quiz answers; grade via AI/local and update user stats."""
    engine = get_ai_engine()
    stats = _load_user_stats(user_id)
    ensure_streak_structure(stats)
    quiz_stats = stats.setdefault("quiz_stats", {})
    topic_scores: dict[str, list[float]] = {}
    items_list = _resolve_quiz_items(quiz_id, req.items, user_id)
    total_score = 0.0
    max_score = len(req.answers) * 10.0 if req.answers else 0.0

    for r in req.answers:
        qid = r.get("question_id", "")
        answer_text = str(r.get("user_answer") or r.get("answer", "")).strip()
        score = float(r.get("score", 0))
        if score == 0 and items_list:
            for it in items_list:
                if it.get("id") == qid:
                    if it.get("options"):
                        score = _score_mcq_answer(answer_text, it)
                    else:
                        score = _local_score(answer_text, it.get("expected_answer", it.get("sample_answer", "")))
                    break
        r["score"] = score
        r["answer"] = answer_text
        r["topic"] = r.get("topic") or next(
            (it.get("topic", "General") for it in items_list if it.get("id") == qid),
            "General",
        )
        topic = r["topic"]
        total_score += score
        topic_scores.setdefault(topic, []).append(score)
        total_attempted = int(quiz_stats.get("total_attempted", 0)) + 1
        total_correct = int(quiz_stats.get("total_correct", 0)) + (1 if score >= 6.0 else 0)
        prev_avg = float(quiz_stats.get("average_score", 0.0))
        quiz_stats["total_attempted"] = total_attempted
        quiz_stats["total_correct"] = total_correct
        quiz_stats["average_score"] = round(((prev_avg * (total_attempted - 1)) + score) / total_attempted, 2)
        by_topic = quiz_stats.setdefault("by_topic", {})
        te = by_topic.setdefault(topic, {"attempts": 0, "avg_score": 0.0})
        te["attempts"] = int(te.get("attempts", 0)) + 1
        te["avg_score"] = round(((float(te.get("avg_score", 0)) * (te["attempts"] - 1)) + score) / te["attempts"], 2)
    if max_score > 0:
        _update_quiz_stats(stats, total_score, max_score)
    _update_streak(stats)
    _save_user_stats(stats, user_id)

    weak_topics_text: Optional[str] = None
    recommendation_text: Optional[str] = None
    if topic_scores:
        weak_topics_payload = {
            topic: round(sum(vals) / len(vals), 2) for topic, vals in topic_scores.items()
        }
        engine = get_ai_engine()
        try:
            weak_topic_response = engine.request(
                task_type=AITaskType.WEAK_TOPIC_DETECTION,
                user_input="Identify weak topics from this exam result.",
                context_data={
                    "exam_mode": "panic_mode",
                    "topic_scores": weak_topics_payload,
                    "total_questions": len(items_list),
                },
                offline_mode=True,
                privacy_sensitive=True,
                user_id=None,
            )
            weak_topics_text = weak_topic_response.text
            if weak_topics_text and weak_topics_text.strip():
                rec_response = engine.request(
                    task_type=AITaskType.STUDY_RECOMMENDATION,
                    user_input="Create a post-exam improvement plan.",
                    context_data={
                        "exam_mode": "panic_mode",
                        "topic_scores": weak_topics_payload,
                        "weak_topics_summary": weak_topics_text,
                        "study_time_minutes": 20,
                    },
                    offline_mode=True,
                    privacy_sensitive=True,
                    user_id=None,
                )
                recommendation_text = rec_response.text
        except (ConnectionError, TimeoutError):
            pass
        if not weak_topics_text:
            weak_topics_text = "AI unavailable for weak-topic analysis."
        if not recommendation_text:
            recommendation_text = "Complete more quizzes and review weak areas from your stats."

    subject = next((r.get("topic", "General") for r in req.answers), "General") if req.answers else "General"
    percent = int(round((total_score / max_score * 100))) if max_score > 0 else 0
    quiz_meta = _load_quiz_from_file(user_id, quiz_id) or {}
    qtype = quiz_meta.get("question_type", "open_ended")

    def _correct_answer_and_explanation(qid: str, it: dict[str, Any], scr: float) -> tuple[str, str]:
        opts = it.get("options")
        if opts:
            idx = int(it.get("correct", 0))
            correct = opts[idx] if idx < len(opts) else ""
            expl = str(it.get("explanation", "")).strip()
            return correct, expl
        return (
            str(it.get("sample_answer", it.get("expected_answer", ""))).strip(),
            str(it.get("explanation", "")).strip(),
        )

    results_out: list[dict[str, Any]] = []
    for r in req.answers:
        qid = r.get("question_id", "")
        scr = float(r.get("score", 0))
        correct = scr >= 6.0
        correct_ans, explanation = "", ""
        for it in items_list:
            if it.get("id") == qid:
                correct_ans, explanation = _correct_answer_and_explanation(qid, it, scr)
                break
        if not correct and r.get("feedback"):
            explanation = r.get("feedback", explanation)
        results_out.append({
            "question_id": qid,
            "correct": correct,
            "score": scr,
            "correct_answer": correct_ans,
            "explanation": explanation,
        })

    answers_payload = [
        {
            "question_id": r.get("question_id", ""),
            "user_answer": r.get("answer", ""),
            "correct": float(r.get("score", 0)) >= 6.0,
            "score": float(r.get("score", 0)),
            "correct_answer": next((ro["correct_answer"] for ro in results_out if ro["question_id"] == r.get("question_id")), ""),
            "explanation": next((ro["explanation"] for ro in results_out if ro["question_id"] == r.get("question_id")), r.get("feedback", "")),
        }
        for r in req.answers
    ]
    result_payload = {
        "quiz_id": quiz_id,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "score": total_score,
        "max_score": max_score,
        "percent": percent,
        "subject": subject,
        "question_type": qtype,
        "answers": answers_payload,
    }
    _save_quiz_result(user_id, quiz_id, result_payload)
    _enqueue_sync(BASE_PATH, user_id, "quiz_result", {
        "userId": user_id,
        "quizId": quiz_id,
        "result": result_payload,
    })

    if req.answers:
        _enqueue_panic_quiz_for_sync(req.answers, len(items_list), user_id)

    return {
        "score": total_score,
        "max_score": max_score,
        "percent": percent,
        "results": results_out,
        "weak_topics_text": weak_topics_text,
        "recommendation_text": recommendation_text,
    }


@app.get("/api/student/assignments")
def student_assignments(class_code: str = "", user_id: str = Depends(get_user_id)):
    """Return assignments for class. Used when profile.class_code is set (teacher_linked)."""
    items = _load_assignments(class_code)
    return [{"id": a.get("id"), "quiz_id": a.get("quiz_id"), "title": a.get("title"), "due_date": a.get("due_date"), "assigned_at": a.get("assigned_at"), "status": a.get("status", "pending")} for a in items]


class AssignmentCompleteRequest(BaseModel):
    assignment_id: str = Field(...)
    score: float = Field(default=0)
    completed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@app.post("/api/student/assignment-complete")
def student_assignment_complete(req: AssignmentCompleteRequest, user_id: str = Depends(get_user_id)):
    """Mark assignment as completed. If offline, enqueue for sync."""
    try:
        p = load_profile_for_user(user_id)
        cc = (p.class_code if p else "") or ""
        if not cc:
            return {"ok": True}
        items = _load_assignments(cc)
        for a in items:
            if a.get("id") == req.assignment_id:
                a["status"] = "completed"
                a["completed_at"] = req.completed_at
                a["score"] = req.score
                _save_assignments(cc, items)
                return {"ok": True}
    except Exception:
        pass
    _enqueue_sync(BASE_PATH, user_id, "assignment_complete", {
        "userId": user_id,
        "assignment_id": req.assignment_id,
        "score": req.score,
        "completed_at": req.completed_at,
    })
    return {"ok": True}


class TeacherAssignQuizRequest(BaseModel):
    class_code: str = Field(..., min_length=1)
    quiz_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    due_date: str = Field(default="", description="YYYY-MM-DD or empty")


@app.post("/api/teacher/assign-quiz")
def teacher_assign_quiz(req: TeacherAssignQuizRequest, user_id: str = Depends(get_user_id)):
    """Create assignment for class. Saves to data/assignments/{class_code}.json"""
    items = _load_assignments(req.class_code)
    aid = str(uuid.uuid4())[:8]
    items.append({
        "id": aid,
        "quiz_id": req.quiz_id,
        "title": req.title,
        "due_date": req.due_date or "",
        "assigned_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    })
    _save_assignments(req.class_code, items)
    return {"ok": True, "assignment_id": aid}


def _enqueue_panic_quiz_for_sync(results: list[dict[str, Any]], total_questions: int, user_id: str) -> None:
    """Queue panic mode quiz attempt for AWS AppSync sync. No-op if sync disabled or anonymous."""
    try:
        if not user_id or user_id == "anonymous":
            return
        prefs = _load_user_stats(user_id).get("preferences") or {}
        if not prefs.get("sync_enabled", True):
            return
        avg = sum(float(r.get("score", 0)) for r in results) / len(results) if results else 0.0
        score_pct = int(round(avg * 10))  # 0–10 scale → 0–100 for AWS
        from sync_manager import SyncManager
        sm = SyncManager(base_path=str(BASE_PATH))
        sm.enqueue_quiz_sync(
            user_id=user_id,
            quiz_id="panic",
            score=min(100, max(0, score_pct)),
            total_questions=total_questions,
            subject="Panic Mode",
            difficulty="Medium",
        )
    except Exception:
        pass  # Sync is best-effort; do not fail the request


class PanicGradeOneRequest(BaseModel):
    question_id: str = Field(...)
    answer: str = Field(default="")
    question: str = Field(...)
    topic: str = Field(default="General")
    expected_answer: str = Field(default="")


class PanicFinalizeRequest(BaseModel):
    results: list[dict[str, Any]] = Field(..., description="Per-question results from grade-one")
    items: list[dict[str, Any]] = Field(..., description="Quiz items for stats")


@app.post("/api/quiz/panic/grade-one")
def panic_grade_one(req: PanicGradeOneRequest):
    """Grade a single panic-mode question. 30s timeout; falls back to local scoring on timeout/error."""
    engine = get_ai_engine()
    score = _local_score(req.answer, req.expected_answer)
    feedback_text = "Grading unavailable."
    try:
        grading = engine.request(
            task_type=AITaskType.GRADING,
            user_input=req.answer,
            context_data={
                "question_id": req.question_id,
                "question": req.question,
                "topic": req.topic,
                "expected_answer": req.expected_answer,
                "difficulty": "Beginner",
                "rubric": "[GRADING_RUBRIC_PLACEHOLDER]",
            },
            offline_mode=True,
            privacy_sensitive=True,
        )
        if grading.state in (AIState.TIMEOUT, AIState.ERROR, AIState.FALLBACK_RESPONSE):
            feedback_text = "AI grading timed out; scored locally."
        else:
            feedback_text = grading.text or "No feedback."
    except (ConnectionError, TimeoutError):
        feedback_text = "AI grading timed out; scored locally."
    return {
        "question_id": req.question_id,
        "score": score,
        "feedback": feedback_text,
        "topic": req.topic,
    }


@app.post("/api/quiz/panic/finalize")
def panic_finalize(req: PanicFinalizeRequest, user_id: str = Depends(get_user_id)):
    """Update stats from pre-graded results and return weak topics + recommendation. Falls back on timeout."""
    stats = _load_user_stats(user_id)
    ensure_streak_structure(stats)
    quiz_stats = stats.setdefault("quiz_stats", {})
    topic_scores: dict[str, list[float]] = {}
    total_score = 0.0
    max_score = len(req.results) * 10.0 if req.results else 0.0
    for r in req.results:
        topic = r.get("topic", "General")
        score = float(r.get("score", 0))
        total_score += score
        topic_scores.setdefault(topic, []).append(score)
        total_attempted = int(quiz_stats.get("total_attempted", 0)) + 1
        total_correct = int(quiz_stats.get("total_correct", 0)) + (1 if score >= 6.0 else 0)
        prev_avg = float(quiz_stats.get("average_score", 0.0))
        quiz_stats["total_attempted"] = total_attempted
        quiz_stats["total_correct"] = total_correct
        quiz_stats["average_score"] = round(((prev_avg * (total_attempted - 1)) + score) / total_attempted, 2)
        by_topic = quiz_stats.setdefault("by_topic", {})
        te = by_topic.setdefault(topic, {"attempts": 0, "avg_score": 0.0})
        te["attempts"] = int(te.get("attempts", 0)) + 1
        te["avg_score"] = round(((float(te.get("avg_score", 0)) * (te["attempts"] - 1)) + score) / te["attempts"], 2)
    if max_score > 0:
        _update_quiz_stats(stats, total_score, max_score)
    _update_streak(stats)
    _save_user_stats(stats, user_id)

    weak_topics_text: Optional[str] = None
    recommendation_text: Optional[str] = None
    if topic_scores:
        weak_topics_payload = {
            topic: round(sum(vals) / len(vals), 2) for topic, vals in topic_scores.items()
        }
        engine = get_ai_engine()
        try:
            weak_topic_response = engine.request(
                task_type=AITaskType.WEAK_TOPIC_DETECTION,
                user_input="Identify weak topics from this exam result.",
                context_data={
                    "exam_mode": "panic_mode",
                    "topic_scores": weak_topics_payload,
                    "total_questions": len(req.items),
                },
                offline_mode=True,
                privacy_sensitive=True,
                user_id=None,
            )
            weak_topics_text = weak_topic_response.text
            if weak_topics_text and weak_topics_text.strip():
                rec_response = engine.request(
                    task_type=AITaskType.STUDY_RECOMMENDATION,
                    user_input="Create a post-exam improvement plan.",
                    context_data={
                        "exam_mode": "panic_mode",
                        "topic_scores": weak_topics_payload,
                        "weak_topics_summary": weak_topics_text,
                        "study_time_minutes": 20,
                    },
                    offline_mode=True,
                    privacy_sensitive=True,
                    user_id=None,
                )
                recommendation_text = rec_response.text
        except (ConnectionError, TimeoutError):
            pass
        if not weak_topics_text:
            weak_topics_text = "AI unavailable for weak-topic analysis."
        if not recommendation_text:
            recommendation_text = "Complete more quizzes and review weak areas from your stats."

    # Enqueue for AWS sync (AppSync recordQuizAttempt) when sync enabled
    if req.results:
        _enqueue_panic_quiz_for_sync(req.results, len(req.items), user_id)

    return {"weak_topics_text": weak_topics_text, "recommendation_text": recommendation_text}


# ---------------------------------------------------------------------------
# User (auth-protected)
# ---------------------------------------------------------------------------


@app.get("/api/user/me")
def user_me(current_user: Annotated[User, Depends(get_current_user)]):
    """Return current authenticated user. Requires valid Bearer token."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
    }


# ---------------------------------------------------------------------------
# User stats
# ---------------------------------------------------------------------------


@app.get("/api/user/stats")
def user_stats_get(user_id: str = Depends(get_user_id)):
    """Return user progress, streaks, preferences for the authenticated user."""
    stats = _load_user_stats(user_id)
    ensure_streak_structure(stats)
    _update_streak(stats)
    _save_user_stats(stats, user_id)
    return stats


@app.put("/api/user/stats")
def user_stats_put(stats: dict[str, Any], user_id: str = Depends(get_user_id)):
    """Update user progress/preferences for the authenticated user. Merges with existing."""
    existing = _load_user_stats(user_id)
    for key, value in stats.items():
        if isinstance(value, dict) and isinstance(existing.get(key), dict):
            existing[key] = {**existing[key], **value}
        else:
            existing[key] = value
    _save_user_stats(existing, user_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Data export & clear (Settings: Export Data, Clear Local Data)
# ---------------------------------------------------------------------------


@app.get("/api/data/export")
def data_export(user_id: str = Depends(get_user_id)):
    """
    Export all user stats and flashcards for the authenticated user.
    """
    from datetime import datetime, timezone
    stats = _load_user_stats(user_id)
    cards = _load_flashcards(user_id)
    profile = load_profile()
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.0",
        "user_id": user_id,
        "user_stats": stats,
        "flashcards": cards,
        "profile": _profile_to_dict(profile),
    }
    return payload


@app.post("/api/data/clear")
def data_clear(user_id: str = Depends(get_user_id)):
    """
    Clear study data for the authenticated user: reset stats to defaults, clear flashcards.
    Does NOT delete auth (users.db) or affect other users.
    """
    default = dict(_DEFAULT_STATS)
    default["user_id"] = user_id
    _save_user_stats(default, user_id)
    _save_flashcards([], user_id)
    return {"ok": True, "message": f"Data cleared for user '{user_id}'."}


# ---------------------------------------------------------------------------
# User profile (AuthContext sync)
# ---------------------------------------------------------------------------


class ProfileRequest(BaseModel):
    """Profile update payload; all fields optional for partial merge."""
    profile_name: Optional[str] = None
    profile_mode: Optional[str] = None  # solo | teacher_linked | teacher_linked_provisional
    class_code: Optional[str] = None
    user_role: Optional[str] = None  # student | teacher
    onboarding_complete: Optional[bool] = None


def _profile_to_dict(p: Optional[UserProfile]) -> dict[str, Any]:
    """Convert UserProfile to JSON-serializable dict."""
    if p is None:
        return {"profile_name": None, "profile_mode": None, "class_code": None, "user_role": None, "onboarding_complete": False}
    return {
        "profile_name": p.profile_name,
        "profile_mode": p.profile_mode,
        "class_code": p.class_code,
        "user_role": p.user_role,
        "onboarding_complete": getattr(p, "onboarding_complete", False),
    }


@app.get("/api/user/profile")
def user_profile_get(user_id: str = Depends(get_user_id)):
    """Return persisted user profile (for AuthContext sync)."""
    p = load_profile_for_user(user_id)
    return _profile_to_dict(p)


@app.post("/api/user/profile")
def user_profile_post(req: ProfileRequest, user_id: str = Depends(get_user_id)):
    """Persist profile; merges with existing. Used by AuthContext. Returns saved profile."""
    existing = load_profile_for_user(user_id) or UserProfile()
    merged = UserProfile(
        profile_name=req.profile_name if req.profile_name is not None else existing.profile_name,
        profile_mode=req.profile_mode if req.profile_mode is not None else existing.profile_mode,
        class_code=req.class_code if req.class_code is not None else existing.class_code,
        user_role=req.user_role if req.user_role is not None else existing.user_role,
        onboarding_complete=req.onboarding_complete if req.onboarding_complete is not None else getattr(existing, "onboarding_complete", False),
    )
    save_profile_for_user(user_id, merged)
    return _profile_to_dict(merged)


# ---------------------------------------------------------------------------
# Sync (SyncManager + ConflictAwareOrchestrator)
# ---------------------------------------------------------------------------

_orchestrator: Optional[Any] = None


def _get_orchestrator():
    """Lazy-load ConflictAwareOrchestrator for conflict endpoints."""
    global _orchestrator
    if _orchestrator is None:
        try:
            from conflict_resolution_engine import ConflictAwareOrchestrator
            _orchestrator = ConflictAwareOrchestrator(base_path=str(BASE_PATH))
        except ImportError:
            pass
    return _orchestrator


def _persist_resolved_entity(entity_type: str, entity_id: str, resolved_data: dict, user_id: str) -> None:
    """Persist resolved conflict data to local store based on entity type."""
    stats = _load_user_stats(user_id)
    et = (entity_type or "").lower()
    if et in ("userstats", "user_stats") or entity_id in ("user_stats", "stats"):
        _save_user_stats(resolved_data, user_id)
    elif et in ("streakrecord", "streak"):
        merged = dict(stats)
        merged["streak"] = {**(stats.get("streak") or {}), **resolved_data}
        _save_user_stats(merged, user_id)
    elif et in ("quizstats", "quiz_stats"):
        merged = dict(stats)
        merged["quiz_stats"] = {**(stats.get("quiz_stats") or {}), **resolved_data}
        _save_user_stats(merged, user_id)
    else:
        # Default: deep merge top-level keys into user_stats
        for k, v in resolved_data.items():
            if k in stats and isinstance(stats[k], dict) and isinstance(v, dict):
                stats[k] = {**stats[k], **v}
            else:
                stats[k] = v
        _save_user_stats(stats, user_id)


@app.post("/api/sync")
def sync_trigger(user_id: str = Depends(get_user_id)):
    """Trigger sync with AWS when online. Uses SyncManager.try_sync()."""
    try:
        from sync_manager import SyncManager
        sm = SyncManager(base_path=str(BASE_PATH), user_id=user_id)
        result = sm.try_sync()
        return {
            "ok": True,
            "synced": result.get("synced", 0),
            "failed": result.get("failed", 0),
            "pending": result.get("pending", 0),
            "online": result.get("online", False),
            "errors": result.get("errors", []),
            "message": (
                f"Synced {result.get('synced', 0)} item(s)"
                if result.get("synced", 0) > 0
                else ("Sync complete" if not result.get("pending") else "Some items pending")
            ),
        }
    except ImportError as e:
        return {"ok": False, "message": f"SyncManager unavailable: {e}", "synced": 0, "failed": 0, "pending": 0, "online": False, "errors": []}
    except Exception as e:
        return {"ok": False, "message": str(e), "synced": 0, "failed": 0, "pending": 0, "online": False, "errors": [str(e)]}


@app.get("/api/sync/status")
def sync_status(user_id: str = Depends(get_user_id)):
    """Return sync status: queue summary, connectivity, last sync."""
    stats = _load_user_stats(user_id)
    prefs = stats.get("preferences") or {}
    sync_enabled = prefs.get("sync_enabled", True)
    last_sync = stats.get("last_sync_timestamp")

    out: dict[str, Any] = {
        "sync_enabled": sync_enabled,
        "last_sync_timestamp": last_sync,
        "online": False,
        "queue": {"total": 0, "quiz_attempts": 0, "streak_updates": 0, "oldest_item": None},
    }

    if not sync_enabled:
        return out

    try:
        from sync_manager import SyncManager
        sm = SyncManager(base_path=str(BASE_PATH), user_id=user_id)
        out["online"] = sm.check_connectivity()
        out["queue"] = sm.get_queue_summary()
    except Exception:
        pass

    return out


@app.get("/api/sync/conflicts")
def get_conflicts():
    """Return pending sync conflicts from ConflictAwareOrchestrator."""
    orch = _get_orchestrator()
    if orch is None:
        return {"conflicts": [], "message": "Conflict orchestrator unavailable"}
    conflicts = orch.get_pending_conflicts()
    # Ensure reason is string for JSON
    for c in conflicts:
        if hasattr(c.get("reason"), "value"):
            c["reason"] = c["reason"].value
    return {"conflicts": conflicts}


class ResolveConflictRequest(BaseModel):
    choice: str = Field(..., description="keep_local | keep_cloud | merge")


@app.post("/api/sync/conflicts/{entity_id}/resolve")
def resolve_conflict(entity_id: str, body: ResolveConflictRequest, user_id: str = Depends(get_user_id)):
    """Resolve a conflict by entity_id. Persists resolved data and removes from pending."""
    choice = (body.choice or "").strip().lower()
    if choice not in ("keep_local", "keep_cloud", "merge"):
        raise HTTPException(400, "choice must be keep_local, keep_cloud, or merge")

    orch = _get_orchestrator()
    if orch is None:
        raise HTTPException(503, "Conflict orchestrator unavailable")

    try:
        # Get entity_type before resolve (resolve removes conflict from pending)
        conflicts = orch.get_pending_conflicts()
        conflict_dict = next((c for c in conflicts if c.get("entity_id") == entity_id), None)
        entity_type = conflict_dict.get("entity_type", "UserStats") if conflict_dict else "UserStats"

        resolved_data = orch.resolve_conflict_manual(entity_id, choice)
        _persist_resolved_entity(entity_type, entity_id, resolved_data, user_id)
        orch.trigger_sync_debounced()
        return {"ok": True, "entity_id": entity_id, "choice": choice}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


# ---------------------------------------------------------------------------
# RAG search (ChromaDB semantic search)
# ---------------------------------------------------------------------------

_rag_vector_store: Optional[Any] = None


def _get_rag_vector_store():
    """Lazy-load ChromaDB vector store. Returns None if DB unavailable."""
    global _rag_vector_store
    if _rag_vector_store is not None:
        return _rag_vector_store
    try:
        from ai_chat.vector import build_vector_store
        _rag_vector_store = build_vector_store(rebuild=False)
        return _rag_vector_store
    except ImportError as e:
        return None
    except Exception:
        return None


def _rag_search(query: str, k: int = 5) -> tuple[list[dict[str, Any]], Optional[str]]:
    """
    Run semantic search over ChromaDB. Returns (results, error_message).
    On success, error_message is None. On failure, results is [] and error_message describes the issue.
    """
    if not query or not query.strip():
        return [], "Provide a non-empty query."

    store = _get_rag_vector_store()
    if store is None:
        return [], "ChromaDB unavailable. Install langchain-chroma and langchain-huggingface, and ensure the vector store is initialized."

    try:
        retriever = store.as_retriever(search_kwargs={"k": k})
        docs = retriever.invoke(query.strip())
    except Exception as e:
        return [], f"ChromaDB query failed: {str(e)}"

    results: list[dict[str, Any]] = []
    for doc in docs or []:
        content = getattr(doc, "page_content", None) or str(doc)
        metadata = getattr(doc, "metadata", None) or {}
        if isinstance(metadata, dict):
            results.append({
                "content": content[:2000] + ("..." if len(content) > 2000 else ""),
                "source": metadata.get("source", "unknown"),
                "subject": metadata.get("subject", "general"),
            })
        else:
            results.append({"content": content[:2000], "source": "unknown", "subject": "general"})

    return results, None


@app.get("/api/rag/search")
def rag_search(q: str = "", k: int = 5):
    """Semantic search over local ChromaDB. Returns top-k matching chunks from embedded textbooks."""
    results, err = _rag_search(q, k=min(max(1, k), 20))
    if err:
        return {"results": [], "message": err}
    return {"results": results}


# ---------------------------------------------------------------------------
# Serve compiled React SPA from frontend/dist (when running as backend.main:app)
# Repo root main.py also mounts SPA when using python main.py.
# IMPORTANT: Do NOT mount StaticFiles at "/" — it catches all requests (including
# /api/*) and returns 405 for POST. Serve /assets and use a GET catch-all for SPA.
# ---------------------------------------------------------------------------

_DIST = _APP_DIR.parent / "frontend" / "dist"

if _DIST.is_dir():
    # Static assets (Vite puts JS/CSS in /assets/)
    _ASSETS = _DIST / "assets"
    if _ASSETS.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_ASSETS)), name="spa_assets")

    # Favicon at root
    _VITE_SVG = _DIST / "vite.svg"
    if _VITE_SVG.is_file():

        @app.get("/vite.svg")
        def _serve_favicon():
            return FileResponse(_VITE_SVG)

    # SPA fallback: GET catch-all returns index.html (client-side routing)
    # API routes are defined above, so POST /api/* etc. match before this
    @app.get("/{full_path:path}")
    def _serve_spa(full_path: str):
        return FileResponse(_DIST / "index.html")
