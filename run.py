"""
Studaxis — Bootstrapper (Phase 8).

Starts the FastAPI server (SPA + API), optionally opens the browser.
Ensure Ollama is running locally for AI features (chat, grading, flashcards).

  python run.py
  python run.py --no-browser
  python run.py --port 8001   # If default port is in use (WinError 10013)

Architecture: .kiro/DOCS_NEW/ARCHITECTURE_NEW.md
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "frontend" / "dist"


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
        help="Port for the API server (default: 6782)",
    )
    args = parser.parse_args()

    if not DIST.is_dir():
        print("Note: frontend/dist not found. Build the React app for SPA serving:")
        print("  cd frontend && npm install && npm run build")
        print("  Then run this script again. API will still be available at /api/*.")
        print()

    def open_browser() -> None:
        time.sleep(2.0)
        webbrowser.open(f"http://localhost:{args.port}")

    if not args.no_browser:
        threading.Thread(target=open_browser, daemon=True).start()

    # Run uvicorn with the same app as main.py
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(ROOT / "backend") not in sys.path:
        sys.path.insert(0, str(ROOT / "backend"))

    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=args.port,
        reload=True,
        reload_dirs=[str(ROOT / "backend"), str(ROOT)],
    )


if __name__ == "__main__":
    main()
