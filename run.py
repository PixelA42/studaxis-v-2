"""
Studaxis — Bootstrapper (Phase 8).

Starts the FastAPI server (SPA + API), optionally opens the browser.
Ensure Ollama is running locally for AI features (chat, grading, flashcards).

  python run.py
  python run.py --no-browser
  python run.py --port 8001   # If default port is in use (WinError 10013)

When packaged as .exe (PyInstaller frozen): data lives in %APPDATA%/Studaxis/.
Architecture: .kiro/DOCS_NEW/ARCHITECTURE_NEW.md
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import threading
import time
import webbrowser
from pathlib import Path

try:
    from urllib.request import urlopen
    from urllib.error import URLError
except ImportError:
    urlopen = None
    URLError = Exception

IS_FROZEN = getattr(sys, "frozen", False)
_MEIPASS = getattr(sys, "_MEIPASS", None)

if IS_FROZEN and _MEIPASS:
    ROOT = Path(_MEIPASS)
else:
    ROOT = Path(__file__).resolve().parent

DIST = ROOT / "frontend" / "dist"
OLLAMA_TIMEOUT = 2


def _get_chroma_dir() -> Path:
    """ChromaDB dir: APPDATA when frozen, else backend/data/chromadb."""
    if IS_FROZEN:
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return Path(appdata) / "Studaxis" / "data" / "chromadb"
    return ROOT / "backend" / "data" / "chromadb"


CHROMA_DIR = _get_chroma_dir()


def _check_ollama() -> bool:
    """Check if Ollama is reachable. Uses 2s timeout."""
    import os
    base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    url = f"{base}/api/tags"
    try:
        if urlopen:
            urlopen(url, timeout=OLLAMA_TIMEOUT)
            return True
    except (URLError, OSError, TimeoutError):
        pass
    except Exception:
        pass
    return False


def _check_chromadb() -> bool:
    """Check if ChromaDB dir exists and is usable (has collection data)."""
    if not CHROMA_DIR.exists():
        return False
    try:
        # ChromaDB stores collections in subdirs; at least one indicates init
        items = list(CHROMA_DIR.iterdir())
        if not items:
            return False
        # Optional: try lightweight open (import can be slow; skip if dir looks good)
        for p in items:
            if p.is_dir() and (p / "header.bin").exists():
                return True
        # Fallback: dir exists with content
        return len(items) > 0
    except OSError:
        return False


def _run_preflight_checks() -> None:
    """Run pre-startup checks; print warnings only, never block."""
    if not _check_ollama():
        print("⚠ OLLAMA NOT RUNNING — Start with: ollama serve")
    if not _check_chromadb():
        print("⚠ ChromaDB not ready — Run: python backend/build_vectorstore.py")


def _bootstrap_appdata() -> None:
    """
    When frozen: set STUDAXIS_BASE_PATH to %APPDATA%/Studaxis, create dirs,
    and copy seed textbooks if data dir is new/empty.
    """
    if not IS_FROZEN or not _MEIPASS:
        return
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return
    base = Path(appdata) / "Studaxis"
    data_dir = base / "data"
    sample_dir = data_dir / "sample_textbooks"
    chroma_dir = data_dir / "chromadb"
    backups_dir = data_dir / "backups"

    os.environ["STUDAXIS_BASE_PATH"] = str(base)

    for d in (data_dir, sample_dir, chroma_dir, backups_dir):
        d.mkdir(parents=True, exist_ok=True)

    seed_src = Path(_MEIPASS) / "sample_textbooks"
    if seed_src.is_dir():
        existing = set(f.name for f in sample_dir.iterdir() if f.is_file())
        for f in seed_src.iterdir():
            if f.is_file() and f.name not in existing:
                try:
                    shutil.copy2(f, sample_dir / f.name)
                except OSError:
                    pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Studaxis bootstrapper")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open browser to http://localhost:6782",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=6782,
        help="Port for the Edge Brain API server (default: 6782)",
    )
    args = parser.parse_args()

    # Bootstrap %APPDATA%/Studaxis before any backend imports
    _bootstrap_appdata()

    if not DIST.is_dir():
        if not IS_FROZEN:
            print("Note: frontend/dist not found. Build the React app for SPA serving:")
            print("  cd frontend && npm install && npm run build")
            print("  Then run this script again. API will still be available at /api/*.")
            print()

    def open_browser() -> None:
        time.sleep(2.0)
        webbrowser.open(f"http://localhost:{args.port}")
        if not IS_FROZEN:
            print(f"[Studaxis] Opened http://localhost:{args.port} in browser")

    if not args.no_browser:
        threading.Thread(target=open_browser, daemon=True).start()

    # Run uvicorn: Edge Brain (FastAPI) serves SPA + API; Ollama + ChromaDB run locally
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(ROOT / "backend") not in sys.path:
        sys.path.insert(0, str(ROOT / "backend"))

    _run_preflight_checks()

    import uvicorn
    kwargs = {
        "host": "0.0.0.0",
        "port": args.port,
    }
    if not IS_FROZEN:
        kwargs["reload"] = True
        # Watch only backend so the venv (e.g. studaxis-vtwo-env) is never watched
        kwargs["reload_dirs"] = [str(ROOT / "backend")]
        kwargs["reload_excludes"] = [
            "*studaxis-vtwo-env*",
            "*node_modules*",
            "*__pycache__*",
            "*.pyc",
            "*.pyo",
        ]
    uvicorn.run("main:app", **kwargs)


if __name__ == "__main__":
    main()
