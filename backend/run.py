#!/usr/bin/env python3
"""
Run the Studaxis server from the backend directory.

This script forwards to the root run.py so the server starts with correct paths.
Run from repo root instead if you prefer:

  cd /path/to/studaxis-vtwo
  python run.py

Or from backend:

  cd backend
  python run.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.exit(subprocess.call([sys.executable, str(ROOT / "run.py")] + sys.argv[1:]))
