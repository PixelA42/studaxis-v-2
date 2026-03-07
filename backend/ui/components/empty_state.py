"""Empty-state placeholder component."""
from __future__ import annotations

from html import escape

import streamlit as st


def render_empty_state(
    title: str,
    description: str,
    *,
    illustration_label: str = "Empty State Illustration Placeholder",
) -> None:
    """Render an empty-state card with icon, title, and description."""
    st.markdown(
        '<div class="db-empty-state" role="status" aria-live="polite">'
        f'<div class="db-empty-state-icon" aria-label="{escape(illustration_label, quote=True)}">&#9633;</div>'
        f'<div class="db-empty-state-title">{escape(title)}</div>'
        f'<div class="db-empty-state-text">{escape(description)}</div>'
        "</div>",
        unsafe_allow_html=True,
    )
