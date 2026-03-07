/**
 * App state — boot complete, last seen version (for hardware modal on first launch).
 * Stored in localStorage so returning users skip boot flow.
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const APP_VERSION = "0.1.0";
const STORAGE_BOOT_COMPLETE = "studaxis_boot_complete";
const STORAGE_LAST_SEEN_VERSION = "studaxis_last_seen_version";

function loadBootComplete(): boolean {
  return localStorage.getItem(STORAGE_BOOT_COMPLETE) === "true";
}

function loadLastSeenVersion(): string | null {
  return localStorage.getItem(STORAGE_LAST_SEEN_VERSION);
}

interface AppStateContextValue {
  bootComplete: boolean;
  lastSeenVersion: string | null;
  appVersion: string;
  setBootComplete: () => void;
  markVersionSeen: () => void;
  resetBoot: () => void;
}

const AppStateContext = createContext<AppStateContextValue | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [bootComplete, setBootCompleteState] = useState(loadBootComplete);
  const [lastSeenVersion, setLastSeenVersion] = useState(loadLastSeenVersion);

  const setBootComplete = useCallback(() => {
    setBootCompleteState(true);
    localStorage.setItem(STORAGE_BOOT_COMPLETE, "true");
  }, []);

  const markVersionSeen = useCallback(() => {
    setLastSeenVersion(APP_VERSION);
    localStorage.setItem(STORAGE_LAST_SEEN_VERSION, APP_VERSION);
  }, []);

  const resetBoot = useCallback(() => {
    setBootCompleteState(false);
    setLastSeenVersion(null);
    localStorage.removeItem(STORAGE_BOOT_COMPLETE);
    localStorage.removeItem(STORAGE_LAST_SEEN_VERSION);
  }, []);

  const value = useMemo(
    () => ({
      bootComplete,
      lastSeenVersion,
      appVersion: APP_VERSION,
      setBootComplete,
      markVersionSeen,
      resetBoot,
    }),
    [bootComplete, lastSeenVersion, setBootComplete, markVersionSeen, resetBoot]
  );

  return (
    <AppStateContext.Provider value={value}>
      {children}
    </AppStateContext.Provider>
  );
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error("useAppState must be used within AppStateProvider");
  return ctx;
}
