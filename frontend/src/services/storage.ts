/**
 * Dual-layer persistence: localStorage (Layer 1) + API mirror.
 * Offline queue for failed writes; flush when back online.
 */

const STORAGE_FLASHCARDS = "studaxis_flashcards";
const STORAGE_RECENT_DECKS = "studaxis_recent_decks";
const STORAGE_NEEDS_REVIEW = "studaxis_needs_review";
const STORAGE_QUIZ_HISTORY = "studaxis_quiz_history";
const STORAGE_ASSIGNMENTS = "studaxis_assignments";
const STORAGE_SYNC_QUEUE = "studaxis_sync_queue";

export interface SyncQueueItem {
  id: string;
  type: "flashcard_review" | "quiz_result" | "flashcard_create" | "flashcard_append" | "flashcard_replace";
  payload: Record<string, unknown>;
  created_at: string;
  retries: number;
}

function loadJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    return parsed as T;
  } catch {
    return fallback;
  }
}

function saveJson(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // quota exceeded, etc.
  }
}

// ——— Flashcards ———

export interface FlashcardDeck {
  id: string;
  title: string;
  subject: string;
  created_at: string;
  cards: FlashcardDeckCard[];
}

export interface FlashcardDeckCard {
  id: string;
  front?: string;
  back?: string;
  ease?: string;
  next_review?: string;
  review_count?: number;
  mastered?: boolean;
  topic?: string;
  [key: string]: unknown;
}

export function loadFlashcardsFromStorage(): { cards: FlashcardDeckCard[]; decks?: FlashcardDeck[] } {
  const data = loadJson<{ cards?: FlashcardDeckCard[]; decks?: FlashcardDeck[] }>(STORAGE_FLASHCARDS, {});
  if (data.decks?.length) {
    const cards: FlashcardDeckCard[] = [];
    for (const d of data.decks) {
      for (const c of d.cards || []) {
        cards.push({ ...c, topic: c.topic || d.subject || d.title || "General" });
      }
    }
    return { cards, decks: data.decks };
  }
  if (Array.isArray(data.cards)) {
    return { cards: data.cards };
  }
  return { cards: [] };
}

export function saveFlashcardsToStorage(decks: FlashcardDeck[]): void {
  saveJson(STORAGE_FLASHCARDS, { decks });
}

export function saveFlashcardsCardsToStorage(cards: unknown[]): void {
  saveJson(STORAGE_FLASHCARDS, { cards });
}

// ——— Recent Decks (deck-level tracking) ———

export interface RecentDeckEntry {
  id: string;
  title: string;
  subject: string;
  card_count: number;
  easy_count: number;
  hard_count: number;
  created_at: string;
  last_studied: string;
  mastered?: boolean;
  cards: FlashcardDeckCard[];
  /** Source subtitle: 📚 BookName | 💬 "topic..." | ✏️ Manual */
  source?: string;
}

export function loadRecentDecksFromStorage(): RecentDeckEntry[] {
  const data = loadJson<RecentDeckEntry[]>(STORAGE_RECENT_DECKS, []);
  return Array.isArray(data) ? data : [];
}

export function saveRecentDecksToStorage(decks: RecentDeckEntry[]): void {
  saveJson(STORAGE_RECENT_DECKS, decks);
}

export function addOrUpdateRecentDeck(deck: RecentDeckEntry): void {
  const decks = loadRecentDecksFromStorage();
  const now = new Date().toISOString();
  const updated: RecentDeckEntry = {
    ...deck,
    last_studied: now,
  };
  const idx = decks.findIndex((d) => d.id === deck.id);
  if (idx >= 0) {
    decks[idx] = updated;
  } else {
    decks.unshift(updated);
  }
  const trimmed = decks.slice(0, 20);
  saveRecentDecksToStorage(trimmed);
}

// ——— Needs Review (hard cards pool) ———

export interface NeedsReviewEntry {
  deck_id: string;
  card: FlashcardDeckCard;
}

export function loadNeedsReviewFromStorage(): NeedsReviewEntry[] {
  const data = loadJson<NeedsReviewEntry[]>(STORAGE_NEEDS_REVIEW, []);
  return Array.isArray(data) ? data : [];
}

export function saveNeedsReviewToStorage(entries: NeedsReviewEntry[]): void {
  saveJson(STORAGE_NEEDS_REVIEW, entries);
}

// ——— Quiz History ———

export interface QuizResultItem {
  quiz_id: string;
  completed_at: string;
  score: number;
  max_score: number;
  percent: number;
  subject: string;
  question_type?: string;
  answers?: Array<{
    question_id: string;
    user_answer: string;
    correct: boolean;
    score: number;
    feedback?: string;
  }>;
}

export function loadQuizHistoryFromStorage(): QuizResultItem[] {
  const data = loadJson<QuizResultItem[]>(STORAGE_QUIZ_HISTORY, []);
  return Array.isArray(data) ? data : [];
}

export function saveQuizHistoryToStorage(results: QuizResultItem[]): void {
  saveJson(STORAGE_QUIZ_HISTORY, results);
}

export interface AssignmentItem {
  id: string;
  quiz_id: string;
  title: string;
  due_date: string;
  assigned_at: string;
  status: "pending" | "in_progress" | "completed";
}

export function loadAssignmentsFromStorage(): AssignmentItem[] {
  const data = loadJson<AssignmentItem[]>(STORAGE_ASSIGNMENTS, []);
  return Array.isArray(data) ? data : [];
}

export function saveAssignmentsToStorage(items: AssignmentItem[]): void {
  saveJson(STORAGE_ASSIGNMENTS, items);
}

// ——— Offline Sync Queue ———

export function loadSyncQueue(): SyncQueueItem[] {
  const data = loadJson<SyncQueueItem[]>(STORAGE_SYNC_QUEUE, []);
  return Array.isArray(data) ? data : [];
}

export function saveSyncQueue(queue: SyncQueueItem[]): void {
  saveJson(STORAGE_SYNC_QUEUE, queue);
}

export function enqueueSyncItem(item: Omit<SyncQueueItem, "id" | "created_at" | "retries">): void {
  const queue = loadSyncQueue();
  const full: SyncQueueItem = {
    ...item,
    id: `sync_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
    created_at: new Date().toISOString(),
    retries: 0,
  };
  queue.push(full);
  saveSyncQueue(queue);
  window.dispatchEvent(new Event("sync-queue-updated"));
}

export function removeSyncItem(id: string): void {
  const queue = loadSyncQueue().filter((i) => i.id !== id);
  saveSyncQueue(queue);
}

export function incrementSyncRetries(id: string): void {
  const queue = loadSyncQueue().map((i) =>
    i.id === id ? { ...i, retries: i.retries + 1 } : i
  );
  saveSyncQueue(queue);
}
