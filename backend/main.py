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
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure backend is on path for imports when run from repo root
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_APP_DIR))

from ai_integration_layer import AIEngine, AIState, AITaskType
from auth_routes import router as auth_router
from database import init_db
from profile_store import UserProfile, load_profile, save_profile

# ---------------------------------------------------------------------------
# Base path for AI engine and data (user_stats, profile, etc.)
# When run as "uvicorn main:app", cwd is backend; when "uvicorn backend.main:app", cwd is repo root.
BASE_PATH = Path(os.environ.get("STUDAXIS_BASE_PATH", str(_APP_DIR)))
DATA_DIR = BASE_PATH / "data"
STATS_FILE = DATA_DIR / "user_stats.json"
FLASHCARDS_FILE = DATA_DIR / "flashcards.json"

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
    "user_id": "student_001",
    "last_sync_timestamp": None,
    "streak": {"current": 0, "longest": 0, "last_activity_date": None},
    "quiz_stats": {
        "total_attempted": 0,
        "total_correct": 0,
        "average_score": 0.0,
        "last_quiz_date": None,
        "by_topic": {},
    },
    "flashcard_stats": {"total_reviewed": 0, "mastered": 0, "due_for_review": 0},
    "chat_history": [],
    "preferences": {
        "difficulty_level": "Beginner",
        "theme": "light",
        "language": "English",
        "sync_enabled": True,
    },
    "hardware_info": {},
}


def _load_user_stats() -> dict[str, Any]:
    """Load user_stats.json from DATA_DIR; return defaults on missing/error."""
    try:
        if STATS_FILE.exists():
            raw = STATS_FILE.read_text(encoding="utf-8")
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


def _save_user_stats(stats: dict[str, Any]) -> None:
    """Persist user stats to DATA_DIR/user_stats.json (atomic write)."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = STATS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(STATS_FILE)
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


class FlashcardGenerateResponse(BaseModel):
    cards: list[FlashcardItem]
    topic: str


class FlashcardExplainRequest(BaseModel):
    front: str = Field(..., description="Card question/front")
    back: str = Field(..., description="Card answer/back")
    topic: str = Field(default="General", description="Card topic")
    user_query: Optional[str] = Field(default=None, description="Optional user prompt (e.g. 'Explain this flashcard: ...')")


class FlashcardExplainResponse(BaseModel):
    text: str
    confidence_score: float = 0.0


class StudyRecommendationRequest(BaseModel):
    topic: str = Field(..., description="Topic or subject for the plan")
    time_budget_minutes: int = Field(default=15, ge=1, le=240, description="Available study time in minutes")
    review_mode: Optional[str] = Field(default="flashcards", description="Context: flashcards, quiz, etc.")
    user_id: Optional[str] = Field(default=None)
    offline_mode: bool = Field(default=True)


class StudyRecommendationResponse(BaseModel):
    text: str
    confidence_score: float = 0.0


# --- Chat ---
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    is_clarification: bool = Field(default=False, description="True if this is a follow-up clarification")
    context: Optional[dict[str, Any]] = Field(default=None, description="Optional: difficulty, chat_history, subject, etc.")


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


class QuizSubmitResponse(BaseModel):
    results: list[dict[str, Any]] = Field(..., description="Per-question grade and feedback")
    quiz_stats_updated: bool = True


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

def _load_flashcards() -> list[dict[str, Any]]:
    """Load flashcards.json; return [] on missing/error."""
    try:
        if FLASHCARDS_FILE.exists():
            raw = FLASHCARDS_FILE.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, list):
                return data
    except (OSError, json.JSONDecodeError):
        pass
    return []


def _save_flashcards(cards: list[dict[str, Any]]) -> None:
    """Overwrite flashcards.json."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        FLASHCARDS_FILE.write_text(
            json.dumps(cards, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


def _append_flashcards(new_cards: list[dict[str, Any]]) -> None:
    """Append cards to flashcards.json."""
    existing = _load_flashcards()
    existing.extend(new_cards)
    _save_flashcards(existing)


def _get_due_cards() -> list[dict[str, Any]]:
    """Return cards where next_review <= now or missing (same logic as LocalStorage)."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    all_cards = _load_flashcards()
    due = []
    for c in all_cards:
        next_review = c.get("next_review") or ""
        if not next_review or next_review <= now:
            due.append(c)
    return due


@app.get("/api/flashcards")
def flashcards_list():
    """Return all stored flashcards (for sync/debug)."""
    return {"cards": _load_flashcards()}


@app.get("/api/flashcards/due")
def flashcards_due():
    """Return cards due for review (next_review <= now or missing)."""
    return {"cards": _get_due_cards()}


class FlashcardsAppendRequest(BaseModel):
    cards: list[dict[str, Any]] = Field(..., description="Cards to append (id, topic, front, back, next_review, etc.)")


@app.post("/api/flashcards")
def flashcards_append(req: FlashcardsAppendRequest):
    """Append generated cards to storage (enriched with next_review, etc.)."""
    if not req.cards:
        return {"ok": True, "appended": 0}
    _append_flashcards(req.cards)
    return {"ok": True, "appended": len(req.cards)}


class FlashcardsReplaceRequest(BaseModel):
    cards: list[dict[str, Any]] = Field(..., description="Full list to replace storage with")


@app.put("/api/flashcards")
def flashcards_replace(req: FlashcardsReplaceRequest):
    """Replace stored flashcards (e.g. after SRS update)."""
    _save_flashcards(req.cards)
    return {"ok": True, "count": len(req.cards)}


@app.post("/api/flashcards/explain", response_model=FlashcardExplainResponse)
def flashcards_explain(req: FlashcardExplainRequest):
    """
    Get an AI explanation for a flashcard (front/back). Uses local LLM.
    """
    engine = get_ai_engine()
    user_input = req.user_query or f"Explain this flashcard: {req.front}"
    try:
        response = engine.request(
            task_type=AITaskType.FLASHCARD_EXPLANATION,
            user_input=user_input,
            context_data={
                "topic": req.topic,
                "front": req.front,
                "back": req.back,
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


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Turn-based chat with local LLM (and optional RAG context)."""
    engine = get_ai_engine()
    task = AITaskType.CLARIFY if req.is_clarification else AITaskType.CHAT
    context = req.context or {}
    context.setdefault("difficulty", "Beginner")
    try:
        response = engine.request(
            task_type=task,
            user_input=req.message.strip(),
            context_data=context,
            offline_mode=True,
            privacy_sensitive=True,
            user_id=context.get("user_id"),
        )
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=503, detail=str(e))
    return ChatResponse(
        text=response.text,
        confidence_score=response.confidence_score,
        metadata=response.metadata,
    )


