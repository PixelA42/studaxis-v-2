/**
 * Offline-first recent tools tracking via localStorage.
 * Tracks visits to Panic Mode, Flash Cards, AI Chat, and Quiz.
 */

import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

const STORAGE_KEY = "studaxis_recent_tools";
const MAX_ITEMS = 6;

export type RecentTool = {
  id: string;
  label: string;
  path: string;
  timestamp: number;
};

const TRACKED_PATHS: Record<string, string> = {
  "/panic-mode": "Panic Mode",
  "/flashcards": "Flash Cards",
  "/chat": "AI Chat",
  "/quiz": "Quiz",
};

function loadRecentTools(): RecentTool[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as RecentTool[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveRecentTools(tools: RecentTool[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tools));
  } catch {
    // Ignore storage errors
  }
}

export function recordToolVisit(path: string) {
  const label = TRACKED_PATHS[path];
  if (!label) return;

  const tools = loadRecentTools();
  const id = path.slice(1).replace(/-/g, "_") || path;
  const now = Date.now();

  const filtered = tools.filter((t) => t.path !== path);
  const updated: RecentTool[] = [
    { id, label, path, timestamp: now },
    ...filtered,
  ].slice(0, MAX_ITEMS);

  saveRecentTools(updated);
}

export function useRecentTools(): RecentTool[] {
  const [tools] = useState<RecentTool[]>(loadRecentTools);
  return tools;
}

/** Hook to record current route when it matches a tracked tool. Call from DashboardLayout. */
export function useRecentToolsTracker() {
  const { pathname } = useLocation();

  useEffect(() => {
    if (TRACKED_PATHS[pathname]) {
      recordToolVisit(pathname);
    }
  }, [pathname]);
}

/** All four tools for empty state / Start Learning links */
export const ALL_TOOLS: RecentTool[] = [
  { id: "panic_mode", label: "Panic Mode", path: "/panic-mode", timestamp: 0 },
  { id: "flashcards", label: "Flash Cards", path: "/flashcards", timestamp: 0 },
  { id: "chat", label: "AI Chat", path: "/chat", timestamp: 0 },
  { id: "quiz", label: "Quiz", path: "/quiz", timestamp: 0 },
];
