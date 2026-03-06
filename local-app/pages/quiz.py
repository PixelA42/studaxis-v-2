"""
Studaxis - Quiz Page

Wires quiz grading and recommendation flows through AIEngine.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st

from ai_integration_layer import AIEngine, AITaskType


_DATA_PATH = Path(__file__).parent.parent / "data" / "user_stats.json"

_QUIZ_ITEMS: list[dict[str, str]] = [
    {
        "id": "q1",
        "topic": "Physics",
        "question": "State Newton's second law and explain what each term means.",
        "expected_answer": "Force equals mass times acceleration. F = m * a.",
    },
    {
        "id": "q2",
        "topic": "Biology",
        "question": "What is osmosis in simple terms?",
        "expected_answer": "Movement of water molecules from high concentration to low concentration through a semipermeable membrane.",
    },
    {
        "id": "q3",
        "topic": "Mathematics",
        "question": "Differentiate x^2 and explain the rule used.",
        "expected_answer": "Derivative of x squared is 2x using the power rule.",
    },
]


def _load_stats() -> dict[str, Any]:
    try:
        if _DATA_PATH.exists():
            return json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return {
        "quiz_stats": {
            "total_attempted": 0,
            "total_correct": 0,
            "average_score": 0.0,
            "by_topic": {},
        },
        "preferences": {"difficulty_level": "Beginner"},
    }


def _save_stats(stats: dict[str, Any]) -> None:
    try:
        os.makedirs(_DATA_PATH.parent, exist_ok=True)
        _DATA_PATH.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _get_ai_engine() -> AIEngine:
    if "ai_engine" not in st.session_state:
        st.session_state.ai_engine = AIEngine(base_path=str(Path(__file__).parent.parent))
    return st.session_state.ai_engine


def _local_score(answer: str, expected: str) -> float:
    """Simple deterministic score for progress stats in this MVP UI."""
    if not answer.strip():
        return 0.0
    answer_tokens = set(answer.lower().split())
    expected_tokens = set(expected.lower().split())
    if not expected_tokens:
        return 0.0
    overlap = len(answer_tokens & expected_tokens) / len(expected_tokens)
    return round(min(10.0, max(0.0, overlap * 10)), 1)


def _update_quiz_stats(topic: str, score: float) -> None:
    stats = _load_stats()
    quiz_stats = stats.setdefault("quiz_stats", {})

    total_attempted = int(quiz_stats.get("total_attempted", 0)) + 1
    total_correct = int(quiz_stats.get("total_correct", 0)) + (1 if score >= 6.0 else 0)
    prev_avg = float(quiz_stats.get("average_score", 0.0))
    new_avg = round(((prev_avg * (total_attempted - 1)) + score) / total_attempted, 2)

    quiz_stats["total_attempted"] = total_attempted
    quiz_stats["total_correct"] = total_correct
    quiz_stats["average_score"] = new_avg

    by_topic = quiz_stats.setdefault("by_topic", {})
    topic_entry = by_topic.setdefault(topic, {"attempts": 0, "avg_score": 0.0})
    topic_attempts = int(topic_entry.get("attempts", 0)) + 1
    topic_avg_prev = float(topic_entry.get("avg_score", 0.0))
    topic_entry["attempts"] = topic_attempts
    topic_entry["avg_score"] = round(((topic_avg_prev * (topic_attempts - 1)) + score) / topic_attempts, 2)

    _save_stats(stats)


def show_quiz() -> None:
    if st.button("← Back to Dashboard", key="quiz_back"):
        st.session_state.page = "dashboard"
        st.rerun()

    st.title("Quick Quiz")
    st.caption("Grading and recommendations are routed via AI Integration Layer.")

    difficulty = _load_stats().get("preferences", {}).get("difficulty_level", "Beginner")
    question_options = [f"{q['topic']} - {q['question']}" for q in _QUIZ_ITEMS]
    selected_label = st.selectbox("Select question", question_options, index=0)
    selected = _QUIZ_ITEMS[question_options.index(selected_label)]

    st.markdown(f"**Question:** {selected['question']}")
    answer = st.text_area("Your answer", placeholder="Write your answer here...", height=150)

    if st.button("Submit for AI Grading", type="primary"):
        ai_engine = _get_ai_engine()
        connectivity = st.session_state.get("connectivity_status", "offline")
        offline_mode = connectivity != "online"

        grading_response = ai_engine.request(
            task_type=AITaskType.GRADING,
            user_input=answer,
            context_data={
                "question_id": selected["id"],
                "question": selected["question"],
                "topic": selected["topic"],
                "expected_answer": selected["expected_answer"],
                "difficulty": difficulty,
                "rubric": "[GRADING_RUBRIC_PLACEHOLDER]",
            },
            offline_mode=offline_mode,
            privacy_sensitive=True,
            user_id=st.session_state.get("profile_name"),
        )

        score = _local_score(answer, selected["expected_answer"])
        _update_quiz_stats(selected["topic"], score)

        st.success(f"Score: {score}/10")
        st.markdown("### AI Feedback")
        st.write(grading_response.text)

        recommendation_response = ai_engine.request(
            task_type=AITaskType.STUDY_RECOMMENDATION,
            user_input=f"Recommend next steps for topic {selected['topic']}.",
            context_data={
                "topic": selected["topic"],
                "score": score,
                "difficulty": difficulty,
                "study_time_minutes": st.session_state.get("study_time_minutes", "[STUDY_TIME_MINUTES]"),
            },
            offline_mode=offline_mode,
            privacy_sensitive=True,
            user_id=st.session_state.get("profile_name"),
        )

        st.markdown("### Study Recommendation")
        st.write(recommendation_response.text)
        st.caption(
            f"AI target: {grading_response.metadata.get('execution_target')} | "
            f"Model: {grading_response.metadata.get('model_name')}"
        )
