"""
AI Insight Engine UI layer for Studaxis dashboards.

This module only defines UI-facing insight contracts and rendering helpers.
It does not implement model inference or analytics computation logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import streamlit as st


WEAK_TOPIC_THRESHOLD = "[WEAK_TOPIC_THRESHOLD]"
MASTERY_SCORE_RANGE = "[MASTERY_SCORE_RANGE]"
INSIGHT_REFRESH_INTERVAL = "[INSIGHT_REFRESH_INTERVAL]"
AI_CONFIDENCE_SCORE = "[AI_CONFIDENCE_SCORE]"


class InsightAudience(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"


class InsightType(str, Enum):
    WEAK_TOPIC_DETECTION = "weak_topic_detection"
    SUBJECT_MASTERY = "subject_mastery"
    DAILY_STREAK = "daily_streak"
    STUDY_RECOMMENDATION = "study_recommendation"
    QUIZ_PERFORMANCE_TREND = "quiz_performance_trend"
    FLASHCARD_RETENTION = "flashcard_retention"
    CLASS_PERFORMANCE_DISTRIBUTION = "class_performance_distribution"
    STRUGGLING_STUDENTS = "struggling_students"
    TOPIC_DIFFICULTY_ANALYSIS = "topic_difficulty_analysis"
    ASSIGNMENT_PERFORMANCE_SUMMARY = "assignment_performance_summary"
    ENGAGEMENT_METRICS = "engagement_metrics"


class InsightPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class InsightAction:
    label: str
    action_type: str
    target: str


@dataclass
class StructuredInsight:
    id: str
    title: str
    description: str
    insight_type: InsightType
    audience: InsightAudience
    priority: InsightPriority
    confidence_score: str = AI_CONFIDENCE_SCORE
    related_subject: str = "[RELATED_SUBJECT]"
    suggested_action: str = "[SUGGESTED_ACTION]"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trend_points: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    actions: list[InsightAction] = field(default_factory=list)


def _safe_pct(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    return round((numerator / denominator) * 100)


def build_student_insights_from_stats(stats: dict[str, Any]) -> list[StructuredInsight]:
    """
    Build UI insight objects from available local stats.

    All thresholds/scores that are not explicitly defined in requirements
    are represented with placeholders.
    """
    streak_current = stats.get("streak", {}).get("current", 0)
    quiz_stats = stats.get("quiz_stats", {})
    flashcard_stats = stats.get("flashcard_stats", {})
    by_topic = quiz_stats.get("by_topic", {})

    weak_topic_name = "Not enough data"
    if isinstance(by_topic, dict) and by_topic:
        weak_topic_name = next(iter(by_topic.keys()))

    quiz_attempted = int(quiz_stats.get("total_attempted", 0) or 0)
    quiz_correct = int(quiz_stats.get("total_correct", 0) or 0)
    quiz_accuracy = _safe_pct(quiz_correct, quiz_attempted)

    flashcards_reviewed = int(flashcard_stats.get("total_reviewed", 0) or 0)
    flashcards_mastered = int(flashcard_stats.get("mastered", 0) or 0)
    flashcard_mastery_pct = _safe_pct(flashcards_mastered, flashcards_reviewed)

    base_actions = [
        InsightAction(label="Explain This Insight", action_type="clarify", target="ai_clarify"),
        InsightAction(label="Open Related Material", action_type="navigate", target="study_material"),
        InsightAction(label="Dismiss", action_type="dismiss", target="dashboard"),
    ]

    return [
        StructuredInsight(
            id="insight_weak_topic",
            title="Weak Topic Alert",
            description=(
                f"Potential weak area: {weak_topic_name}. "
                f"Flag when below {WEAK_TOPIC_THRESHOLD}."
            ),
            insight_type=InsightType.WEAK_TOPIC_DETECTION,
            audience=InsightAudience.STUDENT,
            priority=InsightPriority.HIGH,
            related_subject=weak_topic_name,
            suggested_action="Start a remedial quiz on this topic.",
            metadata={"threshold": WEAK_TOPIC_THRESHOLD, "refresh_interval": INSIGHT_REFRESH_INTERVAL},
            actions=base_actions,
        ),
        StructuredInsight(
            id="insight_mastery",
            title="Subject Mastery Snapshot",
            description=f"Current mastery band: {MASTERY_SCORE_RANGE}.",
            insight_type=InsightType.SUBJECT_MASTERY,
            audience=InsightAudience.STUDENT,
            priority=InsightPriority.MEDIUM,
            related_subject="[SUBJECT]",
            suggested_action="Review weak concepts before the next quiz.",
            metadata={"mastery_range": MASTERY_SCORE_RANGE},
            actions=base_actions,
        ),
        StructuredInsight(
            id="insight_streak",
            title="Daily Learning Streak",
            description=f"Current streak is {streak_current} day(s). Keep momentum going.",
            insight_type=InsightType.DAILY_STREAK,
            audience=InsightAudience.STUDENT,
            priority=InsightPriority.MEDIUM,
            related_subject="All Subjects",
            suggested_action="Complete one activity today to continue your streak.",
            actions=base_actions,
        ),
        StructuredInsight(
            id="insight_quiz_trend",
            title="Quiz Performance Trend",
            description=f"Recent quiz accuracy is {quiz_accuracy}%.",
            insight_type=InsightType.QUIZ_PERFORMANCE_TREND,
            audience=InsightAudience.STUDENT,
            priority=InsightPriority.MEDIUM,
            related_subject="Quiz",
            suggested_action="Retake a quiz in your weakest subject.",
            trend_points=[45, 52, 61, 58, float(quiz_accuracy)],
            actions=base_actions,
        ),
        StructuredInsight(
            id="insight_flashcard_retention",
            title="Flashcard Retention",
            description=f"Retention proxy from review outcomes: {flashcard_mastery_pct}%.",
            insight_type=InsightType.FLASHCARD_RETENTION,
            audience=InsightAudience.STUDENT,
            priority=InsightPriority.LOW,
            related_subject="Flashcards",
            suggested_action="Review due flashcards before starting new cards.",
            trend_points=[30, 39, 44, 51, float(flashcard_mastery_pct)],
            actions=base_actions,
        ),
        StructuredInsight(
            id="insight_recommendation",
            title="AI Study Recommendation",
            description="Next best action based on weak topics and trend signals.",
            insight_type=InsightType.STUDY_RECOMMENDATION,
            audience=InsightAudience.STUDENT,
            priority=InsightPriority.LOW,
            related_subject="[RECOMMENDED_SUBJECT]",
            suggested_action="Study 20 minutes + one focused quiz + flashcard recap.",
            metadata={"refresh_interval": INSIGHT_REFRESH_INTERVAL},
            actions=base_actions,
        ),
    ]


def get_teacher_insight_templates() -> list[StructuredInsight]:
    """
    Teacher insight templates for UI contract and future dashboard integration.
    """
    return [
        StructuredInsight(
            id="teacher_class_distribution",
            title="Class Performance Distribution",
            description="Distribution of class scores across mastery bands.",
            insight_type=InsightType.CLASS_PERFORMANCE_DISTRIBUTION,
            audience=InsightAudience.TEACHER,
            priority=InsightPriority.MEDIUM,
        ),
        StructuredInsight(
            id="teacher_struggling_students",
            title="Struggling Students",
            description=f"Students flagged below {WEAK_TOPIC_THRESHOLD}.",
            insight_type=InsightType.STRUGGLING_STUDENTS,
            audience=InsightAudience.TEACHER,
            priority=InsightPriority.HIGH,
        ),
        StructuredInsight(
            id="teacher_topic_difficulty",
            title="Topic Difficulty Heatmap",
            description="Topics with high error concentration across the class.",
            insight_type=InsightType.TOPIC_DIFFICULTY_ANALYSIS,
            audience=InsightAudience.TEACHER,
            priority=InsightPriority.MEDIUM,
        ),
        StructuredInsight(
            id="teacher_assignment_summary",
            title="Assignment Performance Summary",
            description="Completion and score summary across active assignments.",
            insight_type=InsightType.ASSIGNMENT_PERFORMANCE_SUMMARY,
            audience=InsightAudience.TEACHER,
            priority=InsightPriority.LOW,
        ),
        StructuredInsight(
            id="teacher_engagement",
            title="Engagement Metrics",
            description="Participation, streak adherence, and activity consistency.",
            insight_type=InsightType.ENGAGEMENT_METRICS,
            audience=InsightAudience.TEACHER,
            priority=InsightPriority.LOW,
        ),
    ]


def _priority_class(priority: InsightPriority) -> str:
    return {
        InsightPriority.HIGH: "insight-card--high",
        InsightPriority.MEDIUM: "insight-card--medium",
        InsightPriority.LOW: "insight-card--low",
    }[priority]


def _render_insight_card(insight: StructuredInsight, key_prefix: str) -> None:
    priority_class = _priority_class(insight.priority)
    st.markdown(
        f"""
        <div class="insight-card {priority_class}" role="region" aria-label="{insight.title}">
          <div class="insight-card-head">
            <span class="insight-ai-badge" aria-label="AI generated insight">AI</span>
            <span class="insight-priority">{insight.priority.value.title()} Priority</span>
          </div>
          <div class="insight-title">{insight.title}</div>
          <div class="insight-description">{insight.description}</div>
          <div class="insight-meta">
            Subject: {insight.related_subject} · Confidence: {insight.confidence_score}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    button_cols = st.columns([1, 1, 1], gap="small")
    for idx, action in enumerate(insight.actions[:3]):
        with button_cols[idx]:
            st.button(
                action.label,
                key=f"{key_prefix}_{insight.id}_{action.action_type}",
                use_container_width=True,
                help=f"{action.action_type} for {insight.title}",
            )


