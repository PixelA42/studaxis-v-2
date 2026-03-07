/**
 * Quiz page — select question, answer, submit for AI grading; show score and feedback.
 * Phase 6: wired to GET /api/quiz/:id and POST /api/quiz/:id/submit.
 */

import { useState, useEffect } from "react";
import {
  getQuiz,
  postQuizSubmit,
  getStudyRecommendation,
  getUserStats,
} from "../services/api";
import type { QuizItem, QuizSubmitResult } from "../services/api";
import { PageChrome, GlassCard, LoadingSpinner, HardwareStatus } from "../components";

const QUIZ_ID = "quick";
const STUDY_TIME_MINUTES = 15;

export function QuizPage() {
  const [quiz, setQuiz] = useState<{ id: string; title: string; items: QuizItem[] } | null>(null);
  const [loadingQuiz, setLoadingQuiz] = useState(true);
  const [selectedItem, setSelectedItem] = useState<QuizItem | null>(null);
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<QuizSubmitResult | null>(null);
  const [recommendation, setRecommendation] = useState<string | null>(null);
  const [recommendLoading, setRecommendLoading] = useState(false);
  const [difficulty, setDifficulty] = useState("Beginner");

  useEffect(() => {
    getQuiz(QUIZ_ID)
      .then((data) => {
        setQuiz(data);
        if (data.items.length > 0 && !selectedItem) {
          setSelectedItem(data.items[0] ?? null);
        }
      })
      .catch(() => setQuiz(null))
      .finally(() => setLoadingQuiz(false));
  }, []);

  useEffect(() => {
    getUserStats()
      .then((s) => setDifficulty(s?.preferences?.difficulty_level ?? "Beginner"))
      .catch(() => {});
  }, []);

  const handleSubmit = async () => {
    if (!selectedItem) return;
    setSubmitError(null);
    setLastResult(null);
    setRecommendation(null);
    setSubmitting(true);
    try {
      const res = await postQuizSubmit(QUIZ_ID, {
        answers: [{ question_id: selectedItem.id, answer: answer.trim() }],
      });
      const first = res.results[0];
      if (first) setLastResult(first);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Grading failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleGetRecommendation = async () => {
    if (!selectedItem) return;
    setRecommendLoading(true);
    try {
      const res = await getStudyRecommendation({
        topic: selectedItem.topic,
        time_budget_minutes: STUDY_TIME_MINUTES,
        review_mode: "quiz",
        offline_mode: true,
      });
      setRecommendation(res.text);
    } catch {
      setRecommendation("Could not load recommendation.");
    } finally {
      setRecommendLoading(false);
    }
  };

  if (loadingQuiz || !quiz) {
    return (
      <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold text-primary">Quick Quiz</h2>
          <LoadingSpinner
            loading={loadingQuiz}
            message={loadingQuiz ? "Loading quiz..." : "No quiz available."}
          />
        </div>
      </PageChrome>
    );
  }

  const items = quiz.items;
  const hasItems = items.length > 0;

  return (
    <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="text-2xl font-semibold text-primary">{quiz.title}</h2>
          <HardwareStatus modelName="llama3.2" className="text-xs" />
        </div>
        <p className="text-primary/80">
          Grading and recommendations are routed via the AI integration layer.
        </p>
        <div className="flex items-center gap-2 text-sm text-primary/70">
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 ${
              difficulty === "Beginner"
                ? "bg-accent-blue/20 text-accent-blue"
                : "bg-surface-light border border-glass-border text-primary/80"
            }`}
          >
            {difficulty}
          </span>
        </div>

        {!hasItems ? (
          <GlassCard title="No questions">
            <p className="text-primary/80">No quiz items available. Add content to begin grading.</p>
          </GlassCard>
        ) : (
          <GlassCard>
            <div className="space-y-4">
              <div>
                <label
                  htmlFor="quiz-question-select"
                  className="block text-sm font-medium text-primary/90 mb-2"
                >
                  Select question
                </label>
                <select
                  id="quiz-question-select"
                  value={selectedItem?.id ?? ""}
                  onChange={(e) => {
                    const item = items.find((q) => q.id === e.target.value);
                    setSelectedItem(item ?? null);
                    setAnswer("");
                    setLastResult(null);
                    setRecommendation(null);
                  }}
                  className="w-full max-w-xl px-4 py-2 rounded-lg border border-glass-border bg-surface-light text-primary focus:outline-none focus:ring-2 focus:ring-accent-blue focus:border-transparent"
                >
                  {items.map((q) => (
                    <option key={q.id} value={q.id}>
                      {q.topic} — {q.question.slice(0, 60)}
                      {q.question.length > 60 ? "…" : ""}
                    </option>
                  ))}
                </select>
              </div>

              {selectedItem && (
                <>
                  <div>
                    <p className="text-sm font-medium text-primary/90 mb-2">Question</p>
                    <p className="text-primary">{selectedItem.question}</p>
                  </div>
                  <div>
                    <label
                      htmlFor="quiz-answer"
                      className="block text-sm font-medium text-primary/90 mb-2"
                    >
                      Your answer
                    </label>
                    <textarea
                      id="quiz-answer"
                      value={answer}
                      onChange={(e) => setAnswer(e.target.value)}
                      placeholder="Write your answer here..."
                      rows={6}
                      className="w-full px-4 py-3 rounded-lg border border-glass-border bg-surface-light text-primary placeholder:text-primary/50 focus:outline-none focus:ring-2 focus:ring-accent-blue focus:border-transparent resize-y"
                    />
                  </div>

                  {submitError && (
                    <p className="text-sm text-red-400" role="alert">
                      {submitError}
                    </p>
                  )}

                  <LoadingSpinner
                    loading={submitting}
                    message="Grading your response and preparing recommendations..."
                  >
                    <button
                      type="button"
                      onClick={handleSubmit}
                      disabled={submitting}
                      className="px-5 py-2.5 rounded-xl font-medium text-deep bg-accent-blue hover:bg-accent-blue/90 focus:outline-none focus:ring-2 focus:ring-accent-blue focus:ring-offset-2 focus:ring-offset-deep disabled:opacity-60"
                    >
                      Submit for AI Grading
                    </button>
                  </LoadingSpinner>

                  {lastResult && (
                    <div className="space-y-4 pt-4 border-t border-glass-border">
                      <p className="text-lg font-medium text-primary">
                        Score: {lastResult.score != null ? `${lastResult.score}/10` : "—"}
                      </p>
                      {lastResult.feedback && (
                        <div>
                          <h3 className="text-sm font-semibold text-primary mb-2">AI Feedback</h3>
                          <p className="text-sm text-primary/90 whitespace-pre-wrap">
                            {lastResult.feedback}
                          </p>
                        </div>
                      )}
                      {lastResult.error && (
                        <p className="text-sm text-amber-400">{lastResult.error}</p>
                      )}
                      <div>
                        {recommendLoading ? (
                          <LoadingSpinner message="Loading recommendation..." className="inline" />
                        ) : recommendation ? (
                          <>
                            <h3 className="text-sm font-semibold text-primary mb-2">
                              Study Recommendation
                            </h3>
                            <p className="text-sm text-primary/90 whitespace-pre-wrap">
                              {recommendation}
                            </p>
                          </>
                        ) : (
                          <button
                            type="button"
                            onClick={handleGetRecommendation}
                            className="px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary hover:bg-surface-light/80 text-sm font-medium"
                          >
                            Get study recommendation
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </GlassCard>
        )}
      </div>
    </PageChrome>
  );
}
