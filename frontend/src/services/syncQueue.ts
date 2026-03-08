/**
 * Offline sync queue: flush pending operations when back online.
 */

import {
  loadSyncQueue,
  saveSyncQueue,
  removeSyncItem,
  incrementSyncRetries,
  type SyncQueueItem,
} from "./storage";
import { postFlashcards, putFlashcards, postQuizSubmit, type QuizItem } from "./api";

const MAX_RETRIES = 3;

export async function flushSyncQueue(): Promise<void> {
  const queue = loadSyncQueue();
  if (queue.length === 0) return;

  const remaining: SyncQueueItem[] = [];
  for (const item of queue) {
    if (item.retries >= MAX_RETRIES) {
      continue;
    }
    try {
      const ok = await processSyncItem(item);
      if (ok) {
        removeSyncItem(item.id);
      } else {
        incrementSyncRetries(item.id);
        remaining.push({ ...item, retries: item.retries + 1 });
      }
    } catch {
      incrementSyncRetries(item.id);
      remaining.push({ ...item, retries: item.retries + 1 });
    }
  }
  saveSyncQueue(remaining);
}

async function processSyncItem(item: SyncQueueItem): Promise<boolean> {
  switch (item.type) {
    case "flashcard_append": {
      const { cards } = item.payload as { cards: unknown[] };
      if (!Array.isArray(cards) || cards.length === 0) return true;
      const res = await postFlashcards(cards as Parameters<typeof postFlashcards>[0]);
      return res?.appended !== undefined;
    }
    case "flashcard_replace": {
      const { cards } = item.payload as { cards: unknown[] };
      if (!Array.isArray(cards)) return true;
      await putFlashcards(cards as Parameters<typeof putFlashcards>[0]);
      return true;
    }
    case "quiz_result": {
      const { quizId, answers, items } = item.payload as {
        quizId: string;
        answers: Array<{ question_id: string; answer?: string; user_answer?: string }>;
        items?: QuizItem[];
      };
      if (!quizId || !Array.isArray(answers)) return true;
      await postQuizSubmit(quizId, {
        answers: answers.map((a) => ({ question_id: a.question_id, answer: a.answer ?? a.user_answer ?? "" })),
        ...(items?.length ? { items } : {}),
      });
      return true;
    }
    case "flashcard_review":
      // Backend handles; queued from backend's _enqueue_sync
      return true;
    default:
      return false;
  }
}
