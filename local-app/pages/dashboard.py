"""
Studaxis — Student Dashboard (Solo Mode)
════════════════════════════════════════
Bento grid dashboard rendered inside the Global UI Shell.

Layout
------
  Header card   — avatar · welcome · streak pill · mode badge · connectivity · theme toggle
  Stats row     — 3 glass tiles: streak / quiz average / flashcards mastered
  Feature grid  — 2 rows × asymmetric columns:
                    Row 1: [AI Chat  ·  Quiz]  (3:2)
                    Row 2: [Flashcards  ·  Panic Mode]  (2:3)
  Footer bar    — sync status · last-sync timestamp · logout

Data source: local-app/data/user_stats.json
Session keys consumed: theme, profile_name, profile_mode, connectivity_status
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from deployment_ui import build_environment_badge_html
from notifications_ui import render_notification_bell
from pages.insight_engine_ui import build_student_insights_from_stats, render_student_insight_bento_grid
from performance_ui import (
    render_dashboard_stats_skeleton,
    render_lazy_loading_card,
    render_low_bandwidth_note,
    render_low_power_indicator,
)
from preferences import save_theme_preference


# ── Helpers ──────────────────────────────────────────────────────────────────

_STATS_FILE = Path(__file__).parent.parent / "data" / "user_stats.json"

_DEFAULT_STATS: dict[str, Any] = {
    "user_id": "student_001",
    "last_sync_timestamp": None,
    "streak": {"current": 0, "longest": 0, "last_activity_date": None},
    "quiz_stats": {
        "total_attempted": 0,
        "total_correct": 0,
        "average_score": 0.0,
        "last_quiz_date": None,
        "by_topic": {}
    },
    "flashcard_stats": {"total_reviewed": 0, "mastered": 0, "due_for_review": 0},
    "chat_history": [],
    "preferences": {"difficulty_level": "Beginner", "theme": "light", "language": "English", "sync_enabled": True},
    "hardware_info": {},
}


def _load_user_stats() -> dict[str, Any]:
    """Load user_stats.json; return safe defaults on any error."""
    try:
        if _STATS_FILE.exists():
            raw = _STATS_FILE.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
    except (OSError, json.JSONDecodeError):
        pass
    return _DEFAULT_STATS.copy()


def _fmt_sync_time(raw: str | None) -> str:
    """Return a human-readable last-sync string."""
    if not raw:
        return "Never synced"
    try:
        dt = datetime.fromisoformat(raw)
        return dt.strftime("%d %b %Y, %I:%M %p")
    except ValueError:
        return raw


def _initials(name: str | None) -> str:
    if not name:
        return "S"
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[0].upper()


# ── CSS injection ─────────────────────────────────────────────────────────────

def _streak_progress(streak: int) -> tuple[int, int, str]:
    """
    Return (pct_filled, milestone, label) for the streak progress bar.

    Milestones: 7 → 30 → 100 days.
    """
    milestones = [7, 30, 100]
    for m in milestones:
        if streak < m:
            pct = min(100, round((streak / m) * 100))
            return pct, m, f"{streak}/{m} days to next milestone"
    return 100, 100, "All milestones reached!"


def _inject_dashboard_css(theme: str) -> None:
    """
    Emit dashboard-scoped CSS custom properties.

    Since Streamlit does not expose the <body> element, dark-mode tokens are
    re-injected as a per-render <style> block rather than toggled via a class.
    """
    if theme == "dark":
        overrides = """
        .dashboard-root {
            --db-bg-page: #020617;
            --db-bg-card: rgba(15, 23, 42, 0.85);
            --db-bg-card-solid: #0F172A;
            --db-bg-stat: rgba(15, 23, 42, 0.9);
            --db-text-main: #E5E7EB;
            --db-text-muted: #9CA3AF;
            --db-border: rgba(148, 163, 184, 0.35);
            --db-shadow: 0 18px 45px rgba(0, 0, 0, 0.35);
            --db-shadow-hover: 0 24px 55px rgba(0, 0, 0, 0.5);
        }
        .dashboard-root .stTextInput input,
        .dashboard-root .stSelectbox select {
            background: rgba(15, 23, 42, 0.9);
            color: #E5E7EB;
            border-color: rgba(148, 163, 184, 0.35);
        }
        body { background: #020617 !important; }
        """
        page_bg = "#020617"
    else:
        overrides = "body { background: #F8FAFC !important; }"
        page_bg = "#F8FAFC"

    button_css = f"""
    /* Force page background */
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {{
        background: {page_bg} !important;
    }}
    div[data-testid="stVerticalBlock"] .stButton > button {{
        transition: background 0.16s ease-out, transform 0.16s ease-out, box-shadow 0.16s ease-out;
    }}
    div[data-testid="stVerticalBlock"] .stButton > button:hover {{
        transform: scale(1.02);
    }}
    div[data-testid="stVerticalBlock"] .stButton > button:focus-visible {{
        outline: 2px solid #00A8E8;
        box-shadow: 0 0 0 4px rgba(0, 168, 232, 0.35);
    }}
    """
    st.markdown(f"<style>{overrides}{button_css}</style>", unsafe_allow_html=True)


# ── Section renderers ─────────────────────────────────────────────────────────

def _render_header(
    profile_name: str | None,
    streak: int,
    theme: str,
    connectivity_status: str,
    profile_mode: str | None,
    sync_enabled: bool,
    low_power_mode: bool,
) -> None:
    """Full-width glass header card."""
    initials = _initials(profile_name)
    display_name = profile_name or "Student"
    is_online = connectivity_status == "online"

    conn_html = (
        '<span class="status-pill status-pill--online" role="status" aria-label="Online">● Online</span>'
        if is_online
        else '<span class="status-pill status-pill--offline" role="status" aria-label="Offline">○ Offline</span>'
    )

    mode_label = "Solo Mode" if profile_mode in ("solo", None) else "Class Linked"
    environment_badge = build_environment_badge_html(sync_enabled=sync_enabled)

    streak_html = (
        f'<span class="dashboard-streak-pill" title="Current study streak">'
        f'🔥 <span class="streak-count">{streak}</span>&nbsp;day{"s" if streak != 1 else ""}'
        f'</span>'
    )

    theme_icon = "🌙" if theme == "light" else "☀️"
    theme_label = "Dark mode" if theme == "light" else "Light mode"

    # Keep the header card as the primary visual surface while exposing
    # notification and theme controls in the same top-row header region.
    col_left, col_notify, col_right = st.columns([5.3, 1.2, 1.1])

    with col_left:
        st.markdown(
            f"""
            <div class="dashboard-header-card" role="banner">
              <div class="dashboard-header-left">
                <div class="dashboard-avatar" aria-hidden="true">{initials}</div>
                <div class="dashboard-welcome-text">
                  <span class="dashboard-welcome-name">Welcome back, {display_name}</span>
                  <span class="dashboard-welcome-sub">Personal Mastery · AI Tutor ready</span>
                </div>
              </div>
              <div class="dashboard-header-right">
                {streak_html}
                <span class="dashboard-mode-badge" title="Learning mode">{mode_label}</span>
                {environment_badge}
                {conn_html}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if low_power_mode:
            render_low_power_indicator()

    with col_notify:
        render_notification_bell(
            role="student",
            theme=theme,
            key_prefix="student_header_notifications",
        )

    with col_right:
        if st.button(
            f"{theme_icon} {theme_label}",
            key="theme_toggle_btn",
            help=f"Switch to {'dark' if theme == 'light' else 'light'} mode",
            use_container_width=True,
        ):
            new_theme = "dark" if theme == "light" else "light"
            st.session_state.theme = new_theme
            save_theme_preference(new_theme)
            st.rerun()


def _render_stats_row(
    streak_current: int,
    streak_longest: int,
    quiz_attempted: int,
    quiz_correct: int,
    flashcards_mastered: int,
    flashcards_due: int,
) -> None:
    """Three horizontal glass stat tiles with icon chips and progress indicator."""
    quiz_avg = (
        round((quiz_correct / quiz_attempted) * 100)
        if quiz_attempted > 0 else 0
    )

    # First-run empty state: student has not done anything yet
    is_fresh_start = (
        streak_current == 0
        and quiz_attempted == 0
        and flashcards_mastered == 0
    )

    streak_pct, streak_milestone, streak_milestone_label = _streak_progress(streak_current)

    c1, c2, c3 = st.columns(3, gap="medium")

    with c1:
        progress_bar_html = (
            f'<div class="db-progress-track" role="progressbar" '
            f'aria-valuenow="{streak_pct}" aria-valuemin="0" aria-valuemax="100">'
            f'  <div class="db-progress-fill" style="width:{streak_pct}%"></div>'
            f'</div>'
            f'<div class="db-progress-label">{streak_milestone_label}</div>'
        )
        empty_streak = (
            '<div class="db-empty-state">'
            '  <div class="db-empty-state-text">Complete your first session<br>to start your streak</div>'
            '</div>'
            if is_fresh_start else ""
        )
        st.markdown(
            f"""
            <div class="dashboard-stat-card" role="region" aria-label="Streak">
              <div class="db-icon-chip db-icon-chip--orange" aria-hidden="true">🔥</div>
              <div class="dashboard-stat-number">{streak_current}</div>
              <div class="dashboard-stat-label">Day Streak</div>
              <div class="dashboard-stat-sub">Longest: {streak_longest} days</div>
              {progress_bar_html}
              {empty_streak}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        quiz_empty = (
            '<div class="db-empty-state">'
            '  <div class="db-empty-state-text">Take your first quiz<br>to see your score here</div>'
            '</div>'
            if is_fresh_start else ""
        )
        st.markdown(
            f"""
            <div class="dashboard-stat-card" role="region" aria-label="Quiz average">
              <div class="db-icon-chip db-icon-chip--blue" aria-hidden="true">📊</div>
              <div class="dashboard-stat-number">{quiz_avg}%</div>
              <div class="dashboard-stat-label">Quiz Average</div>
              <div class="dashboard-stat-sub">{quiz_attempted} attempt{"s" if quiz_attempted != 1 else ""} total</div>
              {quiz_empty}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        fc_empty = (
            '<div class="db-empty-state">'
            '  <div class="db-empty-state-text">Review flashcards<br>to track mastery here</div>'
            '</div>'
            if is_fresh_start else ""
        )
        st.markdown(
            f"""
            <div class="dashboard-stat-card" role="region" aria-label="Flashcards mastered">
              <div class="db-icon-chip db-icon-chip--green" aria-hidden="true">🃏</div>
              <div class="dashboard-stat-number">{flashcards_mastered}</div>
              <div class="dashboard-stat-label">Cards Mastered</div>
              <div class="dashboard-stat-sub">{flashcards_due} due for review</div>
              {fc_empty}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Breathing room between stat row and feature grid
    st.markdown("<div style='margin-top: 4px'></div>", unsafe_allow_html=True)


def _render_feature_grid(
    quiz_attempted: int,
    flashcards_due: int,
    difficulty: str,
) -> None:
    """
    Two-row asymmetric Bento feature tiles.

    Row 1 (3:2):  AI Chat  |  Quiz
    Row 2 (2:3):  Flashcards  |  Panic Mode
    """

    # ── Row 1 ──────────────────────────────────────────────────────────────

    col_chat, col_quiz = st.columns([3, 2], gap="medium")

    with col_chat:
        st.markdown(
            """
            <div class="dashboard-feature-card dashboard-feature-card--ai" role="region" aria-label="AI Tutor Chat">
              <div class="db-icon-chip db-icon-chip--blue" aria-hidden="true">🤖</div>
              <div class="dashboard-feature-title">AI Tutor Chat</div>
              <div class="dashboard-feature-desc">
                Ask questions from your textbooks and get curriculum-grounded answers — fully offline, no internet needed.
              </div>
              <div class="dashboard-feature-meta">Powered by Llama 3.2 · RAG-grounded</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "Open Chat →",
            key="nav_chat",
            use_container_width=True,
            help="Start an AI tutoring chat session",
        ):
            st.session_state.page = "chat"
            st.rerun()

    with col_quiz:
        quiz_sub = f"{quiz_attempted} attempt{'s' if quiz_attempted != 1 else ''} · {difficulty}"
        st.markdown(
            f"""
            <div class="dashboard-feature-card" role="region" aria-label="Quick Quiz">
              <div class="db-icon-chip db-icon-chip--orange" aria-hidden="true">📝</div>
              <div class="dashboard-feature-title">Quick Quiz</div>
              <div class="dashboard-feature-desc">
                Test your knowledge with AI-generated questions. Get instant grading and feedback.
              </div>
              <div class="dashboard-feature-meta">{quiz_sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "Start Quiz →",
            key="nav_quiz",
            use_container_width=True,
            help="Start a quiz session",
        ):
            st.session_state.page = "quiz"
            st.rerun()

    # ── Row 2 ──────────────────────────────────────────────────────────────

    col_flash, col_panic = st.columns([2, 3], gap="medium")

    with col_flash:
        due_label = f"{flashcards_due} due" if flashcards_due > 0 else "All caught up"
        st.markdown(
            f"""
            <div class="dashboard-feature-card dashboard-feature-card--flashcards" role="region" aria-label="Flashcards">
              <div class="db-icon-chip db-icon-chip--green" aria-hidden="true">🃏</div>
              <div class="dashboard-feature-title">Flashcards</div>
              <div class="dashboard-feature-desc">
                Spaced-repetition review of key concepts. Mark cards Easy or Hard to schedule the next review.
              </div>
              <div class="dashboard-feature-meta">{due_label} · AI-generated</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "Review →",
            key="nav_flashcards",
            use_container_width=True,
            help="Start flashcard review session",
        ):
            st.session_state.page = "flashcards"
            st.rerun()

    with col_panic:
        st.markdown(
            """
            <div class="dashboard-feature-card dashboard-feature-card--panic" role="region" aria-label="Panic Mode — exam simulator">
              <div class="db-icon-chip db-icon-chip--red" aria-hidden="true">🚨</div>
              <div class="dashboard-feature-title">Panic Mode</div>
              <div class="dashboard-feature-desc">
                Distraction-free exam simulator with a timer. AI assistance is hidden so you practice under real conditions.
                Auto-graded on submission with Red Pen feedback.
              </div>
              <div class="dashboard-feature-meta">⏱ Timed · AI auto-graded · Full-screen</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "Enter Panic Mode →",
            key="nav_panic",
            use_container_width=True,
            help="Launch distraction-free exam simulator",
            type="primary",
        ):
            st.session_state.page = "panic_mode"
            st.rerun()


def _render_sync_indicator(
    sync_status: str,
    last_sync_time: str,
    partial_sync_status: str | None,
) -> None:
    """
    Non-intrusive sync status indicator bar.

    Sits between the header and stats row. Reads only placeholder
    session-state values — no actual cloud sync logic.
    """
    pill_map: dict[str, tuple[str, str]] = {
        "synced": ("synced", "Synced"),
        "syncing": ("syncing", "Syncing…"),
        "pending": ("pending", "Sync Pending"),
        "offline": ("offline", "Offline"),
    }
    variant, label = pill_map.get(sync_status, ("none", sync_status or "Unknown"))

    partial_html = ""
    if partial_sync_status:
        partial_html = (
            f'<div class="sync-monitor__partial" role="note">'
            f'  <span class="sync-monitor__partial-icon" aria-hidden="true">⚠</span>'
            f'  <span>{partial_sync_status}</span>'
            f'</div>'
        )

    retry_count = st.session_state.get("sync_retry_count", "[SYNC_RETRY_COUNT]")

    st.markdown(
        f"""
        <div class="sync-monitor" role="status" aria-label="Sync status indicator">
          <div class="sync-monitor__left">
            <div class="sync-monitor__pill sync-monitor__pill--{variant}" aria-live="polite">
              <span class="sync-monitor__dot" aria-hidden="true"></span>
              <span>Status: {label}</span>
            </div>
          </div>
          <div class="sync-monitor__right">
            <span class="sync-monitor__label">Last Sync:</span>
            <span class="sync-monitor__time">{last_sync_time}</span>
            <span class="sync-monitor__label" aria-label="Retry count">Retries: {retry_count}</span>
          </div>
          {partial_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_low_bandwidth_note()


def _render_footer(connectivity_status: str, last_sync_raw: str | None) -> None:
    """Compact footer: sync status + last sync timestamp + logout."""
    is_online = connectivity_status == "online"
    sync_label = _fmt_sync_time(last_sync_raw)

    conn_pill = (
        '<span class="status-pill status-pill--online" role="status">● Online — ready to sync</span>'
        if is_online
        else '<span class="status-pill status-pill--offline" role="status">○ Offline — queuing locally</span>'
    )

    st.markdown(
        f"""
        <div class="dashboard-sync-row" role="contentinfo">
          <div class="dashboard-sync-left">
            {conn_pill}
            <span class="dashboard-sync-label">Last sync: {sync_label}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_settings, col_logout, _ = st.columns([1, 1, 4])
    with col_settings:
        if st.button("Settings", key="dashboard_settings"):
            st.session_state.page = "settings"
            st.rerun()
    with col_logout:
        if st.button("Logout", key="dashboard_logout"):
            st.session_state.user_logged_in = False
            st.session_state.boot_complete = False
            st.session_state.boot_phase = "splash"
            st.session_state.page = "landing"
            st.rerun()


# ── Main entry point ──────────────────────────────────────────────────────────

def show_dashboard() -> None:
    """
    Render the Student Dashboard (Solo Mode).

    Reads user_stats.json for live data; falls back gracefully to zeros.
    Session state consumed: theme, profile_name, profile_mode, connectivity_status.
    """
    stats = _load_user_stats()

    # Pull session state values with safe defaults
    theme = st.session_state.get("theme", "light")
    profile_name = st.session_state.get("profile_name") or stats.get("user_id", "Student")
    profile_mode = st.session_state.get("profile_mode", "solo")
    connectivity_status = st.session_state.get("connectivity_status", "offline")

    # Hydrate theme from stored preference on first load
    stored_theme = stats.get("preferences", {}).get("theme", "light")
    if "theme" not in st.session_state:
        st.session_state.theme = stored_theme
        theme = stored_theme

    # Stat values
    streak_data = stats.get("streak", {})
    streak_current = streak_data.get("current", 0)
    streak_longest = streak_data.get("longest", 0)

    quiz_data = stats.get("quiz_stats", {})
    quiz_attempted = quiz_data.get("total_attempted", 0)
    quiz_correct = quiz_data.get("total_correct", 0)

    fc_data = stats.get("flashcard_stats", {})
    flashcards_mastered = fc_data.get("mastered", 0)
    flashcards_due = fc_data.get("due_for_review", 0)

    difficulty = stats.get("preferences", {}).get("difficulty_level", "Beginner")
    last_sync = stats.get("last_sync_timestamp")
    sync_enabled = stats.get("preferences", {}).get("sync_enabled", True)

    # Inject dynamic CSS tokens for chosen theme
    _inject_dashboard_css(theme)

    # Decorative background blobs (pointer-events: none, purely visual)
    st.markdown(
        """
        <div class="page-blob-layer" aria-hidden="true">
          <div class="page-blob page-blob--warm-tr"></div>
          <div class="page-blob page-blob--blue-bl"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Wrap everything in the .dashboard-root div for scoped CSS vars
    theme_class = "theme-dark" if theme == "dark" else ""
    st.markdown(
        f'<div class="dashboard-root {theme_class}" id="studaxis-dashboard">',
        unsafe_allow_html=True,
    )

    _render_header(
        profile_name=profile_name,
        streak=streak_current,
        theme=theme,
        connectivity_status=connectivity_status,
        profile_mode=profile_mode,
        sync_enabled=sync_enabled,
        low_power_mode=st.session_state.get("low_power_mode_active", False),
    )

    # ── Sync Monitoring Indicator (placeholder-driven) ─────────
    sync_status = st.session_state.get("sync_status", "[SYNC_STATUS]")
    last_sync_time = st.session_state.get("last_sync_time", "[LAST_SYNC_TIME]")
    partial_sync_status = st.session_state.get("partial_sync_status", None)

    _render_sync_indicator(
        sync_status=sync_status,
        last_sync_time=last_sync_time,
        partial_sync_status=partial_sync_status,
    )

    if not st.session_state.get("dashboard_stats_ready", False):
        render_dashboard_stats_skeleton()
        render_lazy_loading_card(
            title="Dashboard statistics",
            description="Loading data...",
            illustration_ratio="4:3",
        )
        if st.button("Load dashboard statistics", key="load_dashboard_stats", use_container_width=True):
            st.session_state.dashboard_stats_ready = True
            st.rerun()
    else:
        _render_stats_row(
            streak_current=streak_current,
            streak_longest=streak_longest,
            quiz_attempted=quiz_attempted,
            quiz_correct=quiz_correct,
            flashcards_mastered=flashcards_mastered,
            flashcards_due=flashcards_due,
        )

    student_insights = build_student_insights_from_stats(stats)
    render_student_insight_bento_grid(student_insights)

    _render_feature_grid(
        quiz_attempted=quiz_attempted,
        flashcards_due=flashcards_due,
        difficulty=difficulty,
    )

    _render_footer(
        connectivity_status=connectivity_status,
        last_sync_raw=last_sync,
    )

    st.markdown("</div>", unsafe_allow_html=True)
