/**
 * Insights page — replicates Streamlit build_student_insights_from_stats
 * and render_student_insight_bento_grid. AI-generated learning insights.
 */

import { useState, useEffect, useMemo } from "react";
import { PageChrome, GlassCard, StatCard } from "../components";
import { Icons } from "../components/icons";
import { getUserStats } from "../services/api";
import type { UserStats } from "../services/api";

// ---------------------------------------------------------------------------
// Insight types (mirror backend insight_engine_ui.py)
// ---------------------------------------------------------------------------

type InsightType =
  | "weak_topic_detection"
  | "subject_mastery"
  | "daily_streak"
  | "study_recommendation"
  | "quiz_performance_trend"
  | "flashcard_retention";

type InsightPriority = "high" | "medium" | "low";

interface StructuredInsight {
  id: string;
  title: string;
  description: string;
  insight_type: InsightType;
  priority: InsightPriority;
  related_subject: string;
  suggested_action: string;
  trend_points?: number[];
}

function safePct(numerator: number, denominator: number): number {
  if (denominator <= 0) return 0;
  return Math.round((numerator / denominator) * 100);
}

function buildStudentInsightsFromStats(stats: UserStats | null): StructuredInsight[] {
  if (!stats) return [];

  const streakCurrent = stats.streak?.current ?? 0;
  const quizStats = stats.quiz_stats ?? {};
  const flashcardStats = stats.flashcard_stats ?? {};
  const byTopic = quizStats.by_topic ?? {};

  const topicKeys = typeof byTopic === "object" ? Object.keys(byTopic) : [];
  const weakTopicName = topicKeys.length > 0 ? topicKeys[0] : "Not enough data";

  const quizAttempted = quizStats.total_attempted ?? 0;
  const quizCorrect = quizStats.total_correct ?? 0;
  const quizAccuracy = safePct(quizCorrect, quizAttempted);

  const flashcardsReviewed = flashcardStats.total_reviewed ?? 0;
  const flashcardsMastered = flashcardStats.mastered ?? 0;
  const flashcardMasteryPct = safePct(flashcardsMastered, flashcardsReviewed);

  const WEAK_TOPIC_THRESHOLD = "60%";
  const MASTERY_SCORE_RANGE = "Beginner–Intermediate";

  return [
    {
      id: "insight_weak_topic",
      title: "Weak Topic Alert",
      description: `Potential weak area: ${weakTopicName}. Flag when below ${WEAK_TOPIC_THRESHOLD}.`,
      insight_type: "weak_topic_detection",
      priority: "high",
      related_subject: weakTopicName,
      suggested_action: "Start a remedial quiz on this topic.",
    },
    {
      id: "insight_mastery",
      title: "Subject Mastery Snapshot",
      description: `Current mastery band: ${MASTERY_SCORE_RANGE}.`,
      insight_type: "subject_mastery",
      priority: "medium",
      related_subject: "All Subjects",
      suggested_action: "Review weak concepts before the next quiz.",
    },
    {
      id: "insight_streak",
      title: "Daily Learning Streak",
      description: `Current streak is ${streakCurrent} day(s). Keep momentum going.`,
      insight_type: "daily_streak",
      priority: "medium",
      related_subject: "All Subjects",
      suggested_action: "Complete one activity today to continue your streak.",
    },
    {
      id: "insight_quiz_trend",
      title: "Quiz Performance Trend",
      description: `Recent quiz accuracy is ${quizAccuracy}%.`,
      insight_type: "quiz_performance_trend",
      priority: "medium",
      related_subject: "Quiz",
      suggested_action: "Retake a quiz in your weakest subject.",
      trend_points: [45, 52, 61, 58, quizAccuracy],
    },
    {
      id: "insight_flashcard_retention",
      title: "Flashcard Retention",
      description: `Retention proxy from review outcomes: ${flashcardMasteryPct}%.`,
      insight_type: "flashcard_retention",
      priority: "low",
      related_subject: "Flashcards",
      suggested_action: "Review due flashcards before starting new cards.",
      trend_points: [30, 39, 44, 51, flashcardMasteryPct],
    },
    {
      id: "insight_recommendation",
      title: "AI Study Recommendation",
      description: "Next best action based on weak topics and trend signals.",
      insight_type: "study_recommendation",
      priority: "low",
      related_subject: "Recommended",
      suggested_action: "Study 20 minutes + one focused quiz + flashcard recap.",
    },
  ];
}

// ---------------------------------------------------------------------------
// Insight card & trend components
// ---------------------------------------------------------------------------

const priorityClasses: Record<InsightPriority, string> = {
  high: "border-amber-500/40 bg-amber-500/5",
  medium: "border-accent-blue/30 bg-accent-blue/5",
  low: "border-glass-border",
};

