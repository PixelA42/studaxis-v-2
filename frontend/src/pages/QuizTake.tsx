/**
 * Quiz taking page — /quiz/:id
 * MCQ: options A–D, Prev/Next, Submit on last.
 * Open Ended: textarea, Check Answer per question, Next.
 * Results: score, per-question breakdown, Retry/Save flashcards/Back.
 */

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  getQuiz,
  postQuizSubmit,
  postQuizGradeAnswer,
  postFlashcardsFromQuiz,
  postAssignmentComplete,
} from "../services/api";
import {
  saveQuizHistoryToStorage,
  loadAssignmentsFromStorage,
  saveAssignmentsToStorage,
  loadQuizHistoryFromStorage,
} from "../services/storage";
import { PageChrome } from "../components";
import type { QuizItem } from "../services/api";
import "./QuizTake.css";

interface QuizData {
  id: string;
  title: string;
  items: QuizItem[];
  subject?: string;
  difficulty?: string;
  question_type?: string;
}

export function QuizTakePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [quiz, setQuiz] = useState<QuizData | null>(null);
  const [loading, setLoading] = useState(true);
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{
    score: number;
    max_score: number;
    percent: number;
    results: Array<{ question_id: string; correct: boolean; score: number; correct_answer: string; explanation: string }>;
  } | null>(null);
  const [openEndedFeedback, setOpenEndedFeedback] = useState<Record<string, { score: number; feedback: string }>>({});

  useEffect(() => {
    if (!id) return;
    getQuiz(id)
      .then((data) => setQuiz(data as QuizData))
      .catch(() => setQuiz(null))
      .finally(() => setLoading(false));
  }, [id]);

  const items = quiz?.items ?? [];
  const current = items[idx];
  const isMcq = (quiz?.question_type || "mcq") === "mcq";
  const allAnswered = items.every((it) => (answers[it.id] ?? "").trim().length > 0);
  const isLast = idx === items.length - 1;

  const handleMcqSelect = (optIdx: number) => {
    if (!current) return;
    setAnswers((a) => ({ ...a, [current.id]: String(optIdx) }));
  };

  const handleSubmit = async () => {
    if (!quiz || !allAnswered || submitting) return;
    setSubmitting(true);
    try {
      const submission = items.map((it) => ({
        question_id: it.id,
        user_answer: answers[it.id] ?? "",
      }));
      const res = await postQuizSubmit(quiz.id, {
        answers: submission,
      });
      setResult({
        score: res.score,
        max_score: res.max_score,
        percent: res.percent,
        results: res.results,
      });
      const assignments = loadAssignmentsFromStorage();
      const assignment = assignments.find((a) => a.quiz_id === quiz.id);
      if (assignment) {
        assignment.status = "completed";
        saveAssignmentsToStorage(assignments);
        try {
          await postAssignmentComplete({
            assignment_id: assignment.id,
            score: res.percent,
            completed_at: new Date().toISOString(),
          });
        } catch {
          /* offline: already in sync queue */
        }
      }
      const history = loadQuizHistoryFromStorage();
      history.unshift({
        quiz_id: quiz.id,
        completed_at: new Date().toISOString(),
        score: res.score,
        max_score: res.max_score,
        percent: res.percent,
        subject: quiz.subject ?? "General",
        question_type: quiz.question_type,
      });
      saveQuizHistoryToStorage(history.slice(0, 50));
    } catch {
      setResult({ score: 0, max_score: items.length * 10, percent: 0, results: [] });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCheckAnswer = async () => {
    if (!current) return;
    const ans = (answers[current.id] ?? "").trim();
    if (!ans) return;
    try {
      const res = await postQuizGradeAnswer({
        question: current.text ?? current.question ?? "",
        user_answer: ans,
        sample_answer: current.sample_answer ?? current.expected_answer ?? "",
        rubric: current.rubric ?? "",
        difficulty: quiz?.difficulty ?? "Beginner",
      });
      setOpenEndedFeedback((f) => ({
        ...f,
        [current.id]: { score: res.score, feedback: res.feedback },
      }));
    } catch {
      setOpenEndedFeedback((f) => ({
        ...f,
        [current.id]: { score: 0, feedback: "Grading failed." },
      }));
    }
  };

  const handleSaveToFlashcards = async () => {
    if (!result) return;
    const wrong = result.results
      .filter((r) => !r.correct)
      .map((r) => {
        const it = items.find((i) => i.id === r.question_id);
        return {
          question_id: r.question_id,
          text: it?.text ?? it?.question,
          correct_answer: r.correct_answer,
          explanation: r.explanation,
        };
      });
    if (wrong.length === 0) return;
    try {
      await postFlashcardsFromQuiz({ wrong_questions: wrong });
      navigate("/flashcards");
    } catch {
      // ignore
    }
  };

  const handleRetryWrong = () => {
    if (!result) return;
    const wrongItems = items.filter((it) => !result.results.find((r) => r.question_id === it.id)?.correct);
    if (wrongItems.length === 0) return;
    navigate("/quiz");
  };

  const feedbackBorder = (score: number) => {
    if (score >= 7) return "2px solid #10b981";
    if (score >= 4) return "2px solid #FEC288";
    return "2px solid #FA5C5C";
  };

  if (loading || !quiz) {
    return (
      <PageChrome backTo="/quiz" backLabel="← Back to Quiz">
        <div className="quiz-take">Loading quiz...</div>
      </PageChrome>
    );
  }

  if (result) {
    const wrongCount = result.results.filter((r) => !r.correct).length;
    const circleColor =
      result.percent >= 70 ? "#10b981" : result.percent >= 40 ? "#FEC288" : "#FA5C5C";
    return (
      <PageChrome backTo="/quiz" backLabel="← Back to Quiz">
        <div className="quiz-take quiz-take--results">
          <h2 className="quiz-take__title">Quiz Results</h2>
          <div
            className="quiz-take__score-circle"
            style={{ borderColor: circleColor, color: circleColor }}
          >
            {result.percent}%
          </div>
          <p className="quiz-take__message">
            {result.percent >= 70 ? "Great job!" : "Keep practicing!"}
          </p>
          <div className="quiz-take__breakdown">
            {result.results.map((r) => {
              const it = items.find((i) => i.id === r.question_id);
              return (
                <div
                  key={r.question_id}
                  className="quiz-take__result-card"
                  style={{
                    borderLeft: r.correct ? "4px solid #10b981" : "4px solid #FA5C5C",
                  }}
                >
                  <div className="quiz-take__result-header">
                    <span>{r.correct ? "✅" : "❌"}</span>
                    <span>{it?.text ?? it?.question ?? "?"}</span>
                  </div>
                  {!r.correct && (
                    <>
                      <p className="quiz-take__correct">Correct: {r.correct_answer}</p>
                      {r.explanation && (
                        <p className="quiz-take__explanation">{r.explanation}</p>
                      )}
                    </>
                  )}
                </div>
              );
            })}
          </div>
          <div className="quiz-take__actions">
            {wrongCount > 0 && (
              <button
                type="button"
                className="quiz-take__btn quiz-take__btn--secondary"
                onClick={handleRetryWrong}
              >
                Retry Wrong Questions
              </button>
            )}
            {wrongCount > 0 && (
              <button
                type="button"
                className="quiz-take__btn quiz-take__btn--primary"
                onClick={handleSaveToFlashcards}
              >
                Save to Flashcards
              </button>
            )}
            <button
              type="button"
              className="quiz-take__btn quiz-take__btn--primary"
              onClick={() => navigate("/quiz")}
            >
              Back to Quiz Home
            </button>
          </div>
        </div>
      </PageChrome>
    );
  }

  const qText = current?.text ?? current?.question ?? "?";
  const opts = current?.options ?? [];

  return (
    <PageChrome backTo="/quiz" backLabel="← Back to Quiz">
      <div className="quiz-take">
        <div className="quiz-take__header">
          <span className="quiz-take__chip">{quiz.subject ?? "General"}</span>
          <span className="quiz-take__chip">{quiz.difficulty ?? "Beginner"}</span>
          <span className="quiz-take__progress">
            Q{idx + 1}/{items.length}
          </span>
        </div>
        <div
          className="quiz-take__progress-bar"
          style={{ width: `${((idx + 1) / items.length) * 100}%` }}
        />

        <h3 className="quiz-take__question">{qText}</h3>

        {isMcq ? (
          <div className="quiz-take__options">
            {opts.map((opt, i) => (
              <button
                key={i}
                type="button"
                className={`quiz-take__option ${
                  answers[current.id] === String(i) ? "quiz-take__option--selected" : ""
                }`}
                onClick={() => handleMcqSelect(i)}
              >
                {opt}
              </button>
            ))}
          </div>
        ) : (
          <>
            <textarea
              className="quiz-take__textarea"
              rows={5}
              placeholder="Write your answer..."
              value={answers[current?.id ?? ""] ?? ""}
              onChange={(e) =>
                setAnswers((a) => ({ ...a, [current?.id ?? ""]: e.target.value }))
              }
            />
            {openEndedFeedback[current?.id ?? ""] && (
              <div
                className="quiz-take__feedback"
                style={{
                  border: feedbackBorder(openEndedFeedback[current?.id ?? ""].score),
                }}
              >
                <p className="quiz-take__feedback-title">
                  {openEndedFeedback[current?.id ?? ""].score >= 7
                    ? "Great answer!"
                    : openEndedFeedback[current?.id ?? ""].score >= 4
                      ? "Partial credit"
                      : "Needs improvement"}
                </p>
                <p className="quiz-take__feedback-text">
                  {openEndedFeedback[current?.id ?? ""].feedback}
                </p>
              </div>
            )}
            <button
              type="button"
              className="quiz-take__btn quiz-take__btn--secondary"
              onClick={handleCheckAnswer}
            >
              Check Answer
            </button>
          </>
        )}

        <div className="quiz-take__nav">
          <button
            type="button"
            className="quiz-take__btn quiz-take__btn--secondary"
            disabled={idx === 0}
            onClick={() => setIdx((i) => Math.max(0, i - 1))}
          >
            Previous
          </button>
          {isLast ? (
            <button
              type="button"
              className="quiz-take__btn quiz-take__btn--primary"
              disabled={!allAnswered || submitting}
              onClick={handleSubmit}
            >
              {submitting ? "Submitting..." : "Submit Quiz"}
            </button>
          ) : (
            <button
              type="button"
              className="quiz-take__btn quiz-take__btn--primary"
              onClick={() => setIdx((i) => Math.min(items.length - 1, i + 1))}
            >
              Next
            </button>
          )}
        </div>
      </div>
    </PageChrome>
  );
}
