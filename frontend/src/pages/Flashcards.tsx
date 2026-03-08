import { useState, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import {
  explainFlashcard,
  generateFlashcards,
  getFlashcardRecommendation,
  getFlashcardsDue,
  getFlashcards,
  postFlashcards,
  postFlashcardDeck,
  putFlashcards,
  patchFlashcardReview,
  getUserStats,
  updateUserStats,
  type AdaptiveRecommendationResponse,
} from "../services/api";
import {
  loadFlashcardsFromStorage,
  saveFlashcardsCardsToStorage,
  enqueueSyncItem,
  loadRecentDecksFromStorage,
  addOrUpdateRecentDeck,
  loadNeedsReviewFromStorage,
  saveNeedsReviewToStorage,
  type RecentDeckEntry,
  type FlashcardDeckCard,
} from "../services/storage";
import { flushSyncQueue } from "../services/syncQueue";
import { applySrsRating } from "../utils/srs";
import type { FlashcardItem, DashboardFlashcardItem } from "../services/api";
import { useFlashcardDeck } from "../contexts/FlashcardDeckContext";
import { useNotification } from "../contexts/NotificationContext";
import { GlassCard, LoadingSpinner, HardwareStatus, PageChrome, AerogelDashboardCard, EmptyState } from "../components";
import { MarkdownWithMath } from "../components/MarkdownWithMath";
import { FlashcardSourceSelector } from "../components/FlashcardSourceSelector";

const SUBJECT_COLORS: Record<string, string> = {
  Physics: "#3b82f6",
  Mathematics: "#8b5cf6",
  Biology: "#22c55e",
  Chemistry: "#f59e0b",
  General: "#64748b",
};

function RecentDecksList({
  onSelectDeck,
}: {
  onSelectDeck: (entry: RecentDeckEntry) => void;
}) {
  const [decks, setDecks] = useState<RecentDeckEntry[]>([]);
  useEffect(() => {
    setDecks(loadRecentDecksFromStorage());
  }, []);
  if (decks.length === 0) {
    return (
      <EmptyState
        title="No flashcards yet"
        description="Generate a quiz to unlock your first flashcards."
        icon="🎴"
      />
    );
  }
  return (
    <div className="flex flex-col gap-3">
      {decks.slice(0, 8).map((entry) => {
        const color = SUBJECT_COLORS[entry.subject] ?? SUBJECT_COLORS.General;
        const easyCount = entry.easy_count ?? 0;
        const total = entry.card_count ?? 0;
        const toReview = total - easyCount;
        const allMastered = total > 0 && easyCount >= total;
        const pct = total > 0 ? Math.round((easyCount / total) * 100) : 0;
        return (
          <div
            key={entry.id}
            className="flex items-center gap-4 p-4 rounded-xl border border-glass-border bg-surface-light/50 hover:bg-surface-light"
          >
            <span
              className="text-xs font-medium px-2 py-1 rounded-md"
              style={{ background: `${color}20`, color }}
            >
              {entry.subject}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-primary truncate">
                {entry.title}
              </p>
              {entry.source && (
                <p className="text-xs text-primary/60 truncate mt-0.5">
                  {entry.source}
                </p>
              )}
              <div className="flex items-center gap-2 mt-1">
                {allMastered ? (
                  <span className="text-xs font-medium" style={{ color: "#10b981" }}>
                    ✅ Complete
                  </span>
                ) : (
                  <>
                    <div className="flex-1 h-1.5 rounded-full bg-primary/10 overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{ width: `${pct}%`, background: "#10b981" }}
                      />
                    </div>
                    <span className="text-xs text-primary/70 whitespace-nowrap">
                      {easyCount} mastered · {toReview} to review
                    </span>
                  </>
                )}
              </div>
            </div>
            <button
              type="button"
              onClick={() => onSelectDeck(entry)}
              className="px-4 py-2 rounded-xl font-medium text-deep bg-accent-blue hover:bg-accent-blue/90 text-sm"
            >
              Continue
            </button>
          </div>
        );
      })}
    </div>
  );
}

/** Deck complete summary: Easy (left) and Hard (right) columns with chips and actions */
function DeckCompleteSummary({
  easyCards,
  hardCards,
  onSaveAndGoBack,
  onStudyHardAgain,
  onReviewEasy,
}: {
  easyCards: FlashcardItem[];
  hardCards: FlashcardItem[];
  onSaveAndGoBack: () => void;
  onStudyHardAgain: () => void;
  onReviewEasy: (card: FlashcardItem) => void;
}) {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-primary text-center">Deck Complete 🎉</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="rounded-xl border-2 overflow-hidden" style={{ borderColor: "rgba(16, 185, 129, 0.4)" }}>
          <div
            className="px-4 py-2 text-sm font-semibold"
            style={{ background: "#10b981", color: "white" }}
          >
            ✅ Easy ({easyCards.length})
          </div>
          <div className="p-4 bg-surface-light/50 min-h-[120px]">
            {easyCards.length === 0 ? (
              <p className="text-sm text-primary/60">No cards marked easy</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {easyCards.map((c) => (
                  <div key={c.id} className="flex items-center gap-2">
                    <span
                      className="inline-block px-3 py-1 rounded-lg text-sm bg-white/80 border border-glass-border text-primary truncate max-w-[200px]"
                      title={c.front ?? c.question ?? ""}
                    >
                      {(c.front ?? c.question ?? "").slice(0, 40)}{(c.front ?? c.question ?? "").length > 40 ? "…" : ""}
                    </span>
                    <button
                      type="button"
                      onClick={() => onReviewEasy(c)}
                      className="text-xs font-medium text-accent-blue hover:underline"
                    >
                      Review anyway
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="rounded-xl border-2 overflow-hidden" style={{ borderColor: "rgba(239, 68, 68, 0.4)" }}>
          <div
            className="px-4 py-2 text-sm font-semibold"
            style={{ background: "#ef4444", color: "white" }}
          >
            🔁 Hard ({hardCards.length})
          </div>
          <div className="p-4 bg-surface-light/50 min-h-[120px]">
            {hardCards.length === 0 ? (
              <p className="text-sm text-primary/60">No cards marked hard</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {hardCards.map((c) => (
                  <span
                    key={c.id}
                    className="inline-block px-3 py-1 rounded-lg text-sm bg-white/80 border border-glass-border text-primary truncate max-w-[220px]"
                    title={c.front ?? c.question ?? ""}
                  >
                    {(c.front ?? c.question ?? "").slice(0, 40)}{(c.front ?? c.question ?? "").length > 40 ? "…" : ""}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="flex flex-wrap gap-3 justify-center">
        <button
          type="button"
          onClick={onSaveAndGoBack}
          className="px-5 py-2.5 rounded-xl font-medium text-deep bg-accent-blue hover:bg-accent-blue/90"
        >
          Save and Go Back
        </button>
        {hardCards.length > 0 && (
          <button
            type="button"
            onClick={onStudyHardAgain}
            className="px-5 py-2.5 rounded-xl font-medium border border-red-400 text-red-600 hover:bg-red-50"
          >
            Study Hard Cards Again
          </button>
        )}
      </div>
    </div>
  );
}

/** Display structured adaptive recommendation (Weak Topic, Action, Difficulty) */
function AdaptiveRecommendationDisplay({
  data,
  onDismiss,
}: {
  data: AdaptiveRecommendationResponse;
  onDismiss: () => void;
}) {
  if (!data.has_data) {
    return (
      <div className="rounded-lg p-4 border border-amber-200/60 bg-amber-50/50">
        <p className="text-sm text-primary/90">{data.text}</p>
      </div>
    );
  }
  return (
    <div className="rounded-lg p-4 border-t border-glass-border relative pl-4 pt-4">
      <div
        aria-hidden
        className="absolute left-0 top-0 bottom-0 w-1 rounded-sm"
        style={{
          background: "linear-gradient(to bottom, #FA5C5C, #FD8A6B)",
        }}
      />
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold text-primary">Recommendation</span>
        <button
          type="button"
          onClick={onDismiss}
          className="text-sm text-primary/70 hover:text-primary"
        >
          Dismiss
        </button>
      </div>
      <dl className="space-y-2 text-sm">
        {data.weak_topic && (
          <div>
            <dt className="font-medium text-primary/80">Weak Area</dt>
            <dd className="text-primary/90">{data.weak_topic}</dd>
          </div>
        )}
        {data.suggested_action && (
          <div>
            <dt className="font-medium text-primary/80">Suggested Action</dt>
            <dd className="text-primary/90">{data.suggested_action}</dd>
          </div>
        )}
        {data.difficulty_adjustment && (
          <div>
            <dt className="font-medium text-primary/80">Difficulty Adjustment</dt>
            <dd className="text-primary/90">{data.difficulty_adjustment}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}

function createRecentDeckFromCards(
  cards: FlashcardItem[],
  topic: string,
  opts?: { sourceType?: string[]; sourceTextbook?: string; sourceTopic?: string }
): RecentDeckEntry {
  const now = new Date().toISOString();
  const deckId = `deck_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  let source: string;
  if (opts?.sourceTextbook) source = `📚 ${opts.sourceTextbook}`;
  else if (opts?.sourceTopic?.trim()) source = `💬 "${opts.sourceTopic.slice(0, 40)}..."`;
  else {
    const st = opts?.sourceType ?? cards[0]?.sourceType;
    const arr = Array.isArray(st) ? st : st ? [st] : [];
    if (arr.some((s) => String(s).toLowerCase() === "textbook")) source = "📚 Textbook";
    else if (arr.some((s) => String(s).toLowerCase() === "weblink")) source = "🌐 Web link";
    else if (arr.some((s) => String(s).toLowerCase() === "file")) source = "📄 Files";
    else if (arr.some((s) => String(s).toLowerCase() === "paste")) source = "✏️ Pasted text";
    else if (topic && topic !== "General") source = `💬 "${topic.slice(0, 40)}..."`;
    else source = "✏️ Manual";
  }
  return {
    id: deckId,
    title: topic,
    subject: topic,
    source,
    card_count: cards.length,
    easy_count: 0,
    hard_count: 0,
    created_at: now,
    last_studied: now,
    mastered: false,
    cards: cards.map((c) => ({
      ...c,
      id: c.id,
      front: c.front ?? c.question ?? "",
      back: c.back ?? c.answer ?? "",
      topic: c.topic ?? topic,
      ease: (c as { ease?: string }).ease ?? "medium",
    })),
  };
}

/** Enrich generated cards for storage (next_review, question, answer, interval, sourceType, etc.). */
function enrichForStorage(
  cards: FlashcardItem[],
  topic: string,
  sourceType?: string[]
): FlashcardItem[] {
  const now = new Date().toISOString();
  return cards.map((c) => ({
    ...c,
    topic: c.topic || topic,
    question: c.front,
    answer: c.back,
    next_review: now,
    interval: 1,
    repetitions: 0,
    ease_factor: 2.5,
    sourceType: sourceType ?? c.sourceType ?? ["textbook"],
  }));
}

/** Map FlashcardItem to DashboardFlashcardItem for Aerogel (conceptTitle=topic, content=back, sourceType). */
function mapToDashboardCards(deck: FlashcardItem[]): DashboardFlashcardItem[] {
  return deck.map((c) => ({
    id: c.id,
    conceptTitle: c.topic ?? "General",
    content: c.back ?? c.answer ?? "",
    sourceType: c.sourceType,
  }));
}

/** Merge session deck into full storage and PUT (for sync on exit/clear). */
async function syncSessionToBackend(deck: FlashcardItem[]): Promise<void> {
  if (deck.length === 0) return;
  try {
    const { cards: allCards } = await getFlashcards();
    const deckById = new Map(deck.map((c) => [c.id, c]));
    const merged = allCards.map((c) => deckById.get(c.id) ?? c);
    for (const d of deck) {
      if (!merged.some((m) => m.id === d.id)) merged.push(d);
    }
    await putFlashcards(merged);
    saveFlashcardsCardsToStorage(merged as Parameters<typeof saveFlashcardsCardsToStorage>[0]);
  } catch {
    saveFlashcardsCardsToStorage(deck);
    enqueueSyncItem({ type: "flashcard_replace", payload: { cards: deck } });
  }
}

/** Infer source string from deck/cards for recents display. */
function inferDeckSource(
  cards: FlashcardItem[],
  currentDeckRef: React.MutableRefObject<RecentDeckEntry | null>,
  currentTopic?: string,
  currentSubject?: string
): string {
  const existing = currentDeckRef.current?.source;
  if (existing) return existing;
  const st = cards[0]?.sourceType;
  const arr = Array.isArray(st) ? st : st ? [st] : [];
  if (arr.some((s) => String(s).toLowerCase() === "textbook")) return "📚 Textbook";
  if (arr.some((s) => String(s).toLowerCase() === "weblink")) return "🌐 Web link";
  if (arr.some((s) => String(s).toLowerCase() === "file")) return "📄 Files";
  if (arr.some((s) => String(s).toLowerCase() === "paste")) return "✏️ Pasted text";
  const topic = currentTopic ?? currentSubject ?? cards[0]?.topic;
  if (topic && topic !== "General") return `💬 "${String(topic).slice(0, 40)}..."`;
  return "✏️ Manual";
}

export function FlashcardsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const topicFromChat = searchParams.get("topic");
  const topicFetchedRef = useRef(false);
  const { push } = useNotification();

  const {
    deck,
    cardIndex,
    showAnswer: _showAnswer,
    setShowAnswer,
    lastExplanation,
    lastRecommendation: _lastRecommendation,
    setDeck,
    setCardIndex,
    setLastExplanation,
    setLastRecommendation,
    clearDeck,
    advanceToNext,
  } = useFlashcardDeck();

  const deckRef = useRef(deck);
  deckRef.current = deck;
  const currentDeckRef = useRef<RecentDeckEntry | null>(null);
  const [reviewedCardIds, setReviewedCardIds] = useState<Set<string>>(new Set());

  const handleClearDeck = async () => {
    // Clear topic from URL first to prevent auto-regeneration when deck is cleared
    setSearchParams({});
    const cards = deck;
    if (cards.length === 0) {
      clearDeck();
      return;
    }
    const currentTopic = currentDeckRef.current?.title ?? cards[0]?.topic;
    const currentSubject = currentDeckRef.current?.subject ?? cards[0]?.topic ?? "General";
    const source = inferDeckSource(
      cards,
      currentDeckRef,
      currentTopic,
      currentSubject
    );
    const currentDeck: RecentDeckEntry = {
      id: Date.now().toString(),
      title: currentTopic ?? currentSubject ?? "Flashcard Deck",
      subject: currentSubject ?? "General",
      source,
      card_count: cards.length,
      easy_count: cards.filter((c) => (c as { ease?: string }).ease === "easy").length,
      hard_count: cards.filter((c) => (c as { ease?: string }).ease === "hard").length,
      cards: cards as FlashcardDeckCard[],
      created_at: new Date().toISOString(),
      last_studied: new Date().toISOString(),
    };
    const existing = JSON.parse(localStorage.getItem("studaxis_recent_decks") ?? "[]");
    localStorage.setItem(
      "studaxis_recent_decks",
      JSON.stringify([currentDeck, ...existing].slice(0, 20))
    );
    try {
      await postFlashcardDeck({
        ...currentDeck,
        cards: cards.map((c) => ({
          ...c,
          front: c.front ?? c.question ?? "",
          back: c.back ?? c.answer ?? "",
        })),
      });
    } catch {
      /* non-blocking */
    }
    push({
      type: "success",
      title: "Deck saved!",
      message: `${cards.length} cards saved to recents`,
    });
    currentDeckRef.current = null;
    setRecommendationData(null);
    await syncSessionToBackend(cards);
    clearDeck();
  };

  useEffect(() => {
    return () => {
      if (deckRef.current.length > 0) syncSessionToBackend(deckRef.current);
    };
  }, []);

  const [count, setCount] = useState(10);
  const [generateLoading, setGenerateLoading] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [topicFromUrl, setTopicFromUrl] = useState(topicFromChat ?? "");
  const [explainLoading, setExplainLoading] = useState(false);
  const [recommendLoading, setRecommendLoading] = useState(false);
  const [recommendationData, setRecommendationData] =
    useState<AdaptiveRecommendationResponse | null>(null);
  const [dueCount, setDueCount] = useState<number>(() => {
    const { cards } = loadFlashcardsFromStorage();
    const now = new Date().toISOString();
    return (cards ?? []).filter((c) => {
      const nr = c.next_review ?? "";
      return !nr || nr <= now;
    }).length;
  });
  const [loadingReview, setLoadingReview] = useState(false);

  useEffect(() => {
    const onOnline = () => flushSyncQueue();
    window.addEventListener("online", onOnline);
    return () => window.removeEventListener("online", onOnline);
  }, []);

  useEffect(() => {
    if (deck.length > 0) return;
    getFlashcardsDue()
      .then((r) => {
        setDueCount(r.cards.length);
        if (r.cards?.length) {
          const { cards } = loadFlashcardsFromStorage();
          const merged = [...(cards ?? [])];
          const byId = new Map<string, unknown>();
          for (const c of merged) byId.set(c.id, c);
          for (const c of r.cards) byId.set(c.id, c);
          saveFlashcardsCardsToStorage(Array.from(byId.values()));
        }
      })
      .catch(() => {
        const { cards } = loadFlashcardsFromStorage();
        const now = new Date().toISOString();
        setDueCount((cards ?? []).filter((c) => !(c.next_review ?? "") || (c.next_review ?? "") <= now).length);
      });
  }, [deck.length]);

  // When redirected from chat with topic: close any open deck so new generation can run
  useEffect(() => {
    const topic = searchParams.get("topic")?.trim();
    if (!topic) return;
    if (deck.length > 0 || topicFetchedRef.current) {
      clearDeck();
      setRecommendationData(null);
      topicFetchedRef.current = false;
    }
  }, [searchParams, deck.length, clearDeck]);

  // Auto-generate from topic when coming from AI Chat (/?topic=X)
  useEffect(() => {
    const topic = searchParams.get("topic")?.trim();
    if (!topic || deck.length > 0 || topicFetchedRef.current) return;
    topicFetchedRef.current = true;
    setTopicFromUrl(topic);
    setGenerateError(null);
    setGenerateLoading(true);
    generateFlashcards({
      topic_or_chapter: topic,
      input_type: "Topic Name",
      count,
    })
      .then((res) => {
        const topicName = res.topic ?? topic;
        const enriched = enrichForStorage(res.cards, topicName, ["topic"]);
        const recentEntry = createRecentDeckFromCards(enriched, topicName, {
          sourceType: ["topic"],
          sourceTopic: topic,
        });
        return postFlashcards(enriched, {
          deck_id: recentEntry.id,
          deck_title: recentEntry.title,
          deck_subject: recentEntry.subject,
        })
          .then(() => {
            getFlashcards().then((r) => r.cards && saveFlashcardsCardsToStorage(r.cards));
            return { enriched, recentEntry };
          })
          .catch((e) => {
            saveFlashcardsCardsToStorage([...(loadFlashcardsFromStorage().cards ?? []), ...enriched]);
            enqueueSyncItem({ type: "flashcard_append", payload: { cards: enriched } });
            throw e;
          });
      })
      .then(({ enriched, recentEntry }) => {
        addOrUpdateRecentDeck(recentEntry);
        currentDeckRef.current = recentEntry;
        setReviewedCardIds(new Set());
        setDeck(enriched);
        setCardIndex(0);
        setShowAnswer(false);
        setLastExplanation("");
        setLastRecommendation("");
        setRecommendationData(null);
        setSearchParams({}); // clear topic from URL
      })
      .catch((e) => {
        setGenerateError(e instanceof Error ? e.message : "Generation failed.");
        topicFetchedRef.current = false;
      })
      .finally(() => setGenerateLoading(false));
  }, [searchParams, deck.length, count, setDeck, setCardIndex, setShowAnswer, setLastExplanation, setLastRecommendation, setSearchParams]);

  const n = deck.length;
  const idx = n > 0 ? cardIndex % n : 0;
  const card: FlashcardItem | null = n > 0 ? deck[idx]! : null;

  const handleGenerateFromSelector = async (
    cards: FlashcardItem[],
    sourceType: string[]
  ) => {
    setGenerateError(null);
    setGenerateLoading(true);
    const topic = cards[0]?.topic ?? "General";
    const enriched = enrichForStorage(cards, topic, sourceType);
    const recentEntry = createRecentDeckFromCards(enriched, topic, { sourceType });
    try {
      await postFlashcards(enriched, {
        deck_id: recentEntry.id,
        deck_title: recentEntry.title,
        deck_subject: recentEntry.subject,
      });
      const { cards: all } = await getFlashcards();
      if (all?.length) saveFlashcardsCardsToStorage(all);
      addOrUpdateRecentDeck(recentEntry);
      currentDeckRef.current = recentEntry;
      setReviewedCardIds(new Set());
      setDeck(enriched);
      setCardIndex(0);
      setShowAnswer(false);
      setLastExplanation("");
      setLastRecommendation("");
      setRecommendationData(null);
    } catch (e) {
      saveFlashcardsCardsToStorage(enriched);
      enqueueSyncItem({ type: "flashcard_append", payload: { cards: enriched } });
      const recentEntry = createRecentDeckFromCards(enriched, topic);
      addOrUpdateRecentDeck(recentEntry);
      setGenerateError(e instanceof Error ? e.message : "Failed to save deck.");
    } finally {
      setGenerateLoading(false);
    }
  };

  const loadDueCards = async () => {
    setLoadingReview(true);
    try {
      let cards: FlashcardItem[] = [];
      try {
        const res = await getFlashcardsDue();
        cards = res.cards ?? [];
      } catch {
        const { cards: cached } = loadFlashcardsFromStorage();
        const now = new Date().toISOString();
        const due = (cached ?? []).filter((c) => !(c.next_review ?? "") || (c.next_review ?? "") <= now);
        cards = due.map((c) => ({
          ...c,
          id: c.id,
          topic: c.topic ?? "General",
          front: c.front ?? (c as FlashcardItem).question ?? "",
          back: c.back ?? (c as FlashcardItem).answer ?? "",
        })) as FlashcardItem[];
      }
      if (cards.length > 0) {
        currentDeckRef.current = null;
        setReviewedCardIds(new Set());
        setDeck(cards);
        setCardIndex(0);
        setShowAnswer(false);
        setLastExplanation("");
        setLastRecommendation("");
        setRecommendationData(null);
      }
    } finally {
      setLoadingReview(false);
    }
  };

  const [userDifficulty, setUserDifficulty] = useState(() => {
    const cached = localStorage.getItem("studaxis_user_difficulty");
    return cached ?? "Beginner";
  });
  useEffect(() => {
    getUserStats()
      .then((s) => {
        const d = s?.preferences?.difficulty_level ?? "Beginner";
        setUserDifficulty(d);
        localStorage.setItem("studaxis_user_difficulty", d);
      })
      .catch(() => {});
  }, []);

  const handleExplain = async () => {
    if (!card) return;
    setExplainLoading(true);
    try {
      const subject = deck[0]?.topic ?? card.topic ?? "General";
      const res = await explainFlashcard({
        front: card.front ?? card.question ?? "",
        back: card.back ?? card.answer ?? "",
        subject,
        difficulty: userDifficulty,
      });
      setLastExplanation(res.text);
    } catch (e) {
      setLastExplanation(
        e instanceof Error ? e.message : "Could not get explanation."
      );
    } finally {
      setExplainLoading(false);
    }
  };

  useEffect(() => {
    setLastExplanation("");
  }, [cardIndex, setLastExplanation]);

  const handleRecommendation = async () => {
    setRecommendLoading(true);
    setRecommendationData(null);
    setLastRecommendation("");
    try {
      const deckEntry = currentDeckRef.current;
      const hasDeck = deck.length > 0;
      const subject = hasDeck
        ? (deck[0]?.topic ?? card?.topic ?? "General")
        : "";
      const deckId = deckEntry?.id ?? (hasDeck ? `deck_${Date.now()}` : "");
      const hardCards = hasDeck
        ? deck
            .filter((c) => (c as { ease?: string }).ease?.toLowerCase() === "hard")
            .map((c) => c.front ?? (c as { question?: string }).question ?? "")
        : [];
      const easyCount = deckEntry?.easy_count ?? (hasDeck ? deck.filter((c) => (c as { ease?: string }).ease?.toLowerCase() === "easy").length : 0);
      const hardCount = deckEntry?.hard_count ?? hardCards.length;
      const res = await getFlashcardRecommendation({
        deck_id: deckId,
        subject,
        hard_cards: hardCards,
        easy_count: easyCount,
        hard_count: hardCount,
        difficulty: userDifficulty,
      });
      setRecommendationData(res);
      setLastRecommendation(res.text);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Could not get recommendation.";
      setRecommendationData({
        weak_topic: "",
        suggested_action: "",
        difficulty_adjustment: "",
        text: msg,
        confidence_score: 0,
        has_data: false,
      });
      setLastRecommendation(msg);
    } finally {
      setRecommendLoading(false);
    }
  };

  const handleEasy = async () => {
    if (!card) return;
    setReviewedCardIds((prev) => new Set([...prev, card.id]));
    const updated = applySrsRating(card, 4); // quality 4 = easy
    const nextDeck = deck.map((c) => (c.id === card.id ? { ...updated, ease: "easy" } : c));
    const deckEntry = currentDeckRef.current;
    const nextReview = (updated as { next_review?: string }).next_review ?? new Date().toISOString().slice(0, 10);
    if (deckEntry) {
      const updatedCards = deckEntry.cards.map((c) =>
        c.id === card.id ? { ...c, ease: "easy", next_review: nextReview } : c
      );
      const newEasy = updatedCards.filter((c) => (c.ease || "").toLowerCase() === "easy").length;
      const updatedEntry: RecentDeckEntry = {
        ...deckEntry,
        easy_count: newEasy,
        mastered: newEasy === deckEntry.card_count,
        cards: updatedCards,
      };
      addOrUpdateRecentDeck(updatedEntry);
      currentDeckRef.current = updatedEntry;
      try {
        await patchFlashcardReview({
          deck_id: deckEntry.id,
          card_id: card.id,
          ease: "easy",
          next_review: nextReview,
        });
      } catch {
        saveFlashcardsCardsToStorage(nextDeck);
        enqueueSyncItem({ type: "flashcard_replace", payload: { cards: nextDeck } });
      }
    } else {
      try {
        const stats = await getUserStats();
        const prev = stats?.flashcard_stats ?? {};
        await updateUserStats({
          flashcard_stats: {
            total_reviewed: (prev.total_reviewed ?? 0) + 1,
            mastered: (prev.mastered ?? 0) + 1,
            due_for_review: prev.due_for_review ?? 0,
          },
        });
      } catch {
        /* non-blocking */
      }
      try {
        const { cards: allCards } = await getFlashcards();
        const merged = allCards.map((c) => (c.id === card.id ? updated : c));
        await putFlashcards(merged);
        saveFlashcardsCardsToStorage(merged);
      } catch {
        saveFlashcardsCardsToStorage(nextDeck);
        enqueueSyncItem({ type: "flashcard_replace", payload: { cards: nextDeck } });
      }
    }
    setDeck(nextDeck);
    advanceToNext();
  };

  const handleHard = async () => {
    if (!card) return;
    setReviewedCardIds((prev) => new Set([...prev, card.id]));
    const updated = applySrsRating(card, 2); // quality 2 = hard
    const nextDeck = deck.map((c) => (c.id === card.id ? { ...updated, ease: "hard" } : c));
    const deckEntry = currentDeckRef.current;
    const nextReview = (updated as { next_review?: string }).next_review ?? new Date().toISOString().slice(0, 10);
    if (deckEntry) {
      const hardCards = loadNeedsReviewFromStorage();
      hardCards.unshift({ deck_id: deckEntry.id, card: { ...card, id: card.id, front: card.front ?? card.question, back: card.back ?? card.answer, ease: "hard", next_review: nextReview } });
      saveNeedsReviewToStorage(hardCards.slice(0, 100));
      const updatedCards = deckEntry.cards.map((c) =>
        c.id === card.id ? { ...c, ease: "hard", next_review: nextReview } : c
      );
      const newHard = updatedCards.filter((c) => (c.ease || "").toLowerCase() === "hard").length;
      const updatedEntry: RecentDeckEntry = {
        ...deckEntry,
        hard_count: newHard,
        cards: updatedCards,
      };
      addOrUpdateRecentDeck(updatedEntry);
      currentDeckRef.current = updatedEntry;
      try {
        await patchFlashcardReview({
          deck_id: deckEntry.id,
          card_id: card.id,
          ease: "hard",
          next_review: nextReview,
        });
      } catch {
        saveFlashcardsCardsToStorage(nextDeck);
        enqueueSyncItem({ type: "flashcard_replace", payload: { cards: nextDeck } });
      }
    } else {
      try {
        const stats = await getUserStats();
        const prev = stats?.flashcard_stats ?? {};
        await updateUserStats({
          flashcard_stats: {
            total_reviewed: (prev.total_reviewed ?? 0) + 1,
            mastered: prev.mastered ?? 0,
            due_for_review: (prev.due_for_review ?? 0) + 1,
          },
        });
      } catch {
        /* non-blocking */
      }
      try {
        const { cards: allCards } = await getFlashcards();
        const merged = allCards.map((c) => (c.id === card.id ? updated : c));
        await putFlashcards(merged);
        saveFlashcardsCardsToStorage(merged);
      } catch {
        saveFlashcardsCardsToStorage(nextDeck);
        enqueueSyncItem({ type: "flashcard_replace", payload: { cards: nextDeck } });
      }
    }
    setDeck(nextDeck);
    advanceToNext();
  };

  if (deck.length === 0) {
    return (
      <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
        <div className="space-y-6">
          <h2 className="text-2xl font-semibold text-primary">Flashcards</h2>
          <p className="text-primary/80">
            Generate decks with local AI and review with explanations and
            recommendations.
          </p>

          {topicFromUrl && generateLoading && (
            <GlassCard title="Creating your deck">
              <div className="flex flex-col items-center gap-4 py-6">
                <LoadingSpinner message={`Generating flashcards for: ${topicFromUrl}`} />
                <p className="text-sm text-primary/70 text-center">
                  Cards are being generated from your topic. This may take a moment.
                </p>
              </div>
            </GlassCard>
          )}

          {dueCount > 0 && !generateLoading && (
            <GlassCard title="Review due cards">
              <p className="text-sm text-primary/70 mb-4">
                You have {dueCount} card{dueCount !== 1 ? "s" : ""} due for review.
              </p>
              <LoadingSpinner loading={loadingReview} message="Loading due cards...">
                <button
                  type="button"
                  onClick={loadDueCards}
                  disabled={loadingReview}
                  className="px-5 py-2.5 rounded-xl font-medium text-deep bg-accent-blue hover:bg-accent-blue/90 focus:outline-none focus:ring-2 focus:ring-accent-blue"
                >
                  Review {dueCount} due card{dueCount !== 1 ? "s" : ""}
                </button>
              </LoadingSpinner>
            </GlassCard>
          )}

          {(!topicFromUrl || !generateLoading) && (
          <GlassCard title="Create your deck">
            <p className="text-sm text-primary/70 mb-4">
              Choose a source (Textbook, Web link, or Files) and generate flashcards with local AI.
            </p>
            <FlashcardSourceSelector
              count={count}
              onCountChange={setCount}
              onGenerate={handleGenerateFromSelector}
              loading={generateLoading}
              error={generateError}
              onError={setGenerateError}
            />
          </GlassCard>
          )}

          {/* Recent decks — from studaxis_recent_decks */}
          <GlassCard title="Recent decks">
            <p className="text-sm text-primary/70 mb-4">
              Continue studying your recent decks. Progress is saved per deck.
            </p>
            <RecentDecksList
              onSelectDeck={(entry) => {
                currentDeckRef.current = entry;
                addOrUpdateRecentDeck(entry);
                setReviewedCardIds(new Set());
                setDeck(
                  entry.cards.map((c) => ({
                    ...c,
                    id: c.id,
                    topic: c.topic ?? entry.subject,
                    front: c.front ?? (c as { question?: string }).question ?? "",
                    back: c.back ?? (c as { answer?: string }).answer ?? "",
                  })) as FlashcardItem[]
                );
                setCardIndex(0);
                setShowAnswer(false);
                setLastExplanation("");
                setLastRecommendation("");
                setRecommendationData(null);
              }}
            />
          </GlassCard>

          {/* Adaptive Recommendation — shown even without deck (uses quiz data) */}
          <GlassCard title="📊 Adaptive Recommendation">
            <p className="text-sm text-primary/70 mb-4">
              Get personalized study suggestions based on your flashcards or quiz performance.
            </p>
            {recommendLoading ? (
              <LoadingSpinner message="Analyzing your progress..." className="flex-shrink-0" />
            ) : recommendationData ? (
              <AdaptiveRecommendationDisplay
                data={recommendationData}
                onDismiss={() => {
                  setRecommendationData(null);
                  setLastRecommendation("");
                }}
              />
            ) : (
              <button
                type="button"
                onClick={handleRecommendation}
                className="px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary hover:bg-surface-light/80 text-sm font-medium"
              >
                Get study recommendation
              </button>
            )}
          </GlassCard>
      </div>
    </PageChrome>
    );
  }

  const easyCards = deck.filter((c) => (c as { ease?: string }).ease === "easy");
  const hardCards = deck.filter((c) => (c as { ease?: string }).ease === "hard");
  const deckComplete = deck.length > 0 && reviewedCardIds.size >= deck.length;

  const handleStudyHardAgain = () => {
    const hardOnly = deck.filter((c) => (c as { ease?: string }).ease === "hard");
    if (hardOnly.length === 0) return;
    setReviewedCardIds(new Set());
    setDeck(hardOnly);
    setCardIndex(0);
    setShowAnswer(false);
  };

  const handleReviewEasy = (c: FlashcardItem) => {
    setReviewedCardIds(new Set());
    setDeck([c]);
    setCardIndex(0);
    setShowAnswer(false);
  };

  /** Map FlashcardItem to DashboardFlashcardItem for Aerogel (conceptTitle=topic, content=back, sourceType) */
  const aerogelCards = mapToDashboardCards(deck);

  if (deckComplete) {
    return (
      <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <h2 className="text-2xl font-semibold text-primary">Flashcards</h2>
            <HardwareStatus modelName="llama3.2" className="text-xs" />
          </div>
          <GlassCard>
            <DeckCompleteSummary
              easyCards={easyCards}
              hardCards={hardCards}
              onSaveAndGoBack={handleClearDeck}
              onStudyHardAgain={handleStudyHardAgain}
              onReviewEasy={handleReviewEasy}
            />
          </GlassCard>
        </div>
      </PageChrome>
    );
  }

  return (
    <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="text-2xl font-semibold text-primary">Flashcards</h2>
          <HardwareStatus modelName="llama3.2" className="text-xs" />
        </div>

      <div className="flex flex-col gap-4">
        <button
          type="button"
          onClick={handleClearDeck}
          className="self-start px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary/90 hover:bg-surface-light/80 text-sm font-medium"
        >
          Save and Go Back
        </button>

        <AerogelDashboardCard
          cards={aerogelCards}
          limit={deck.length}
          index={cardIndex}
          onIndexChange={setCardIndex}
          onEasy={handleEasy}
          onHard={handleHard}
          onExplain={handleExplain}
          explainLoading={explainLoading}
        />

        {lastExplanation && (
          <div
            className="flashcard-explanation-panel"
            style={{
              background: "#fff",
              border: "1px solid rgba(0,0,0,0.08)",
              borderRadius: "12px",
              padding: "16px 20px",
              marginTop: "-8px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
              <span style={{ color: "#00a8e8", fontSize: "0.85rem", fontWeight: 600 }}>
                AI Explanation
              </span>
              <button
                type="button"
                onClick={() => setLastExplanation("")}
                aria-label="Close explanation"
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  fontSize: "1.25rem",
                  lineHeight: 1,
                  color: "rgba(0,0,0,0.5)",
                  padding: "0 4px",
                }}
              >
                ×
              </button>
            </div>
            <div className="text-sm text-primary/90 prose prose-sm max-w-none">
              <MarkdownWithMath>{lastExplanation}</MarkdownWithMath>
            </div>
          </div>
        )}

        <GlassCard>
          <p className="text-sm text-primary/70 mb-2">
            Card {idx + 1} of {n} · Topic: {card?.topic ?? "General"} · Flip the card above to reveal the answer
          </p>

          <div className="flex flex-wrap gap-3 mb-4">
                {recommendLoading ? (
                  <LoadingSpinner
                    message="Processing with local AI..."
                    className="flex-shrink-0"
                  />
                ) : !recommendationData ? (
                  <button
                    type="button"
                    onClick={handleRecommendation}
                    className="px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary hover:bg-surface-light/80 text-sm font-medium"
                  >
                    Get study recommendation
                  </button>
                ) : null}
              </div>

              {recommendationData && (
                <AdaptiveRecommendationDisplay
                  data={recommendationData}
                  onDismiss={() => {
                    setRecommendationData(null);
                    setLastRecommendation("");
                  }}
                />
              )}
        </GlassCard>
      </div>
      </div>
    </PageChrome>
  );
}
