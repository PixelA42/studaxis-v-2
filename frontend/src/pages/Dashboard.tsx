/**
 * Dashboard page — welcome header, stats row, feature grid (Chat, Quiz, Flashcards, Panic Mode).
 * Loads real data from getUserStats, getSyncStatus, getFlashcardsDue, getInsights.
 * Redirects to /onboarding when profile.profile_name is missing.
 */

import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";
import { useNotification } from "../contexts/NotificationContext";
import { useEffect, useState } from "react";
import { StatCard, FeatureCard, StatusIndicator, SkeletonCard, Skeleton } from "../components";
import { Icons } from "../components/icons";
import type { UserStats, InsightItem } from "../services/api";
import {
  getUserStats,
  getSyncStatus,
  getFlashcardsDue,
  getInsights,
} from "../services/api";

/** Flame icon for streak badge — Studaxis accent-coral */
const FlameIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" className="flex-shrink-0">
    <path
      d="M12 2C12 2 8 6.5 8 10.5C8 12.985 9.79 15 12 15C14.21 15 16 12.985 16 10.5C16 9.2 15.3 8.1 14.5 7.2C14.5 7.2 14 9 12.5 9C11.5 9 11 8 11 8C11 8 12 5.5 12 2Z"
      fill="#FD8A6B"
    />
    <path
      d="M12 13C10.343 13 9 14.343 9 16C9 18.5 10.5 20.5 12 22C13.5 20.5 15 18.5 15 16C15 14.343 13.657 13 12 13Z"
      fill="#FEC288"
    />
  </svg>
);

function formatLastSync(iso: string | null | undefined): string {
  if (!iso) return "Never synced";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return "Never synced";
  }
}

