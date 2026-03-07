"""Status pills, mode badges, and sync-monitor components."""
from __future__ import annotations

from html import escape

import streamlit as st


def render_status_pill(label: str, *, online: bool) -> None:
    """Render an online/offline status pill."""
    variant = "online" if online else "offline"
    dot = "\u25cf" if online else "\u25cb"
    safe_label = escape(label)

    st.markdown(
        f'<span class="status-pill status-pill--{variant}"'
        f' role="status" aria-label="{safe_label}">'
        f"{dot} {safe_label}</span>",
        unsafe_allow_html=True,
    )


def render_mode_badge(label: str) -> None:
    """Render a learning-mode badge."""
    st.markdown(
        f'<span class="dashboard-mode-badge">{escape(label)}</span>',
        unsafe_allow_html=True,
    )


def render_sync_monitor(
    *,
    status: str,
    last_sync_time: str,
    retry_count: str = "[SYNC_RETRY_COUNT]",
    partial_sync_status: str | None = None,
) -> None:
    """Render the full sync-monitor status bar."""
    pill_map: dict[str, tuple[str, str]] = {
        "synced": ("synced", "Synced"),
        "syncing": ("syncing", "Syncing\u2026"),
        "pending": ("pending", "Sync Pending"),
        "offline": ("offline", "Offline"),
    }
    variant, pill_label = pill_map.get(status, ("none", escape(status) if status else "Unknown"))

    partial_html = ""
    if partial_sync_status:
        partial_html = (
            '<div class="sync-monitor__partial" role="note">'
            '<span class="sync-monitor__partial-icon" aria-hidden="true">\u26a0</span>'
            f"<span>{escape(partial_sync_status)}</span>"
            "</div>"
        )

    st.markdown(
        f'<div class="sync-monitor" role="status" aria-label="Sync status indicator">'
        f'<div class="sync-monitor__left">'
        f'<div class="sync-monitor__pill sync-monitor__pill--{escape(variant, quote=True)}" aria-live="polite">'
        f'<span class="sync-monitor__dot" aria-hidden="true"></span>'
        f"<span>Status: {escape(pill_label)}</span>"
        f"</div></div>"
        f'<div class="sync-monitor__right">'
        f'<span class="sync-monitor__label">Last Sync:</span>'
        f'<span class="sync-monitor__time">{escape(last_sync_time)}</span>'
        f'<span class="sync-monitor__label" aria-label="Retry count">Retries: {escape(retry_count)}</span>'
        f"</div>"
        f"{partial_html}"
        f"</div>",
        unsafe_allow_html=True,
    )
