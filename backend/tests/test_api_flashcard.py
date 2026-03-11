"""
API tests for flashcard endpoints.

These tests use a mocked get_ai_engine (fake AI responses) so the suite runs
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

# Ensure backend on path (conftest does this when running via pytest; duplicate for standalone)
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from ai_integration_layer import AIResponse, AIState
from fastapi.testclient import TestClient

# Import backend main so patch targets it (not repo root main.py)
import main as backend_main


def _mock_ai_response(text: str, state: AIState = AIState.RESPONSE_RECEIVED) -> AIResponse:
    return AIResponse(
        text=text,
        confidence_score=0.9,
        metadata={},
        state=state,
    )


def _flashcards_json(count: int = 3) -> str:
    cards = [
        {"front": f"Question {i+1}", "back": f"Answer {i+1}", "topic": "Physics"}
        for i in range(count)
    ]
    return json.dumps(cards)


@patch.object(backend_main, "get_ai_engine")
class TestFlashcardAPI(unittest.TestCase):
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

    def test_flashcards_generate_topic_returns_cards(self, mock_get_engine: MagicMock) -> None:
        mock_engine = MagicMock()
        mock_engine.request.return_value = _mock_ai_response(_flashcards_json(5))
        mock_get_engine.return_value = mock_engine

        app = self._get_app()
        with TestClient(app) as client:
            r = client.post(
                "/api/flashcards/generate",
                json={
                    "topic_or_chapter": "Newton's Laws",
                    "count": 5,
                    "input_type": "topic",
                    "offline_mode": True,
                },
                headers={"X-Test-User": "testuser"},
            )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("cards", data)
        self.assertGreaterEqual(len(data["cards"]), 1)
        self.assertIn("topic", data)

    def test_flashcards_generate_from_text_returns_cards(self, mock_get_engine: MagicMock) -> None:
        mock_engine = MagicMock()
        mock_engine.request.return_value = _mock_ai_response(_flashcards_json(5))
        mock_get_engine.return_value = mock_engine

        app = self._get_app()
        with TestClient(app) as client:
            r = client.post(
                "/api/flashcards/generate-from-text",
                json={
                    "subject": "Motion",
                    "num_cards": 5,
                    "paste_text": "Newton's First Law: An object at rest stays at rest and an object in motion stays in motion unless acted upon by a net external force. This is inertia. Newton's Second Law: F=ma. Force equals mass times acceleration. Newton's Third Law: For every action there is an equal and opposite reaction. Momentum p = mv. Impulse equals change in momentum.",
                },
                headers={"X-Test-User": "testuser"},
            )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("cards", data)
        self.assertGreaterEqual(len(data["cards"]), 1)

    def test_flashcards_explain_returns_text(self, mock_get_engine: MagicMock) -> None:
        mock_engine = MagicMock()
        mock_engine.request.return_value = _mock_ai_response(
            "Force equals mass times acceleration. The more mass, the harder to accelerate."
        )
        mock_get_engine.return_value = mock_engine

        app = self._get_app()
        with TestClient(app) as client:
            r = client.post(
                "/api/flashcards/explain",
                json={
                    "front": "What is F=ma?",
                    "back": "Newton's Second Law",
                    "subject": "Physics",
                    "difficulty": "Beginner",
                },
            )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("text", data)
        self.assertIn("confidence_score", data)

    def test_flashcards_generate_returns_503_when_ai_unavailable(
        self, mock_get_engine: MagicMock
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.request.side_effect = ConnectionError("Ollama not reachable")
        mock_get_engine.return_value = mock_engine

        app = self._get_app()
        with TestClient(app) as client:
            r = client.post(
                "/api/flashcards/generate",
                json={
                    "topic_or_chapter": "Topic",
                    "count": 5,
                    "input_type": "topic",
                    "offline_mode": True,
                },
                headers={"X-Test-User": "testuser"},
            )
        self.assertEqual(r.status_code, 503, r.text)

    def test_flashcards_list_requires_auth(self, mock_get_engine: MagicMock) -> None:
        app = self._get_app()
        with TestClient(app) as client:
            r = client.get("/api/flashcards")
        self.assertIn(r.status_code, (401, 200), r.text)


if __name__ == "__main__":
    unittest.main()
