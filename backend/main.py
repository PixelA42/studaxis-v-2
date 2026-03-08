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
from profile_store import UserProfile, load_profile, save_profile

# ---------------------------------------------------------------------------
# Base path for AI engine and data (user_stats, profile, etc.)
# When run as "uvicorn main:app", cwd is backend; when "uvicorn backend.main:app", cwd is repo root.
BASE_PATH = Path(os.environ.get("STUDAXIS_BASE_PATH", str(_APP_DIR)))
DATA_DIR = BASE_PATH / "data"
STATS_FILE = DATA_DIR / "user_stats.json"
FLASHCARDS_FILE = DATA_DIR / "flashcards.json"
SAMPLE_TEXTBOOKS_DIR = DATA_DIR / "sample_textbooks"
_DEFAULT_USER_ID = "student_001"


def _user_dir(user_id: str) -> Path:
    """Return per-user data directory, creating it if needed."""
    d = DATA_DIR / "users" / user_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _stats_file(user_id: str) -> Path:
    """Return path to user_stats.json, migrating legacy flat file on first access."""
    per_user = _user_dir(user_id) / "user_stats.json"
    if not per_user.exists():
        legacy = DATA_DIR / "user_stats.json"
        if legacy.exists() and user_id == _DEFAULT_USER_ID:
            import shutil
            shutil.copy2(legacy, per_user)
    return per_user


def _flashcards_file(user_id: str) -> Path:
    """Return path to flashcards.json, migrating legacy flat file on first access."""
    per_user = _user_dir(user_id) / "flashcards.json"
    if not per_user.exists():
        legacy = DATA_DIR / "flashcards.json"
        if legacy.exists() and user_id == _DEFAULT_USER_ID:
            import shutil
            shutil.copy2(legacy, per_user)
    return per_user

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

_DEFAULT_USER_ID = "student_001"

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


def _load_user_stats(user_id: str = _DEFAULT_USER_ID) -> dict[str, Any]:
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
    results: list[dict[str, Any]] = Field(..., description="Per-question grade and feedback")
    quiz_stats_updated: bool = True
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


