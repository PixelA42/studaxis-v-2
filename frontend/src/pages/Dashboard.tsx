/**
 * Dashboard page — welcome header, stats row, feature grid (Chat, Quiz, Flashcards, Panic Mode).
 */

import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";
import { useEffect, useState } from "react";
import { StatCard, FeatureCard, StatusIndicator } from "../components";
import { Icons } from "../components/icons";
import type { UserStats } from "../services/api";
import { getUserStats } from "../services/api";

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
  const navigate = useNavigate();
  const [stats, setStats] = useState<UserStats | null>(null);

  useEffect(() => {
    getUserStats()
      .then(setStats)
      .catch(() => setStats(null));
  }, []);

  const name = profile.profile_name || "Student";
  const streak = stats?.streak?.current ?? 0;
  const streakLongest = stats?.streak?.longest ?? 0;
  const quizAttempted = stats?.quiz_stats?.total_attempted ?? 0;
  const quizCorrect = stats?.quiz_stats?.total_correct ?? 0;
  const quizAvg = quizAttempted > 0 ? Math.round((quizCorrect / quizAttempted) * 100) : 0;
  const flashcardsMastered = stats?.flashcard_stats?.mastered ?? 0;
  const flashcardsDue = stats?.flashcard_stats?.due_for_review ?? 0;
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

  return (
    <div className="space-y-6">
      <div className="ambient-glow" aria-hidden />
      <header className="glass-panel rounded-xl border border-glass-border p-5 flex flex-wrap items-center justify-between gap-4 shadow-soft">
        <div className="flex items-center gap-4">
          <div
            className="w-12 h-12 rounded-xl bg-pastel-blue/60 border border-pastel-blue/50 flex items-center justify-center text-heading-dark font-bold"
            aria-hidden
          >
            {initials}
          </div>
          <div>
            <h1 className="text-xl font-extrabold text-heading-dark">
              Welcome back, <span className="text-pastel-pink">{name}</span>
            </h1>
            <p className="text-sm text-primary/60">Personal Mastery - AI Tutor ready</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="flex items-center gap-1.5 text-sm font-medium text-primary/80">
            {Icons.streak} {streak} day{streak !== 1 ? "s" : ""}
          </span>
          <span className="px-2.5 py-1 rounded-lg border border-glass-border text-xs font-medium text-primary/70">
            {modeLabel}
          </span>
          <StatusIndicator status={connectivityStatus} />
          <button
            type="button"
            onClick={toggleTheme}
            className="px-3 py-1.5 rounded-lg border border-glass-border text-xs font-medium text-primary/70 hover:bg-surface-light transition-colors"
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {theme === "dark" ? <>{Icons.sun} Light</> : <>{Icons.moon} Dark</>}
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
        >
          <Link
            to="/chat"
            className="inline-block mt-2 px-4 py-2 rounded-xl bg-accent-blue/20 text-accent-blue font-medium text-sm hover:bg-accent-blue/30 transition-colors"
          >
            Open Chat
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
            className="inline-block mt-2 px-4 py-2 rounded-xl bg-accent-blue/20 text-accent-blue font-medium text-sm hover:bg-accent-blue/30 transition-colors"
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
          pastelBg="pink"
        >
          <Link
            to="/flashcards"
            className="inline-block mt-2 px-4 py-2 rounded-xl bg-accent-blue/20 text-accent-blue font-medium text-sm hover:bg-accent-blue/30 transition-colors"
          >
            Review
          </Link>
        </FeatureCard>
        <FeatureCard
          icon={Icons.panic}
          iconColor="red"
          title="Panic Mode"
          description="Distraction-free exam simulator with a timer. AI assistance hidden until submission."
          meta="Timed - AI auto-graded - Full-screen"
          variant="panic"
          pastelBg="pink"
        >
          <Link
            to="/panic-mode"
            className="inline-block mt-2 px-4 py-2 rounded-xl bg-red-500/20 text-red-400 font-medium text-sm hover:bg-red-500/30 transition-colors"
          >
            Enter Panic Mode
          </Link>
        </FeatureCard>
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-glass-border">
        <div className="flex items-center gap-3">
          <StatusIndicator status={connectivityStatus} />
          <span className="text-xs text-primary/50">Last sync: {lastSyncLabel}</span>
        </div>
        <div className="flex gap-3">
          <Link
            to="/settings"
            className="px-4 py-2 rounded-xl border border-glass-border text-primary/80 text-sm font-medium hover:bg-surface-light"
          >
            Settings
          </Link>
          <button
            type="button"
            onClick={() => {
              logout();
              navigate("/", { replace: true });
            }}
            className="px-4 py-2 rounded-xl border border-glass-border text-primary/80 text-sm font-medium hover:bg-surface-light"
          >
            Logout
          </button>
        </div>
      </footer>
    </div>
  );
}
