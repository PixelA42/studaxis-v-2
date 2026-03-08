/**
 * Aerogel Dashboard Card — light glassmorphism flashcard with flip-from-right.
 * Fetches from /api/dashboard/flashcards. Studaxis colors: #111827, #0ea5e9, #fef08a.
 * Front: conceptTitle (question). Back: content. Click flips from right.
 */

import { useState, useEffect } from "react";
import { getDashboardFlashcards } from "../services/api";
import type { DashboardFlashcardItem } from "../services/api";
import { LoadingSpinner } from "./LoadingSpinner";
import { MarkdownWithMath } from "./MarkdownWithMath";

export interface AerogelDashboardCardProps {
  /** Optional: limit number of cards shown */
  limit?: number;
  /** Optional: custom class for container */
  className?: string;
  /** Optional: when provided, use these cards instead of fetching from API */
  cards?: DashboardFlashcardItem[];
  /** Optional: controlled index (for syncing with parent actions like Easy/Hard) */
  index?: number;
  /** Optional: called when user navigates to a different card */
  onIndexChange?: (i: number) => void;
  /** Optional: show Easy/Hard/Explain on back when flipped (SRS review mode) */
  onEasy?: () => void;
  onHard?: () => void;
  onExplain?: () => void;
  explainLoading?: boolean;
}

