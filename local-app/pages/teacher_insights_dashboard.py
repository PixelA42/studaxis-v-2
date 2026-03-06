"""
Studaxis - Teacher Insight Dashboard (Local Preview)

Bento-style teacher analytics view built from standardized AI insight objects.
This page is UI-only and does not execute AI analytics logic.

The Sync Monitoring section uses placeholder values only.
No actual cloud sync, AWS AppSync, or backend logic is implemented here.
"""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

from deployment_ui import build_environment_badge_html
from notifications_ui import render_notification_bell
from pages.insight_engine_ui import get_teacher_insight_templates, render_teacher_insight_bento_grid
from performance_ui import (
    render_lazy_loading_card,
    render_low_power_indicator,
    render_teacher_analytics_skeleton,
)


# ── Placeholder student sync roster ────────────────────────────────────────
# Each entry uses placeholder values. Real data would come from the cloud
# sync layer (AppSync / DynamoDB) which is NOT implemented here.

_PLACEHOLDER_STUDENTS: list[dict[str, Any]] = [
    {
        "id": "STU001",
        "name": "Student A",
        "sync_status": "[STUDENT_SYNC_STATUS]",
        "last_sync": "[LAST_SYNC_TIME]",
        "tooltip": "Sync state provided by cloud backend",
    },
    {
        "id": "STU002",
        "name": "Student B",
        "sync_status": "[STUDENT_SYNC_STATUS]",
        "last_sync": "[LAST_SYNC_TIME]",
        "tooltip": "Sync state provided by cloud backend",
    },
    {
        "id": "STU003",
        "name": "Student C",
        "sync_status": "[STUDENT_SYNC_STATUS]",
        "last_sync": "[LAST_SYNC_TIME]",
        "tooltip": "Sync state provided by cloud backend",
    },
    {
        "id": "STU004",
        "name": "Student D",
        "sync_status": "[STUDENT_SYNC_STATUS]",
        "last_sync": "[LAST_SYNC_TIME]",
        "tooltip": "Sync state provided by cloud backend",
        "partial": "[PARTIAL_SYNC_STATUS]",
    },
]

_BADGE_VARIANTS: dict[str, str] = {
    "synced": "synced",
    "pending": "pending",
    "stale": "stale",
    "none": "none",
    "partial": "partial",
}


def _sync_badge_html(status: str) -> str:
    """Return an inline sync status badge with dot, using design system colors."""
    variant = _BADGE_VARIANTS.get(status, "none")
    return (
        f'<span class="teacher-sync-badge teacher-sync-badge--{variant}">'
        f'  <span class="teacher-sync-badge__dot" aria-hidden="true"></span>'
        f'  {status}'
        f'</span>'
    )


def _render_student_sync_table(students: list[dict[str, Any]]) -> None:
    """
    Render a glass-card table showing per-student sync status.

    All values are placeholders — no backend logic is executed.
    """
    rows_html = ""
    for s in students:
        initials = s["name"][:2].upper() if s["name"] else "??"
        badge = _sync_badge_html(s["sync_status"])
        tooltip_text = s.get("tooltip", "")

        partial_cell = ""
        if s.get("partial"):
            partial_cell = (
                f'<span class="teacher-sync-badge teacher-sync-badge--partial">'
                f'  <span class="teacher-sync-badge__dot" aria-hidden="true"></span>'
                f'  {s["partial"]}'
                f'</span>'
            )
        else:
            partial_cell = '<span class="teacher-sync-time">—</span>'

        rows_html += f"""
        <tr>
          <td>
            <div class="teacher-sync-student">
              <span class="teacher-sync-avatar" aria-hidden="true">{initials}</span>
              <span class="teacher-sync-name">{s["name"]}</span>
            </div>
          </td>
          <td>
            <div class="teacher-sync-tooltip" tabindex="0">
              {badge}
              <span class="teacher-sync-tooltip__text" role="tooltip">{tooltip_text}</span>
            </div>
          </td>
          <td><span class="teacher-sync-time">{s["last_sync"]}</span></td>
          <td>{partial_cell}</td>
        </tr>
        """

    st.markdown(
        f"""
        <div class="teacher-sync-card" role="region" aria-label="Student sync status">
          <h3 class="teacher-sync-title">Student Sync Status</h3>
          <p class="teacher-sync-subtitle">
            Per-student device sync visibility — placeholder data below
          </p>
          <table class="teacher-sync-table" role="table">
            <thead>
              <tr>
                <th scope="col">Student</th>
                <th scope="col">Sync Status</th>
                <th scope="col">Last Sync</th>
                <th scope="col">Partial Sync</th>
              </tr>
            </thead>
            <tbody>
              {rows_html}
            </tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_teacher_insights_dashboard() -> None:
    theme = st.session_state.get("theme", "light")
    theme_class = "theme-dark" if theme == "dark" else ""
    environment_badge = build_environment_badge_html()

    st.markdown(
        f'<div class="dashboard-root {theme_class}" id="studaxis-teacher-dashboard">',
        unsafe_allow_html=True,
    )

    col_header, col_notify = st.columns([6, 1.2])

    with col_header:
        st.markdown(
            """
            <div class="dashboard-header-card" role="banner">
              <div class="dashboard-header-left">
                <div class="dashboard-avatar" aria-hidden="true">T</div>
                <div class="dashboard-welcome-text">
                  <span class="dashboard-welcome-name">Teacher Insight Dashboard</span>
                  <span class="dashboard-welcome-sub">
                    Class-level AI insights for intervention planning
                  </span>
                </div>
              </div>
              <div class="dashboard-header-right">
                <span class="dashboard-mode-badge" title="Role">Teacher View</span>
                {environment_badge}
                <span class="status-pill status-pill--online" role="status">● Insights Ready</span>
              </div>
            </div>
            """.format(environment_badge=environment_badge),
            unsafe_allow_html=True,
        )
        if st.session_state.get("low_power_mode_active", False):
            render_low_power_indicator()

    with col_notify:
        render_notification_bell(
            role="teacher",
            theme=theme,
            key_prefix="teacher_header_notifications",
        )

    # ── Student Sync Monitoring Table ──────────────────────────
    _render_student_sync_table(_PLACEHOLDER_STUDENTS)

    if not st.session_state.get("teacher_analytics_visible", False):
        render_lazy_loading_card(
            title="Teacher analytics",
            description="Loading data...",
            illustration_ratio="4:3",
        )
        render_teacher_analytics_skeleton()
        if st.button("Load teacher analytics", key="load_teacher_analytics", use_container_width=True):
            st.session_state.teacher_analytics_visible = True
            st.rerun()
    else:
        teacher_insights = get_teacher_insight_templates()
        render_teacher_insight_bento_grid(teacher_insights)

    teacher_dashboard_url = os.getenv("TEACHER_DASHBOARD_URL", "").strip()

    col_open_cloud, col_back, _ = st.columns([2, 1, 3])
    with col_open_cloud:
        if teacher_dashboard_url:
            try:
                st.link_button(
                    "Open Cloud Teacher Dashboard",
                    teacher_dashboard_url,
                    use_container_width=True,
                )
            except AttributeError:
                st.markdown(f"[Open Cloud Teacher Dashboard]({teacher_dashboard_url})")
        else:
            st.button(
                "Cloud Dashboard URL Not Configured",
                disabled=True,
                use_container_width=True,
                key="teacher_cloud_dashboard_missing",
            )

    with col_back:
        if st.button("Back", key="teacher_insights_back", use_container_width=True):
            st.session_state.page = "landing"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
