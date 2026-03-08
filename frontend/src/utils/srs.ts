/**
 * Spaced Repetition (SRS) logic — mirrors backend flashcards_system/spaced_repetition.py.
 * Quality: 1–5 (1=again, 2=hard, 3=medium, 4=good, 5=easy).
 */

import type { FlashcardItem } from "../services/api";

export function applySrsRating(
  card: FlashcardItem,
  quality: number
): FlashcardItem {
  const c = { ...card };
  const repetitions = c.repetitions ?? 0;
  let interval = c.interval ?? 1;
  let ease_factor = c.ease_factor ?? 2.5;

  if (quality < 3) {
    c.repetitions = 0;
    c.interval = 1;
  } else {
    c.repetitions = repetitions + 1;
    if (c.repetitions === 1) {
      c.interval = 1;
    } else if (c.repetitions === 2) {
      c.interval = 6;
    } else {
      c.interval = Math.round(interval * ease_factor);
    }
    ease_factor += 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02);
    c.ease_factor = Math.max(1.3, ease_factor);
  }

  const d = new Date();
  d.setDate(d.getDate() + (c.interval ?? 1));
  c.next_review = d.toISOString();
  return c;
}