export function AerogelDashboardCard({
  limit = 6,
  className = "",
  cards: cardsProp,
  index: indexProp,
  onIndexChange,
  onEasy,
  onHard,
  onExplain,
  explainLoading = false,
}: AerogelDashboardCardProps) {
  const [cards, setCards] = useState<DashboardFlashcardItem[]>([]);
  const [loading, setLoading] = useState(!cardsProp);
  const [error, setError] = useState<string | null>(null);
  const [internalIndex, setInternalIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const index = indexProp ?? internalIndex;

  useEffect(() => {
    if (cardsProp && cardsProp.length > 0) {
      setCards(cardsProp.slice(0, limit));
      setLoading(false);
      setError(null);
      return;
    }
    if (!cardsProp) {
      setLoading(true);
      getDashboardFlashcards()
        .then((res) => setCards(res.cards.slice(0, limit)))
        .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
        .finally(() => setLoading(false));
    }
  }, [limit, cardsProp]);

  const card = cards[index] ?? null;

  const handleFlip = () => setFlipped((f) => !f);
  const handlePrev = () => {
    const next = index <= 0 ? cards.length - 1 : index - 1;
    if (onIndexChange) onIndexChange(next);
    else setInternalIndex(next);
    setFlipped(false);
  };
  const handleNext = () => {
    const next = index >= cards.length - 1 ? 0 : index + 1;
    if (onIndexChange) onIndexChange(next);
    else setInternalIndex(next);
    setFlipped(false);
  };

  if (loading) {
    return (
      <div className={`aerogel-dashboard-card ${className}`}>
        <style>{AEROGEL_STYLES}</style>
        <div className="aerogel-body">
          <div className="membrane" style={{ alignItems: "center", justifyContent: "center" }}>
            <LoadingSpinner message="Loading concepts…" />
          </div>
        </div>
      </div>
    );
  }

  if (error || cards.length === 0) {
    return (
      <div className={`aerogel-dashboard-card ${className}`}>
        <style>{AEROGEL_STYLES}</style>
        <div className="aerogel-body">
          <div className="membrane aerogel-empty">
            <p className="aerogel-empty-text">
              {error ?? "No dashboard concepts yet. Generate flashcards to see them here."}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`aerogel-dashboard-card ${className}`}>
      <style>{AEROGEL_STYLES}</style>
      <div className="aerogel-body">
        <div
          className={`membrane aerogel-flip-container ${flipped ? "flipped" : ""}`}
          onClick={handleFlip}
          onKeyDown={(e) => e.key === "Enter" && handleFlip()}
          role="button"
          tabIndex={0}
          aria-label={flipped ? "Show question" : "Show answer"}
        >
          <div className="aerogel-flip-card">
            <div className="aerogel-flip-inner">
              <div className="aerogel-face aerogel-front">
                <div className="text-area">
                  <h2>Question</h2>
                  <div className="aerogel-question">
                    <MarkdownWithMath>{card?.conceptTitle ?? "—"}</MarkdownWithMath>
                  </div>
                  <span className="aerogel-hint">Click to reveal answer</span>
                </div>
              </div>
              <div className="aerogel-face aerogel-back">
                <div className="text-area">
                  <h2>{card?.conceptTitle ?? "Concept"}</h2>
                  <div>
                    <MarkdownWithMath>{card?.content ?? ""}</MarkdownWithMath>
                  </div>
                </div>
                {(onEasy || onHard || onExplain) && (
                  <div className="aerogel-back-actions" onClick={(e) => e.stopPropagation()}>
                    {onEasy && (
                      <button
                        type="button"
                        onClick={onEasy}
                        className="aerogel-btn aerogel-btn-easy"
                        aria-label="Mark easy"
                      >
                        Easy
                      </button>
                    )}
                    {onHard && (
                      <button
                        type="button"
                        onClick={onHard}
                        className="aerogel-btn aerogel-btn-hard"
                        aria-label="Mark hard"
                      >
                        Hard
                      </button>
                    )}
                    {onExplain && (
                      <button
                        type="button"
                        onClick={onExplain}
                        disabled={explainLoading}
                        className="aerogel-btn aerogel-btn-explain"
                        aria-label="Explain with AI"
                      >
                        {explainLoading ? (
                          <span className="aerogel-btn-spinner" aria-hidden />
                        ) : (
                          "Explain"
                        )}
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div
            className="dash"
            onClick={(e) => {
              e.stopPropagation();
              handleNext();
            }}
            onKeyDown={(e) => e.key === "Enter" && handleNext()}
            role="button"
            tabIndex={0}
            aria-label="Next card"
          />
        </div>

        <div className="aerogel-nav" aria-hidden>
          <button type="button" onClick={handlePrev} aria-label="Previous">
            ←
          </button>
          <span>
            {index + 1} / {cards.length}
          </span>
          <button type="button" onClick={handleNext} aria-label="Next">
            →
          </button>
        </div>
      </div>
    </div>
  );
}

const AEROGEL_STYLES = `
.aerogel-dashboard-card { font-family: 'Inter', sans-serif; }
.aerogel-body {
  min-height: 520px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: #ffffff;
  background-image:
    linear-gradient(rgba(0,0,0,0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,0,0,0.02) 1px, transparent 1px);
  background-size: 24px 24px;
}
.membrane {
  width: 320px;
  height: 460px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  border-radius: 40px;
  border: 1px solid rgba(17, 24, 39, 0.08);
  display: flex;
  flex-direction: column;
  padding: 40px;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.06);
  position: relative;
  cursor: pointer;
}
.membrane:not(.aerogel-flip-container) { overflow: hidden; }
.aerogel-flip-container { overflow: visible; }
.membrane::after {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: conic-gradient(from 0deg, transparent, rgba(14,165,233,0.03), transparent);
  animation: aerogel-rotate 10s linear infinite;
  pointer-events: none;
}
@keyframes aerogel-rotate { 100% { transform: rotate(360deg); } }
.text-area {
  flex: 1;
  color: #111827;
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.text-area h2 {
  font-weight: 300;
  letter-spacing: 4px;
  font-size: 0.8rem;
  opacity: 0.6;
  margin-bottom: 20px;
  color: #111827;
}
.text-area p {
  font-size: 1.2rem;
  line-height: 1.5;
  font-weight: 500;
  color: #111827;
}
.aerogel-question { font-size: 1.1rem; }
.aerogel-hint {
  font-size: 0.75rem;
  opacity: 0.5;
  margin-top: 12px;
  color: #111827;
}
.dash {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: 40px;
  height: 4px;
  background: rgba(17, 24, 39, 0.2);
  border-radius: 2px;
  cursor: pointer;
  z-index: 10;
}
.dash:hover { background: #0ea5e9; }
/* Flip card: perspective on outer, inner rotates, front/back stacked with backface-visibility */
.aerogel-flip-card {
  flex: 1;
  min-height: 0;
  width: 100%;
  position: relative;
  perspective: 1000px;
  transform-style: preserve-3d;
}
.aerogel-flip-inner {
  position: relative;
  width: 100%;
  height: 100%;
  text-align: center;
  transform-style: preserve-3d;
  transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
.aerogel-flip-container.flipped .aerogel-flip-inner {
  transform: rotateY(180deg);
}
.aerogel-face {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: 100%;
  height: 100%;
  -webkit-backface-visibility: hidden;
  backface-visibility: hidden;
  border-radius: 24px;
  padding: 20px;
  box-sizing: border-box;
}
.aerogel-face.aerogel-front {
  background: rgba(255, 255, 255, 0.85);
  color: #111827;
}
.aerogel-face.aerogel-back {
  background: rgba(255, 255, 255, 0.9);
  color: #111827;
  transform: rotateY(180deg);
}
.aerogel-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 16px;
  color: #111827;
  font-size: 0.9rem;
}
.aerogel-nav button {
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid rgba(17, 24, 39, 0.15);
  background: rgba(255,255,255,0.8);
  color: #111827;
  cursor: pointer;
  transition: 0.2s;
}
.aerogel-nav button:hover {
  background: #0ea5e9;
  color: white;
  border-color: #0ea5e9;
}
.aerogel-empty { align-items: center; justify-content: center; }
.aerogel-empty-text { color: #111827; opacity: 0.7; text-align: center; padding: 20px; }
/* SRS buttons on back */
.aerogel-back-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(17, 24, 39, 0.08);
}
.aerogel-btn {
  padding: 8px 16px;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: 0.2s;
  border: 1px solid transparent;
}
.aerogel-btn-easy {
  background: rgba(34, 197, 94, 0.15);
  color: #16a34a;
  border-color: rgba(34, 197, 94, 0.3);
}
.aerogel-btn-easy:hover { background: rgba(34, 197, 94, 0.25); }
.aerogel-btn-hard {
  background: rgba(245, 158, 11, 0.15);
  color: #d97706;
  border-color: rgba(245, 158, 11, 0.3);
}
.aerogel-btn-hard:hover { background: rgba(245, 158, 11, 0.25); }
.aerogel-btn-explain {
  background: rgba(14, 165, 233, 0.1);
  color: #0ea5e9;
  border-color: rgba(14, 165, 233, 0.25);
}
.aerogel-btn-explain:hover:not(:disabled) { background: rgba(14, 165, 233, 0.2); }
.aerogel-btn-explain:disabled { opacity: 0.6; cursor: not-allowed; }
.aerogel-btn-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(14, 165, 233, 0.3);
  border-top-color: #0ea5e9;
  border-radius: 50%;
  animation: aerogel-spin 0.8s linear infinite;
}
@keyframes aerogel-spin { to { transform: rotate(360deg); } }
`;