def _list_textbooks() -> list[dict[str, str]]:
    """List *.pdf and *.txt files in sample_textbooks."""
    out: list[dict[str, str]] = []
    if not SAMPLE_TEXTBOOKS_DIR.is_dir():
        return out
    for p in sorted(SAMPLE_TEXTBOOKS_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() in (".pdf", ".txt"):
            out.append({"id": p.name, "name": p.stem})
    return out


@app.get("/api/textbooks")
def textbooks_list():
    """List textbooks from data/sample_textbooks (*.pdf, *.txt)."""
    return {"textbooks": _list_textbooks()}


@app.post("/api/textbooks/upload")
def textbooks_upload(file: UploadFile = File(...)):
    """Multipart file upload; save PDF to sample_textbooks."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
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


def _generate_cards_from_content(content: str, count: int, source_type: str) -> FlashcardGenerateResponse:
    """Generate flashcards from extracted text via AI."""
    if not content or not content.strip():
        raise HTTPException(status_code=422, detail="No extractable text from source")
    engine = get_ai_engine()
    truncated = content[:12000] if len(content) > 12000 else content
    try:
        response = engine.request(
            task_type=AITaskType.FLASHCARD_GENERATION,
            user_input=f"Generate {count} flashcards from this content. Return a JSON array of objects with id, topic, front, back.",
            context_data={
                "input_type": "Textbook Chapter",
                "topic_or_chapter": "Content-based",
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
    """Generate flashcards from a textbook file. Falls back to topic if content cannot be loaded."""
    path = SAMPLE_TEXTBOOKS_DIR / req.textbook_id
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Textbook '{req.textbook_id}' not found")
    try:
        content = _extract_text_from_file(path)
        if not content.strip():
            raise HTTPException(status_code=422, detail="Could not extract text from textbook")
        return _generate_cards_from_content(content, req.count, "textbook")
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

def _load_flashcards(user_id: str = _DEFAULT_USER_ID) -> list[dict[str, Any]]:
    """Load per-user flashcards.json; return [] on missing/error."""
    try:
        f = _flashcards_file(user_id)
        if f.exists():
            raw = f.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, list):
                return data
    except (OSError, json.JSONDecodeError):
        pass
    return []


def _save_flashcards(cards: list[dict[str, Any]], user_id: str = _DEFAULT_USER_ID) -> None:
    """Overwrite per-user flashcards.json."""
    try:
        f = _flashcards_file(user_id)
        f.write_text(json.dumps(cards, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _append_flashcards(new_cards: list[dict[str, Any]], user_id: str = _DEFAULT_USER_ID) -> None:
    """Append cards to per-user flashcards.json."""
    existing = _load_flashcards(user_id)
    existing.extend(new_cards)
    _save_flashcards(existing, user_id)


def _get_due_cards(user_id: str = _DEFAULT_USER_ID) -> list[dict[str, Any]]:
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
    """Return all stored flashcards for the authenticated user."""
    return {"cards": _load_flashcards(user_id)}


def _dashboard_flashcards(user_id: str = _DEFAULT_USER_ID) -> list[dict[str, Any]]:
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


@app.post("/api/flashcards")
def flashcards_append(req: FlashcardsAppendRequest, user_id: str = Depends(get_user_id)):
    """Append generated cards to storage for the authenticated user."""
    if not req.cards:
        return {"ok": True, "appended": 0}
    _append_flashcards(req.cards, user_id)
    return {"ok": True, "appended": len(req.cards)}


class FlashcardsReplaceRequest(BaseModel):
    cards: list[dict[str, Any]] = Field(..., description="Full list to replace storage with")


@app.put("/api/flashcards")
def flashcards_replace(req: FlashcardsReplaceRequest, user_id: str = Depends(get_user_id)):
    """Replace stored flashcards for the authenticated user."""
    _save_flashcards(req.cards, user_id)
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
    """Turn-based chat with local LLM. Supports clarification follow-ups and RAG context."""
    engine = get_ai_engine()
    ctx: dict[str, Any] = dict(req.context) if req.context else {}
    ctx["is_clarification"] = req.is_clarification
    try:
        response = engine.request(
            task_type=AITaskType.CHAT,
            user_input=req.message,
            context_data=ctx,
            offline_mode=True,
            privacy_sensitive=True,
            user_id=ctx.get("user_id"),
        )
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=503, detail=str(e))

    return ChatResponse(
        text=response.text,
        confidence_score=response.confidence_score,
        metadata=response.metadata,
    )


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


class PanicGenerateTextbookRequest(BaseModel):
    subject: str = Field(..., min_length=1)
    textbook_id: str = Field(...)
    chapter: Optional[str] = Field(default=None)
    count: int = Field(default=5, ge=3, le=15)


class PanicGenerateWeblinkRequest(BaseModel):
    subject: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    count: int = Field(default=5, ge=3, le=15)


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


@app.post("/api/quiz/{quiz_id}/submit", response_model=QuizSubmitResponse)
def quiz_submit(quiz_id: str, req: QuizSubmitRequest, user_id: str = Depends(get_user_id)):
    """Submit quiz answers; grade via AI and update user stats."""
    engine = get_ai_engine()
    stats = _load_user_stats(user_id)
    quiz_stats = stats.setdefault("quiz_stats", {})
    topic_scores: dict[str, list[float]] = {}
    items_list = req.items or []
    for r in req.answers:
        topic = r.get("topic", "General")
        score = float(r.get("score", 0))
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

    # Enqueue for AWS sync (AppSync recordQuizAttempt) when sync enabled
    if req.answers:
        _enqueue_panic_quiz_for_sync(req.answers, len(items_list), user_id)

    return {"weak_topics_text": weak_topics_text, "recommendation_text": recommendation_text}


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
    quiz_stats = stats.setdefault("quiz_stats", {})
    topic_scores: dict[str, list[float]] = {}
    for r in req.results:
        topic = r.get("topic", "General")
        score = float(r.get("score", 0))
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
    return _load_user_stats(user_id)


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
        onboarding_complete=req.onboarding_complete if req.onboarding_complete is not None else getattr(existing, "onboarding_complete", False),
    )
    save_profile(merged)
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
