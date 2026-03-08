"""
Adaptive Recommendation Service — modular, context-aware study recommendations.

Logic:
  IF flashcard_topic exists:
      generate recommendation using flashcard topic (+ quiz data if available)
  ELSE IF quiz_history exists:
      analyze average score, difficulty, weak concepts
      generate recommendation from quiz data
  ELSE:
      return "no_data" — UI shows empty state message

Never generates generic time-based plans (e.g. "Minutes 1-3 review...").
Recommendations are always tied to user data: topics, weak areas, or quiz performance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

def _has_flashcard_topic(subject: Optional[str], hard_cards: Optional[list]) -> bool:
    """True if we have a meaningful flashcard topic to base recommendations on."""
    if not subject or not subject.strip():
        return False
    # "General" without hard cards is not a real topic
    if subject.strip().lower() == "general" and not (hard_cards and len(hard_cards) > 0):
        return False
    return True


def _has_quiz_data(stats: dict[str, Any]) -> bool:
    """True if user has quiz history we can analyze."""
    qs = stats.get("quiz_stats") or {}
    by_topic = qs.get("by_topic") or {}
    total = int(qs.get("total_attempted", 0) or 0)
    return total > 0 or (isinstance(by_topic, dict) and len(by_topic) > 0)


def _get_weak_topics_from_quiz(stats: dict[str, Any]) -> list[tuple[str, float]]:
    """Extract weak topics from quiz_stats.by_topic, sorted by avg_score ascending."""
    qs = stats.get("quiz_stats") or {}
    by_topic = qs.get("by_topic") or {}
    if not isinstance(by_topic, dict):
        return []
    entries = []
    for topic, entry in by_topic.items():
        if isinstance(entry, dict):
            avg = float(entry.get("avg_score", 0) or 0)
        else:
            avg = float(entry) if isinstance(entry, (int, float)) else 0
        entries.append((str(topic), avg))
    entries.sort(key=lambda x: x[1])
    return entries


def _get_quiz_profile(stats: dict[str, Any]) -> dict[str, Any]:
    """Build quiz profile for prompts: avg_score, weak_topics, difficulty_level."""
    qs = stats.get("quiz_stats") or {}
    by_topic = qs.get("by_topic") or {}
    weak = _get_weak_topics_from_quiz(stats)
    avg_pct = int(qs.get("average_percent", 0) or 0)
    if avg_pct == 0 and qs.get("total_score_sum") and qs.get("total_max_sum"):
        total_max = float(qs.get("total_max_sum", 0))
        if total_max > 0:
            avg_pct = round((float(qs.get("total_score_sum", 0)) / total_max) * 100)
    return {
        "avg_score_percent": avg_pct,
        "weak_topics": weak,
        "weak_topics_str": ", ".join(t for t, _ in weak[:5]) if weak else "None identified",
        "total_attempted": int(qs.get("total_attempted", 0) or 0),
        "by_topic": by_topic,
    }


@dataclass
class AdaptiveRecommendation:
    """Structured recommendation output."""
    weak_topic: str
    suggested_action: str
    difficulty_adjustment: str
    text: str  # Human-readable summary for legacy/display


def build_flashcard_based_prompt(
    subject: str,
    difficulty: str,
    hard_cards: list[str],
    easy_count: int,
    hard_count: int,
    quiz_profile: Optional[dict[str, Any]],
) -> str:
    """Build prompt for flashcard-topic–based recommendation. Never generic."""
    hard_list = "\n".join(f"- {f}" for f in (hard_cards or [])[:15]) or "- None"
    prompt = f"""You are an adaptive study coach for a {difficulty} level student studying {subject}.

Their current flashcard deck progress:
- {easy_count} cards mastered, {hard_count} still hard
- Hard cards (concepts to focus on):
{hard_list}
"""
    if quiz_profile and (quiz_profile.get("weak_topics") or quiz_profile.get("avg_score_percent", 0) > 0):
        prompt += f"""
Their quiz performance:
- Average quiz score: {quiz_profile.get('avg_score_percent', 0)}%
- Weak topics from quizzes: {quiz_profile.get('weak_topics_str', 'None')}
"""
    prompt += """
Give a TARGETED study recommendation with exactly these 3 parts, each on its own line:
1. WEAK_TOPIC: <the main topic/concept to focus on, from their hard cards or weak quiz topics>
2. SUGGESTED_ACTION: <one specific action, e.g. "Review flashcards on X and attempt a medium difficulty quiz">
3. DIFFICULTY_ADJUSTMENT: <whether to try easier, medium, or harder material>

Be specific to their data. NEVER use generic time-based plans like "Minutes 1-3 review, 4-6 summarize."
"""
    return prompt


def build_quiz_only_prompt(
    difficulty: str,
    quiz_profile: dict[str, Any],
) -> str:
    """Build prompt when only quiz data exists. Never generic."""
    weak = quiz_profile.get("weak_topics") or []
    weak_str = quiz_profile.get("weak_topics_str", "None identified")
    avg = quiz_profile.get("avg_score_percent", 0)
    prompt = f"""You are an adaptive study coach for a {difficulty} level student.

Their quiz performance:
- Average quiz score: {avg}%
- Weak topics (lowest scores): {weak_str}
"""
    if weak:
        prompt += f"\nWeakest topic to focus on: {weak[0][0]} (avg score {weak[0][1]:.1f}/10)\n"
    prompt += """
Give a TARGETED study recommendation with exactly these 3 parts, each on its own line:
1. WEAK_TOPIC: <the weakest topic from their quiz history>
2. SUGGESTED_ACTION: <one specific action, e.g. "Generate new flashcards for X and attempt a medium difficulty quiz">
3. DIFFICULTY_ADJUSTMENT: <suggest easier quiz if score low, medium, or harder if ready>

Be specific to their quiz data. NEVER use generic time-based plans like "Minutes 1-3 review."
"""
    return prompt


def parse_ai_response(text: str, fallback_weak: str = "Your weakest topic") -> AdaptiveRecommendation:
    """Parse AI response into structured fields. Handles various formats."""
    weak_topic = fallback_weak
    suggested_action = ""
    difficulty_adjustment = ""
    lines = (text or "").strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("weak_topic:"):
            weak_topic = line.split(":", 1)[-1].strip()
        elif lower.startswith("suggested_action:"):
            suggested_action = line.split(":", 1)[-1].strip()
        elif lower.startswith("difficulty_adjustment:"):
            difficulty_adjustment = line.split(":", 1)[-1].strip()
    if not suggested_action:
        suggested_action = f"Review and practice {weak_topic}."
    if not difficulty_adjustment:
        difficulty_adjustment = "Try medium difficulty quizzes."
    summary = text.strip() if text else f"Weak Area: {weak_topic}\nRecommendation: {suggested_action}\nDifficulty: {difficulty_adjustment}"
    return AdaptiveRecommendation(
        weak_topic=weak_topic,
        suggested_action=suggested_action,
        difficulty_adjustment=difficulty_adjustment,
        text=summary,
    )