export function DashboardPage() {
  const { profile, connectivityStatus, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { push } = useNotification();
  const navigate = useNavigate();
  const [stats, setStats] = useState<UserStats | null>(null);
  const [syncPending, setSyncPending] = useState(false);
  const [flashcardsDueCount, setFlashcardsDueCount] = useState<number>(0);
  const [insights, setInsights] = useState<InsightItem[]>([]);
  const [loadingStats, setLoadingStats] = useState(true);
  const [loadingSync, setLoadingSync] = useState(true);
  const [loadingFlashcards, setLoadingFlashcards] = useState(true);
  const [loadingInsights, setLoadingInsights] = useState(true);

  useEffect(() => {
    setLoadingStats(true);
    getUserStats()
      .then(setStats)
      .catch((e) => {
        setStats(null);
        push({
          type: "error",
          title: "Failed to load stats",
          message: connectivityStatus === "offline"
            ? "You're offline. Stats will load when back online."
            : (e instanceof Error ? e.message : "Please try again."),
        });
      })
      .finally(() => setLoadingStats(false));
  }, [connectivityStatus, push]);

  useEffect(() => {
    setLoadingSync(true);
    getSyncStatus()
      .then((s) => setSyncPending((s.queue?.total ?? 0) > 0))
      .catch(() => {
        setSyncPending(false);
        push({
          type: "warning",
          title: "Sync status unavailable",
          message: connectivityStatus === "offline" ? "Connect to check sync status." : "Could not check sync status.",
        });
      })
      .finally(() => setLoadingSync(false));
  }, [connectivityStatus, push]);

  useEffect(() => {
    setLoadingFlashcards(true);
    getFlashcardsDue()
      .then((r) => setFlashcardsDueCount(r?.cards?.length ?? 0))
      .catch(() => setFlashcardsDueCount(0))
      .finally(() => setLoadingFlashcards(false));
  }, []);

  useEffect(() => {
    setLoadingInsights(true);
    getInsights()
      .then((r) => setInsights(r?.insights ?? []))
      .catch(() => setInsights([]))
      .finally(() => setLoadingInsights(false));
  }, []);

  const statsLoading = loadingStats;

  if (!profile.profile_name) {
    navigate("/onboarding", { replace: true });
    return null;
  }

  const name = profile.profile_name;
  const streak = stats?.streak?.current ?? 0;
  const streakLongest = stats?.streak?.longest ?? 0;
  const quizAttempted = stats?.quiz_stats?.total_attempted ?? 0;
  const quizCorrect = stats?.quiz_stats?.total_correct ?? 0;
  const quizAvg = quizAttempted > 0 ? Math.round((quizCorrect / quizAttempted) * 100) : 0;
  const flashcardsMastered = stats?.flashcard_stats?.mastered ?? 0;
  const flashcardsDue = Math.max(
    stats?.flashcard_stats?.due_for_review ?? 0,
    flashcardsDueCount
  );
  const difficulty = stats?.preferences?.difficulty_level ?? "Beginner";
  const modeLabel = profile.profile_mode === "solo" || !profile.profile_mode ? "Solo Mode" : "Class Linked";
  const lastSyncLabel = formatLastSync(stats?.last_sync_timestamp);

  const streakMilestones = [7, 30, 100];
  let streakProgressPct = 100;
  let streakMilestoneLabel: string | undefined;
  for (const m of streakMilestones) {
    if (streak < m) {
      streakProgressPct = Math.min(100, Math.round((streak / m) * 100));
      streakMilestoneLabel = `${streak}/${m} days to next milestone`;
      break;
    }
  }
  if (streak >= 100) streakMilestoneLabel = "All milestones reached!";

  const initials = name
    .trim()
    .split(/\s+/)
    .map((s) => s[0])
    .join("")
    .toUpperCase()
    .slice(0, 2) || "S";

  const dark = theme === "dark";
  const isOnline = connectivityStatus === "online";

  return (
    <div className="space-y-6">
      <div className="ambient-glow" aria-hidden />
      <header
        className="content-card border border-glass-border overflow-hidden transition-shadow duration-300 hover:shadow-soft"
        style={{
          borderRadius: "20px",
          padding: "0 28px",
          height: "76px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "16px",
        }}
      >
        {/* LEFT: Avatar + Name */}
        <div className="flex items-center gap-[14px] flex-shrink-0">
          <div
            className="w-11 h-11 rounded-[13px] flex items-center justify-center text-white font-bold text-[17px] tracking-tight flex-shrink-0"
            style={{
              background: "linear-gradient(135deg, #00A8E8 0%, #0284c7 100%)",
              boxShadow: "0 3px 10px rgba(0,168,232,0.35)",
            }}
            aria-hidden
          >
            {initials}
          </div>
          <div>
            <h1 className="text-[15px] font-semibold leading-tight tracking-tight text-primary">
              Welcome back,{" "}
              <span className="text-[#FA5C5C] font-bold">{name}</span>
            </h1>
            <p className="text-xs text-muted font-normal mt-0.5 tracking-wide">
              Personal Mastery · AI Tutor ready
            </p>
          </div>
        </div>

        {/* DIVIDER */}
        <div
          className="w-px h-9 flex-shrink-0"
          style={{ background: "var(--glass-border)" }}
        />

        {/* CENTER: Streak badge */}
        <div
          className="flex items-center gap-[7px] rounded-[10px] px-3.5 py-[7px] flex-shrink-0 cursor-default transition-transform duration-150 hover:scale-[1.02]"
          style={{
            background: dark ? "rgba(253,138,107,0.1)" : "rgba(253,138,107,0.07)",
            border: `1px solid ${dark ? "rgba(253,138,107,0.2)" : "rgba(253,138,107,0.15)"}`,
          }}
        >
          <FlameIcon />
          <span className="text-[13.5px] font-semibold text-[#FD8A6B] tracking-tight">
            {streak} day{streak !== 1 ? "s" : ""}
          </span>
        </div>

        {/* DIVIDER */}
        <div
          className="w-px h-9 flex-shrink-0"
          style={{ background: "var(--glass-border)" }}
        />

        {/* RIGHT: Pills + Theme toggle */}
        <div className="flex items-center gap-2.5 flex-shrink-0">
          <span
            className="rounded-[9px] px-3.5 py-[7px] text-[13px] font-medium text-muted transition-all duration-200 hover:-translate-y-px border border-glass-border"
            style={{
              background: dark ? "#252836" : "#f1f3f8",
            }}
          >
            {modeLabel}
          </span>
          <span
            className={`inline-flex items-center gap-1.5 rounded-[9px] px-3 py-[7px] text-[13px] font-medium transition-all duration-200 hover:-translate-y-px ${
              isOnline
                ? syncPending
                  ? "bg-amber-500/10 border border-amber-500/25 text-amber-600 dark:text-amber-400"
                  : dark
                    ? "bg-success/10 border border-success/25 text-success"
                    : "bg-success/10 border border-success/20 text-success"
                : "bg-surface-light border border-glass-border text-muted"
            }`}
          >
            <span
              className={`w-[7px] h-[7px] rounded-full flex-shrink-0 ${
                isOnline ? (syncPending ? "bg-amber-500 animate-pulse" : "bg-success animate-pulse") : "bg-muted"
              }`}
            />
            {isOnline ? (syncPending ? "Pending sync" : "Online") : "Offline"}
          </span>
          <button
            type="button"
            onClick={toggleTheme}
            className="rounded-[9px] w-9 h-[34px] flex items-center justify-center text-muted transition-all duration-200 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-accent-blue/30"
            style={{
              background: dark ? "#252836" : "var(--surface-light)",
              border: "1px solid var(--glass-border)",
            }}
            title={dark ? "Switch to light mode" : "Switch to dark mode"}
            aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
          >
            {dark ? Icons.sun : Icons.moon}
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {statsLoading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          <>
            <StatCard
              icon={Icons.streak}
              iconColor="orange"
              value={String(streak)}
              label="Day Streak"
              sub={`Longest: ${streakLongest} days`}
              progressPct={streakProgressPct}
              progressLabel={streakMilestoneLabel}
              emptyHint={streak === 0 && quizAttempted === 0 && flashcardsMastered === 0 ? "Complete your first session to start your streak" : undefined}
            />
            <StatCard
              icon={Icons.chart}
              iconColor="blue"
              value={`${quizAvg}%`}
              label="Quiz Average"
              sub={`${quizAttempted} attempt${quizAttempted !== 1 ? "s" : ""} total`}
              emptyHint={quizAttempted === 0 ? "Take your first quiz to see your score here" : undefined}
            />
            <StatCard
              icon={Icons.cards}
              iconColor="green"
              value={String(flashcardsMastered)}
              label="Cards Mastered"
              sub={`${flashcardsDue} due for review`}
              emptyHint={flashcardsMastered === 0 ? "Review flashcards to track mastery here" : undefined}
            />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <FeatureCard
          icon={Icons.ai}
          iconColor="blue"
          title="AI Tutor Chat"
          description="Ask questions from your textbooks and get curriculum-grounded answers — fully offline."
          meta="Powered by Llama 3.2 - RAG-grounded"
          variant="ai"
          pastelBg="blue"
          iconOnDark
        >
          <Link
            to="/chat"
            className="inline-block mt-2 px-4 py-2.5 rounded-xl bg-white text-[#0d1b2a] font-semibold text-sm hover:bg-white/90 transition-colors shadow-md border border-white/20"
          >
            AI Chat
          </Link>
        </FeatureCard>
        <FeatureCard
          icon={Icons.quiz}
          iconColor="orange"
          title="Quick Quiz"
          description="Test your knowledge with AI-generated questions. Get instant grading and feedback."
          meta={`${quizAttempted} attempt${quizAttempted !== 1 ? "s" : ""} - ${difficulty}`}
          pastelBg="yellow"
        >
          <Link
            to="/quiz"
            className="inline-block mt-2 px-4 py-2.5 rounded-xl bg-white text-[#0d1b2a] font-semibold text-sm hover:bg-white/90 transition-colors shadow-md border border-white/20"
          >
            Start Quiz
          </Link>
        </FeatureCard>
        <FeatureCard
          icon={Icons.cards}
          iconColor="green"
          title="Flashcards"
          description="Spaced-repetition review. Mark cards Easy or Hard to schedule the next review."
          meta={`${flashcardsDue > 0 ? flashcardsDue + " due" : "All caught up"} - AI-generated`}
          variant="flashcards"
          pastelBg="coral"
        >
          <Link
            to="/flashcards"
            className="inline-block mt-2 px-4 py-2.5 rounded-xl bg-white text-[#0d1b2a] font-semibold text-sm hover:bg-white/90 transition-colors shadow-md border border-white/20"
          >
            Review
          </Link>
        </FeatureCard>
        <FeatureCard
          icon={Icons.panic}
          iconColor="blue"
          title="Panic Mode"
          description="Distraction-free exam simulator with a timer. AI assistance hidden until submission."
          meta="Timed - AI auto-graded - Full-screen"
          variant="panic"
          pastelBg="blue"
          iconOnDark
        >
          <Link
            to="/panic-mode"
            className="inline-block mt-2 px-4 py-2.5 rounded-xl bg-white text-[#0d1b2a] font-semibold text-sm hover:bg-white/90 transition-colors shadow-md border border-white/20"
          >
            Enter Panic Mode
          </Link>
        </FeatureCard>
      </div>

      {/* Widgets: Recent activity, flashcards due, weak topics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Recent activity */}
        <div
          className="content-card border border-glass-border rounded-2xl p-4 transition-shadow hover:shadow-soft"
          style={{ minHeight: 120 }}
        >
          <h3 className="text-sm font-semibold text-heading-dark mb-2 flex items-center gap-2">
            <span aria-hidden>{Icons.chart}</span>
            Recent Activity
          </h3>
          {stats?.chat_history && stats.chat_history.length > 0 ? (
            <ul className="space-y-1.5 text-xs text-muted">
              {stats.chat_history.slice(-3).reverse().map((m, i) => (
                <li key={i} className="truncate">
                  {m.role === "user" ? "You asked" : "AI replied"} — {String(m.content).slice(0, 40)}…
                </li>
              ))}
            </ul>
          ) : quizAttempted > 0 || flashcardsMastered > 0 ? (
            <p className="text-xs text-muted">
              {quizAttempted > 0 ? `Last quiz: ${quizAttempted} attempt${quizAttempted !== 1 ? "s" : ""}` : ""}
              {quizAttempted > 0 && flashcardsMastered > 0 ? " · " : ""}
              {flashcardsMastered > 0 ? `${flashcardsMastered} cards mastered` : ""}
            </p>
          ) : (
            <p className="text-xs text-muted">No recent activity. Start a chat or quiz!</p>
          )}
        </div>

        {/* Flashcards due */}
        <div
          className="content-card border border-glass-border rounded-2xl p-4 transition-shadow hover:shadow-soft"
          style={{ minHeight: 120 }}
        >
          <h3 className="text-sm font-semibold text-heading-dark mb-2 flex items-center gap-2">
            <span aria-hidden>{Icons.cards}</span>
            Flashcards Due
          </h3>
          {loadingFlashcards ? (
            <>
              <Skeleton width="40%" height={28} variant="text" className="mb-2" aria-label="Loading flashcards count" />
              <Skeleton width="70%" height={12} variant="text" aria-label="Loading flashcards sub" />
            </>
          ) : flashcardsDue > 0 ? (
            <>
              <p className="text-2xl font-bold text-accent-blue">{flashcardsDue}</p>
              <p className="text-xs text-muted mt-1">cards ready for review</p>
              <Link
                to="/flashcards"
                className="inline-block mt-2 text-xs font-semibold text-accent-blue hover:underline"
              >
                Review now →
              </Link>
            </>
          ) : (
            <p className="text-xs text-muted">All caught up! Add or generate more cards.</p>
          )}
        </div>

        {/* Weak topics */}
        <div
          className="content-card border border-glass-border rounded-2xl p-4 transition-shadow hover:shadow-soft"
          style={{ minHeight: 120 }}
        >
          <h3 className="text-sm font-semibold text-heading-dark mb-2 flex items-center gap-2">
            <span aria-hidden>{Icons.insights}</span>
            Weak Topics
          </h3>
          {loadingInsights ? (
            <>
              <Skeleton width="60%" height={14} variant="text" className="mb-2" aria-label="Loading weak topics" />
              <Skeleton width="80%" height={14} variant="text" className="mb-1" aria-label="Loading weak topics" />
              <Skeleton width="50%" height={14} variant="text" aria-label="Loading weak topics" />
            </>
          ) : insights.filter((i) => i.insight_type === "weak_topic_detection").length > 0 ? (
            <>
              <ul className="space-y-1.5 text-xs text-muted">
                {insights
                  .filter((i) => i.insight_type === "weak_topic_detection")
                  .slice(0, 2)
                  .map((i) => (
                    <li key={i.id}>
                      {i.weak_topic_name ?? i.title}
                      {i.weak_topic_score != null ? ` (${i.weak_topic_score}%)` : ""}
                    </li>
                  ))}
              </ul>
              <Link to="/insights" className="inline-block mt-2 text-xs font-semibold text-accent-blue hover:underline">
                View insights →
              </Link>
            </>
          ) : quizAttempted > 0 ? (
            <Link to="/insights" className="text-xs font-semibold text-accent-blue hover:underline">
              View full insights →
            </Link>
          ) : (
            <p className="text-xs text-muted">Complete quizzes to see weak topic analysis.</p>
          )}
        </div>
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-glass-border">
        <div className="flex items-center gap-3">
          <StatusIndicator status={connectivityStatus} />
          <span className="text-xs font-medium text-heading-dark/60">Last sync: {lastSyncLabel}</span>
        </div>
        <div className="flex gap-3">
          <Link
            to="/settings"
            className="px-4 py-2 rounded-xl border border-glass-border text-heading-dark font-semibold text-sm hover:bg-surface-light transition-colors"
          >
            Settings
          </Link>
          <button
            type="button"
            onClick={() => {
              logout();
              navigate("/", { replace: true });
            }}
            className="px-4 py-2 rounded-xl border border-glass-border text-heading-dark font-semibold text-sm hover:bg-surface-light transition-colors"
          >
            Logout
          </button>
        </div>
      </footer>
    </div>
  );
}
