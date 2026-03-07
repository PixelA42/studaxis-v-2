/**
 * Theme context — light/dark; persisted via PUT /api/user/stats (preferences.theme).
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
import { getUserStats, updateUserStats } from "../services/api";

type Theme = "light" | "dark";

const STORAGE_THEME = "studaxis_theme";

function loadStoredTheme(): Theme {
  try {
    const t = localStorage.getItem(STORAGE_THEME);
    if (t === "light" || t === "dark") return t;
  } catch {
    // ignore
  }
  return "dark";
}

function applyTheme(t: Theme) {
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-theme", t);
    localStorage.setItem(STORAGE_THEME, t);
  }
}

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    const t = loadStoredTheme();
    applyTheme(t);
    return t;
  });

  useEffect(() => {
    getUserStats()
      .then((s) => {
        const t = s.preferences?.theme;
        if (t === "light" || t === "dark") {
          setThemeState(t);
          localStorage.setItem(STORAGE_THEME, t);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(STORAGE_THEME, theme);
  }, [theme]);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
    updateUserStats({ preferences: { theme: next } }).catch(() => {});
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(theme === "dark" ? "light" : "dark");
  }, [theme, setTheme]);

  const value = useMemo(
    () => ({ theme, setTheme, toggleTheme }),
    [theme, setTheme, toggleTheme]
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