# ---------------------------------------------------------------------------
# Grade
# ---------------------------------------------------------------------------


@app.post("/api/grade", response_model=GradeResponse)
def grade(req: GradeRequest):
    """Grade subjective/objective answers (local LLM, Red Pen–style feedback)."""
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
    return GradeResponse(
        text=response.text,
        confidence_score=response.confidence_score,
        metadata=response.metadata,
    )


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------


@app.get("/api/quiz/{quiz_id}")
def quiz_get(quiz_id: str):
    """Get quiz content by id. Returns stub list for known ids."""
    if quiz_id == "default" or quiz_id == "quick":
        return {"id": quiz_id, "items": QUIZ_ITEMS, "title": "Quick Quiz"}
    if quiz_id == "panic":
        return {"id": quiz_id, "items": PANIC_ITEMS, "title": "Panic Mode Exam"}
    # Single-item quiz by question id
    for item in QUIZ_ITEMS + PANIC_ITEMS:
        if item["id"] == quiz_id:
            return {"id": quiz_id, "items": [item], "title": f"Quiz: {item['topic']}"}
    raise HTTPException(status_code=404, detail=f"Quiz {quiz_id} not found")


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


@app.post("/api/quiz/{quiz_id}/submit", response_model=QuizSubmitResponse)
def quiz_submit(quiz_id: str, req: QuizSubmitRequest):
    """Submit quiz answers; grade via AI and update user stats."""
    engine = get_ai_engine()
    stats = _load_user_stats()
    quiz_stats = stats.setdefault("quiz_stats", {})
    results: list[dict[str, Any]] = []
    difficulty = (stats.get("preferences") or {}).get("difficulty_level", "Beginner")

    items_list = PANIC_ITEMS if quiz_id == "panic" else QUIZ_ITEMS
    items_by_id = {q["id"]: q for q in items_list}
    for entry in req.answers:
        qid = entry.get("question_id") or entry.get("id")
        answer = entry.get("answer", "")
        if not qid or qid not in items_by_id:
            results.append({"question_id": qid, "error": "unknown question", "score": 0.0})
            continue
        item = items_by_id[qid]
        expected = item.get("expected_answer", "")
        score = _local_score(answer, expected)
        try:
            grading = engine.request(
                task_type=AITaskType.GRADING,
                user_input=answer,
                context_data={
                    "question_id": item["id"],
                    "question": item["question"],
                    "topic": item["topic"],
                    "expected_answer": expected,
                    "difficulty": difficulty,
                    "rubric": "[GRADING_RUBRIC_PLACEHOLDER]",
                },
                offline_mode=True,
                privacy_sensitive=True,
            )
            feedback_text = grading.text
        except (ConnectionError, TimeoutError):
            feedback_text = "Grading unavailable."
        results.append({"question_id": qid, "score": score, "feedback": feedback_text})

        total_attempted = int(quiz_stats.get("total_attempted", 0)) + 1
        total_correct = int(quiz_stats.get("total_correct", 0)) + (1 if score >= 6.0 else 0)
        prev_avg = float(quiz_stats.get("average_score", 0.0))
        quiz_stats["total_attempted"] = total_attempted
        quiz_stats["total_correct"] = total_correct
        quiz_stats["average_score"] = round(((prev_avg * (total_attempted - 1)) + score) / total_attempted, 2)
        by_topic = quiz_stats.setdefault("by_topic", {})
        topic = item.get("topic", "General")
        te = by_topic.setdefault(topic, {"attempts": 0, "avg_score": 0.0})
        te["attempts"] = int(te.get("attempts", 0)) + 1
        te["avg_score"] = round(((float(te.get("avg_score", 0)) * (te["attempts"] - 1)) + score) / te["attempts"], 2)

    _save_user_stats(stats)
    return QuizSubmitResponse(results=results, quiz_stats_updated=True)


