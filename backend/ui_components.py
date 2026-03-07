"""Shared UI helpers for local Streamlit pages.

This module re-exports from the new ui.components package for backward
compatibility.  New code should import directly from ui.components.
"""
from __future__ import annotations

from ui.components.empty_state import render_empty_state
from ui.components.status_indicator import render_status_pill


def render_mode_status_badge(label: str, *, online: bool) -> None:
    """Render a compact connectivity/mode badge.
    
    Backward-compatible wrapper around render_status_pill.
    """
    render_status_pill(label, online=online)


__all__ = ["render_empty_state", "render_mode_status_badge"]
