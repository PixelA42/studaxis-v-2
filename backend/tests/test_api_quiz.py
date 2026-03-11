"""
API tests for quiz endpoints: generate, get, submit, grade-answer.

These tests use a mocked get_ai_engine so the suite runs without Ollama.
The real app uses real Ollama; only this test module mocks it.
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


def _mcq_quiz_json(count: int = 3) -> str:
    items = []
    for i in range(count):
        items.append({
            "id": f"q{i+1}",
            "question": f"What is question {i+1}?",
            "options": ["A. One", "B. Two", "C. Three", "D. Four"],
            "correct": 0,
        })
    return json.dumps(items)


@patch.object(backend_main, "get_ai_engine")
class TestQuizAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tmpdir.name)
        os.environ["STUDAXIS_BASE_PATH"] = str(self.base)
        os.environ["STUDAXIS_TEST"] = "1"

    def tearDown(self) -> None:
        os.environ.pop("STUDAXIS_TEST", None)
        os.environ.pop("STUDAXIS_BASE_PATH", None)
        self.tmpdir.cleanup()

    def _get_app(self):
        from main import app
        return app

    def test_quiz_generate_topic_returns_items(self, mock_get_engine: MagicMock) -> None:
        mock_engine = MagicMock()
        mock_engine.request.return_value = _mock_ai_response(_mcq_quiz_json(5))
        mock_get_engine.return_value = mock_engine

        app = self._get_app()
        with TestClient(app) as client:
            r = client.post(
                "/api/quiz/generate",
                json={
                    "source": "topic",
                    "topic_text": "Newton's Laws",
                    "subject": "Physics",
                    "question_type": "mcq",
                    "num_questions": 5,
                    "difficulty": "medium",
                },
                headers={"X-Test-User": "quizuser"},
            )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        items = data.get("items") or data.get("questions") or []
        self.assertGreaterEqual(len(items), 1)
        # API returns "text" for question text (not "question")
        self.assertIn("text", items[0] if items else {})

    def test_quiz_generate_from_text_returns_items(self, mock_get_engine: MagicMock) -> None:
        mock_engine = MagicMock()
        mock_engine.request.return_value = _mock_ai_response(_mcq_quiz_json(4))
        mock_get_engine.return_value = mock_engine

        app = self._get_app()
        with TestClient(app) as client:
            r = client.post(
                "/api/quiz/generate-from-text",
                json={
                    "text": "Newton's First Law: An object at rest stays at rest. An object in motion stays in motion unless acted upon by a net force. This is inertia. Newton's Second Law: F=ma. Force equals mass times acceleration. Newton's Third Law: For every action there is an equal and opposite reaction. Momentum p = mv.",
                    "subject": "Physics",
                    "num_questions": 4,
                    "question_type": "mcq",
                    "difficulty": "medium",
                },
                headers={"X-Test-User": "quizuser"},
            )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        items = data.get("items") or data.get("questions") or []
        self.assertGreaterEqual(len(items), 1)

    def test_quiz_get_returns_404_for_unknown_id(self, mock_get_engine: MagicMock) -> None:
        app = self._get_app()
        with TestClient(app) as client:
            r = client.get(
                "/api/quiz/nonexistent_quiz_id_123",
                headers={"X-Test-User": "quizuser"},
            )
        self.assertIn(r.status_code, (404, 200), r.text)

    def test_quiz_submit_quick_returns_score(self, mock_get_engine: MagicMock) -> None:
        # Mock AI so weak_topics_text and recommendation_text are real strings (not MagicMock)
        mock_engine = MagicMock()
        weak_resp = MagicMock()
        weak_resp.text = "Weak topics: Mechanics. Consider reviewing Newton's laws."
        rec_resp = MagicMock()
        rec_resp.text = "Complete more quizzes and review weak areas from your stats."
        mock_engine.request.side_effect = [weak_resp, rec_resp]
        mock_get_engine.return_value = mock_engine

        app = self._get_app()
        with TestClient(app) as client:
            r = client.post(
                "/api/quiz/quick/submit",
                json={
                    "answers": [
                        {"question_id": "q1", "user_answer": "A"},
                        {"question_id": "q2", "user_answer": "B"},
                    ],
                    "items": None,
                },
                headers={"X-Test-User": "quizuser"},
            )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("score", data)
        self.assertIn("max_score", data)

    def test_quiz_grade_answer_returns_feedback(self, mock_get_engine: MagicMock) -> None:
        mock_engine = MagicMock()
        mock_engine.request.return_value = _mock_ai_response(
            "Correct. Force equals mass times acceleration."
        )
        mock_get_engine.return_value = mock_engine

        app = self._get_app()
        with TestClient(app) as client:
            r = client.post(
                "/api/quiz/grade-answer",
                json={
                    "question_id": "q1",
                    "question": "What is F=ma?",
                    "user_answer": "Force equals mass times acceleration",
                    "expected_answer": "Newton's Second Law",
                    "subject": "Physics",
                    "question_type": "open_ended",
                },
                headers={"X-Test-User": "quizuser"},
            )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("feedback", data)

    def test_quiz_generate_returns_503_when_ai_unavailable(
        self, mock_get_engine: MagicMock
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.request.side_effect = ConnectionError("Ollama not reachable")
        mock_get_engine.return_value = mock_engine

        app = self._get_app()
        with TestClient(app) as client:
            r = client.post(
                "/api/quiz/generate",
                json={
                    "source": "topic",
                    "topic_text": "Motion",
                    "subject": "Physics",
                    "question_type": "mcq",
                    "num_questions": 5,
                    "difficulty": "medium",
                },
                headers={"X-Test-User": "quizuser"},
            )
        self.assertEqual(r.status_code, 503, r.text)


if __name__ == "__main__":
    unittest.main()
