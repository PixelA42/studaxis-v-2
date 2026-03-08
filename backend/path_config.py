"""
Base path for Studaxis data. Respects STUDAXIS_BASE_PATH for frozen/portable installs.
When running from the .exe, run.py sets this env before any imports.
"""
from __future__ import annotations

import os
from pathlib import Path

_BASE: Path | None = None


def get_base_path() -> Path:
    """Return base directory for data (profile.json, users.db, etc.)."""
    global _BASE
    if _BASE is not None:
        return _BASE
    p = os.environ.get("STUDAXIS_BASE_PATH")
    if p and os.path.isabs(p):
        _BASE = Path(p)
    else:
        _BASE = Path(__file__).resolve().parent
    return _BASE


def get_data_dir() -> Path:
    """Return data directory (profile.json, chromadb, sample_textbooks, etc.)."""
    return get_base_path() / "data"
