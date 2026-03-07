"""
Database setup and User model for Studaxis auth.

User model: email (unique, indexed), username (unique, indexed), hashed_password.
SQLite database stored in backend/data/users.db for offline-first compatibility.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import DateTime, String

# Base path: same as main.py (backend dir when run from backend, or STUDAXIS_BASE_PATH)
_APP_DIR = Path(__file__).resolve().parent
_BASE_PATH = Path(os.environ.get("STUDAXIS_BASE_PATH", str(_APP_DIR)))
DATA_DIR = _BASE_PATH / "data"
DB_PATH = DATA_DIR / "users.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


class User(Base):
    """
    User model for authentication.

    - email: unique, indexed (login and lookup)
    - username: unique, indexed (display and lookup)
    - hashed_password: bcrypt hash via passlib (never store plaintext)
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email!r}, username={self.username!r})>"


def init_db() -> None:
    """Create all tables. Call on app startup."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator:
    """Dependency: yield a DB session, close on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
