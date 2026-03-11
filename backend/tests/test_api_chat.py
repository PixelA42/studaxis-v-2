"""
API tests for AI chat endpoint: POST /api/chat.

These tests use a mocked get_ai_engine so the suite runs without Ollama.
The real app uses real Ollama; only this test module mocks it.
"""
from __future__ import annotations

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


@patch.object(backend_main, "get_ai_engine")
class TestChatAPI(unittest.TestCase):
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

    def test_chat_returns_response(self, mock_get_engine: MagicMock) -> None:
        mock_engine = MagicMock()
        mock_engine.request.return_value = _mock_ai_response(
            "Newton's Second Law states that F = ma: force equals mass times acceleration."
        )
        mock_get_engine.return_value = mock_engine

        app = self._get_app()
        with TestClient(app) as client:
            r = client.post(
                "/api/chat",
                json={"message": "Explain Newton's Second Law", "history": []},
                headers={"X-Test-User": "chatuser"},
            )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("text", data)
        self.assertIn("confidence_score", data)

    def test_chat_returns_503_when_ai_unavailable(self, mock_get_engine: MagicMock) -> None:
        mock_engine = MagicMock()
        mock_engine.request.side_effect = ConnectionError("Ollama not reachable")
        mock_get_engine.return_value = mock_engine

        app = self._get_app()
        with TestClient(app) as client:
            r = client.post(
                "/api/chat",
                json={"message": "Hello", "history": []},
                headers={"X-Test-User": "chatuser"},
            )
        self.assertEqual(r.status_code, 503, r.text)

    def test_chat_requires_auth(self, mock_get_engine: MagicMock) -> None:
        app = self._get_app()
        with TestClient(app) as client:
            r = client.post(
                "/api/chat",
                json={"message": "Hi", "history": []},
            )
        self.assertEqual(r.status_code, 401, r.text)


if __name__ == "__main__":
    unittest.main()
