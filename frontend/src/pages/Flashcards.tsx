import { useState, useEffect } from "react";
import {
  explainFlashcard,
  getStudyRecommendation,
  getFlashcardsDue,
  getFlashcards,
  postFlashcards,
  putFlashcards,
  getUserStats,
  updateUserStats,
} from "../services/api";
import type { FlashcardItem, DashboardFlashcardItem } from "../services/api";
import { useFlashcardDeck } from "../contexts/FlashcardDeckContext";
import { GlassCard, LoadingSpinner, HardwareStatus, PageChrome, AerogelDashboardCard } from "../components";
import { CascadingCardStack } from "../components/CascadingCardStack";
import { FlashcardSourceSelector } from "../components/FlashcardSourceSelector";

const STUDY_TIME_MINUTES = 15;

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

/** Set next_review to now + days (ISO string). */
function nextReviewInDays(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString();
}

export function FlashcardsPage() {
  const {
    deck,
    cardIndex,
    showAnswer: _showAnswer,
    setShowAnswer,
    lastExplanation,
    lastRecommendation,
    setDeck,
    setCardIndex,
    setLastExplanation,
    setLastRecommendation,
    clearDeck,
    advanceToNext,
  } = useFlashcardDeck();

  const [count, setCount] = useState(10);
  const [generateLoading, setGenerateLoading] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [explainLoading, setExplainLoading] = useState(false);
  const [recommendLoading, setRecommendLoading] = useState(false);
  const [dueCount, setDueCount] = useState<number>(0);
  const [, setLoadingDue] = useState(false);
  const [loadingReview, setLoadingReview] = useState(false);

  useEffect(() => {
    if (deck.length > 0) return;
    setLoadingDue(true);
    getFlashcardsDue()
      .then((r) => setDueCount(r.cards.length))
      .catch(() => setDueCount(0))
      .finally(() => setLoadingDue(false));
  }, [deck.length]);

  const n = deck.length;
  const idx = n > 0 ? cardIndex % n : 0;
  const card: FlashcardItem | null = n > 0 ? deck[idx]! : null;

  const handleGenerateFromSelector = async (
    cards: FlashcardItem[],
    sourceType: string[]
  ) => {
    setGenerateError(null);
    setGenerateLoading(true);
    try {
      const topic = cards[0]?.topic ?? "General";
      const enriched = enrichForStorage(cards, topic, sourceType);
      await postFlashcards(enriched);
      setDeck(enriched);
      setCardIndex(0);
      setShowAnswer(false);
      setLastExplanation("");
      setLastRecommendation("");
    } catch (e) {
      setGenerateError(e instanceof Error ? e.message : "Failed to save deck.");
    } finally {
      setGenerateLoading(false);
    }
  };

  const loadDueCards = async () => {
    setLoadingReview(true);
    try {
      const res = await getFlashcardsDue();
      if (res.cards.length > 0) {
        setDeck(res.cards);
        setCardIndex(0);
        setShowAnswer(false);
        setLastExplanation("");
        setLastRecommendation("");
      }
    } finally {
      setLoadingReview(false);
    }
  };

  const handleExplain = async () => {
    if (!card) return;
    setExplainLoading(true);
    try {
      const res = await explainFlashcard({
        front: card.front ?? card.question ?? "",
        back: card.back ?? card.answer ?? "",
        topic: card.topic,
        user_query: `Explain this flashcard: ${card.front ?? card.question ?? ""}`,
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

  const handleRecommendation = async () => {
    if (!card) return;
    setRecommendLoading(true);
    try {
      const res = await getStudyRecommendation({
        topic: card.topic,
        time_budget_minutes: STUDY_TIME_MINUTES,
        review_mode: "flashcards",
        offline_mode: true,
      });
      setLastRecommendation(res.text);
    } catch (e) {
      setLastRecommendation(
        e instanceof Error ? e.message : "Could not get recommendation."
      );
    } finally {
      setRecommendLoading(false);
    }
  };

  const handleEasy = async () => {
    if (!card) return;
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
      // non-blocking
    }
    const updated = { ...card, next_review: nextReviewInDays(3) };
    const nextDeck = deck.map((c) => (c.id === card.id ? updated : c));
    setDeck(nextDeck);
    try {
      const { cards: allCards } = await getFlashcards();
      const merged = allCards.map((c) => (c.id === card.id ? updated : c));
      await putFlashcards(merged);
    } catch {
      // keep local state
    }
    advanceToNext();
  };

  const handleHard = async () => {
    if (!card) return;
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
      // non-blocking
    }
    const updated = { ...card, next_review: nextReviewInDays(1) };
    const nextDeck = deck.map((c) => (c.id === card.id ? updated : c));
    setDeck(nextDeck);
    try {
      const { cards: allCards } = await getFlashcards();
      const merged = allCards.map((c) => (c.id === card.id ? updated : c));
      await putFlashcards(merged);
    } catch {
      // keep local state
    }
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

          {dueCount > 0 && (
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

          {/* Stored decks — cascading card stack */}
          <GlassCard title="Your stored decks">
            <p className="text-sm text-primary/70 mb-4">
              Click a deck below to load it for review. Decks are grouped by topic from your stored flashcards.
            </p>
            <CascadingCardStack
              onSelectDeck={(cards, _topic) => {
                setDeck(cards);
                setCardIndex(0);
                setShowAnswer(false);
                setLastExplanation("");
                setLastRecommendation("");
              }}
            />
          </GlassCard>
      </div>
    </PageChrome>
    );
  }

  /** Map FlashcardItem to DashboardFlashcardItem for Aerogel (conceptTitle=topic, content=back, sourceType) */
  const aerogelCards = mapToDashboardCards(deck);

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
          onClick={clearDeck}
          className="self-start px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary/90 hover:bg-surface-light/80 text-sm font-medium"
        >
          Clear deck & generate new
        </button>

        <AerogelDashboardCard
          cards={aerogelCards}
          limit={deck.length}
          index={cardIndex}
          onIndexChange={setCardIndex}
        />

        <GlassCard>
          <p className="text-sm text-primary/70 mb-2">
            Card {idx + 1} of {n} · Topic: {card?.topic ?? "General"} · Flip the card above to reveal the answer
          </p>

          <div className="flex flex-wrap gap-3 mb-4">
                {explainLoading ? (
                  <LoadingSpinner
                    message="Processing with local AI..."
                    className="flex-shrink-0"
                  />
                ) : (
                  <button
                    type="button"
                    onClick={handleExplain}
                    className="px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary hover:bg-surface-light/80 text-sm font-medium"
                  >
                    Explain with AI
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleEasy}
                  className="px-4 py-2 rounded-xl border border-green-500/40 bg-green-500/10 text-green-400 hover:bg-green-500/20 text-sm font-medium"
                >
                  Mark easy
                </button>
                <button
                  type="button"
                  onClick={handleHard}
                  className="px-4 py-2 rounded-xl border border-amber-500/40 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 text-sm font-medium"
                >
                  Mark hard
                </button>
                {recommendLoading ? (
                  <LoadingSpinner
                    message="Processing with local AI..."
                    className="flex-shrink-0"
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
              </div>

              {lastExplanation && (
                <div className="mt-4 pt-4 border-t border-glass-border">
                  <h3 className="text-sm font-semibold text-primary mb-2">
                    AI explanation
                  </h3>
                  <p className="text-sm text-primary/90 whitespace-pre-wrap">
                    {lastExplanation}
                  </p>
                </div>
              )}
              {lastRecommendation && (
                <div className="mt-4 pt-4 border-t border-glass-border">
                  <h3 className="text-sm font-semibold text-primary mb-2">
                    AI recommendation
                  </h3>
                  <p className="text-sm text-primary/90 whitespace-pre-wrap">
                    {lastRecommendation}
                  </p>
                </div>
              )}
        </GlassCard>
      </div>
      </div>
    </PageChrome>
  );
}
