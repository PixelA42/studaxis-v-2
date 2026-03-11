"""
API tests for panic mode: GET panic, grade-one, submit, generate/textbook, weblink, files.

These tests use a mocked get_ai_engine for generate endpoints so the suite runs
without Ollama. The real app uses real Ollama; only this test module mocks it.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from ai_integration_layer import AIResponse, AIState
from fastapi.testclient import TestClient

import main as backend_main


def _mock_ai_response(text: str, state: AIState = AIState.RESPONSE_RECEIVED) -> AIResponse:
    return AIResponse(text=text, confidence_score=0.9, metadata={}, state=state)


def _panic_mcq_json(count: int = 3) -> str:
    items = []
    for i in range(count):
        items.append({
            "id": f"p{i+1}",
            "question": f"Panic question {i+1}?",
            "options": ["A", "B", "C", "D"],
            "correct": 0,
            "topic": "Physics",
        })
    return json.dumps(items)


@patch.object(backend_main, "get_ai_engine")
class TestPanicAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tmpdir.name)
        os.environ["STUDAXIS_BASE_PATH"] = str(self.base)
        os.environ["STUDAXIS_TEST"] = "1"
        (self.base / "data").mkdir(parents=True, exist_ok=True)
        (self.base / "data" / "sample_textbooks").mkdir(parents=True, exist_ok=True)
        sample = self.base / "data" / "sample_textbooks" / "panic_test.txt"
        sample.write_text(
            "Newton's First Law: inertia. Second Law: F=ma. Third Law: action-reaction.",
            encoding="utf-8",
        )
        # Ensure the app uses this test dir for textbooks (main may have been imported with different BASE_PATH)
        self._sample_textbooks_patcher = patch.object(
            backend_main, "SAMPLE_TEXTBOOKS_DIR", self.base / "data" / "sample_textbooks"
        )
        self._sample_textbooks_patcher.start()

    def tearDown(self) -> None:
        self._sample_textbooks_patcher.stop()
        os.environ.pop("STUDAXIS_TEST", None)
        os.environ.pop("STUDAXIS_BASE_PATH", None)
        self.tmpdir.cleanup()

    def _get_app(self):
        from main import app
        return app

    def test_panic_get_returns_items_or_empty(self, mock_get_engine: MagicMock) -> None:
        app = self._get_app()
        with TestClient(app) as client:
            r = client.get("/api/quiz/panic", headers={"X-Test-User": "panicuser"})
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("items", data)

    def test_panic_grade_one_open_ended_returns_feedback(
        self, mock_get_engine: MagicMock
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.request.return_value = _mock_ai_response(
            "Correct. The law of inertia is well stated."
        )
        mock_get_engine.return_value = mock_engine

        app = self._get_app()
        with TestClient(app) as client:
            r = client.post(
                "/api/quiz/panic/grade-one",
                json={
                    "question_id": "p1",
                    "question": "What is Newton's First Law?",
                    "answer": "An object at rest stays at rest unless acted upon.",
                    "topic": "Physics",
                    "expected_answer": "Law of inertia.",
                    "question_type": "open_ended",
                },
            )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("feedback", data)

    def test_panic_grade_one_mcq_returns_feedback(self, mock_get_engine: MagicMock) -> None:
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        app = self._get_app()
        with TestClient(app) as client:
            r = client.post(
                "/api/quiz/panic/grade-one",
                json={
                    "question_id": "pq1",
                    "question": "What is the SI unit of force?",
                    "answer": "C",
                    "topic": "Physics",
                    "expected_answer": "Newton",
                    "question_type": "mcq",
                    "options": ["A. Joule", "B. Watt", "C. Newton", "D. Pascal"],
                    "correct": 2,
                },
            )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("feedback", data)

    def test_panic_submit_returns_score(self, mock_get_engine: MagicMock) -> None:
        app = self._get_app()
        with TestClient(app) as client:
            r = client.post(
                "/api/quiz/panic/finalize",
                json={
                    "results": [
                        {"question_id": "p1", "topic": "Physics", "score": 8},
                        {"question_id": "p2", "topic": "Physics", "score": 10},
                    ],
                    "items": [
                        {"id": "p1", "topic": "Physics", "question": "First Law?", "expected_answer": "Inertia"},
                        {"id": "p2", "topic": "Physics", "question": "Second Law?", "expected_answer": "F=ma"},
                    ],
                },
                headers={"X-Test-User": "panicuser"},
            )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("weak_topics_text", data)
        self.assertIn("recommendation_text", data)

    def test_panic_generate_textbook_returns_items(self, mock_get_engine: MagicMock) -> None:
        mock_engine = MagicMock()
        mock_engine.request.return_value = _mock_ai_response(_panic_mcq_json(5))
        mock_get_engine.return_value = mock_engine

        app = self._get_app()
        with TestClient(app) as client:
            r = client.post(
                "/api/quiz/panic/generate/textbook",
                json={
                    "subject": "Physics",
                    "textbook_id": "panic_test.txt",
                    "chapter": "Chapter 1",
                    "count": 5,
                    "question_type": "mcq",
                },
                headers={"X-Test-User": "panicuser"},
            )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("items", data)
        self.assertGreaterEqual(len(data["items"]), 1)

    def test_panic_generate_files_returns_items(self, mock_get_engine: MagicMock) -> None:
        mock_engine = MagicMock()
        mock_engine.request.return_value = _mock_ai_response(_panic_mcq_json(5))
        mock_get_engine.return_value = mock_engine

        app = self._get_app()
        sample_path = self.base / "data" / "sample_textbooks" / "panic_test.txt"
        with TestClient(app) as client:
            with open(sample_path, "rb") as f:
                r = client.post(
                    "/api/quiz/panic/generate/files",
                    files=[("files", ("panic_test.txt", f, "text/plain"))],
                    data={"subject": "Physics", "count": "5", "question_type": "mcq"},
                    headers={"X-Test-User": "panicuser"},
                )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("items", data)
        self.assertGreaterEqual(len(data["items"]), 1)

    def test_panic_generate_textbook_returns_503_when_ai_unavailable(
        self, mock_get_engine: MagicMock
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.request.side_effect = ConnectionError("Ollama not reachable")
        mock_get_engine.return_value = mock_engine

        app = self._get_app()
        with TestClient(app) as client:
            r = client.post(
                "/api/quiz/panic/generate/textbook",
                json={
                    "subject": "Physics",
                    "textbook_id": "panic_test.txt",
                    "chapter": "Ch1",
                    "count": 5,
                    "question_type": "mcq",
                },
                headers={"X-Test-User": "panicuser"},
            )
        self.assertEqual(r.status_code, 503, r.text)


if __name__ == "__main__":
    unittest.main()
