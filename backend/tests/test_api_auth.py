"""
API tests for auth endpoints: signup, login, /api/user/me.
Uses temp dir for SQLite DB and mocks email/OTP so no real mail is sent.
"""
from __future__ import annotations

import os
import sys
import tempfile
import uuid
import unittest
from pathlib import Path
from unittest.mock import patch

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from fastapi.testclient import TestClient

# Import backend main so patches target it (not repo root main.py)
import main as backend_main


class TestAuthAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tmpdir.name)
        os.environ["STUDAXIS_BASE_PATH"] = str(self.base)

    def tearDown(self) -> None:
        os.environ.pop("STUDAXIS_BASE_PATH", None)
        try:
            from database import engine
            engine.dispose()
        except Exception:
            pass
        self.tmpdir.cleanup()

    def _get_app(self):
        from main import app
        return app

    @patch("auth_routes.send_verification_email")
    @patch("auth_routes._generate_and_send_otp")
    def test_signup_returns_token(
        self, mock_otp: patch, mock_verification: patch
    ) -> None:
        app = self._get_app()
        from database import init_db
        init_db()
        with TestClient(app) as client:
            username = f"authtest_{uuid.uuid4().hex[:6]}"
            email = f"auth_{uuid.uuid4().hex[:8]}@example.com"
            r = client.post(
                "/api/auth/signup",
                json={
                    "email": email,
                    "username": username,
                    "password": "TestPass1!",
                },
            )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("access_token", data)
        self.assertEqual(data.get("username"), username)
        self.assertIn("email", data)

    def test_login_returns_token(self) -> None:
        app = self._get_app()
        from database import init_db, SessionLocal, User
        from auth_utils import hash_password
        init_db()
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == "logintest").first()
            if not user:
                user = User(
                    email="logintest@example.com",
                    username="logintest",
                    hashed_password=hash_password("Pass1!word"),
                )
                db.add(user)
                db.commit()
                db.refresh(user)
        finally:
            db.close()

        with TestClient(app) as client:
            r = client.post(
                "/api/auth/login",
                json={"username_or_email": "logintest", "password": "Pass1!word"},
            )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("access_token", data)
        self.assertEqual(data.get("username"), "logintest")

    def test_login_invalid_password_returns_401(self) -> None:
        app = self._get_app()
        from database import init_db, SessionLocal, User
        from auth_utils import hash_password
        init_db()
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == "logintest").first()
            if not user:
                user = User(
                    email="logintest@example.com",
                    username="logintest",
                    hashed_password=hash_password("Pass1!word"),
                )
                db.add(user)
                db.commit()
        finally:
            db.close()
        with TestClient(app) as client:
            r = client.post(
                "/api/auth/login",
                json={"username_or_email": "logintest", "password": "WrongPass1!"},
            )
        self.assertEqual(r.status_code, 401, r.text)

    def test_user_me_returns_user_with_valid_token(self) -> None:
        app = self._get_app()
        from database import init_db, SessionLocal, User
        from auth_utils import hash_password
        from auth_routes import _create_jwt
        init_db()
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == "metest").first()
            if not user:
                user = User(
                    email="metest@example.com",
                    username="metest",
                    hashed_password=hash_password("Pass1!word"),
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            token = _create_jwt(user.id, user.username)
        finally:
            db.close()
        with TestClient(app) as client:
            r = client.get(
                "/api/user/me",
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("username", data)
        self.assertEqual(data.get("username"), "metest")

    def test_user_me_returns_401_without_token(self) -> None:
        app = self._get_app()
        with TestClient(app) as client:
            r = client.get("/api/user/me")
        self.assertEqual(r.status_code, 401, r.text)


if __name__ == "__main__":
    unittest.main()
