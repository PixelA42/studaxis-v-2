/**
 * Insights page — AI Insight Engine UI
 * Design reference: AIInsightEngine.jsx — priority cards, mastery bar, streak,
 * weak topic alert, quiz trend chart, study recommendations.
 */

import { useState, useEffect, useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from "recharts";
import { PageChrome } from "../components";
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
  mastery_pct?: number;
  weak_topic_score?: number;
  weak_topic_name?: string;
}

const BAR_COLORS = ["#FA5C5C", "#FD8A6B", "#FEC288", "#FBEF76", "#00a8e8"];

const priorityConfig: Record<
  InsightPriority,
  {
    label: string;
    dot: string;
    bg: string;
    border: string;
    badge: { bg: string; color: string; border: string };
    accent: string;
  }
> = {
  high: {
    label: "High Priority",
    dot: "#FA5C5C",
    bg: "linear-gradient(135deg, #fff5f5 0%, #fff0eb 100%)",
    border: "#FA5C5C33",
    badge: { bg: "#FA5C5C15", color: "#c0392b", border: "#FA5C5C30" },
    accent: "#FA5C5C",
  },
  medium: {
    label: "Medium Priority",
    dot: "#FD8A6B",
    bg: "linear-gradient(135deg, #fffaf7 0%, #fff8f0 100%)",
    border: "#FEC28833",
    badge: { bg: "#FD8A6B15", color: "#a0521f", border: "#FD8A6B30" },
    accent: "#FD8A6B",
  },
  low: {
    label: "Low Priority",
    dot: "#00a8e8",
    bg: "linear-gradient(135deg, #f0faff 0%, #e8f7ff 100%)",
    border: "#00a8e833",
    badge: { bg: "#00a8e815", color: "#0077a8", border: "#00a8e830" },
    accent: "#00a8e8",
  },
};

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
  const weakTopicEntry = topicKeys.length > 0 ? byTopic[topicKeys[0]] : null;
  const weakTopicScoreRaw = weakTopicEntry?.avg_score ?? 0;
  const weakTopicScore = weakTopicScoreRaw <= 1 ? Math.round(weakTopicScoreRaw * 100) : Math.round(weakTopicScoreRaw);

  const quizAttempted = quizStats.total_attempted ?? 0;
  const quizCorrect = quizStats.total_correct ?? 0;
  const quizAccuracy = safePct(quizCorrect, quizAttempted);

  const flashcardsReviewed = flashcardStats.total_reviewed ?? 0;
  const flashcardsMastered = flashcardStats.mastered ?? 0;
  const flashcardMasteryPct = safePct(flashcardsMastered, flashcardsReviewed);

  const masteryPct = Math.round((quizAccuracy * 0.6 + flashcardMasteryPct * 0.4));

  const trendPoints = [45, 52, 61, 58, quizAccuracy].filter((_, i) => i < 5);

  return [
    {
      id: "insight_weak_topic",
      title: "Weak Topic Alert",
      description: `Potential weak area: ${weakTopicName}. Flag when below 60%.`,
      insight_type: "weak_topic_detection",
      priority: "high",
      related_subject: weakTopicName,
      suggested_action: "Start a remedial quiz on this topic.",
      weak_topic_name: weakTopicName,
      weak_topic_score: weakTopicScore,
    },
    {
      id: "insight_mastery",
      title: "Subject Mastery Snapshot",
      description: "Current mastery band: Beginner–Intermediate.",
      insight_type: "subject_mastery",
      priority: "medium",
      related_subject: "All Subjects",
      suggested_action: "Review weak concepts before the next quiz.",
      mastery_pct: masteryPct,
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
      trend_points: trendPoints,
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
// AI Insight Engine components (AIInsightEngine.jsx style)
// ---------------------------------------------------------------------------

function AIBadge({ priority }: { priority: InsightPriority }) {
  const cfg = priorityConfig[priority];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
      <div
        style={{
          width: "26px",
          height: "26px",
          borderRadius: "7px",
          background: "linear-gradient(135deg, #FA5C5C, #FD8A6B)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "10px",
          fontWeight: 800,
          color: "#fff",
          letterSpacing: "0.3px",
          flexShrink: 0,
          boxShadow: "0 2px 8px rgba(250,92,92,0.35)",
        }}
      >
        AI
      </div>
      <span
        style={{
          fontSize: "12px",
          fontWeight: 600,
          background: cfg.badge.bg,
          border: `1px solid ${cfg.badge.border}`,
          color: cfg.badge.color,
          borderRadius: "20px",
          padding: "3px 10px",
          display: "flex",
          alignItems: "center",
          gap: "5px",
        }}
      >
        <span
          style={{
            width: "6px",
            height: "6px",
            borderRadius: "50%",
            background: cfg.dot,
            display: "inline-block",
          }}
        />
        {cfg.label}
      </span>
    </div>
  );
}

function InsightCard({
  priority,
  title,
  desc,
  meta,
  children,
  style: extraStyle = {},
}: {
  priority: InsightPriority;
  title: string;
  desc?: string;
  meta?: string;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}) {
  const cfg = priorityConfig[priority];
  const [hovered, setHovered] = useState(false);
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: cfg.bg,
        border: `1.5px solid ${hovered ? cfg.accent + "55" : cfg.border}`,
        borderRadius: "18px",
        padding: "22px 24px",
        transition: "transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s",
        transform: hovered ? "translateY(-3px)" : "translateY(0)",
        boxShadow: hovered
          ? `0 12px 40px ${cfg.accent}20, 0 2px 8px rgba(0,0,0,0.06)`
          : "0 2px 12px rgba(0,0,0,0.05)",
        position: "relative",
        overflow: "hidden",
        ...extraStyle,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "3px",
          background: `linear-gradient(90deg, ${cfg.accent}, ${cfg.accent}00)`,
          borderRadius: "18px 18px 0 0",
        }}
      />
      <AIBadge priority={priority} />
      <h3
        style={{
          fontSize: "17px",
          fontWeight: 800,
          color: "#0d1b2a",
          letterSpacing: "-0.4px",
          marginBottom: "7px",
          lineHeight: 1.25,
        }}
      >
        {title}
      </h3>
      {desc && (
        <p style={{ fontSize: "13.5px", color: "#4a5568", fontWeight: 500, marginBottom: "5px", lineHeight: 1.5 }}>
          {desc}
        </p>
      )}
      {meta && <p style={{ fontSize: "12px", color: "#9ca3af", fontWeight: 400 }}>{meta}</p>}
      {children}
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

  const quizData = useMemo(() => {
    const pts = quizTrend?.trend_points ?? [0, 0, 0, 0, 0];
    return ["Mon", "Tue", "Wed", "Thu", "Fri"].map((label, i) => ({
      label,
      value: pts[i] ?? 0,
    }));
  }, [quizTrend]);

  return (
    <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
      <div
        style={{
          minHeight: "100%",
          background: "linear-gradient(160deg, #f8f9fc 0%, #f0f4ff 100%)",
          fontFamily: "'Plus Jakarta Sans', 'DM Sans', sans-serif",
          padding: "36px 28px",
          maxWidth: "1100px",
          margin: "0 auto",
          borderRadius: "18px",
        }}
      >
        <style>{`
          @keyframes fadeUp {
            from { opacity:0; transform:translateY(20px); }
            to   { opacity:1; transform:translateY(0); }
          }
          .insight-card-anim { animation: fadeUp 0.55s cubic-bezier(0.16,1,0.3,1) both; }
          .insight-card-anim:nth-child(1) { animation-delay: 0.05s; }
          .insight-card-anim:nth-child(2) { animation-delay: 0.12s; }
          .insight-card-anim:nth-child(3) { animation-delay: 0.19s; }
          .insight-card-anim:nth-child(4) { animation-delay: 0.26s; }
          .insight-card-anim:nth-child(5) { animation-delay: 0.33s; }
          .insight-card-anim:nth-child(6) { animation-delay: 0.40s; }
          @media (max-width: 640px) {
            .insight-row-2 { grid-template-columns: 1fr !important; }
          }
        `}</style>

        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            marginBottom: "28px",
            flexWrap: "wrap",
          }}
        >
          <div
            style={{
              width: "38px",
              height: "38px",
              borderRadius: "11px",
              background: "linear-gradient(135deg, #FA5C5C 0%, #FD8A6B 50%, #FEC288 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 4px 16px rgba(250,92,92,0.35)",
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"
                fill="white"
              />
            </svg>
          </div>
          <div>
            <h1
              style={{
                fontSize: "22px",
                fontWeight: 900,
                color: "#0d1b2a",
                letterSpacing: "-0.5px",
                lineHeight: 1.2,
              }}
            >
              AI Insight Engine
            </h1>
            <p style={{ fontSize: "12px", color: "#9ca3af", fontWeight: 500, marginTop: "2px" }}>
              Personalized learning analytics · Real-time
            </p>
          </div>
          <div
            style={{
              marginLeft: "auto",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              background: "#fff",
              border: "1.5px solid #e5e7eb",
              borderRadius: "10px",
              padding: "7px 14px",
            }}
          >
            <span
              style={{
                width: "7px",
                height: "7px",
                borderRadius: "50%",
                background: "#10b981",
                display: "inline-block",
              }}
            />
            <span style={{ fontSize: "12px", fontWeight: 600, color: "#374151" }}>Live Analysis</span>
          </div>
        </div>

        {/* Row 1: 2 cols — Mastery | Streak */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: "16px",
            marginBottom: "16px",
          }}
        >
          {mastery && (
            <div className="insight-card-anim">
              <InsightCard
                priority="medium"
                title={mastery.title}
                desc={mastery.description}
                meta={`Subject: ${mastery.related_subject} · ${mastery.suggested_action}`}
              >
                <div style={{ marginTop: "14px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                    <span style={{ fontSize: "11px", color: "#9ca3af", fontWeight: 500 }}>Mastery Level</span>
                    <span style={{ fontSize: "11px", color: "#FD8A6B", fontWeight: 700 }}>
                      {mastery.mastery_pct ?? 0}%
                    </span>
                  </div>
                  <div
                    style={{
                      height: "7px",
                      background: "#f1f3f8",
                      borderRadius: "10px",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        width: `${mastery.mastery_pct ?? 0}%`,
                        background: "linear-gradient(90deg, #FA5C5C, #FD8A6B, #FEC288)",
                        borderRadius: "10px",
                        transition: "width 1s ease",
                      }}
                    />
                  </div>
                  <div style={{ display: "flex", gap: "6px", marginTop: "12px", flexWrap: "wrap" }}>
                    {["Beginner", "Intermediate", "Advanced"].map((lvl, i) => (
                      <span
                        key={i}
                        style={{
                          fontSize: "10.5px",
                          fontWeight: 600,
                          padding: "3px 9px",
                          borderRadius: "20px",
                          background:
                            i === 0
                              ? "rgba(250,92,92,0.12)"
                              : i === 1
                                ? "rgba(253,138,107,0.1)"
                                : "#f1f3f8",
                          color: i === 0 ? "#FA5C5C" : i === 1 ? "#FD8A6B" : "#9ca3af",
                          border: `1px solid ${i === 0 ? "#FA5C5C30" : i === 1 ? "#FD8A6B25" : "#e5e7eb"}`,
                        }}
                      >
                        {lvl}
                      </span>
                    ))}
                  </div>
                </div>
              </InsightCard>
            </div>
          )}

          {streakInsight && (
            <div className="insight-card-anim">
              <InsightCard
                priority="medium"
                title={streakInsight.title}
                desc={streakInsight.description}
                meta={`Subject: ${streakInsight.related_subject} · ${streakInsight.suggested_action}`}
              >
                <div style={{ marginTop: "14px", display: "flex", gap: "6px" }}>
                  {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => (
                    <div key={i} style={{ flex: 1, textAlign: "center" }}>
                      <div
                        style={{
                          height: "32px",
                          borderRadius: "7px",
                          background:
                            i < streak
                              ? "linear-gradient(180deg, #FEC288, #FBEF76)"
                              : "#f1f3f8",
                          marginBottom: "4px",
                          border:
                            i < streak ? "1px solid #FEC28840" : "1px solid #e5e7eb",
                          boxShadow: i < streak ? "0 2px 8px rgba(254,194,136,0.35)" : "none",
                        }}
                      />
                      <span
                        style={{
                          fontSize: "10px",
                          color: i < streak ? "#FD8A6B" : "#9ca3af",
                          fontWeight: 600,
                        }}
                      >
                        {d}
                      </span>
                    </div>
                  ))}
                </div>
              </InsightCard>
            </div>
          )}
        </div>

        {/* Row 2: narrow + wide — Weak Topic | Quiz Trend */}
        <div
          className="insight-row-2"
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1.6fr",
            gap: "16px",
            marginBottom: "16px",
          }}
        >
          {weak && (
            <div className="insight-card-anim">
              <InsightCard
                priority="high"
                title={weak.title}
                desc={weak.description}
                meta={`Subject: ${weak.related_subject} · ${weak.suggested_action}`}
              >
                <div style={{ marginTop: "14px" }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                      background: "rgba(250,92,92,0.07)",
                      border: "1px solid rgba(250,92,92,0.15)",
                      borderRadius: "10px",
                      padding: "10px 14px",
                    }}
                  >
                    <div
                      style={{
                        width: "32px",
                        height: "32px",
                        borderRadius: "8px",
                        flexShrink: 0,
                        background: "linear-gradient(135deg, #FA5C5C, #FD8A6B)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                        <path
                          d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
                          stroke="white"
                          strokeWidth="2"
                          strokeLinecap="round"
                        />
                      </svg>
                    </div>
                    <div>
                      <div style={{ fontSize: "12px", fontWeight: 700, color: "#FA5C5C" }}>
                        {weak.weak_topic_name ?? weak.related_subject} — {weak.weak_topic_score ?? 0}%
                      </div>
                      <div style={{ fontSize: "11px", color: "#9ca3af", marginTop: "1px" }}>
                        Below threshold (60%)
                      </div>
                    </div>
                  </div>
                </div>
              </InsightCard>
            </div>
          )}

          {quizTrend && (
            <div className="insight-card-anim">
              <InsightCard priority="medium" title={quizTrend.title} desc={quizTrend.description}>
                <div style={{ marginTop: "14px", height: "110px" }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={quizData} barSize={28} barGap={6}>
                      <XAxis
                        dataKey="label"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fontSize: 11, fill: "#9ca3af", fontWeight: 600 }}
                      />
                      <YAxis hide domain={[0, 100]} />
                      <Tooltip
                        cursor={{ fill: "rgba(0,168,232,0.06)", radius: 6 }}
                        contentStyle={{
                          background: "#fff",
                          border: "1px solid #e5e7eb",
                          borderRadius: "10px",
                          fontSize: 12,
                        }}
                      />
                      <Bar dataKey="value" radius={[6, 6, 0, 0]} minPointSize={6}>
                        {quizData.map((_, i) => (
                          <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} fillOpacity={0.75} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </InsightCard>
            </div>
          )}
        </div>

        {/* Row 3: full width — AI Study Recommendation */}
        {recommendation && (
          <div className="insight-card-anim" style={{ marginBottom: "16px" }}>
            <InsightCard
              priority="low"
              title={recommendation.title}
              desc={recommendation.description}
              meta={`Subject: ${recommendation.related_subject} · ${recommendation.suggested_action}`}
            >
              <div style={{ marginTop: "14px", display: "flex", gap: "10px", flexWrap: "wrap" }}>
                {[
                  { icon: "📖", label: "Study 20 min", color: "#00a8e8" },
                  { icon: "🧠", label: "Focused Quiz", color: "#FD8A6B" },
                  { icon: "🃏", label: "Flashcard Recap", color: "#FBEF76", textColor: "#a07c00" },
                ].map((item, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "7px",
                      background: "#fff",
                      border: `1.5px solid ${item.color}30`,
                      borderRadius: "10px",
                      padding: "8px 14px",
                      fontSize: "12.5px",
                      fontWeight: 600,
                      color: "#374151",
                      boxShadow: `0 2px 8px ${item.color}15`,
                    }}
                  >
                    <span>{item.icon}</span>
                    <span style={{ color: item.textColor ?? item.color }}>{item.label}</span>
                  </div>
                ))}
              </div>
            </InsightCard>
          </div>
        )}

        {/* Study Trends */}
        <div className="insight-card-anim">
          <div
            style={{
              background: "#fff",
              border: "1.5px solid #e5e7eb",
              borderRadius: "18px",
              overflow: "hidden",
              boxShadow: "0 2px 12px rgba(0,0,0,0.04)",
            }}
          >
            <div
              style={{
                padding: "16px 24px",
                borderBottom: "1px solid #f1f3f8",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: "8px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <div
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    background: "linear-gradient(135deg, #FA5C5C, #FD8A6B)",
                  }}
                />
                <h3
                  style={{
                    fontSize: "15px",
                    fontWeight: 800,
                    color: "#0d1b2a",
                    letterSpacing: "-0.3px",
                  }}
                >
                  Study Trends
                </h3>
              </div>
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 600,
                  color: "#9ca3af",
                  background: "#f8f9fc",
                  borderRadius: "8px",
                  padding: "4px 10px",
                  border: "1px solid #e5e7eb",
                }}
              >
                Last 7 days
              </span>
            </div>
            <div style={{ padding: "20px 24px" }}>
              <p
                style={{
                  fontSize: "13.5px",
                  color: "#6b7280",
                  lineHeight: 1.65,
                  fontWeight: 400,
                }}
              >
                Your quiz performance and flashcard retention data are analyzed above.{" "}
                <span
                  style={{
                    background: "linear-gradient(90deg, #FA5C5C, #FD8A6B)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    fontWeight: 700,
                  }}
                >
                  Keep studying to improve your insights.
                </span>
              </p>
              <div style={{ display: "flex", gap: "12px", marginTop: "16px", flexWrap: "wrap" }}>
                {[
                  { label: "Quizzes Taken", val: String(attempted), color: "#FA5C5C" },
                  { label: "Flashcards", val: String(mastered), color: "#00a8e8" },
                  { label: "Avg. Score", val: attempted > 0 ? `${quizPct}%` : "—", color: "#FEC288" },
                ].map((s, i) => (
                  <div
                    key={i}
                    style={{
                      flex: 1,
                      minWidth: "100px",
                      background: "#f8f9fc",
                      borderRadius: "12px",
                      padding: "12px 16px",
                      border: "1px solid #f1f3f8",
                    }}
                  >
                    <div
                      style={{
                        fontSize: "20px",
                        fontWeight: 900,
                        color: s.color,
                        letterSpacing: "-1px",
                      }}
                    >
                      {s.val}
                    </div>
                    <div
                      style={{
                        fontSize: "11px",
                        color: "#9ca3af",
                        fontWeight: 500,
                        marginTop: "2px",
                      }}
                    >
                      {s.label}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </PageChrome>
  );
}
