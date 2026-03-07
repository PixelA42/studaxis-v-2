"""
Studaxis - Flashcards Page

Dynamic flashcard generation via local AI and zero-lag review UI.
Integrated with flashcards_system: LocalStorage, spaced repetition, StudentModel, and optional RAG.
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

from ai_integration_layer import AIEngine, AITaskType
from performance_ui import render_low_power_indicator

# Allow importing flashcards_system when running from backend
_APP_DIR = Path(__file__).resolve().parent.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

# LocalStorage: ensure backend is on path so "utils" resolves

try:
    from flashcards_system.spaced_repetition import update_card as update_card_srs
    from flashcards_system.student_model import StudentModel
    _HAS_FLASHCARDS_SYSTEM = True
except ImportError:
    _HAS_FLASHCARDS_SYSTEM = False

from utils.local_storage import LocalStorage

_DATA_PATH = Path(__file__).parent.parent / "data" / "user_stats.json"


def _get_storage() -> LocalStorage:
    if "flashcard_storage" not in st.session_state:
        st.session_state.flashcard_storage = LocalStorage(base_path=str(Path(__file__).parent.parent))
    return st.session_state.flashcard_storage


def _get_student_model() -> "StudentModel | None":
    if not _HAS_FLASHCARDS_SYSTEM:
        return None
    if "flashcard_student_model" not in st.session_state:
        st.session_state.flashcard_student_model = StudentModel(_get_storage())  # pyright: ignore[reportPossiblyUnboundVariable]
    return st.session_state.flashcard_student_model


def _load_stats() -> dict[str, Any]:
    return _get_storage().load_user_stats()


def _save_stats(stats: dict[str, Any]) -> None:
    _get_storage().save_user_stats(stats)


def _get_ai_engine() -> AIEngine:
    if "ai_engine" not in st.session_state:
        st.session_state.ai_engine = AIEngine(base_path=str(Path(__file__).parent.parent))
    return st.session_state.ai_engine


def _ensure_state() -> None:
    st.session_state.setdefault("current_deck", [])
    st.session_state.setdefault("flashcard_index", 0)
    st.session_state.setdefault("flashcard_show_answer", False)
    st.session_state.setdefault("flashcard_last_ai_explanation", "")
    st.session_state.setdefault("flashcard_last_recommendation", "")


def _normalize_cards(raw: list[Any]) -> list[dict[str, Any]]:
    """Convert LLM output to list of cards with id, topic, front, back."""
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        front = str(item.get("front", item.get("question", ""))).strip() or "?"
        back = str(item.get("back", item.get("answer", ""))).strip() or "—"
        topic = str(item.get("topic", "")).strip() or "General"
        card_id = str(item.get("id", item.get("card_id", str(uuid.uuid4()))))
        out.append({
            "id": card_id,
            "card_id": card_id,
            "topic": topic,
            "front": front,
            "back": back,
        })
    return out


def _enrich_for_storage(cards: list[dict[str, Any]], topic: str) -> list[dict[str, Any]]:
    """Add flashcards_system / spaced-repetition fields and return new list."""
    now = datetime.now(timezone.utc).isoformat()
    enriched = []
    for c in cards:
        card = dict(c)
        card["card_id"] = card.get("card_id") or card.get("id") or str(uuid.uuid4())
        card["topic"] = card.get("topic") or topic
        card["question"] = card.get("front", card.get("question", "?"))
        card["answer"] = card.get("back", card.get("answer", "—"))
        card["type"] = card.get("type", "conceptual")
        card["created_at"] = card.get("created_at") or now
        card["interval"] = int(card.get("interval", 1))
        card["repetitions"] = int(card.get("repetitions", 0))
        card["ease_factor"] = float(card.get("ease_factor", 2.5))
        card["next_review"] = card.get("next_review") or now
        enriched.append(card)
    return enriched


def _card_display_front(card: dict[str, Any]) -> str:
    return card.get("front") or card.get("question") or "?"


def _card_display_back(card: dict[str, Any]) -> str:
    return card.get("back") or card.get("answer") or "—"


def _card_id(card: dict[str, Any]) -> str:
    return str(card.get("card_id") or card.get("id") or "")


def _extract_json_array(text: str) -> str:
    """Try to extract a JSON array from model output (strip markdown code blocks etc.)."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _update_flashcard_stats(mark: str) -> None:
    stats = _load_stats()
    fc = stats.setdefault("flashcard_stats", {})
    fc["total_reviewed"] = int(fc.get("total_reviewed", 0)) + 1
    if mark == "easy":
        fc["mastered"] = int(fc.get("mastered", 0)) + 1
    else:
        fc["due_for_review"] = int(fc.get("due_for_review", 0)) + 1
    _save_stats(stats)


