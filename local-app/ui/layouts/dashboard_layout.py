"""Dashboard header and footer layout components."""
from __future__ import annotations

from html import escape

import streamlit as st


def render_dashboard_header(
    *,
    initials: str,
    display_name: str,
    streak: int,
    theme: str,
    connectivity_status: str,
    mode_label: str,
    environment_badge_html: str,
) -> None:
    """Render the full-width dashboard header card."""
    safe_name = escape(display_name)
    safe_initials = escape(initials)
    safe_mode = escape(mode_label)
    is_online = connectivity_status == "online"

    conn_html = (
        '<span class="status-pill status-pill--online" role="status" aria-label="Online">'
        "\u25cf Online</span>"
        if is_online
        else '<span class="status-pill status-pill--offline" role="status" aria-label="Offline">'
        "\u25cb Offline</span>"
    )

    streak_s = "s" if streak != 1 else ""

    st.markdown(
        f'<div class="dashboard-header-card" role="banner">'
        f'<div class="dashboard-header-left">'
        f'<div class="dashboard-avatar" aria-hidden="true">{safe_initials}</div>'
        f'<div class="dashboard-welcome-text">'
        f'<span class="dashboard-welcome-name">Welcome back, {safe_name}</span>'
        f'<span class="dashboard-welcome-sub">Personal Mastery \u00b7 AI Tutor ready</span>'
        f"</div></div>"
        f'<div class="dashboard-header-right">'
        f'<span class="dashboard-streak-pill" title="Current study streak">'
        f'\U0001f525 <span class="streak-count">{streak}</span>&nbsp;day{streak_s}</span>'
        f'<span class="dashboard-mode-badge" title="Learning mode">{safe_mode}</span>'
        f"{environment_badge_html}"
        f"{conn_html}"
        f"</div></div>",
        unsafe_allow_html=True,
    )


def render_dashboard_footer(
    *,
    connectivity_status: str,
    last_sync_label: str,
) -> None:
    """Render the dashboard sync-row footer."""
    is_online = connectivity_status == "online"

    conn_pill = (
        '<span class="status-pill status-pill--online" role="status">'
        "\u25cf Online \u2014 ready to sync</span>"
        if is_online
        else '<span class="status-pill status-pill--offline" role="status">'
        "\u25cb Offline \u2014 queuing locally</span>"
    )

    st.markdown(
        f'<div class="dashboard-sync-row" role="contentinfo">'
        f'<div class="dashboard-sync-left">'
        f"{conn_pill}"
        f'<span class="dashboard-sync-label">Last sync: {escape(last_sync_label)}</span>'
        f"</div></div>",
        unsafe_allow_html=True,
    )
