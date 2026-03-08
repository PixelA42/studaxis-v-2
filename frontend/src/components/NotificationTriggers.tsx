/**
 * NotificationTriggers — Pushes notifications for streak, sync, welcome, study reminders.
 * Mounted inside NotificationProvider + AuthProvider; does not modify other components.
 */

import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useNotification } from "../contexts/NotificationContext";
import { getUserStats } from "../services/api";

const STORAGE_WELCOME = "studaxis_last_welcome_date";
const STORAGE_SYNC_OFFLINE = "studaxis_sync_offline_shown";
const STORAGE_SYNC_ONLINE = "studaxis_sync_online_shown";
const STORAGE_STREAK_REMINDER = "studaxis_streak_reminder_date";
const STORAGE_STUDY_REMINDER = "studaxis_study_reminder_time";

function todayLocal(): string {
  return new Date().toISOString().slice(0, 10);
}

function isToday(iso: string | null | undefined): boolean {
  if (!iso) return false;
  try {
    const d = new Date(iso);
    const today = new Date();
    return d.getDate() === today.getDate() && d.getMonth() === today.getMonth() && d.getFullYear() === today.getFullYear();
  } catch {
    return false;
  }
}

export function NotificationTriggers() {
  const { isAuthenticated, connectivityStatus } = useAuth();
  const { push } = useNotification();
  const location = useLocation();
  const prevStatus = useRef<"online" | "offline" | "unknown">("unknown");
  const mounted = useRef(false);

  const isDashboardRoute = location.pathname.startsWith("/home") ||
    location.pathname.startsWith("/dashboard") ||
    location.pathname.startsWith("/chat") ||
    location.pathname.startsWith("/flashcards") ||
    location.pathname.startsWith("/quiz");

  // Welcome back — once per day when user lands on a main route
  useEffect(() => {
    if (!isAuthenticated || !isDashboardRoute) return;
    const today = todayLocal();
    const last = localStorage.getItem(STORAGE_WELCOME);
    if (last === today) return;
    localStorage.setItem(STORAGE_WELCOME, today);
    push({
      type: "info",
      title: "Welcome back",
      message: "Pick up where you left off. A quick quiz or flashcard review keeps your streak going.",
      tag: "welcome",
    });
  }, [isAuthenticated, isDashboardRoute, push]);

  // Sync status — when going offline / back online
  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true;
      prevStatus.current = connectivityStatus;
      return;
    }
    if (!isAuthenticated) return;

    if (prevStatus.current === "online" && connectivityStatus === "offline") {
      const last = sessionStorage.getItem(STORAGE_SYNC_OFFLINE);
      const now = Date.now();
      if (!last || now - parseInt(last, 10) > 60000) {
        sessionStorage.setItem(STORAGE_SYNC_OFFLINE, String(now));
        push({
          type: "sync",
          title: "You're offline",
          message: "Changes will sync when you're back online.",
          tag: "sync",
        });
      }
    } else if (prevStatus.current === "offline" && connectivityStatus === "online") {
      const last = sessionStorage.getItem(STORAGE_SYNC_ONLINE);
      const now = Date.now();
      if (!last || now - parseInt(last, 10) > 60000) {
        sessionStorage.setItem(STORAGE_SYNC_ONLINE, String(now));
        push({
          type: "success",
          title: "Back online",
          message: "Your progress will sync automatically.",
          tag: "sync",
        });
      }
    }
    prevStatus.current = connectivityStatus;
  }, [connectivityStatus, isAuthenticated, push]);

  // Streak reminder — if user has streak but hasn't studied today (once per day)
  useEffect(() => {
    if (!isAuthenticated || !isDashboardRoute) return;

    let cancelled = false;
    const run = async () => {
      try {
        const stats = await getUserStats();
        if (cancelled) return;
        const streak = stats?.streak?.current ?? 0;
        const lastDate = stats?.streak?.last_activity_date;
        const today = todayLocal();
        const lastReminder = localStorage.getItem(STORAGE_STREAK_REMINDER);
        if (streak > 0 && !isToday(lastDate) && lastReminder !== today) {
          localStorage.setItem(STORAGE_STREAK_REMINDER, today);
          push({
            type: "streak",
            title: "Don't break your streak!",
            message: `You're at ${streak} day${streak !== 1 ? "s" : ""}. Complete a quick activity today.`,
            tag: "streak",
            action: { label: "Start session", href: "/flashcards" },
          });
        }
      } catch {
        // Offline or not logged in
      }
    };
    const t = setTimeout(run, 2000);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [isAuthenticated, isDashboardRoute, push]);

  // Study reminder — flashcards due for review (once per 6 hours)
  useEffect(() => {
    if (!isAuthenticated || !isDashboardRoute) return;

    let cancelled = false;
    const run = async () => {
      try {
        const last = sessionStorage.getItem(STORAGE_STUDY_REMINDER);
        const now = Date.now();
        if (last && now - parseInt(last, 10) < 6 * 60 * 60 * 1000) return;

        const stats = await getUserStats();
        if (cancelled) return;
        const due = stats?.flashcard_stats?.due_for_review ?? 0;
        if (due > 0) {
          sessionStorage.setItem(STORAGE_STUDY_REMINDER, String(now));
          push({
            type: "assignment",
            title: "Flashcards due",
            message: `${due} card${due !== 1 ? "s" : ""} ready for review.`,
            tag: "study",
            action: { label: "Review now", href: "/flashcards" },
          });
        }
      } catch {
        // Offline
      }
    };
    const t = setTimeout(run, 4000);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [isAuthenticated, isDashboardRoute, push]);

  return null;
}
