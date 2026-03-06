"""
Studaxis - Flashcards Page

Wires flashcard explanation and recommendation flows through AIEngine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from ai_integration_layer import AIEngine, AITaskType
from performance_ui import render_lazy_loading_card, render_low_power_indicator


_DATA_PATH = Path(__file__).parent.parent / "data" / "user_stats.json"

_FLASHCARDS: list[dict[str, str]] = [
    {
        "id": "f1",
        "topic": "Physics",
        "front": "What is acceleration?",
        "back": "Acceleration is the rate of change of velocity with time.",
    },
    {
        "id": "f2",
        "topic": "Biology",
        "front": "What is osmosis?",
        "back": "Movement of water through a semipermeable membrane from higher to lower water potential.",
    },
    {
        "id": "f3",
        "topic": "Mathematics",
        "front": "What is the derivative of x^2?",
        "back": "2x",
    },
]


def _load_stats() -> dict[str, Any]:
    try:
        if _DATA_PATH.exists():
            return json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return {"flashcard_stats": {"total_reviewed": 0, "mastered": 0, "due_for_review": 0}}


def _save_stats(stats: dict[str, Any]) -> None:
    try:
        _DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        _DATA_PATH.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _get_ai_engine() -> AIEngine:
    if "ai_engine" not in st.session_state:
        st.session_state.ai_engine = AIEngine(base_path=str(Path(__file__).parent.parent))
    return st.session_state.ai_engine


def _ensure_state() -> None:
    st.session_state.setdefault("flashcard_index", 0)
    st.session_state.setdefault("flashcard_show_answer", False)
    st.session_state.setdefault("flashcard_last_ai_explanation", "")
    st.session_state.setdefault("flashcard_last_recommendation", "")


def _update_flashcard_stats(mark: str) -> None:
    stats = _load_stats()
    fc = stats.setdefault("flashcard_stats", {})
    fc["total_reviewed"] = int(fc.get("total_reviewed", 0)) + 1
    if mark == "easy":
        fc["mastered"] = int(fc.get("mastered", 0)) + 1
    else:
        fc["due_for_review"] = int(fc.get("due_for_review", 0)) + 1
    _save_stats(stats)


def show_flashcards() -> None:
    _ensure_state()

    if st.button("← Back to Dashboard", key="flash_back"):
        st.session_state.page = "dashboard"
        st.rerun()

    st.title("Flashcards")
    st.caption("Flashcard explanation and study recommendation are routed via AI Integration Layer.")
    if st.session_state.get("low_power_mode_active", False):
        render_low_power_indicator()

    if not st.session_state.get("flashcard_set_visible", False):
        render_lazy_loading_card(
            title="Large flashcard set",
            description="Loading data...",
            illustration_ratio="4:3",
        )
        if st.button("Load flashcard set", key="flashcard_set_load", use_container_width=True):
            st.session_state.flashcard_set_visible = True
            st.rerun()
        return

    idx = st.session_state.flashcard_index % len(_FLASHCARDS)
    card = _FLASHCARDS[idx]
    progress = f"Card {idx + 1} of {len(_FLASHCARDS)}"
    st.markdown(f"**{progress}**  \n**Topic:** {card['topic']}")

    if not st.session_state.flashcard_show_answer:
        st.info(card["front"])
        if st.button("Show Answer", type="primary"):
            st.session_state.flashcard_show_answer = True
            st.rerun()
        return

    st.success(card["back"])
    connectivity = st.session_state.get("connectivity_status", "offline")
    offline_mode = connectivity != "online"
    ai_engine = _get_ai_engine()

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Explain with AI"):
            response = ai_engine.request(
                task_type=AITaskType.FLASHCARD_EXPLANATION,
                user_input=f"Explain this flashcard: {card['front']}",
                context_data={
                    "flashcard_id": card["id"],
                    "topic": card["topic"],
                    "front": card["front"],
                    "back": card["back"],
                },
                offline_mode=offline_mode,
                privacy_sensitive=True,
                user_id=st.session_state.get("profile_name"),
            )
            st.session_state.flashcard_last_ai_explanation = response.text
            st.rerun()

    with col2:
        if st.button("Mark Easy"):
            _update_flashcard_stats("easy")
            st.session_state.flashcard_show_answer = False
            st.session_state.flashcard_index = (idx + 1) % len(_FLASHCARDS)
            st.rerun()

    with col3:
        if st.button("Mark Hard"):
            _update_flashcard_stats("hard")
            st.session_state.flashcard_show_answer = False
            st.session_state.flashcard_index = (idx + 1) % len(_FLASHCARDS)
            st.rerun()

    if st.button("Get Study Recommendation"):
        recommendation = ai_engine.request(
            task_type=AITaskType.STUDY_RECOMMENDATION,
            user_input=f"Suggest a review plan for topic {card['topic']}.",
            context_data={
                "topic": card["topic"],
                "review_mode": "flashcards",
                "recent_card_id": card["id"],
                "time_budget_minutes": st.session_state.get("study_time_minutes", "[STUDY_TIME_MINUTES]"),
            },
            offline_mode=offline_mode,
            privacy_sensitive=True,
            user_id=st.session_state.get("profile_name"),
        )
        st.session_state.flashcard_last_recommendation = recommendation.text
        st.rerun()

    if st.session_state.flashcard_last_ai_explanation:
        st.markdown("### AI Explanation")
        st.write(st.session_state.flashcard_last_ai_explanation)

    if st.session_state.flashcard_last_recommendation:
        st.markdown("### AI Recommendation")
        st.write(st.session_state.flashcard_last_recommendation)