def _apply_rating_and_advance(card: dict[str, Any], quality: int, deck: list[dict[str, Any]], idx: int, n: int) -> None:
    """Update card with spaced repetition, persist to storage, update topic performance."""
    storage = _get_storage()
    all_cards = storage.get_all_flashcards()
    cid = _card_id(card)
    for i, c in enumerate(all_cards):
        if str(c.get("card_id") or c.get("id")) == cid:
            updated = update_card_srs(c, quality) if _HAS_FLASHCARDS_SYSTEM else c  # pyright: ignore[reportPossiblyUnboundVariable]
            all_cards[i] = updated
            break
    else:
        # Card not in storage (e.g. from current session only); still run SRS and append
        card_copy = dict(card)
        card_copy.setdefault("interval", 1)
        card_copy.setdefault("repetitions", 0)
        card_copy.setdefault("ease_factor", 2.5)
        card_copy.setdefault("next_review", datetime.now(timezone.utc).isoformat())
        if _HAS_FLASHCARDS_SYSTEM:
            update_card_srs(card_copy, quality)  # pyright: ignore[reportPossiblyUnboundVariable]
        all_cards.append(card_copy)
    storage.save_flashcards(all_cards)

    student_model = _get_student_model()
    if student_model:
        student_model.update_topic_performance(card.get("topic", "General"), quality >= 3)

    _update_flashcard_stats("easy" if quality >= 4 else "hard")
    st.session_state.flashcard_show_answer = False
    st.session_state.flashcard_index = (idx + 1) % n
    st.rerun()


def _render_generator_ui() -> None:
    """Show generator card when current_deck is empty. Option to start due review."""
    storage = _get_storage()
    due = storage.get_due_cards() if _HAS_FLASHCARDS_SYSTEM else []

    if due and st.button("📋 Review due cards", type="secondary", key="flash_review_due"):
        # Convert to display format (front/back) for UI
        deck = []
        for c in due:
            deck.append({
                **c,
                "front": c.get("question", c.get("front", "?")),
                "back": c.get("answer", c.get("back", "—")),
            })
        st.session_state.current_deck = deck
        st.session_state.flashcard_index = 0
        st.session_state.flashcard_show_answer = False
        st.session_state.flashcard_last_ai_explanation = ""
        st.session_state.flashcard_last_recommendation = ""
        st.rerun()

    with st.container():
        st.subheader("Create your deck")
        st.caption("What would you like to study? We'll generate flashcards with local AI.")
        if due:
            st.caption(f"You have **{len(due)}** card(s) due for review — use the button above to review them.")

        input_type = st.radio(
            "Input type",
            options=["Topic Name", "Textbook Chapter"],
            key="flash_input_type",
            horizontal=True,
        )
        topic_or_chapter = st.text_input(
            "Enter topic or chapter name",
            key="flash_topic_input",
            placeholder="e.g. Newton's Laws, Chapter 5 – Cell Biology",
        )
        count = st.slider(
            "Number of flashcards",
            min_value=5,
            max_value=35,
            value=10,
            key="flash_count",
            help="AI may adjust this based on content density.",
        )

        if st.button("Generate Flashcards", type="primary", key="flash_generate_btn"):
            if not (topic_or_chapter and topic_or_chapter.strip()):
                st.warning("Please enter a topic or chapter name.")
                return
            with st.spinner("Generating your custom deck with local AI..."):
                ai_engine = _get_ai_engine()
                connectivity = st.session_state.get("connectivity_status", "offline")
                offline_mode = connectivity != "online"
                try:
                    response = ai_engine.request(
                        task_type=AITaskType.FLASHCARD_GENERATION,
                        user_input=topic_or_chapter.strip(),
                        context_data={
                            "input_type": input_type,
                            "topic_or_chapter": topic_or_chapter.strip(),
                            "count": count,
                        },
                        offline_mode=offline_mode,
                        privacy_sensitive=True,
                        user_id=st.session_state.get("profile_name"),
                    )
                    raw_text = _extract_json_array(response.text)
                    parsed = json.loads(raw_text)
                    if not isinstance(parsed, list):
                        st.error("AI returned invalid format: expected a JSON array of cards.")
                        return
                    deck = _normalize_cards(parsed)
                    if not deck:
                        st.error("AI returned no valid flashcards. Try a different topic or count.")
                        return
                    topic = topic_or_chapter.strip()
                    enriched = _enrich_for_storage(deck, topic)
                    storage = _get_storage()
                    storage.add_flashcards(enriched)
                    st.session_state.current_deck = enriched
                    st.session_state.flashcard_index = 0
                    st.session_state.flashcard_show_answer = False
                    st.session_state.flashcard_last_ai_explanation = ""
                    st.session_state.flashcard_last_recommendation = ""
                    st.rerun()
                except json.JSONDecodeError as e:
                    st.error(
                        "Could not parse AI response as JSON. The model may have added extra text. "
                        f"Details: {e}"
                    )
                except (ConnectionError, TimeoutError) as e:
                    st.error(str(e))


