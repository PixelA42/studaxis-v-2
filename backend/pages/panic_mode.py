"""
Studaxis - Panic Mode (Exam Simulator)

Distraction-free timed exam flow with AIEngine-based grading and
post-exam feedback generation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

from ai_integration_layer import AIEngine, AITaskType
from ui_components import render_empty_state, render_mode_status_badge


_DATA_DIR = Path(__file__).parent.parent / "data"


def _user_stats_path() -> Path:
    uid = st.session_state.get("profile_name", "")
    if uid:
        d = _DATA_DIR / "users" / uid
        d.mkdir(parents=True, exist_ok=True)
        return d / "user_stats.json"
    return _DATA_DIR / "user_stats.json"

_PANIC_QUESTIONS: list[dict[str, str]] = [
    {
        "id": "p1",
        "topic": "Physics",
        "question": "Define momentum and explain one real-world example.",
        "expected_answer": "Momentum is mass multiplied by velocity.",
    },
    {
        "id": "p2",
        "topic": "Biology",
        "question": "Explain why osmosis is important in plant cells.",
        "expected_answer": "It helps maintain turgor pressure and water balance.",
    },
    {
        "id": "p3",
        "topic": "Mathematics",
        "question": "What is the derivative of x^3 and which rule applies?",
        "expected_answer": "3x^2 using the power rule.",
    },
    {
        "id": "p4",
        "topic": "Chemistry",
        "question": "What is pH and what does pH 7 indicate?",
        "expected_answer": "pH measures acidity/basicity; pH 7 is neutral.",
    },
    {
        "id": "p5",
        "topic": "Physics",
        "question": "State one difference between speed and velocity.",
        "expected_answer": "Speed is scalar; velocity includes direction.",
    },
]


def _load_stats() -> dict[str, Any]:
    p = _user_stats_path()
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return {
        "quiz_stats": {"total_attempted": 0, "total_correct": 0, "average_score": 0.0, "by_topic": {}},
        "panic_mode_stats": {"attempts": 0, "last_score": 0.0, "last_attempt_at": None},
    }


def _save_stats(stats: dict[str, Any]) -> None:
    p = _user_stats_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _get_ai_engine() -> AIEngine:
    if "ai_engine" not in st.session_state:
        st.session_state.ai_engine = AIEngine(base_path=str(Path(__file__).parent.parent))
    return st.session_state.ai_engine


def _local_score(answer: str, expected: str) -> float:
    if not answer.strip():
        return 0.0
    answer_tokens = set(answer.lower().split())
    expected_tokens = set(expected.lower().split())
    if not expected_tokens:
        return 0.0
    return round(min(10.0, max(0.0, (len(answer_tokens & expected_tokens) / len(expected_tokens)) * 10)), 1)


def _ensure_exam_state() -> None:
    st.session_state.setdefault("panic_started", False)
    st.session_state.setdefault("panic_start_time", None)
    st.session_state.setdefault("panic_duration_minutes", 15)
    st.session_state.setdefault("panic_answers", {})
    st.session_state.setdefault("panic_submitted", False)
    st.session_state.setdefault("panic_result", None)


def _reset_exam_state() -> None:
    st.session_state.panic_started = False
    st.session_state.panic_start_time = None
    st.session_state.panic_answers = {}
    st.session_state.panic_submitted = False
    st.session_state.panic_result = None


def _update_stats(scores: list[float], topic_scores: dict[str, list[float]]) -> None:
    stats = _load_stats()

    quiz_stats = stats.setdefault("quiz_stats", {})
    total_attempted = int(quiz_stats.get("total_attempted", 0))
    total_correct = int(quiz_stats.get("total_correct", 0))
    avg_prev = float(quiz_stats.get("average_score", 0.0))

    for score in scores:
        total_attempted += 1
        if score >= 6.0:
            total_correct += 1

    if total_attempted > 0:
        total_score_count_before = total_attempted - len(scores)
        cumulative = (avg_prev * total_score_count_before) + sum(scores)
        quiz_stats["average_score"] = round(cumulative / total_attempted, 2)
    else:
        quiz_stats["average_score"] = 0.0

    quiz_stats["total_attempted"] = total_attempted
    quiz_stats["total_correct"] = total_correct

    by_topic = quiz_stats.setdefault("by_topic", {})
    for topic, topic_list in topic_scores.items():
        entry = by_topic.setdefault(topic, {"attempts": 0, "avg_score": 0.0})
        prev_attempts = int(entry.get("attempts", 0))
        prev_avg = float(entry.get("avg_score", 0.0))
        new_attempts = prev_attempts + len(topic_list)
        entry["attempts"] = new_attempts
        entry["avg_score"] = round(((prev_avg * prev_attempts) + sum(topic_list)) / new_attempts, 2)

    pm_stats = stats.setdefault("panic_mode_stats", {"attempts": 0, "last_score": 0.0, "last_attempt_at": None})
    pm_stats["attempts"] = int(pm_stats.get("attempts", 0)) + 1
    pm_stats["last_score"] = round(sum(scores) / len(scores), 2) if scores else 0.0
    pm_stats["last_attempt_at"] = datetime.now(timezone.utc).isoformat()

    _save_stats(stats)


def _submit_exam() -> None:
    ai_engine = _get_ai_engine()
    connectivity = st.session_state.get("connectivity_status", "offline")
    offline_mode = connectivity != "online"

    answers = st.session_state.panic_answers
    grading_rows: list[dict[str, Any]] = []
    scores: list[float] = []
    topic_scores: dict[str, list[float]] = {}

    try:
        with st.spinner("Submitting panic mode exam for grading..."):
            for q in _PANIC_QUESTIONS:
                answer = answers.get(q["id"], "")
                grading = ai_engine.request(
                    task_type=AITaskType.GRADING,
                    user_input=answer,
                    context_data={
                        "exam_mode": "panic_mode",
                        "question_id": q["id"],
                        "question": q["question"],
                        "topic": q["topic"],
                        "expected_answer": q["expected_answer"],
                        "rubric": "[PROMPT_TEMPLATE_GRADING]",
                    },
                    offline_mode=offline_mode,
                    privacy_sensitive=True,
                    user_id=st.session_state.get("profile_name"),
                )
                score = _local_score(answer, q["expected_answer"])
                scores.append(score)
                topic_scores.setdefault(q["topic"], []).append(score)
                grading_rows.append(
                    {
                        "question_id": q["id"],
                        "topic": q["topic"],
                        "score": score,
                        "feedback": grading.text,
                        "model": grading.metadata.get("model_name"),
                    }
                )

            weak_topics_payload = {
                topic: round(sum(vals) / len(vals), 2) for topic, vals in topic_scores.items()
            }
            weak_topic_response = ai_engine.request(
                task_type=AITaskType.WEAK_TOPIC_DETECTION,
                user_input="Identify weak topics from this exam result.",
                context_data={
                    "exam_mode": "panic_mode",
                    "topic_scores": weak_topics_payload,
                    "total_questions": len(_PANIC_QUESTIONS),
                },
                offline_mode=offline_mode,
                privacy_sensitive=True,
                user_id=st.session_state.get("profile_name"),
            )

            recommendation = ai_engine.request(
                task_type=AITaskType.STUDY_RECOMMENDATION,
                user_input="Create a post-exam improvement plan.",
                context_data={
                    "exam_mode": "panic_mode",
                    "topic_scores": weak_topics_payload,
                    "weak_topics_summary": weak_topic_response.text,
                    "study_time_minutes": st.session_state.get("study_time_minutes", "[STUDY_TIME_MINUTES]"),
                },
                offline_mode=offline_mode,
                privacy_sensitive=True,
                user_id=st.session_state.get("profile_name"),
            )
    except Exception as exc:
        st.error(f"Panic mode submission failed: {exc}")
        return

    _update_stats(scores, topic_scores)

    st.session_state.panic_result = {
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
        "scores": scores,
        "grading_rows": grading_rows,
        "weak_topics_text": weak_topic_response.text,
        "recommendation_text": recommendation.text,
        "model": recommendation.metadata.get("model_name"),
        "target": recommendation.metadata.get("execution_target"),
    }
    st.session_state.panic_submitted = True


def show_panic_mode() -> None:
    _ensure_exam_state()

    if st.button("← Back to Dashboard", key="panic_back"):
        _reset_exam_state()
        st.session_state.page = "dashboard"
        st.rerun()

    st.title("Panic Mode")
    st.caption("Timed exam simulator. Grading + post-exam feedback are routed through AIEngine.")
    connectivity = st.session_state.get("connectivity_status", "offline")
    render_mode_status_badge(
        "Online mode" if connectivity == "online" else "Offline mode - exam is fully local",
        online=connectivity == "online",
    )

    if not _PANIC_QUESTIONS:
        render_empty_state(
            "No panic mode questions available",
            "Empty State Illustration Placeholder - add a question set to start the exam simulator.",
        )
        return

    if not st.session_state.panic_started:
        duration = st.selectbox("Exam duration (minutes)", [15, 30, 60], index=0)
        if st.button("Start Panic Mode Exam", type="primary"):
            st.session_state.panic_duration_minutes = duration
            st.session_state.panic_started = True
            st.session_state.panic_start_time = datetime.now(timezone.utc).isoformat()
            st.rerun()
        return

    if not st.session_state.panic_submitted:
        st.warning(
            "Distraction-free mode: complete all answers, then submit once for AI grading."
        )
        for idx, q in enumerate(_PANIC_QUESTIONS, start=1):
            st.markdown(f"### Q{idx}. {q['question']}")
            ans = st.text_area(
                f"Answer {idx}",
                key=f"panic_ans_{q['id']}",
                value=st.session_state.panic_answers.get(q["id"], ""),
                height=120,
            )
            st.session_state.panic_answers[q["id"]] = ans

        if st.button("Submit Exam", type="primary"):
            _submit_exam()
            st.rerun()
        return

    result = st.session_state.panic_result or {}
    st.success(f"Exam submitted. Average score: {result.get('average_score', 0.0)}/10")
    st.markdown("## Question-wise Feedback")
    for row in result.get("grading_rows", []):
        st.markdown(f"**{row['question_id']} ({row['topic']})** - Score: {row['score']}/10")
        st.write(row["feedback"])

    st.markdown("## Weak Topic Detection")
    st.write(result.get("weak_topics_text", "No weak topic summary available."))

    st.markdown("## Post-Exam Study Plan")
    st.write(result.get("recommendation_text", "No recommendation available."))
    st.caption(
        f"AI target: {result.get('target', 'local')} | Model: {result.get('model', '[LOCAL_AI_MODEL]')}"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Retake Panic Mode"):
            _reset_exam_state()
            st.rerun()
    with col2:
        if st.button("Return to Dashboard"):
            _reset_exam_state()
            st.session_state.page = "dashboard"
            st.rerun()
