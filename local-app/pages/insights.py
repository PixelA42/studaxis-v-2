"""
Studaxis — Insights Page
════════════════════════════════════════════════════════════════════
AI-generated learning insights and analytics dashboard.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from pages.insight_engine_ui import build_student_insights_from_stats, render_student_insight_bento_grid
from ui.components.page_chrome import render_background_blobs, render_page_root_close, render_page_root_open


_STATS_FILE = Path(__file__).parent.parent / "data" / "user_stats.json"

_DEFAULT_STATS: dict[str, Any] = {
    "user_id": "student_001",
    "streak": {"current": 0, "longest": 0},
    "quiz_stats": {"total_attempted": 0, "total_correct": 0, "average_score": 0.0},
    "flashcard_stats": {"total_reviewed": 0, "mastered": 0, "due_for_review": 0},
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


def show_insights() -> None:
    """Render the insights analytics page."""
    theme = st.session_state.get("theme", "light")
    stats = _load_user_stats()
    
    render_background_blobs()
    render_page_root_open("insights", theme)
    
    st.markdown(
        """
        <div class="hero-wrapper" style="margin-bottom: 24px; padding: 40px 24px;">
            <div class="hero-content">
                <h1 class="hero-title" style="font-size: 2rem;">
                    Learning <span class="highlight">Insights</span>
                </h1>
                <p class="hero-subtitle">
                    AI-powered analysis of your study patterns and progress
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    streak_data = stats.get("streak", {})
    quiz_data = stats.get("quiz_stats", {})
    fc_data = stats.get("flashcard_stats", {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            f"""
            <div class="dashboard-stat-card">
                <span class="dashboard-stat-icon">🔥</span>
                <span class="dashboard-stat-number">{streak_data.get('current', 0)}</span>
                <span class="dashboard-stat-label">Current Streak</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col2:
        quiz_avg = 0
        if quiz_data.get("total_attempted", 0) > 0:
            quiz_avg = round((quiz_data.get("total_correct", 0) / quiz_data["total_attempted"]) * 100)
        st.markdown(
            f"""
            <div class="dashboard-stat-card">
                <span class="dashboard-stat-icon">📊</span>
                <span class="dashboard-stat-number">{quiz_avg}%</span>
                <span class="dashboard-stat-label">Quiz Average</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col3:
        st.markdown(
            f"""
            <div class="dashboard-stat-card">
                <span class="dashboard-stat-icon">🃏</span>
                <span class="dashboard-stat-number">{fc_data.get('mastered', 0)}</span>
                <span class="dashboard-stat-label">Cards Mastered</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col4:
        st.markdown(
            f"""
            <div class="dashboard-stat-card">
                <span class="dashboard-stat-icon">📝</span>
                <span class="dashboard-stat-number">{quiz_data.get('total_attempted', 0)}</span>
                <span class="dashboard-stat-label">Quizzes Taken</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
    
    st.markdown("### AI-Generated Insights")
    student_insights = build_student_insights_from_stats(stats)
    render_student_insight_bento_grid(student_insights)
    
    st.markdown("---")
    
    st.markdown("### Study Trends")
    
    if quiz_data.get("total_attempted", 0) == 0:
        st.info(
            "📈 Complete some quizzes and flashcard reviews to see your learning trends here. "
            "Our AI will analyze your patterns and provide personalized recommendations."
        )
    else:
        st.markdown(
            """
            <div class="insight-card insight-card--trend" style="padding: 20px;">
                <div class="insight-card-head">
                    <span class="insight-ai-badge">AI</span>
                    <span class="insight-priority">Trend Analysis</span>
                </div>
                <p class="insight-description">
                    Your quiz performance and flashcard retention data will be analyzed here 
                    to show progress over time. More data = better insights.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    col_back, _ = st.columns([1, 3])
    with col_back:
        if st.button("← Back to Dashboard", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
    
    render_page_root_close()
