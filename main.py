"""
Studaxis — Root entrypoint.

Loads the FastAPI app from backend (which already mounts the compiled React SPA
from frontend/dist when that folder exists). Runs uvicorn.

  python main.py
  # or: uvicorn backend.main:app --reload --host 0.0.0.0 --port 6782

Architecture: .kiro/DOCS_NEW/ARCHITECTURE_NEW.md
"""

from __future__ import annotations

import sys
from pathlib import Path

# Resolve repo root and ensure backend is on path
ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load FastAPI app from backend/main.py (app already mounts SPA when frontend/dist exists)
import importlib.util
_spec = importlib.util.spec_from_file_location("backend_main", BACKEND / "main.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
app = _module.app

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", os.environ.get("STUDAXIS_PORT", "6782")))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=[str(BACKEND), str(ROOT)],
    )
