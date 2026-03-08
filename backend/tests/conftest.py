"""
Pytest configuration for backend tests.
Ensures backend directory is first in sys.path so 'main' resolves to backend/main.py.
Prevents root main.py from loading backend as 'backend_main'.
"""
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_BACKEND_STR = str(_BACKEND)
# Ensure backend is first so 'main' resolves to backend/main.py (not root main.py)
if _BACKEND_STR in sys.path:
    sys.path.remove(_BACKEND_STR)
sys.path.insert(0, _BACKEND_STR)
