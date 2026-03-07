"""Studaxis modular CSS style loader."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

_STYLES_DIR = Path(__file__).parent

_CSS_LOAD_ORDER = [
    "animations.css",
    "theme.css",
    "glass.css",
    "components.css",
    "hardware.css",
    "sidebar.css",
    "dashboard.css",
    "landing.css",
    "auth.css",
    "chat.css",
    "settings.css",
    "sync.css",
    "teacher.css",
    "errors.css",
]


def inject_all_css() -> None:
    """Load and inject all modular CSS files in the correct order.

    Falls back to the legacy monolithic ``styles/theme.css`` when the
    modular files are not present (keeps backward compatibility during
    the migration window).
    """
    if st.session_state.get("_ui_css_injected"):
        return

    parts: list[str] = []
    for filename in _CSS_LOAD_ORDER:
        css_path = _STYLES_DIR / filename
        if css_path.exists():
            parts.append(css_path.read_text(encoding="utf-8"))

    if not parts:
        legacy = _STYLES_DIR.parent.parent / "styles" / "theme.css"
        if legacy.exists():
            parts.append(legacy.read_text(encoding="utf-8"))

    if parts:
        combined = "\n".join(parts)
        st.markdown(f"<style>{combined}</style>", unsafe_allow_html=True)

    st.session_state["_ui_css_injected"] = True
