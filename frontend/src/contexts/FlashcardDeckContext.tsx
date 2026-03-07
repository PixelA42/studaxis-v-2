import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { FlashcardItem } from "../services/api";

export interface FlashcardDeckState {
  deck: FlashcardItem[];
  cardIndex: number;
  showAnswer: boolean;
  lastExplanation: string;
  lastRecommendation: string;
}

interface FlashcardDeckContextValue extends FlashcardDeckState {
  setDeck: (deck: FlashcardItem[]) => void;
  setCardIndex: (index: number) => void;
  setShowAnswer: (show: boolean) => void;
  setLastExplanation: (text: string) => void;
  setLastRecommendation: (text: string) => void;
  clearDeck: () => void;
  advanceToNext: () => void;
}

const initialState: FlashcardDeckState = {
  deck: [],
  cardIndex: 0,
  showAnswer: false,
  lastExplanation: "",
  lastRecommendation: "",
};

const FlashcardDeckContext = createContext<FlashcardDeckContextValue | null>(
  null
);

export function FlashcardDeckProvider({ children }: { children: ReactNode }) {
  const [deck, setDeck] = useState<FlashcardItem[]>(initialState.deck);
  const [cardIndex, setCardIndex] = useState(initialState.cardIndex);
  const [showAnswer, setShowAnswer] = useState(initialState.showAnswer);
  const [lastExplanation, setLastExplanation] = useState(
    initialState.lastExplanation
  );
  const [lastRecommendation, setLastRecommendation] = useState(
    initialState.lastRecommendation
  );

  const clearDeck = useCallback(() => {
    setDeck([]);
    setCardIndex(0);
    setShowAnswer(false);
    setLastExplanation("");
    setLastRecommendation("");
  }, []);

  const advanceToNext = useCallback(() => {
    const n = deck.length;
    if (n === 0) return;
    setCardIndex((i) => (i + 1) % n);
    setShowAnswer(false);
  }, [deck.length]);

  const value = useMemo<FlashcardDeckContextValue>(
    () => ({
      deck,
      cardIndex,
      showAnswer,
      lastExplanation,
      lastRecommendation,
      setDeck,
      setCardIndex,
      setShowAnswer,
      setLastExplanation,
      setLastRecommendation,
      clearDeck,
      advanceToNext,
    }),
    [
      deck,
      cardIndex,
      showAnswer,
      lastExplanation,
      lastRecommendation,
      clearDeck,
      advanceToNext,
    ]
  );

  return (
    <FlashcardDeckContext.Provider value={value}>
      {children}
    </FlashcardDeckContext.Provider>
  );
}

export function useFlashcardDeck(): FlashcardDeckContextValue {
  const ctx = useContext(FlashcardDeckContext);
  if (!ctx) {
    throw new Error("useFlashcardDeck must be used within FlashcardDeckProvider");
  }
  return ctx;
}
