/**
 * Panic Mode — distraction-free timed exam. Loads quiz "panic", timer, submit for AI grading.
 */

import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { getQuiz, postQuizSubmit } from "../services/api";
import type { QuizItem, QuizSubmitResult } from "../services/api";
import { PageChrome, GlassCard, LoadingSpinner } from "../components";

const DURATION_OPTIONS = [15, 30, 60] as const;

function formatTime(secondsLeft: number): string {
  const m = Math.floor(secondsLeft / 60);
  const s = secondsLeft % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function PanicModePage() {
  const navigate = useNavigate();
  const [quiz, setQuiz] = useState<{ id: string; title: string; items: QuizItem[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [started, setStarted] = useState(false);
  const [durationMinutes, setDurationMinutes] = useState(15);
  const [endTimeMs, setEndTimeMs] = useState<number | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [results, setResults] = useState<QuizSubmitResult[]>([]);
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);

  useEffect(() => {
    getQuiz("panic")
      .then(setQuiz)
      .catch(() => setQuiz(null))
      .finally(() => setLoading(false));
  }, []);

  const tick = useCallback(() => {
    if (endTimeMs == null) return;
    const left = Math.max(0, Math.ceil((endTimeMs - Date.now()) / 1000));
    setSecondsLeft(left);
  }, [endTimeMs]);

  useEffect(() => {
    if (endTimeMs == null) return;
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [endTimeMs, tick]);

  const handleStart = () => {
    setStarted(true);
    setEndTimeMs(Date.now() + durationMinutes * 60 * 1000);
    setSecondsLeft(durationMinutes * 60);
    if (quiz) {
      const initial: Record<string, string> = {};
      quiz.items.forEach((q) => (initial[q.id] = ""));
      setAnswers(initial);
    }
  };

  const handleSubmit = async () => {
    if (!quiz) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await postQuizSubmit("panic", {
        answers: quiz.items.map((q) => ({ question_id: q.id, answer: answers[q.id] ?? "" })),
      });
      setResults(res.results);
      setSubmitted(true);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Submit failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRetake = () => {
    setStarted(false);
    setSubmitted(false);
    setEndTimeMs(null);
    setSecondsLeft(null);
    setAnswers({});
    setResults([]);
  };

  if (loading || !quiz) {
    return (
      <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold text-primary">Panic Mode</h2>
          <LoadingSpinner loading={loading} message={loading ? "Loading exam..." : "No exam available."} />
        </div>
      </PageChrome>
    );
  }

  const items = quiz.items;
  const hasItems = items.length > 0;

  if (!hasItems) {
    return (
      <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold text-primary">Panic Mode</h2>
          <GlassCard title="No questions">
            <p className="text-primary/80">No panic mode questions available.</p>
          </GlassCard>
        </div>
      </PageChrome>
    );
  }

  if (!started) {
    return (
      <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
        <div className="space-y-6">
          <h2 className="text-2xl font-semibold text-primary">Panic Mode</h2>
          <p className="text-primary/80">Timed exam simulator. Complete all answers, then submit once for AI grading.</p>
          <GlassCard title="Start Exam">
            <div className="space-y-4">
              <div>
                <label htmlFor="panic-duration" className="block text-sm font-medium text-primary/90 mb-2">
                  Exam duration (minutes)
                </label>
                <select
                  id="panic-duration"
                  value={durationMinutes}
                  onChange={(e) => setDurationMinutes(Number(e.target.value))}
                  className="w-full max-w-xs px-4 py-2 rounded-lg border border-glass-border bg-surface-light text-primary focus:outline-none focus:ring-2 focus:ring-accent-blue"
                >
                  {DURATION_OPTIONS.map((m) => (
                    <option key={m} value={m}>{m} min</option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                onClick={handleStart}
                className="px-5 py-2.5 rounded-xl font-medium text-deep bg-accent-blue hover:bg-accent-blue/90 focus:outline-none focus:ring-2 focus:ring-accent-blue"
              >
                Start Panic Mode Exam
              </button>
            </div>
          </GlassCard>
        </div>
      </PageChrome>
    );
  }

  if (submitted) {
    const avgScore =
      results.length > 0
        ? results.reduce((s, r) => s + (r.score ?? 0), 0) / results.length
        : 0;
    return (
      <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
        <div className="space-y-6">
          <h2 className="text-2xl font-semibold text-primary">Panic Mode — Results</h2>
          <p className="text-primary/80">Average score: {avgScore.toFixed(1)}/10</p>
          <GlassCard title="Question-wise Feedback">
            <div className="space-y-4">
              {results.map((r) => (
                <div key={r.question_id} className="border-b border-glass-border pb-4 last:border-0">
                  <p className="text-primary font-medium">
                    {r.question_id} — Score: {r.score != null ? `${r.score}/10` : "—"}
                  </p>
                  {r.feedback && (
                    <p className="text-sm text-primary/80 mt-2 whitespace-pre-wrap">{r.feedback}</p>
                  )}
                </div>
              ))}
            </div>
          </GlassCard>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleRetake}
              className="px-5 py-2.5 rounded-xl font-medium text-deep bg-accent-blue hover:bg-accent-blue/90"
            >
              Retake Panic Mode
            </button>
            <button
              type="button"
              onClick={() => navigate("/dashboard")}
              className="px-5 py-2.5 rounded-xl border border-glass-border bg-surface-light text-primary hover:bg-surface-light/80 font-medium"
            >
              Return to Dashboard
            </button>
          </div>
        </div>
      </PageChrome>
    );
  }

  return (
    <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="text-2xl font-semibold text-primary">Panic Mode</h2>
          {secondsLeft != null && (
            <div
              className={`text-xl font-mono font-semibold px-4 py-2 rounded-xl border ${
                secondsLeft <= 60 ? "border-amber-500/50 text-amber-400 bg-amber-500/10" : "border-glass-border text-primary"
              }`}
              role="timer"
              aria-live="polite"
            >
              {formatTime(secondsLeft)}
            </div>
          )}
        </div>
        <p className="text-sm text-amber-400/90">
          Distraction-free mode: complete all answers, then submit once for AI grading.
        </p>
        <GlassCard>
          <div className="space-y-6">
            {items.map((q, idx) => (
              <div key={q.id}>
                <p className="text-primary font-medium mb-2">
                  Q{idx + 1}. {q.question}
                </p>
                <textarea
                  value={answers[q.id] ?? ""}
                  onChange={(e) => setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}
                  placeholder="Your answer..."
                  rows={4}
                  className="w-full px-4 py-3 rounded-lg border border-glass-border bg-surface-light text-primary placeholder:text-primary/50 focus:outline-none focus:ring-2 focus:ring-accent-blue resize-y"
                />
              </div>
            ))}
            {submitError && <p className="text-sm text-red-400">{submitError}</p>}
            <LoadingSpinner loading={submitting} message="Submitting for grading...">
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitting}
                className="px-5 py-2.5 rounded-xl font-medium text-deep bg-accent-blue hover:bg-accent-blue/90 disabled:opacity-60"
              >
                Submit Exam
              </button>
            </LoadingSpinner>
          </div>
        </GlassCard>
      </div>
    </PageChrome>
  );
}
