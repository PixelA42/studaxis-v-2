/**
 * Panic Exam Context — signals when a Panic Mode exam is in progress.
 * DashboardLayout hides the sidebar when active to prevent navigation during the test.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useLocation } from "react-router-dom";

interface PanicExamContextValue {
  /** True when user is in fullscreen exam (locks navbar) */
  examActive: boolean;
  setExamActive: (active: boolean) => void;
}

const PanicExamContext = createContext<PanicExamContextValue | null>(null);

export function PanicExamProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const [examActive, setExamActiveState] = useState(false);

  // FIX 3: Reset examActive when navigating away from panic mode
  useEffect(() => {
    if (!location.pathname.includes("/panic-mode")) {
      setExamActiveState(false);
    }
  }, [location.pathname]);

  const setExamActive = useCallback((active: boolean) => {
    setExamActiveState(active);
  }, []);

  const value = useMemo(
    () => ({ examActive, setExamActive }),
    [examActive, setExamActive]
  );

  return (
    <PanicExamContext.Provider value={value}>
      {children}
    </PanicExamContext.Provider>
  );
}

export function usePanicExam() {
  const ctx = useContext(PanicExamContext);
  if (!ctx) {
    return {
      examActive: false,
      setExamActive: (_: boolean) => {},
    };
  }
  return ctx;
}