# ---------------------------------------------------------------------------
# User stats
# ---------------------------------------------------------------------------


@app.get("/api/user/stats")
def user_stats_get():
    """Return user progress, streaks, preferences (same schema as Streamlit)."""
    return _load_user_stats()


@app.put("/api/user/stats")
def user_stats_put(stats: dict[str, Any]):
    """Update user progress/preferences. Merges with existing or replaces."""
    existing = _load_user_stats()
    for key, value in stats.items():
        if isinstance(value, dict) and isinstance(existing.get(key), dict):
            existing[key] = {**existing[key], **value}
        else:
            existing[key] = value
    _save_user_stats(existing)
    return {"ok": True}


# ---------------------------------------------------------------------------
# User profile (AuthContext sync)
# ---------------------------------------------------------------------------


class ProfileRequest(BaseModel):
    """Profile update payload; all fields optional for partial merge."""
    profile_name: Optional[str] = None
    profile_mode: Optional[str] = None  # solo | teacher_linked | teacher_linked_provisional
    class_code: Optional[str] = None
    user_role: Optional[str] = None  # student | teacher


def _profile_to_dict(p: Optional[UserProfile]) -> dict[str, Any]:
    """Convert UserProfile to JSON-serializable dict."""
    if p is None:
        return {"profile_name": None, "profile_mode": None, "class_code": None, "user_role": None}
    return {
        "profile_name": p.profile_name,
        "profile_mode": p.profile_mode,
        "class_code": p.class_code,
        "user_role": p.user_role,
    }


@app.get("/api/user/profile")
def user_profile_get():
    """Return persisted user profile (for AuthContext sync)."""
    p = load_profile()
    return _profile_to_dict(p)


@app.post("/api/user/profile")
def user_profile_post(req: ProfileRequest):
    """Persist profile; merges with existing. Used by AuthContext. Returns saved profile."""
    existing = load_profile() or UserProfile()
    merged = UserProfile(
        profile_name=req.profile_name if req.profile_name is not None else existing.profile_name,
        profile_mode=req.profile_mode if req.profile_mode is not None else existing.profile_mode,
        class_code=req.class_code if req.class_code is not None else existing.class_code,
        user_role=req.user_role if req.user_role is not None else existing.user_role,
    )
    save_profile(merged)
    return _profile_to_dict(merged)


# ---------------------------------------------------------------------------
# Sync (stub)
# ---------------------------------------------------------------------------


@app.post("/api/sync")
def sync_trigger():
    """Trigger sync with AWS when online. Stub until SyncManager wired."""
    return {"ok": True, "message": "Sync triggered (stub). Connect SyncManager when online."}


# ---------------------------------------------------------------------------
# RAG search (stub)
# ---------------------------------------------------------------------------


@app.get("/api/rag/search")
def rag_search(q: str = ""):
    """Semantic search over local ChromaDB. Stub until RAG wired."""
    if not q.strip():
        return {"results": [], "message": "Provide query parameter q."}
    return {"results": [], "message": "RAG search stub. Wire ChromaDB when ready."}


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
