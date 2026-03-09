#!/usr/bin/env python3
"""
Test all backend API endpoints with real sample data.
Run from repo root with backend server up:
  STUDAXIS_TEST=1 python test_endpoints.py

Quiz Generator endpoints tested (by --quiz-only or at end of full run):
  POST /api/quiz/generate         — Quick Topic, Textbook (source=topic|materials)
  POST /api/quiz/generate-from-url — Web Link
  POST /api/quiz/generate-from-text — Paste Text
  POST /api/quiz/generate-from-file — Upload File (not in script; multipart)

To test current code without a server (in-process):
  STUDAXIS_TEST=1 python test_endpoints.py --inprocess

Quiz-only (no other endpoints):
  STUDAXIS_TEST=1 python test_endpoints.py --quiz-only
  STUDAXIS_TEST=1 python test_endpoints.py --quiz-only --inprocess

Panic Mode endpoints are tested first (GET /api/quiz/panic, grade-one, submit, then generate/textbook and generate/weblink).
When running --inprocess, the first request may trigger Ollama; ensure Ollama is running or allow 60–90s for AI timeouts and fallback responses.

Requires: httpx (pip install httpx). For --inprocess: fastapi (TestClient)
Backend: uvicorn backend.main:app --host 0.0.0.0 --port 6782
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Ensure project root on path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)

BASE = os.environ.get("STUDAXIS_API_BASE", "http://localhost:6782")
TEST_HEADERS = {"X-Test-User": "testuser"} if os.environ.get("STUDAXIS_TEST") else {}
INPROCESS = "--inprocess" in sys.argv
QUIZ_ONLY = "--quiz-only" in sys.argv

# Sample payloads (aligned with backend API paths and request models)
TOPIC_QUIZ = {
    "source": "topic",
    "topic": "Newton's Laws of Motion",
    "subject": "Physics",
    "difficulty": "medium",
    "num_questions": 5,
    "question_type": "mcq",
}

PASTE_QUIZ = {
    "source": "paste",
    "topic": "Laws of Motion",
    "subject": "Physics",
    "difficulty": "easy",
    "num_questions": 5,
    "question_type": "mcq",
    "paste_text": "Newton's First Law states that an object at rest stays at rest and an object in motion stays in motion with the same speed and direction unless acted upon by an unbalanced force. This property is called inertia. Newton's Second Law states that the acceleration of an object depends on the net force acting on it and its mass: F = ma. Newton's Third Law states that for every action there is an equal and opposite reaction. Forces always occur in pairs. The SI unit of force is Newton (N) where 1N = 1 kg m/s2. Momentum is defined as p = mv. Impulse is the change in momentum: J = F x t.",
}

WEBLINK_QUIZ = {
    "url": "https://en.wikipedia.org/wiki/Newton%27s_laws_of_motion",
    "topic": "Laws of Motion",
    "subject": "Physics",
    "difficulty": "medium",
    "num_questions": 5,
    "question_type": "mcq",
}

NOTES_PASTE = {
    "source": "paste",
    "topic": "Newton's Laws of Motion",
    "subject": "Physics",
    "style": "summary",
    "paste_text": "Newton's First Law: An object at rest stays at rest, and an object in motion continues in motion at constant velocity unless acted upon by a net external force. This is the law of inertia. Inertia is the resistance of any physical object to a change in its velocity. Newton's Second Law: The net force acting on an object equals the mass of the object multiplied by its acceleration: F = ma. The direction of force and acceleration are the same. Newton's Third Law: For every action force there is an equal and opposite reaction force. Action and reaction forces act on different bodies. Momentum (p) = mass x velocity. Impulse = change in momentum = F x delta t. Law of Conservation of Momentum: total momentum of an isolated system remains constant.",
}

NOTES_TOPIC = {
    "source": "topic",
    "topic": "Photosynthesis",
    "subject": "Biology",
    "style": "detailed",
    "paste_text": "Photosynthesis is the process by which plants convert light energy into chemical energy. Chlorophyll in chloroplasts absorbs light. The light reactions occur in the thylakoid membranes and produce ATP and NADPH. The Calvin cycle (dark reactions) occurs in the stroma and uses ATP and NADPH to fix CO2 into glucose. Key inputs: water, CO2, light. Key output: glucose and oxygen. This process is fundamental to life on Earth.",
}

FLASHCARDS_PASTE = {
    "source": "paste",
    "topic": "Newton's Laws",
    "num_cards": 10,
    "paste_text": "Newton's First Law: An object at rest stays at rest, and an object in motion stays in motion unless acted upon by a net external force. Newton's Second Law: F = ma (Force equals mass times acceleration). Newton's Third Law: For every action there is an equal and opposite reaction. Momentum p = mv. Impulse = F x t = change in momentum. Inertia is the tendency of an object to resist changes in its state of motion. The SI unit of force is Newton (N). Weight = mass x gravitational acceleration = mg.",
}

CHAT_PAYLOAD = {
    "message": "Explain Newton's Second Law in simple terms",
    "history": [],
}

# ── PANIC MODE PAYLOADS (aligned with frontend: api/quiz/panic/*) ──
PANIC_TEXTBOOK = {
    "subject": "Physics",
    "textbook_id": "panic_test.txt",
    "chapter": "Chapter 4 - Motion in a Plane",
    "count": 5,
    "question_type": "mcq",
}
PANIC_WEBLINK = {
    "subject": "Biology",
    "url": "https://en.wikipedia.org/wiki/Photosynthesis",
    "count": 5,
    "question_type": "mcq",
}
PANIC_GRADE_ONE = {
    "question_id": "p1",
    "question": "What is Newton's First Law?",
    "answer": "An object at rest stays at rest unless acted upon by an external force.",
    "topic": "Physics",
    "expected_answer": "Law of inertia.",
    "question_type": "open_ended",
}
PANIC_GRADE_ONE_MCQ = {
    "question_id": "pq1",
    "question": "What is the SI unit of force?",
    "answer": "A",
    "topic": "Physics",
    "expected_answer": "Newton",
    "question_type": "mcq",
    "options": ["A. Joule", "B. Watt", "C. Newton", "D. Pascal"],
    "correct": 2,
}
PANIC_SUBMIT = {
    "answers": [
        {"question_id": "p1", "user_answer": "Momentum is mass times velocity."},
        {"question_id": "p2", "user_answer": "Osmosis maintains turgor pressure."},
    ],
    "items": [
        {"id": "p1", "topic": "Physics", "question": "Define momentum.", "expected_answer": "p = mv"},
        {"id": "p2", "topic": "Biology", "question": "Why is osmosis important in plants?", "expected_answer": "Turgor pressure."},
    ],
}

# ── QUIZ GENERATOR TESTS (endpoints used by Quiz form) ──
QUIZ_TESTS = [
    ("Quick Topic MCQ", "POST", "/api/quiz/generate", {
        "source": "topic", "topic_text": "Newton's Laws of Motion",
        "subject": "Physics", "question_type": "mcq", "num_questions": 5, "difficulty": "medium",
    }, False),
    ("Quick Topic Open Ended", "POST", "/api/quiz/generate", {
        "source": "topic", "topic_text": "Photosynthesis",
        "subject": "Biology", "question_type": "open_ended", "num_questions": 5, "difficulty": "easy",
    }, False),
    ("Paste Text MCQ", "POST", "/api/quiz/generate-from-text", {
        "text": "Newton's First Law states that an object at rest stays at rest and an object in motion stays in motion unless acted upon by a net external force. F=ma is Newton's Second Law. For every action there is an equal and opposite reaction. Momentum p = mv. Inertia is the property of matter.",
        "subject": "Physics", "num_questions": 5, "question_type": "mcq", "difficulty": "medium",
    }, False),
    ("Web Link", "POST", "/api/quiz/generate-from-url", {
        "url": "https://en.wikipedia.org/wiki/Photosynthesis",
        "subject": "Biology", "topic_text": "Photosynthesis", "num_questions": 5, "question_type": "mcq", "difficulty": "medium",
    }, False),
    ("Empty Topic (should 422)", "POST", "/api/quiz/generate", {
        "source": "topic", "topic_text": "", "topic": "", "subject": "General",
        "question_type": "mcq", "num_questions": 5, "difficulty": "easy",
    }, True),
    ("Bad URL (should not 500)", "POST", "/api/quiz/generate-from-url", {
        "url": "https://fake-xyz-does-not-exist-12345.com",
        "subject": "General", "num_questions": 5, "question_type": "mcq", "difficulty": "easy",
    }, True),
]


def validate_quiz_response(data, question_type):
    """Validate backend response: has items, each item has required fields."""
    items = data.get("items") if isinstance(data, dict) else data.get("questions")
    if items is None or not isinstance(items, list):
        return False, "Missing or invalid 'items'"
    if len(items) == 0:
        return False, "Empty items array"
    q = items[0]
    text = q.get("question") or q.get("text") or ""
    if not text or text == "?":
        return False, "Missing question text in first item"
    if question_type == "mcq":
        opts = q.get("options") or []
        if not isinstance(opts, list) or len(opts) < 2:
            return False, "MCQ needs at least 2 options"
        if "correct" not in q and "correct_answer" not in q:
            return False, "MCQ needs 'correct'"
    else:
        if not (q.get("sample_answer") or q.get("model_answer") or q.get("expected_answer")):
            return False, "Open-ended needs sample_answer or expected_answer"
    return True, "OK"


def ensure_test_pdf():
    """Create test_sample.pdf if missing (minimal PDF with extractable text)."""
    path = ROOT / "test_sample.pdf"
    if path.exists():
        return path
    try:
        from PyPDF2 import PdfWriter
        from PyPDF2 import PageObject
        w = PdfWriter()
        p = PageObject.create_blank_page(None, 612, 792)
        w.add_page(p)
        with open(path, "wb") as f:
            w.write(f)
        return path
    except Exception:
        try:
            from reportlab.pdfgen.canvas import Canvas
            c = Canvas(str(path))
            c.drawString(72, 720, "Chapter 1: Laws of Motion. Newton's First Law states that a body remains at rest or in uniform motion unless acted upon by an external force.")
            c.save()
            return path
        except Exception:
            return None
    return None


def ensure_panic_textbook():
    """Create a sample textbook file for panic/generate/textbook test (backend/data/sample_textbooks)."""
    sample_dir = ROOT / "backend" / "data" / "sample_textbooks"
    sample_dir.mkdir(parents=True, exist_ok=True)
    path = sample_dir / "panic_test.txt"
    if path.exists():
        return str(path)
    path.write_text(
        "Newton's First Law: An object at rest stays at rest and an object in motion stays in motion unless acted upon by an external force (inertia). "
        "Newton's Second Law: F = ma. Newton's Third Law: For every action there is an equal and opposite reaction. "
        "Momentum p = mv. SI unit of force is Newton (N).",
        encoding="utf-8",
    )
    return str(path)


async def test_all():
    if INPROCESS:
        from fastapi.testclient import TestClient
        from backend.main import app
        _client = TestClient(app)
    ensure_panic_textbook()

    async with httpx.AsyncClient(timeout=90) as client:
        results: list[tuple[str, str]] = []

        tests = [
            ("GET", "/api/health", None, None),
            # ── PANIC MODE (fast: no AI) ──
            ("GET", "/api/quiz/panic", None, TEST_HEADERS),
            ("POST", "/api/quiz/panic/grade-one", PANIC_GRADE_ONE, None),
            ("POST", "/api/quiz/panic/grade-one", PANIC_GRADE_ONE_MCQ, None),
            ("POST", "/api/quiz/panic/submit", PANIC_SUBMIT, TEST_HEADERS),
            # ── Panic generate (may be slow if Ollama cold) ──
            ("POST", "/api/quiz/panic/generate/textbook", PANIC_TEXTBOOK, TEST_HEADERS),
            ("POST", "/api/quiz/panic/generate/weblink", PANIC_WEBLINK, TEST_HEADERS),
            # ── Other ──
            ("POST", "/api/quiz/generate", TOPIC_QUIZ, TEST_HEADERS),
            ("POST", "/api/quiz/generate", PASTE_QUIZ, TEST_HEADERS),
            ("POST", "/api/quiz/generate-from-url", WEBLINK_QUIZ, TEST_HEADERS),
            ("POST", "/api/notes/generate", NOTES_PASTE, TEST_HEADERS),
            ("POST", "/api/notes/generate", NOTES_TOPIC, TEST_HEADERS),
            ("POST", "/api/flashcards/generate-from-text", FLASHCARDS_PASTE, None),
            ("POST", "/api/chat", CHAT_PAYLOAD, TEST_HEADERS),
        ]

        for method, path, body, headers in tests:
            try:
                h = dict(headers or {})
                if INPROCESS:
                    if method == "GET":
                        r = _client.get(path, headers=h)
                    else:
                        r = _client.post(path, json=body, headers=h)
                elif method == "POST" and body is not None:
                    r = await client.post(BASE + path, json=body, headers=h)
                elif method == "GET":
                    r = await client.get(BASE + path, headers=h)
                else:
                    r = await client.request(method, BASE + path, headers=h)

                status = "PASS" if r.status_code == 200 else "FAIL %s" % r.status_code
                panic_fail = False
                if r.status_code == 200:
                    try:
                        data = r.json()
                        if path.startswith("/api/quiz/panic") and isinstance(data, dict):
                            items = data.get("items", data.get("questions"))
                            if items is not None and not isinstance(items, list):
                                items = None
                            if path == "/api/quiz/panic" or "/generate/" in path:
                                if not items or len(items) < 1:
                                    panic_fail = True
                                    results.append((path, "items missing or empty"))
                    except Exception:
                        pass
                if panic_fail:
                    status = "FAIL (no items)"
                symbol = "PASS" if r.status_code == 200 and not panic_fail else "FAIL"
                print("%s %s %s %s" % ("[OK]" if r.status_code == 200 and not panic_fail else "[FAIL]", status, method, path))
                if r.status_code != 200:
                    print("   Response: %s" % (r.text[:400],))
                else:
                    try:
                        data = r.json()
                        keys = list(data.keys()) if isinstance(data, dict) else "list"
                        print("   Keys: %s" % (keys,))
                        if panic_fail:
                            print("   PANIC CHECK: items array missing or empty")
                    except Exception:
                        print("   Body: %s" % (r.text[:200],))
            except Exception as e:
                print("ERROR %s %s: %s" % (method, path, e))
                results.append((path, str(e)))

        # PDF upload (multipart)
        pdf_path = ensure_test_pdf()
        if pdf_path and Path(pdf_path).exists():
            try:
                with open(pdf_path, "rb") as f:
                    if INPROCESS:
                        r = _client.post("/api/textbooks/upload", files={"file": ("test_sample.pdf", f, "application/pdf")}, headers=TEST_HEADERS)
                    else:
                        r = await client.post(BASE + "/api/textbooks/upload", files={"file": ("test_sample.pdf", f, "application/pdf")}, headers=TEST_HEADERS)
                status = "PASS" if r.status_code == 200 else "FAIL %s" % r.status_code
                print("%s %s POST /api/textbooks/upload" % ("[OK]" if r.status_code == 200 else "[FAIL]", status))
                if r.status_code != 200:
                    print("   Response: %s" % (r.text[:300],))
            except Exception as e:
                print("ERROR POST /api/textbooks/upload: %s" % (e,))
        else:
            print("SKIP POST /api/textbooks/upload (no test_sample.pdf; install PyPDF2 or reportlab to generate)")

        # Panic generate/files (multipart)
        try:
            sample_dir = ROOT / "backend" / "data" / "sample_textbooks"
            panic_txt = sample_dir / "panic_test.txt"
            if panic_txt.exists():
                with open(panic_txt, "rb") as f:
                    if INPROCESS:
                        r = _client.post(
                            "/api/quiz/panic/generate/files",
                            files=[("files", ("panic_test.txt", f, "text/plain"))],
                            data={"subject": "Physics", "count": "5", "question_type": "mcq"},
                            headers=TEST_HEADERS,
                        )
                    else:
                        r = await client.post(
                            BASE + "/api/quiz/panic/generate/files",
                            files=[("files", ("panic_test.txt", f, "text/plain"))],
                            data={"subject": "Physics", "count": "5", "question_type": "mcq"},
                            headers=TEST_HEADERS,
                        )
                status = "PASS" if r.status_code == 200 else "FAIL %s" % r.status_code
                print("%s %s POST /api/quiz/panic/generate/files" % ("[OK]" if r.status_code == 200 else "[FAIL]", status))
                if r.status_code != 200:
                    print("   Response: %s" % (r.text[:300],))
                elif r.status_code == 200:
                    try:
                        data = r.json()
                        if not data.get("items") or len(data.get("items", [])) < 1:
                            print("   PANIC CHECK: items missing or empty")
                            results.append(("/api/quiz/panic/generate/files", "items missing or empty"))
                    except Exception:
                        pass
            else:
                print("SKIP POST /api/quiz/panic/generate/files (no panic_test.txt)")
        except Exception as e:
            print("ERROR POST /api/quiz/panic/generate/files: %s" % (e,))
            results.append(("/api/quiz/panic/generate/files", str(e)))

    return results


async def run_quiz_tests():
    """Run Quiz Generator endpoint tests. Uses TEST_HEADERS (set STUDAXIS_TEST=1). Returns list of failed test names."""
    failed = []
    print("\n" + "=" * 40)
    print("   QUIZ GENERATOR ENDPOINT TESTS")
    print("=" * 40 + "\n")
    _client = None
    if INPROCESS:
        from fastapi.testclient import TestClient
        from backend.main import app
        _client = TestClient(app)
    async with httpx.AsyncClient(timeout=120) as client:
        for t in QUIZ_TESTS:
            name = t[0]
            method = t[1]
            path = t[2]
            payload = t[3]
            expect_fail = t[4] if len(t) > 4 else False
            try:
                if _client is not None:
                    r = _client.post(path, json=payload, headers=TEST_HEADERS)
                else:
                    r = await client.post(BASE + path, json=payload, headers=TEST_HEADERS)

                if name.startswith("Empty Topic"):
                    ok = r.status_code in (400, 422)
                    status = "[PASS]" if ok else "[FAIL] — expected 400/422, got %s" % r.status_code
                    if not ok:
                        failed.append(name)
                    print("%s  [%s]" % (status, name))
                    continue
                if name.startswith("Bad URL"):
                    ok = r.status_code != 500
                    status = "[PASS]" if ok else "[FAIL] — crashed with 500"
                    if not ok:
                        failed.append(name)
                    print("%s  [%s]" % (status, name))
                    continue

                if r.status_code != 200:
                    failed.append(name)
                    print("[FAIL]  [%s] — HTTP %s" % (name, r.status_code))
                    print("         Response: %s\n" % (r.text[:400],))
                    continue
                data = r.json()
                qtype = payload.get("question_type", "mcq")
                valid, msg = validate_quiz_response(data, qtype)
                if valid:
                    count = len(data.get("items") or data.get("questions") or [])
                    print("[PASS]  [%s] — %s questions returned" % (name, count))
                else:
                    failed.append(name)
                    print("[FAIL]  [%s] — %s" % (name, msg))
                    print("         Response keys: %s\n" % (list(data.keys()) if isinstance(data, dict) else "n/a"))
            except Exception as e:
                failed.append(name)
                print("[ERROR] [%s] — %s\n" % (name, e))
    return failed


if __name__ == "__main__":
    if not TEST_HEADERS:
        print("Tip: set STUDAXIS_TEST=1 for auth-required endpoints (quiz, notes, chat).")
    if QUIZ_ONLY:
        failed = asyncio.run(run_quiz_tests())
        sys.exit(1 if failed else 0)
    errs = asyncio.run(test_all())
    failed = asyncio.run(run_quiz_tests())
    sys.exit(1 if (errs or failed) else 0)
