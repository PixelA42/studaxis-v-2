/**
 * Cascading Card Stack — vellum-style flashcard deck preview.
 * Fetches stored flashcards from /api/flashcards, groups by topic, displays as decks.
 * Clicking a card loads that deck for review.
 * Studaxis colors: #111827 (slate), #0ea5e9 (blue), #fef08a (yellow).
 */

import { useState, useEffect, useRef } from "react";
import { getFlashcards } from "../services/api";
import type { FlashcardItem } from "../services/api";

export interface FlashcardDeckItem {
  topicName: string;
  textbook: string;
  selectedExistingTextbook: boolean;
  link: string;
  /** Cards in this deck (for loading into review) */
  cards: FlashcardItem[];
}

const CARD_CLASSES = ["card-1", "card-2", "card-3", "card-4"] as const;

export interface CascadingCardStackProps {
  /** Called when user clicks a deck to load it for review */
  onSelectDeck?: (cards: FlashcardItem[], topic: string) => void;
}

export function CascadingCardStack({ onSelectDeck }: CascadingCardStackProps) {
  const [decks, setDecks] = useState<FlashcardDeckItem[]>([]);
  const [loading, setLoading] = useState(true);
  const stackRef = useRef<HTMLDivElement>(null);
  const [parallax, setParallax] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const fetchDecks = async () => {
      try {
        const { cards } = await getFlashcards();
        if (!cards || cards.length === 0) {
          setDecks([]);
          return;
        }
        // Group by topic — each group becomes a deck
        const byTopic = new Map<string, FlashcardItem[]>();
        for (const c of cards) {
          const topic = c.topic?.trim() || "General";
          if (!byTopic.has(topic)) byTopic.set(topic, []);
          byTopic.get(topic)!.push(c);
        }
        const deckList: FlashcardDeckItem[] = Array.from(byTopic.entries())
          .sort((a, b) => b[1].length - a[1].length) // most cards first
          .slice(0, 4)
          .map(([topic, topicCards]) => ({
            topicName: topic,
            textbook: "Stored",
            selectedExistingTextbook: true,
            link: "/flashcards",
            cards: topicCards,
          }));
        setDecks(deckList);
      } catch {
        setDecks([]);
      } finally {
        setLoading(false);
      }
    };
    fetchDecks();
  }, []);

  useEffect(() => {
    const handleMouse = (e: MouseEvent) => {
      const x = (window.innerWidth / 2 - e.pageX) / 50;
      const y = (window.innerHeight / 2 - e.pageY) / 50;
      setParallax({ x, y });
    };
    window.addEventListener("mousemove", handleMouse);
    return () => window.removeEventListener("mousemove", handleMouse);
  }, []);

  const displayDecks = decks.slice(0, 4);

  return (
    <div className="cascading-stack-container">
      <style>{`
        .cascading-stack-container {
          --bg: #fdfdfc;
          --vellum-white: rgba(255, 255, 255, 0.35);
          --vellum-border: rgba(255, 255, 255, 0.5);
          --ink: #111827;
          --accent-blue: #0ea5e9;
          --accent-yellow: #fef08a;
          --shadow: rgba(0, 0, 0, 0.04);
          --transition: cubic-bezier(0.2, 0.8, 0.2, 1);
          font-family: 'Inter', 'Plus Jakarta Sans', sans-serif;
          color: var(--ink);
        }
        .cascading-stack-container .stack-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-end;
          margin-bottom: 24px;
        }
        .cascading-stack-container .stack-header h2 {
          font-weight: 700;
          font-size: 2rem;
          letter-spacing: -0.04em;
          line-height: 0.9;
          text-transform: lowercase;
          color: var(--ink);
        }
        .cascading-stack-container .stack-meta {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.75rem;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          opacity: 0.5;
          color: var(--ink);
        }
        .cascading-card-stack {
          position: relative;
          height: 400px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: transform 0.3s var(--transition);
        }
        .vellum-card {
          position: absolute;
          width: 320px;
          height: 450px;
          background: var(--vellum-white);
          backdrop-filter: blur(20px) saturate(160%);
          border: 1px solid var(--vellum-border);
          border-radius: 4px;
          padding: 30px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          box-shadow: 0 4px 30px var(--shadow), inset 0 0 0 1px rgba(255,255,255,0.2);
          transition: transform 0.6s var(--transition), opacity 0.6s var(--transition),
            filter 0.6s var(--transition), box-shadow 0.6s var(--transition);
          cursor: pointer;
          transform-origin: center center;
        }
        .vellum-card::after {
          content: '';
          position: absolute;
          inset: 0;
          background: linear-gradient(135deg, rgba(255,255,255,0.2) 0%, transparent 50%, rgba(0,0,0,0.02) 100%);
          pointer-events: none;
          border-radius: 4px;
        }
        .vellum-card.card-1 { transform: translateX(-180px) rotate(-8deg); z-index: 1; background: rgba(255, 248, 235, 0.4); }
        .vellum-card.card-2 { transform: translateX(-60px) rotate(-3deg); z-index: 2; background: rgba(224, 242, 254, 0.4); }
        .vellum-card.card-3 { transform: translateX(60px) rotate(2deg); z-index: 3; background: rgba(254, 249, 195, 0.35); }
        .vellum-card.card-4 { transform: translateX(180px) rotate(7deg); z-index: 4; background: rgba(255, 255, 255, 0.45); }
        .cascading-card-stack:hover .vellum-card {
          filter: blur(2px) grayscale(0.5);
          opacity: 0.6;
        }
        .cascading-card-stack .vellum-card:hover {
          filter: blur(0) grayscale(0) !important;
          opacity: 1 !important;
          z-index: 100;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
        }
        .cascading-card-stack:hover .vellum-card.card-1 { transform: translateX(-240px) rotate(0deg) scale(0.95); }
        .cascading-card-stack:hover .vellum-card.card-2 { transform: translateX(-80px) rotate(0deg) scale(0.95); }
        .cascading-card-stack:hover .vellum-card.card-3 { transform: translateX(80px) rotate(0deg) scale(0.95); }
        .cascading-card-stack:hover .vellum-card.card-4 { transform: translateX(240px) rotate(0deg) scale(0.95); }
        .cascading-card-stack .vellum-card.card-1:hover { transform: translateX(-240px) translateY(-20px) rotate(0deg) scale(1.05) !important; }
        .cascading-card-stack .vellum-card.card-2:hover { transform: translateX(-80px) translateY(-20px) rotate(0deg) scale(1.05) !important; }
        .cascading-card-stack .vellum-card.card-3:hover { transform: translateX(80px) translateY(-20px) rotate(0deg) scale(1.05) !important; }
        .cascading-card-stack .vellum-card.card-4:hover { transform: translateX(240px) translateY(-20px) rotate(0deg) scale(1.05) !important; }
        .card-top { display: flex; justify-content: space-between; align-items: flex-start; }
        .chip {
          width: 40px;
          height: 30px;
          background: rgba(0,0,0,0.05);
          border-radius: 4px;
          position: relative;
          overflow: hidden;
        }
        .chip::before {
          content: '';
          position: absolute;
          top: 50%; left: 0; width: 100%; height: 1px;
          background: rgba(0,0,0,0.1);
        }
        .card-type {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 0.2em;
          opacity: 0.8;
          color: var(--ink);
        }
        .card-middle { margin-top: auto; margin-bottom: 40px; }
        .card-number {
          font-family: 'JetBrains Mono', monospace;
          font-size: 1rem;
          letter-spacing: 0.08em;
          color: var(--ink);
          word-break: break-word;
        }
        .card-number.long { font-size: 0.85rem; }
        .card-bottom { display: flex; justify-content: space-between; align-items: flex-end; }
        .card-holder {
          text-transform: uppercase;
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 0.05em;
          opacity: 0.6;
          color: var(--ink);
        }
        .card-holder a {
          color: var(--accent-blue);
          text-decoration: none;
        }
        .card-holder a:hover { text-decoration: underline; }
        .status-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: var(--accent-blue);
          display: inline-block;
          margin-right: 8px;
          vertical-align: middle;
        }
        .expiry {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.75rem;
          opacity: 0.8;
          color: var(--ink);
        }
        @keyframes reveal {
          from { transform: translateY(40px) rotate(0deg); opacity: 0; filter: blur(10px); }
          to { opacity: 1; filter: blur(0); }
        }
        .vellum-card { animation: reveal 1s var(--transition) both; }
        .vellum-card.card-1 { animation-delay: 0.1s; }
        .vellum-card.card-2 { animation-delay: 0.2s; }
        .vellum-card.card-3 { animation-delay: 0.3s; }
        .vellum-card.card-4 { animation-delay: 0.4s; }
        @media (max-width: 768px) {
          .cascading-card-stack { height: 500px; transform: scale(0.75); }
        }
      `}</style>

      <header className="stack-header">
        <div>
          <p className="stack-meta">Vault / {new Date().getFullYear()}</p>
          <h2>recent.</h2>
        </div>
        <div className="stack-meta">Stored Decks: {displayDecks.length}</div>
      </header>

      {loading ? (
        <div className="cascading-card-stack" style={{ alignItems: "center", justifyContent: "center" }}>
          <p className="stack-meta">Loading…</p>
        </div>
      ) : displayDecks.length === 0 ? (
        <div className="cascading-card-stack" style={{ alignItems: "center", justifyContent: "center" }}>
          <p className="stack-meta">No stored decks yet. Generate flashcards above to see them here.</p>
        </div>
      ) : (
        <main
          ref={stackRef}
          className="cascading-card-stack"
          style={{ transform: `translateX(${parallax.x}px) translateY(${parallax.y}px)` }}
        >
          {displayDecks.map((deck, i) => (
            <button
              key={deck.topicName}
              type="button"
              onClick={() => onSelectDeck?.(deck.cards, deck.topicName)}
              className={`vellum-card ${CARD_CLASSES[i] ?? CARD_CLASSES[0]}`}
              style={{ border: "none", background: "transparent", cursor: "pointer", textAlign: "left", font: "inherit" }}
            >
              <div className="card-top">
                <div className="chip" />
                <div className="card-type">
                  {deck.selectedExistingTextbook ? deck.textbook : "CUSTOM TOPIC"}
                </div>
              </div>
              <div className="card-middle">
                <div className={`card-number ${deck.topicName.length > 25 ? "long" : ""}`}>
                  {deck.topicName}
                </div>
              </div>
              <div className="card-bottom">
                <div className="card-holder">
                  <span
                    className="status-dot"
                    style={{ background: i % 2 === 0 ? "var(--accent-blue)" : "var(--accent-yellow)" }}
                  />
                  {deck.link && deck.link.startsWith("http") ? (
                    <a
                      href={deck.link}
                      onClick={(e) => e.stopPropagation()}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      View Source Link
                    </a>
                  ) : (
                    <span>View Source Link</span>
                  )}
                </div>
                <div className="expiry">{deck.cards.length} cards</div>
              </div>
            </button>
          ))}
        </main>
      )}
    </div>
  );
}