def _render_trend_chart_card(insight: StructuredInsight) -> None:
    st.markdown(
        f"""
        <div class="insight-card insight-card--trend" role="region" aria-label="{insight.title}">
          <div class="insight-card-head">
            <span class="insight-ai-badge">AI</span>
            <span class="insight-priority">{insight.priority.value.title()} Priority</span>
          </div>
          <div class="insight-title">{insight.title}</div>
          <div class="insight-description">{insight.description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if insight.trend_points:
        st.line_chart(insight.trend_points, height=120, use_container_width=True)


def render_student_insight_bento_grid(insights: list[StructuredInsight]) -> None:
    """
    Student insight placement for Bento dashboard:
      Row 1: [AI Insight Card] [Daily Streak Insight]
      Row 2: [Weak Topic Alert] [Quiz Trend Chart]
      Row 3: [Study Recommendation]
    """
    insight_by_type = {insight.insight_type: insight for insight in insights}

    st.markdown(
        """
        <div class="insight-section-title" role="heading" aria-level="2">
          AI Insight Engine
        </div>
        """,
        unsafe_allow_html=True,
    )

    row1_col1, row1_col2 = st.columns([3, 2], gap="medium")
    with row1_col1:
        mastery = insight_by_type.get(InsightType.SUBJECT_MASTERY)
        if mastery:
            _render_insight_card(mastery, "student")
    with row1_col2:
        streak = insight_by_type.get(InsightType.DAILY_STREAK)
        if streak:
            _render_insight_card(streak, "student")

    row2_col1, row2_col2 = st.columns([2, 3], gap="medium")
    with row2_col1:
        weak = insight_by_type.get(InsightType.WEAK_TOPIC_DETECTION)
        if weak:
            _render_insight_card(weak, "student")
    with row2_col2:
        quiz_trend = insight_by_type.get(InsightType.QUIZ_PERFORMANCE_TREND)
        if quiz_trend:
            _render_trend_chart_card(quiz_trend)

    recommendation = insight_by_type.get(InsightType.STUDY_RECOMMENDATION)
    if recommendation:
        _render_insight_card(recommendation, "student")


def render_teacher_insight_bento_grid(insights: list[StructuredInsight]) -> None:
    """
    Teacher insight placement for Bento dashboard:
      Row 1: [Class Performance Chart] [Engagement Metrics]
      Row 2: [Struggling Students List] [Topic Difficulty Heatmap]
      Row 3: [Assignment Performance Summary]
    """
    insight_by_type = {insight.insight_type: insight for insight in insights}

    st.markdown(
        """
        <div class="insight-section-title" role="heading" aria-level="2">
          Teacher AI Insights
        </div>
        """,
        unsafe_allow_html=True,
    )

    row1_col1, row1_col2 = st.columns([3, 2], gap="medium")
    with row1_col1:
        class_distribution = insight_by_type.get(InsightType.CLASS_PERFORMANCE_DISTRIBUTION)
        if class_distribution:
            class_distribution.trend_points = [58, 61, 64, 62, 66]
            _render_trend_chart_card(class_distribution)
    with row1_col2:
        engagement = insight_by_type.get(InsightType.ENGAGEMENT_METRICS)
        if engagement:
            _render_insight_card(engagement, "teacher")

    row2_col1, row2_col2 = st.columns([2, 3], gap="medium")
    with row2_col1:
        struggling = insight_by_type.get(InsightType.STRUGGLING_STUDENTS)
        if struggling:
            _render_insight_card(struggling, "teacher")
    with row2_col2:
        difficulty = insight_by_type.get(InsightType.TOPIC_DIFFICULTY_ANALYSIS)
        if difficulty:
            difficulty.trend_points = [42, 47, 51, 49, 54]
            _render_trend_chart_card(difficulty)

    assignment = insight_by_type.get(InsightType.ASSIGNMENT_PERFORMANCE_SUMMARY)
    if assignment:
        _render_insight_card(assignment, "teacher")
