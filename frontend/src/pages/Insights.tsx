/**
 * Insights page — stats and AI-generated insight cards from user_stats.
 */

import { useState, useEffect } from "react";
import { PageChrome, GlassCard, StatCard } from "../components";
import { getUserStats } from "../services/api";
import type { UserStats } from "../services/api";

export function InsightsPage() {
  const [stats, setStats] = useState<UserStats | null>(null);

  useEffect(() => {
    getUserStats().then(setStats).catch(() => setStats(null));
  }, []);

  const streak = stats?.streak?.current ?? 0;
  const quizStats = stats?.quiz_stats;
  const attempted = quizStats?.total_attempted ?? 0;
  const correct = quizStats?.total_correct ?? 0;
  const quizPct = attempted > 0 ? Math.round((correct / attempted) * 100) : 0;
  const fcStats = stats?.flashcard_stats;
  const mastered = fcStats?.mastered ?? 0;
  const byTopic = quizStats?.by_topic ?? {};
  const firstTopic = typeof byTopic === "object" && Object.keys(byTopic).length > 0
    ? Object.keys(byTopic)[0]
    : null;

  return (
    <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold text-primary">Learning Insights</h2>
          <p className="text-primary/80 mt-1">AI-powered analysis of your study patterns and progress.</p>
        </div>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard
            label="Current Streak"
            value={String(streak)}
            icon="🔥"
          />
          <StatCard
            label="Quiz Average"
            value={`${quizPct}%`}
            icon="📊"
          />
          <StatCard
            label="Cards Mastered"
            value={String(mastered)}
            icon="🃏"
          />
          <StatCard
            label="Quizzes Taken"
            value={String(attempted)}
            icon="📝"
          />
        </div>

        <GlassCard title="AI-Generated Insights">
          <div className="space-y-4">
            {firstTopic ? (
              <div className="p-4 rounded-xl border border-glass-border bg-surface-light/50">
                <span className="text-xs font-semibold text-primary/60 uppercase tracking-wide">Weak Topic Alert</span>
                <p className="text-primary mt-1">
                  Potential weak area: <strong>{firstTopic}</strong>. Complete more quizzes and reviews to improve.
                </p>
              </div>
            ) : (
              <p className="text-primary/80">
                Complete quizzes and flashcard reviews to see weak-topic and trend insights here.
              </p>
            )}
          </div>
        </GlassCard>

        <GlassCard title="Study Trends">
          {attempted === 0 ? (
            <p className="text-primary/80">
              Complete some quizzes and flashcard reviews to see your learning trends here. More data = better insights.
            </p>
          ) : (
            <p className="text-primary/80">
              Your quiz performance and flashcard retention data will be analyzed here to show progress over time.
            </p>
          )}
        </GlassCard>
      </div>
    </PageChrome>
  );
}
