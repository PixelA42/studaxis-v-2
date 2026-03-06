"""Dashboard stat-card component."""
from __future__ import annotations

from html import escape

import streamlit as st


def render_stat_card(
    *,
    icon: str,
    icon_color: str = "blue",
    value: str,
    label: str,
    sub: str = "",
    progress_pct: int | None = None,
    progress_label: str = "",
    empty_hint: str = "",
) -> None:
    """Render a single dashboard stat tile with icon chip, value, and optional progress bar."""
    safe_label = escape(label)
    safe_value = escape(value)
    safe_icon = escape(icon)
    safe_color = escape(icon_color, quote=True)

    sub_html = f'<div class="dashboard-stat-sub">{escape(sub)}</div>' if sub else ""

    progress_html = ""
    if progress_pct is not None:
        clamped = max(0, min(100, progress_pct))
        progress_html = (
            f'<div class="db-progress-track" role="progressbar"'
            f' aria-valuenow="{clamped}" aria-valuemin="0" aria-valuemax="100">'
            f'<div class="db-progress-fill" style="width:{clamped}%"></div>'
            f"</div>"
            f'<div class="db-progress-label">{escape(progress_label)}</div>'
        )

    empty_html = ""
    if empty_hint:
        empty_html = (
            '<div class="db-empty-state">'
            f'<div class="db-empty-state-text">{escape(empty_hint)}</div>'
            "</div>"
        )

    st.markdown(
        f'<div class="dashboard-stat-card" role="region" aria-label="{safe_label}">'
        f'<div class="db-icon-chip db-icon-chip--{safe_color}" aria-hidden="true">{safe_icon}</div>'
        f'<div class="dashboard-stat-number">{safe_value}</div>'
        f'<div class="dashboard-stat-label">{safe_label}</div>'
        f"{sub_html}"
        f"{progress_html}"
        f"{empty_html}"
        "</div>",
        unsafe_allow_html=True,
    )