function InsightCard({ insight }: { insight: StructuredInsight }) {
  return (
    <div
      className={`rounded-xl border p-4 ${priorityClasses[insight.priority]}`}
      role="region"
      aria-label={insight.title}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-accent-blue/20 text-accent-blue">AI</span>
        <span className="text-xs text-primary/60 capitalize">{insight.priority} priority</span>
      </div>
      <h3 className="text-lg font-semibold text-primary mb-1">{insight.title}</h3>
      <p className="text-sm text-primary/80">{insight.description}</p>
      <p className="text-xs text-primary/50 mt-2">
        Subject: {insight.related_subject} · {insight.suggested_action}
      </p>
    </div>
  );
}

function TrendCard({ insight }: { insight: StructuredInsight }) {
  const points = insight.trend_points ?? [];
  const maxVal = Math.max(...points, 1);

  return (
    <div
      className={`rounded-xl border p-4 ${priorityClasses[insight.priority]}`}
      role="region"
      aria-label={insight.title}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-accent-blue/20 text-accent-blue">AI</span>
        <span className="text-xs text-primary/60 capitalize">{insight.priority} priority</span>
      </div>
      <h3 className="text-lg font-semibold text-primary mb-1">{insight.title}</h3>
      <p className="text-sm text-primary/80 mb-3">{insight.description}</p>
      {points.length > 0 && (
        <div className="flex items-end gap-1 h-16" role="img" aria-label={`Trend: ${points.join(", ")}`}>
          {points.map((p, i) => (
            <div
              key={i}
              className="flex-1 min-w-0 rounded-t bg-accent-blue/40 transition-all"
              style={{ height: `${Math.max(8, (p / maxVal) * 100)}%` }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export function InsightsPage() {
  const [stats, setStats] = useState<UserStats | null>(null);

  useEffect(() => {
    getUserStats().then(setStats).catch(() => setStats(null));
  }, []);

  const insights = useMemo(() => buildStudentInsightsFromStats(stats), [stats]);
  const insightByType = useMemo(() => {
    const m = new Map<InsightType, StructuredInsight>();
    insights.forEach((i) => m.set(i.insight_type, i));
    return m;
  }, [insights]);

  const streak = stats?.streak?.current ?? 0;
  const quizStats = stats?.quiz_stats ?? {};
  const attempted = quizStats.total_attempted ?? 0;
  const correct = quizStats.total_correct ?? 0;
  const quizPct = attempted > 0 ? Math.round((correct / attempted) * 100) : 0;
  const fcStats = stats?.flashcard_stats ?? {};
  const mastered = fcStats.mastered ?? 0;

  const mastery = insightByType.get("subject_mastery");
  const streakInsight = insightByType.get("daily_streak");
  const weak = insightByType.get("weak_topic_detection");
  const quizTrend = insightByType.get("quiz_performance_trend");
  const recommendation = insightByType.get("study_recommendation");

  return (
    <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold text-primary">Learning Insights</h2>
          <p className="text-primary/80 mt-1">AI-powered analysis of your study patterns and progress.</p>
        </div>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard label="Current Streak" value={String(streak)} icon={Icons.streak} iconColor="orange" />
          <StatCard label="Quiz Average" value={`${quizPct}%`} icon={Icons.chart} iconColor="blue" />
          <StatCard label="Cards Mastered" value={String(mastered)} icon={Icons.cards} iconColor="green" />
          <StatCard label="Quizzes Taken" value={String(attempted)} icon={Icons.quiz} iconColor="blue" />
        </div>

        <div>
          <h3 className="text-lg font-semibold text-primary mb-4">AI Insight Engine</h3>
          {/* Bento grid: Row 1 [Mastery | Streak], Row 2 [Weak Topic | Quiz Trend], Row 3 [Recommendation] */}
          <div className="grid gap-4 md:grid-cols-5">
            <div className="md:col-span-3">
              {mastery && <InsightCard insight={mastery} />}
            </div>
            <div className="md:col-span-2">
              {streakInsight && <InsightCard insight={streakInsight} />}
            </div>
            <div className="md:col-span-2">
              {weak && <InsightCard insight={weak} />}
            </div>
            <div className="md:col-span-3">
              {quizTrend && <TrendCard insight={quizTrend} />}
            </div>
            <div className="md:col-span-5">
              {recommendation && <InsightCard insight={recommendation} />}
            </div>
          </div>
        </div>

        <GlassCard title="Study Trends">
          {attempted === 0 ? (
            <p className="text-primary/80">
              Complete some quizzes and flashcard reviews to see your learning trends here. More data = better insights.
            </p>
          ) : (
            <p className="text-primary/80">
              Your quiz performance and flashcard retention data are analyzed above. Keep studying to improve your
              insights.
            </p>
          )}
        </GlassCard>
      </div>
    </PageChrome>
  );
}