def _render_review_ui(deck: list[dict[str, Any]]) -> None:
    """Zero-lag review UI: Front → Show Answer → Back, Explain, Mark Easy/Hard, Recommendation."""
    if st.button("🗑️ Clear deck & generate new", type="secondary", key="flash_clear_deck"):
        st.session_state.current_deck = []
        st.session_state.flashcard_index = 0
        st.session_state.flashcard_show_answer = False
        st.session_state.flashcard_last_ai_explanation = ""
        st.session_state.flashcard_last_recommendation = ""
        st.rerun()

    n = len(deck)
    idx = st.session_state.flashcard_index % n
    card = deck[idx]
    progress = f"Card {idx + 1} of {n}"
    st.markdown(f"**{progress}**  \n**Topic:** {card.get('topic', 'General')}")

    if not st.session_state.flashcard_show_answer:
        st.info(_card_display_front(card))
        if st.button("Show answer", type="primary", key="flash_show_answer"):
            st.session_state.flashcard_show_answer = True
            st.rerun()
        return

    ai_engine = _get_ai_engine()
    st.success(_card_display_back(card))
    connectivity = st.session_state.get("connectivity_status", "offline")
    offline_mode = connectivity != "online"

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Explain with AI", key="flash_explain"):
            with st.spinner("Processing with local AI..."):
                response = ai_engine.request(
                    task_type=AITaskType.FLASHCARD_EXPLANATION,
                    user_input=f"Explain this flashcard: {_card_display_front(card)}",
                    context_data={
                        "flashcard_id": _card_id(card),
                        "topic": card.get("topic", "General"),
                        "front": _card_display_front(card),
                        "back": _card_display_back(card),
                    },
                    offline_mode=offline_mode,
                    privacy_sensitive=True,
                    user_id=st.session_state.get("profile_name"),
                )
            st.session_state.flashcard_last_ai_explanation = response.text
            st.rerun()

    with col2:
        if st.button("Mark easy", key="flash_easy"):
            _apply_rating_and_advance(card, 4, deck, idx, n)

    with col3:
        if st.button("Mark hard", key="flash_hard"):
            _apply_rating_and_advance(card, 2, deck, idx, n)

    if st.button("Get study recommendation", key="flash_recommendation"):
        with st.spinner("Processing with local AI..."):
            recommendation = ai_engine.request(
                task_type=AITaskType.STUDY_RECOMMENDATION,
                user_input=f"Suggest a review plan for topic {card.get('topic', 'General')}.",
                context_data={
                    "topic": card.get("topic", "General"),
                    "review_mode": "flashcards",
                    "recent_card_id": _card_id(card),
                    "front": _card_display_front(card),
                    "back": _card_display_back(card),
                    "time_budget_minutes": st.session_state.get("study_time_minutes", 15),
                },
                offline_mode=offline_mode,
                privacy_sensitive=True,
                user_id=st.session_state.get("profile_name"),
            )
        st.session_state.flashcard_last_recommendation = recommendation.text
        st.rerun()

    if st.session_state.flashcard_last_ai_explanation:
        st.markdown("### AI explanation")
        st.write(st.session_state.flashcard_last_ai_explanation)

    if st.session_state.flashcard_last_recommendation:
        st.markdown("### AI recommendation")
        st.write(st.session_state.flashcard_last_recommendation)


def show_flashcards() -> None:
    _ensure_state()

    if st.button("← Back to dashboard", key="flash_back"):
        st.session_state.page = "dashboard"
        st.rerun()

    st.title("Flashcards")
    st.caption("Generate decks with local AI and review with explanations and recommendations.")
    if _HAS_FLASHCARDS_SYSTEM:
        st.caption("Integrated with spaced repetition and due-card review.")
    if st.session_state.get("low_power_mode_active", False):
        render_low_power_indicator()

    current_deck = st.session_state.current_deck
    if not current_deck:
        _render_generator_ui()
        return

    _render_review_ui(current_deck)
