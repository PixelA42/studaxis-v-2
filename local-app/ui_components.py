"""Shared UI helpers for local Streamlit pages."""

from __future__ import annotations

from html import escape

import streamlit as st


def render_empty_state(
    title: str,
    description: str,
    *,
    illustration_label: str = "Empty State Illustration Placeholder",
) -> None:
    """Render a reusable empty-state block aligned to global theme styles."""
    st.markdown(
        f"""
        <div class="db-empty-state" role="status" aria-live="polite">
          <div class="db-empty-state-icon" aria-label="{escape(illustration_label)}">□</div>
          <div class="db-empty-state-title">{escape(title)}</div>
          <div class="db-empty-state-text">{escape(description)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_mode_status_badge(label: str, *, online: bool) -> None:
    """Render a compact connectivity/mode badge."""
    status_class = "status-pill--online" if online else "status-pill--offline"
    st.markdown(
        f"""
        <div class="status-pill {status_class}" role="status" aria-live="polite">
          {escape(label)}
        </div>
        """,
        unsafe_allow_html=True,
    )
