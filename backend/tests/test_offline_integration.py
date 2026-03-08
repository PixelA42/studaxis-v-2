"""
Offline Integration Test — Studaxis Local Backend
═══════════════════════════════════════════════════

Proves the FastAPI + Ollama backend functions correctly when there is
absolutely zero internet connection to AWS (AppSync, S3, API Gateway).

- Mocks: SyncManager connectivity, boto3, requests to cloud endpoints
- Does NOT mock: Local Ollama, ChromaDB (offline Edge Brain)
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
import importlib.util

# Ensure backend dir is first and load backend main as "main" (avoids backend_main from root main.py)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Load backend main cleanly so Pydantic models resolve (root main.py loads it as "backend_main")
if "main" in sys.modules and hasattr(sys.modules["main"], "__file__"):
    _mf = getattr(sys.modules["main"], "__file__", "") or ""
    if "backend" not in _mf.replace("\\", "/"):
        del sys.modules["main"]
if "backend_main" in sys.modules:
    del sys.modules["backend_main"]

from fastapi.testclient import TestClient


def _is_localhost_url(url_or_request) -> bool:
    """Check if target is localhost (Ollama, ChromaDB) — allow; else block as cloud."""
    try:
        if hasattr(url_or_request, "url"):
            url = url_or_request.url
        else:
            url = str(url_or_request)
        url_lower = url.lower()
        return any(
            h in url_lower
            for h in ("localhost", "127.0.0.1", "0.0.0.0")
        )
    except Exception:
        return False


class TestOfflineIntegration(unittest.TestCase):
    """Offline-first backend integration tests with mocked cloud connectivity."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="studaxis_offline_")
        self.base_path = Path(self.test_dir)
        os.environ["STUDAXIS_BASE_PATH"] = str(self.base_path)

    def tearDown(self):
        if "STUDAXIS_BASE_PATH" in os.environ:
            del os.environ["STUDAXIS_BASE_PATH"]
        if hasattr(self, "test_dir") and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_offline_quiz_submission_and_queueing(self):
        """
        Submit quiz while offline (AWS unreachable).
        Assert: 200 OK, user_stats updated, sync queue has pending item.
        """
        # Load backend/main.py as "main" so Pydantic resolves (root main.py loads it as "backend_main")
        for modname in ("backend_main", "main"):
            if modname in sys.modules:
                m = sys.modules[modname]
                if getattr(m, "__file__", "") and "backend" in str(m.__file__).replace("\\", "/"):
                    del sys.modules[modname]
                    break
        spec = importlib.util.spec_from_file_location("main", _BACKEND_DIR / "main.py")
        main_mod = importlib.util.module_from_spec(spec)
        sys.modules["main"] = main_mod
        spec.loader.exec_module(main_mod)
        app = main_mod.app

        # Create test user and JWT for auth (avoids dependency override issues)
        from database import init_db, SessionLocal, User
        from auth_utils import hash_password
        from auth_routes import _create_jwt
        init_db()  # uses STUDAXIS_BASE_PATH from setUp
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == "offline_test_user").first()
            if not user:
                user = User(
                    email="offline_test@example.com",
                    username="offline_test_user",
                    hashed_password=hash_password("TestPass1!"),
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            token = _create_jwt(user.id, user.username)
        finally:
            db.close()
        headers = {"Authorization": f"Bearer {token}"}

        # Simulate zero internet to AWS: patch requests.Session.post and boto3
        from requests.sessions import Session as RequestsSession

        _original_post = RequestsSession.post

        def block_cloud_post(self, url, *args, **kwargs):
            if _is_localhost_url(url):
                return _original_post(self, url, *args, **kwargs)
            raise ConnectionError("Simulated offline: no connection to cloud")

        def _raise_connection_error(*args, **kwargs):
            raise ConnectionError("Simulated offline: AWS unavailable")

        patches = [
            patch.object(RequestsSession, "post", block_cloud_post),
            patch("device_id.get_or_generate_device_id", return_value="offline-test-device"),
        ]
        try:
            import boto3
            patches.append(patch("boto3.client", side_effect=_raise_connection_error))
        except ImportError:
            pass  # boto3 not installed; skip (quiz_submit does not use S3)

        for p in patches:
            p.start()

        try:
            with TestClient(app) as client:
                # Quiz submit: use quiz_id "quick" with static QUIZ_ITEMS
                payload = {
                    "answers": [
                        {"question_id": "q1", "user_answer": "Force equals mass times acceleration. F = m * a."},
                        {"question_id": "q2", "user_answer": "Movement of water from high to low concentration through a membrane."},
                        {"question_id": "q3", "user_answer": "2x using the power rule."},
                    ],
                    "items": None,
                }

                response = client.post(
                    "/api/quiz/quick/submit",
                    json=payload,
                    headers=headers,
                )

                # Assert 1: 200 OK — app did not crash when AWS unreachable
                self.assertEqual(
                    response.status_code,
                    200,
                    f"Quiz submit should return 200 OK when offline, got {response.status_code}: {response.text}",
                )

                body = response.json()
                self.assertIn("score", body)
                self.assertIn("max_score", body)
                self.assertIn("percent", body)

                # Assert 2: user_stats.json updated with new score
                stats_path = self.base_path / "data" / "users" / "offline_test_user" / "user_stats.json"
                self.assertTrue(
                    stats_path.exists(),
                    f"user_stats.json should exist at {stats_path}",
                )
                stats = json.loads(stats_path.read_text(encoding="utf-8"))
                quiz_stats = stats.get("quiz_stats") or {}
                self.assertGreater(
                    int(quiz_stats.get("total_attempted", 0)),
                    0,
                    "user_stats should have total_attempted > 0 after quiz submit",
                )
                self.assertIn("average_score", quiz_stats)
                self.assertIn("by_topic", quiz_stats)

                # Assert 3: Sync queue has pending item (pending_sync == in queue)
                queue_path = self.base_path / "data" / "sync_queue.json"
                self.assertTrue(
                    queue_path.exists(),
                    f"sync_queue.json should exist at {queue_path}",
                )
                queue = json.loads(queue_path.read_text(encoding="utf-8"))
                self.assertTrue(
                    isinstance(queue, list),
                    "sync_queue should be a list",
                )
                quiz_items = [q for q in queue if q.get("mutation_type") == "recordQuizAttempt"]
                self.assertGreater(
                    len(quiz_items),
                    0,
                    "Sync queue should contain at least one recordQuizAttempt (pending_sync)",
                )
                # Check our quiz is in the queue
                quick_items = [q for q in quiz_items if q.get("payload", {}).get("quizId") == "quick"]
                self.assertGreater(
                    len(quick_items),
                    0,
                    "Sync queue should contain our quiz (quick) as pending_sync",
                )
        finally:
            for p in patches:
                p.stop()


if __name__ == "__main__":
    unittest.main()
