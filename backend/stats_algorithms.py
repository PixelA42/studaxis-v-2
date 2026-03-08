"""
Live data algorithms for dashboard stat cards.
100% offline, local JSON storage only.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def ensure_streak_structure(stats: dict[str, Any]) -> None:
    """Ensure streak has all required fields."""
    s = stats.setdefault("streak", {})
    if "current" not in s:
        s["current"] = 0
    if "longest" not in s:
        s["longest"] = 0
    if "last_active_date" not in s and "last_activity_date" not in s:
        s["last_active_date"] = None
    elif "last_active_date" not in s and "last_activity_date" in s:
        s["last_active_date"] = s["last_activity_date"]
    if "milestone_next" not in s:
        s["milestone_next"] = 7


def ensure_quiz_structure(stats: dict[str, Any]) -> None:
    """Ensure quiz_stats has spec fields; add quiz block for average_percent."""
    qs = stats.setdefault("quiz_stats", {})
    qs.setdefault("total_attempted", 0)
    qs.setdefault("total_correct", 0)
    qs.setdefault("average_score", 0.0)
    qs.setdefault("last_quiz_date", None)
    qs.setdefault("by_topic", {})
    qs.setdefault("total_score_sum", 0)
    qs.setdefault("total_max_sum", 0)
    qs.setdefault("average_percent", 0)
    qs.setdefault("last_score", None)


def ensure_flashcard_structure(stats: dict[str, Any]) -> None:
    """Ensure flashcard_stats has total_mastered, due_for_review, cards."""
    fc = stats.setdefault("flashcard_stats", {})
    fc.setdefault("total_reviewed", 0)
    fc.setdefault("mastered", 0)
    fc.setdefault("due_for_review", 0)
    fc.setdefault("cards", {})


def update_streak(stats: dict[str, Any]) -> None:
    """
    Update streak based on last_active_date.
    Call when: dashboard load, quiz complete, chat message sent, flashcard reviewed.
    """
    ensure_streak_structure(stats)
    streak = stats["streak"]
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    last = streak.get("last_active_date") or streak.get("last_activity_date")

    if last == today:
        pass  # already counted today
    elif last == yesterday:
        streak["current"] = int(streak.get("current", 0)) + 1
        streak["last_active_date"] = today
    else:
        streak["current"] = 1
        streak["last_active_date"] = today

    current_val = int(streak.get("current", 0))
    longest = int(streak.get("longest", 0))
    if current_val > longest:
        streak["longest"] = current_val

    for milestone in [7, 30, 100]:
        if current_val < milestone:
            streak["milestone_next"] = milestone
            break
    else:
        streak["milestone_next"] = 100


def update_quiz_stats(stats: dict[str, Any], score: float, max_score: float) -> None:
    """
    Update quiz stats after a quiz submission.
    score: raw score (sum of question scores), max_score: total possible (e.g. N * 10).
    """
    ensure_quiz_structure(stats)
    qs = stats["quiz_stats"]
    if max_score <= 0:
        return
    qs["total_attempted"] = int(qs.get("total_attempted", 0)) + 1
    qs["total_score_sum"] = float(qs.get("total_score_sum", 0)) + score
    total_max = float(qs.get("total_max_sum", 0)) + max_score
    qs["total_max_sum"] = total_max
    qs["average_percent"] = round((qs["total_score_sum"] / total_max) * 100) if total_max > 0 else 0
    qs["last_score"] = round((score / max_score) * 100)


def update_flashcard_stats_from_cards(
    stats: dict[str, Any],
    cards: list[dict[str, Any]],
) -> None:
    """
    Recompute total_mastered and due_for_review from card list.
    Due: next_review <= today or missing.
    Mastered: card has next_review > 21 days from now (long interval = retained).
    """
    from datetime import datetime, timezone, timedelta

    ensure_flashcard_structure(stats)
    fc = stats["flashcard_stats"]
    fc.setdefault("cards", {})
    now_d = datetime.now(timezone.utc).date()
    now = now_d.isoformat()
    mastered_threshold = (now_d + timedelta(days=21)).isoformat()

    total_mastered = 0
    due_for_review = 0

    cards_dict = fc.get("cards") or {}
    for c in cards:
        cid = c.get("id") or str(c.get("id", ""))
        if not cid:
            continue
        next_review = c.get("next_review") or ""
        if not next_review or next_review <= now:
            due_for_review += 1
        entry = cards_dict.get(cid, {})
        if entry.get("mastered") or (next_review and next_review > mastered_threshold):
            total_mastered += 1

    fc["mastered"] = total_mastered
    fc["due_for_review"] = due_for_review


def update_flashcard_entry(
    stats: dict[str, Any],
    card_id: str,
    ease: str,
    next_review: str,
    mastered: bool = False,
) -> None:
    """
    Update a single card entry in flashcard_stats.cards.
    ease: "hard" | "medium" | "easy"
    """
    ensure_flashcard_structure(stats)
    fc = stats["flashcard_stats"]
    cards = fc["cards"]
    entry = cards.setdefault(card_id, {
        "ease": "medium",
        "next_review": "",
        "review_count": 0,
        "mastered": False,
    })
    entry["ease"] = ease
    entry["next_review"] = next_review
    entry["review_count"] = int(entry.get("review_count", 0)) + 1
    entry["mastered"] = mastered
