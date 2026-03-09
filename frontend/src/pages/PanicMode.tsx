/**
 * Panic Mode — distraction-free timed exam. ExamMode-style UI with project color scheme.
 * Full pipeline: getQuiz("panic") → Lobby → ExamScreen (fullscreen) → postQuizSubmit → Results.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  getQuiz,
  postQuizSubmit,
  postPanicGradeOne,
  generatePanicQuizFromTextbook,
  generatePanicQuizFromWeblink,
  generatePanicQuizFromFiles,
  getTextbooks,
  uploadTextbook,
} from "../services/api";
import { enqueueSyncItem } from "../services/storage";
import type { QuizItem, QuizSubmitResult } from "../services/api";
import { PageChrome, LoadingSpinner } from "../components";
import { usePanicExam } from "../contexts/PanicExamContext";
import { useAuth } from "../contexts/AuthContext";

const DURATION_OPTIONS = [15, 30, 45, 60] as const;
const SUBJECTS = ["Physics", "Biology", "Mathematics", "Chemistry", "Computer Science", "General"] as const;
type SourceTab = "textbook" | "weblink" | "files";
const ACCENT_PINK = "var(--accent-pink, #FA5C5C)";
const ACCENT_CORAL = "var(--accent-coral, #FD8A6B)";
const ACCENT_BLUE = "var(--accent-blue, #00A8E8)";
const SUCCESS = "var(--success, #22c55e)";

/* ═══ Timer hook ═══ */
function useTimer(
  totalSec: number,
  start: boolean,
  onExpire: () => void
): { display: string; fraction: number; urgent: boolean } {
  const [sec, setSec] = useState(totalSec);
  const ref = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    if (!start) return;
    ref.current = setInterval(() => {
      setSec((s) => {
        if (s <= 1) {
          if (ref.current) clearInterval(ref.current);
          onExpire();
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => {
      if (ref.current) clearInterval(ref.current);
    };
  }, [start, totalSec, onExpire]);
  const mm = String(Math.floor(sec / 60)).padStart(2, "0");
  const ss = String(sec % 60).padStart(2, "0");
  return {
    display: `${mm}:${ss}`,
    fraction: sec / totalSec,
    urgent: sec < 300,
  };
}

/* ═══ Circular progress timer ═══ */
function CircleTimer({
  fraction,
  display,
  urgent,
}: {
  fraction: number;
  display: string;
  urgent: boolean;
}) {
  const R = 72;
  const C = 2 * Math.PI * R;
  const offset = C * (1 - fraction);
  const color = urgent ? ACCENT_PINK : ACCENT_BLUE;
  return (
    <div
      className="panic-circle-timer"
      style={{
        position: "relative",
        width: 168,
        height: 168,
        flexShrink: 0,
      }}
    >
      <svg width="168" height="168" style={{ transform: "rotate(-90deg)" }}>
        <circle
          cx="84"
          cy="84"
          r={R}
          fill="none"
          stroke="var(--glass-border)"
          strokeWidth="7"
        />
        <circle
          cx="84"
          cy="84"
          r={R}
          fill="none"
          stroke={color}
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={C}
          strokeDashoffset={offset}
          style={{
            transition: "stroke-dashoffset 1s linear, stroke .4s ease",
            filter: `drop-shadow(0 0 6px ${color}40)`,
          }}
        />
      </svg>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <span
          className="font-mono text-[9px] font-bold uppercase tracking-widest"
          style={{ color: "var(--text-subtle)", marginBottom: 2 }}
        >
          Remaining
        </span>
        <span
          className="font-mono text-[28px] font-bold tracking-tight"
          style={{
            color: urgent ? ACCENT_PINK : "var(--heading-dark)",
            textShadow: urgent ? `0 0 16px ${ACCENT_PINK}35` : "none",
            transition: "color .4s, text-shadow .4s",
          }}
        >
          {display}
        </span>
      </div>
    </div>
  );
}

/* ═══ Setup — subject + material selector ═══ */
function Setup({
  onLoad,
  loading,
  error,
  onErrorClear,
  setLoading,
  setError,
  onUseDefault,
}: {
  onLoad: (quiz: { id: string; title: string; items: QuizItem[]; question_type?: "mcq" | "open_ended" }) => void;
  loading: boolean;
  error: string | null;
  onErrorClear: () => void;
  setLoading?: (v: boolean) => void;
  setError?: (v: string | null) => void;
  onUseDefault?: () => void;
}) {
  const { connectivityStatus } = useAuth();
  const [subject, setSubject] = useState<string>(SUBJECTS[0]);
  const [questionType, setQuestionType] = useState<"mcq" | "open_ended">("open_ended");
  const [tab, setTab] = useState<SourceTab>("textbook");
  const [textbooks, setTextbooks] = useState<{ id: string; name: string }[]>([]);
  const [textbookMode, setTextbookMode] = useState<"existing" | "upload">("existing");
  const [selectedTextbook, setSelectedTextbook] = useState("");
  const [chapterInput, setChapterInput] = useState("");
  const [weblinkUrl, setWeblinkUrl] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    getTextbooks().then((r) => setTextbooks(r.textbooks)).catch(() => setTextbooks([]));
  }, []);

  const handleTextbookUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
      onErrorClear();
      return;
    }
    setUploading(true);
    onErrorClear();
    try {
      const res = await uploadTextbook(file);
      setTextbooks((prev) => [...prev, { id: res.id, name: res.name }]);
      setSelectedTextbook(res.id);
    } catch (err) {
      setError?.(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
    e.target.value = "";
  };

  const handleLoad = async () => {
    onErrorClear();
    setLoading?.(true);
    try {
      if (tab === "textbook") {
        if (!selectedTextbook) {
          setError?.("Select or upload a textbook first.");
          return;
        }
        const res = await generatePanicQuizFromTextbook({
          subject,
          textbook_id: selectedTextbook,
          chapter: chapterInput.trim() || undefined,
          count: 5,
          question_type: questionType,
        });
        onLoad({
          id: res.id,
          title: res.title,
          items: res.items,
          question_type: res.question_type === "mcq" ? "mcq" : "open_ended",
        });
      } else if (tab === "weblink") {
        const url = weblinkUrl.trim();
        if (!url) {
          setError?.("Enter a valid URL.");
          return;
        }
        if (connectivityStatus === "offline") {
          setError?.("You need to be connected to use web links.");
          return;
        }
        const res = await generatePanicQuizFromWeblink({ subject, url, count: 5, question_type: questionType });
        onLoad({
          id: res.id,
          title: res.title,
          items: res.items,
          question_type: res.question_type === "mcq" ? "mcq" : "open_ended",
        });
      } else {
        if (files.length === 0) {
          setError?.("Select one or more files (txt, pdf, ppt).");
          return;
        }
        const res = await generatePanicQuizFromFiles({ subject, files, count: 5, question_type: questionType });
        onLoad({
          id: res.id,
          title: res.title,
          items: res.items,
          question_type: res.question_type === "mcq" ? "mcq" : "open_ended",
        });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Load failed.";
      const friendly =
        msg.toLowerCase().includes("abort") || msg.toLowerCase().includes("signal")
          ? "Request timed out. Generating questions via AI can take 1–2 minutes — please try again. Ensure Ollama is running on localhost:11434."
          : msg;
      setError?.(friendly);
    } finally {
      setLoading?.(false);
    }
  };

  const addFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const chosen = Array.from(e.target.files ?? []);
    const allowed = chosen.filter((f) => {
      const n = f.name.toLowerCase();
      return n.endsWith(".txt") || n.endsWith(".pdf") || n.endsWith(".ppt") || n.endsWith(".pptx");
    });
    setFiles((prev) => [...prev, ...allowed]);
    e.target.value = "";
  };

  const tabs: { key: SourceTab; label: string; title: string }[] = [
    { key: "textbook", label: "TX", title: "Textbook" },
    { key: "weblink", label: "WI", title: "Web link" },
    { key: "files", label: "FL", title: "Files" },
  ];

  return (
    <div className="panic-lobby min-h-screen flex items-center justify-center p-6 font-sans">
      <div className="w-full max-w-[620px] animate-panic-fade-up">
        <div className="content-card rounded-card overflow-hidden border border-glass-border shadow-card">
          <div
            className="h-1"
            style={{
              background: `linear-gradient(90deg,${ACCENT_PINK},${ACCENT_CORAL},var(--accent-peach,#FEC288),var(--accent-yellow,#FBEF76),${ACCENT_BLUE})`,
            }}
          />
          <div className="p-9">
            <div className="flex items-center gap-3.5 mb-6">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{
                  background: `linear-gradient(135deg,${ACCENT_PINK},${ACCENT_CORAL})`,
                  boxShadow: `0 4px 16px ${ACCENT_PINK}35`,
                }}
              >
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                  <path d="M9 11l3 3L22 4" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" stroke="white" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
              <div>
                <div className="text-lg font-extrabold text-heading-dark tracking-tight">Panic Mode — Setup</div>
                <div className="font-mono text-xs text-subtle mt-0.5">Select subject & material (one source)</div>
              </div>
            </div>

            <div className="mb-5">
              <div className="text-xs font-bold text-muted mb-2">Question type</div>
              <div className="flex gap-2 mb-4">
                <button
                  type="button"
                  onClick={() => setQuestionType("mcq")}
                  className={`px-4 py-2 rounded-xl text-sm font-medium ${
                    questionType === "mcq" ? "bg-accent-blue text-white" : "border border-glass-border bg-surface-light text-primary hover:bg-surface-light/80"
                  }`}
                >
                  MCQ
                </button>
                <button
                  type="button"
                  onClick={() => setQuestionType("open_ended")}
                  className={`px-4 py-2 rounded-xl text-sm font-medium ${
                    questionType === "open_ended" ? "bg-accent-blue text-white" : "border border-glass-border bg-surface-light text-primary hover:bg-surface-light/80"
                  }`}
                >
                  Open-ended
                </button>
              </div>
            </div>

            <div className="mb-5">
              <label className="block text-xs font-bold text-muted mb-2">Subject (one only)</label>
              <select
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full max-w-[280px] px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary font-medium"
              >
                {SUBJECTS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            <div className="mb-5">
              <div className="text-xs font-bold text-muted mb-2">Material source</div>
              <div className="flex gap-2 mb-4">
                {tabs.map(({ key, label, title }) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setTab(key)}
                    className={`px-4 py-2 rounded-xl text-sm font-medium ${
                      tab === key ? "bg-accent-blue text-white" : "border border-glass-border bg-surface-light text-primary hover:bg-surface-light/80"
                    }`}
                  >
                    {label} — {title}
                  </button>
                ))}
              </div>

              {tab === "textbook" && (
                <div className="space-y-4">
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="radio" name="tbMode" checked={textbookMode === "existing"} onChange={() => setTextbookMode("existing")} className="accent-accent-blue" />
                      <span className="text-sm text-primary">Existing</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="radio" name="tbMode" checked={textbookMode === "upload"} onChange={() => setTextbookMode("upload")} className="accent-accent-blue" />
                      <span className="text-sm text-primary">Upload PDF</span>
                    </label>
                  </div>
                  {textbookMode === "upload" && (
                    <input type="file" accept=".pdf" onChange={handleTextbookUpload} disabled={uploading} className="block w-full max-w-md text-sm text-primary file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:bg-accent-blue file:text-white file:font-medium" />
                  )}
                  {textbookMode === "existing" && textbooks.length > 0 && (
                    <select
                      value={selectedTextbook}
                      onChange={(e) => setSelectedTextbook(e.target.value)}
                      className="w-full max-w-md px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary"
                    >
                      <option value="">— Select —</option>
                      {textbooks.map((t) => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                      ))}
                    </select>
                  )}
                  <input
                    type="text"
                    value={chapterInput}
                    onChange={(e) => setChapterInput(e.target.value)}
                    placeholder="Chapter (optional)"
                    className="w-full max-w-md px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary placeholder:text-subtle"
                  />
                </div>
              )}
              {tab === "weblink" && (
                <input
                  type="url"
                  value={weblinkUrl}
                  onChange={(e) => setWeblinkUrl(e.target.value)}
                  placeholder="https://example.com/article"
                  className="w-full max-w-md px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary placeholder:text-subtle"
                />
              )}
              {tab === "files" && (
                <div>
                  <input
                    type="file"
                    accept=".txt,.pdf,.ppt,.pptx"
                    multiple
                    onChange={addFiles}
                    className="block w-full max-w-md text-sm text-primary file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:bg-accent-blue file:text-white file:font-medium"
                  />
                  {files.length > 0 && (
                    <ul className="mt-2 space-y-1 text-sm text-primary">
                      {files.map((f, i) => (
                        <li key={i} className="flex justify-between">
                          <span className="truncate">{f.name}</span>
                          <button type="button" onClick={() => setFiles((p) => p.filter((_, j) => j !== i))} className="text-red-400">×</button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>

            {error && <p className="mb-4 text-sm text-red-400">{error}</p>}

            <LoadingSpinner loading={loading} message="Generating questions...">
              <div className="flex flex-col gap-3">
                <button
                  type="button"
                  onClick={handleLoad}
                  disabled={loading || (tab === "textbook" && !selectedTextbook) || (tab === "weblink" && !weblinkUrl.trim()) || (tab === "files" && files.length === 0)}
                  className="w-full h-[48px] rounded-xl border-none font-extrabold text-sm cursor-pointer flex items-center justify-center gap-2 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ background: `linear-gradient(135deg,${ACCENT_PINK},${ACCENT_CORAL})`, boxShadow: `0 4px 16px ${ACCENT_PINK}35` }}
                >
                  Load Exam
                </button>
                {onUseDefault && (
                  <button
                    type="button"
                    onClick={onUseDefault}
                    disabled={loading}
                    className="w-full h-[40px] rounded-xl border border-glass-border bg-surface-light text-primary font-medium text-sm hover:bg-surface-light/80 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Use default questions
                  </button>
                )}
              </div>
            </LoadingSpinner>
          </div>
        </div>
      </div>
    </div>
  );
}

function Lobby({
  quiz,
  durationMinutes,
  onDurationChange,
  onStart,
}: {
  quiz: { id: string; title: string; items: QuizItem[]; question_type?: "mcq" | "open_ended" };
  durationMinutes: number;
  onDurationChange: (m: number) => void;
  onStart: () => void;
}) {
  const items = quiz.items;
  const topicCounts = items.reduce<Record<string, number>>((acc, q) => {
    const t = q.topic ?? "General";
    acc[t] = (acc[t] || 0) + 1;
    return acc;
  }, {});
  const topics = Object.entries(topicCounts);

  return (
    <div className="panic-lobby min-h-screen flex items-center justify-center p-6 font-sans">
      <div className="w-full max-w-[620px] animate-panic-fade-up">
        <div className="content-card rounded-card overflow-hidden border border-glass-border shadow-card">
          <div
            className="h-1"
            style={{
              background: `linear-gradient(90deg,${ACCENT_PINK},${ACCENT_CORAL},var(--accent-peach,#FEC288),var(--accent-yellow,#FBEF76),${ACCENT_BLUE})`,
            }}
          />
          <div className="p-9">
            <div className="flex items-center gap-3.5 mb-7">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{
                  background: `linear-gradient(135deg,${ACCENT_PINK},${ACCENT_CORAL})`,
                  boxShadow: `0 4px 16px ${ACCENT_PINK}35`,
                }}
              >
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M9 11l3 3L22 4"
                    stroke="white"
                    strokeWidth="2.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"
                    stroke="white"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                </svg>
              </div>
              <div>
                <div className="text-lg font-extrabold text-heading-dark tracking-tight">
                  {quiz.title}
                </div>
                <div className="font-mono text-xs text-subtle mt-0.5">
                  Studaxis Panic Mode
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 mb-6">
              {[
                { icon: "📋", label: "Questions", val: String(items.length) },
                {
                  icon: "⏱",
                  label: "Duration",
                  val: `${durationMinutes} min`,
                },
                {
                  icon: "📚",
                  label: "Topics",
                  val: String(topics.length),
                },
              ].map((s, i) => (
                <div
                  key={i}
                  className="p-3.5 rounded-xl border border-glass-border bg-deep/50 text-center"
                >
                  <div className="text-xl mb-1">{s.icon}</div>
                  <div className="text-base font-extrabold text-heading-dark tracking-tight">
                    {s.val}
                  </div>
                  <div className="text-xs text-subtle font-medium">{s.label}</div>
                </div>
              ))}
            </div>

            {topics.length > 0 && (
              <div className="mb-6 p-3.5 rounded-xl border border-glass-border bg-deep/50">
                <div className="text-xs font-bold text-muted mb-2.5">
                  Topic breakdown
                </div>
                <div className="flex flex-wrap gap-2">
                  {topics.map(([topic, n]) => (
                    <div
                      key={topic}
                      className="px-2 py-1.5 rounded-lg text-center"
                      style={{
                        background: `${ACCENT_BLUE}15`,
                        border: `1.5px solid ${ACCENT_BLUE}30`,
                      }}
                    >
                      <span
                        className="text-sm font-extrabold"
                        style={{ color: ACCENT_BLUE }}
                      >
                        {n}
                      </span>
                      <span
                        className="text-[10px] font-bold ml-1"
                        style={{ color: ACCENT_BLUE }}
                      >
                        {topic}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="mb-6 p-3.5 rounded-xl border border-glass-border">
              <label
                htmlFor="panic-duration"
                className="block text-xs font-bold mb-2"
                style={{ color: ACCENT_PINK }}
              >
                Exam duration (minutes)
              </label>
              <select
                id="panic-duration"
                value={durationMinutes}
                onChange={(e) => onDurationChange(Number(e.target.value))}
                className="w-full max-w-[200px] px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary focus:outline-none focus:ring-2 focus:ring-accent-blue font-medium"
              >
                {DURATION_OPTIONS.map((m) => (
                  <option key={m} value={m}>
                    {m} min
                  </option>
                ))}
              </select>
            </div>

            <div
              className="mb-7 p-3.5 rounded-xl"
              style={{
                background: `${ACCENT_PINK}08`,
                border: `1.5px solid ${ACCENT_PINK}20`,
              }}
            >
              <div
                className="text-xs font-bold mb-2 flex items-center gap-1.5"
                style={{ color: ACCENT_PINK }}
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke={ACCENT_PINK} strokeWidth="2" />
                  <path
                    d="M12 8v4M12 16h.01"
                    stroke={ACCENT_PINK}
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                </svg>
                Before you begin
              </div>
              {[
                "The exam will enter fullscreen. Do not exit or your session may be flagged.",
                "Your answers auto-save as you type.",
                "Submit before time runs out — the exam ends automatically when the timer hits 0.",
              ].map((r, i) => (
                <div
                  key={i}
                  className="flex gap-2 items-start mb-1.5 last:mb-0"
                >
                  <span
                    className="font-extrabold text-xs flex-shrink-0"
                    style={{ color: ACCENT_PINK }}
                  >
                    ·
                  </span>
                  <span className="text-xs text-muted leading-relaxed">{r}</span>
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={onStart}
              className="w-full h-[52px] rounded-xl border-none font-extrabold text-base font-sans cursor-pointer flex items-center justify-center gap-2.5 transition-all duration-150 hover:-translate-y-0.5 text-white"
              style={{
                background: `linear-gradient(135deg,${ACCENT_PINK},${ACCENT_CORAL})`,
                boxShadow: `0 4px 20px ${ACCENT_PINK}40`,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = `0 8px 28px ${ACCENT_PINK}45`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = `0 4px 20px ${ACCENT_PINK}40`;
              }}
            >
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                <polygon points="5 3 19 12 5 21 5 3" fill="white" />
              </svg>
              Start Exam — Enter Fullscreen
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══ Results screen ═══ */
function Results({
  quiz,
  answers,
  results,
  timeUp,
  weakTopicsText,
  recommendationText,
  onRetake,
}: {
  quiz: { id: string; title: string; items: QuizItem[]; question_type?: "mcq" | "open_ended" };
  answers: Record<string, string>;
  results: QuizSubmitResult[];
  timeUp: boolean;
  weakTopicsText: string | null;
  recommendationText: string | null;
  onRetake: () => void;
}) {
  const navigate = useNavigate();
  const items = quiz.items;
  const answered = Object.keys(answers).filter((k) => (answers[k] ?? "").trim()).length;
  const resultsByQid = Object.fromEntries(results.map((r) => [r.question_id, r]));
  const avgScore =
    results.length > 0
      ? results.reduce((s, r) => s + (r.score ?? 0), 0) / results.length
      : 0;
  const pct = items.length > 0 ? Math.round((avgScore / 10) * 100) : 0;
  const grade = pct >= 80 ? "A" : pct >= 60 ? "B" : pct >= 40 ? "C" : "D";
  const gradeColor =
    pct >= 80 ? SUCCESS : pct >= 60 ? ACCENT_BLUE : pct >= 40 ? ACCENT_CORAL : ACCENT_PINK;

  return (
    <div className="panic-lobby min-h-screen flex items-center justify-center p-6 font-sans">
      <div className="w-full max-w-[580px] animate-panic-fade-up">
        <div className="content-card rounded-card overflow-hidden border border-glass-border shadow-card">
          <div
            className="h-1"
            style={{
              background: `linear-gradient(90deg,${ACCENT_PINK},${ACCENT_CORAL},var(--accent-peach,#FEC288),var(--accent-yellow,#FBEF76),${ACCENT_BLUE})`,
            }}
          />
          <div className="p-9">
            {timeUp && (
              <div
                className="flex items-center gap-2 mb-5 p-2.5 rounded-xl"
                style={{
                  background: `${ACCENT_PINK}0a`,
                  border: `1px solid ${ACCENT_PINK}30`,
                }}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke={ACCENT_PINK} strokeWidth="2" />
                  <path
                    d="M12 8v4M12 16h.01"
                    stroke={ACCENT_PINK}
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                </svg>
                <span
                  className="text-sm font-semibold"
                  style={{ color: ACCENT_PINK }}
                >
                  Time's up — your exam was automatically submitted.
                </span>
              </div>
            )}

            <div className="text-center mb-7">
              <div
                className="w-20 h-20 rounded-[22px] mx-auto mb-3.5 flex items-center justify-center text-4xl font-black text-white"
                style={{
                  background: `linear-gradient(135deg,${gradeColor},${gradeColor}bb)`,
                  boxShadow: `0 6px 24px ${gradeColor}40`,
                }}
              >
                {grade}
              </div>
              <h2 className="text-xl font-black text-heading-dark tracking-tight mb-1">
                Exam Complete
              </h2>
              <p className="text-sm text-subtle">{quiz.title}</p>
            </div>

            <div className="grid grid-cols-3 gap-2.5 mb-6">
              {[
                { label: "Score", val: `${pct}%`, color: gradeColor },
                {
                  label: "Answered",
                  val: `${answered}/${items.length}`,
                  color: ACCENT_BLUE,
                },
                {
                  label: "Avg",
                  val: avgScore.toFixed(1) + "/10",
                  color: SUCCESS,
                },
              ].map((s, i) => (
                <div
                  key={i}
                  className="p-3.5 rounded-xl border border-glass-border bg-deep/50 text-center"
                >
                  <div
                    className="text-xl font-black tracking-tight"
                    style={{ color: s.color }}
                  >
                    {s.val}
                  </div>
                  <div className="text-xs text-subtle font-medium mt-0.5">
                    {s.label}
                  </div>
                </div>
              ))}
            </div>

            <div className="mb-6">
              <div className="text-xs font-bold text-muted mb-2.5">
                Question Review
              </div>
              <div className="flex flex-wrap gap-2">
                {items.map((q, i) => {
                  const r = resultsByQid[q.id];
                  const score = r?.score ?? 0;
                  const isGood = score >= 6;
                  const skipped = !(answers[q.id] ?? "").trim();
                  const c = skipped
                    ? "var(--text-subtle)"
                    : isGood
                      ? SUCCESS
                      : ACCENT_PINK;
                  return (
                    <div
                      key={q.id}
                      className="w-[38px] h-[38px] rounded-xl flex items-center justify-center text-sm font-extrabold"
                      style={{
                        background: `${c}15`,
                        border: `2px solid ${c}`,
                        color: c,
                      }}
                    >
                      {i + 1}
                    </div>
                  );
                })}
              </div>
              <div className="flex gap-3.5 mt-2.5">
                {[
                  [SUCCESS, "Good (≥6)"],
                  [ACCENT_PINK, "Needs work"],
                  ["var(--text-subtle)", "Skipped"],
                ].map(([c, l]) => (
                  <div key={String(l)} className="flex items-center gap-1">
                    <div
                      className="w-2.5 h-2.5 rounded-md"
                      style={{ background: c as string }}
                    />
                    <span className="text-xs text-subtle font-medium">{l}</span>
                  </div>
                ))}
              </div>
            </div>

            {results.length > 0 && (
              <div className="mb-6 space-y-3">
                <div className="text-xs font-bold text-muted">
                  Per-question feedback
                </div>
                {results.map((r) => (
                  <div
                    key={r.question_id}
                    className="p-3 rounded-xl border border-glass-border bg-deep/30"
                  >
                    <div className="text-sm font-semibold text-primary">
                      {r.question_id} — Score: {r.score != null ? `${r.score}/10` : "—"}
                    </div>
                    {r.feedback && (
                      <p className="text-xs text-muted mt-1.5 whitespace-pre-wrap">
                        {r.feedback}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {(weakTopicsText || recommendationText) && (
              <div className="grid gap-4 md:grid-cols-2 mb-6">
                {weakTopicsText && (
                  <div className="p-4 rounded-xl border border-glass-border bg-deep/30">
                    <div className="text-xs font-bold text-muted mb-2">
                      Weak Topic Analysis
                    </div>
                    <p className="text-sm text-muted whitespace-pre-wrap">
                      {weakTopicsText}
                    </p>
                  </div>
                )}
                {recommendationText && (
                  <div className="p-4 rounded-xl border border-glass-border bg-deep/30">
                    <div className="text-xs font-bold text-muted mb-2">
                      Study Recommendation
                    </div>
                    <p className="text-sm text-muted whitespace-pre-wrap">
                      {recommendationText}
                    </p>
                  </div>
                )}
              </div>
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={onRetake}
                className="flex-1 h-12 rounded-xl border-none font-extrabold text-sm cursor-pointer transition-all hover:-translate-y-0.5 text-white"
                style={{
                  background: `linear-gradient(135deg,${ACCENT_PINK},${ACCENT_CORAL})`,
                  boxShadow: `0 4px 16px ${ACCENT_PINK}35`,
                }}
              >
                Retake Panic Mode
              </button>
              <button
                type="button"
                onClick={() => navigate("/dashboard")}
                className="flex-1 h-12 rounded-xl border border-glass-border bg-surface-light text-primary font-bold text-sm cursor-pointer hover:bg-surface-light/80 transition-colors"
              >
                Back to Dashboard
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══ Exam screen (fullscreen) ═══ */
function ExamScreen({
  quiz,
  durationMinutes,
  answers,
  onAnswerChange,
  onSubmit,
  submitting,
  submitError,
}: {
  quiz: { id: string; title: string; items: QuizItem[]; question_type?: "mcq" | "open_ended" };
  durationMinutes: number;
  answers: Record<string, string>;
  onAnswerChange: (qid: string, value: string) => void;
  onSubmit: (wasTimeUp?: boolean) => void;
  submitting: boolean;
  submitError: string | null;
}) {
  const [qIdx, setQIdx] = useState(0);
  const [timeUp, setTimeUp] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [openEndedFeedback, setOpenEndedFeedback] = useState<
    Record<string, { score: number; feedback: string }>
  >({});
  const [checkingAnswer, setCheckingAnswer] = useState(false);
  const isMcq = (quiz.question_type || "open_ended") === "mcq";
  const totalSec = durationMinutes * 60;
  const items = quiz.items;
  const q = items[qIdx];
  const answered = Object.keys(answers).filter((k) => (answers[k] ?? "").trim()).length;

  const handleTimeUp = useCallback(() => {
    setTimeUp(true);
    onSubmit(true);
  }, [onSubmit]);

  const { display, fraction, urgent } = useTimer(totalSec, !timeUp, handleTimeUp);

  const next = () => {
    if (qIdx < items.length - 1) setQIdx(qIdx + 1);
  };
  const prev = () => {
    if (qIdx > 0) setQIdx(qIdx - 1);
  };

  return (
    <div
      className="w-screen h-screen flex flex-col font-sans overflow-hidden relative bg-surface-light"
      style={{ color: "var(--text-primary)" }}
    >
      {timeUp && (
        <div
          className="absolute inset-0 z-[999] flex flex-col items-center justify-center gap-4 bg-surface-light/95 backdrop-blur-sm"
          style={{ color: "var(--text-primary)" }}
        >
          <div className="loading-spinner w-8 h-8 border-[3px]" />
          <p className="text-lg font-bold text-heading-dark">
            Time's up. Submitting your exam...
          </p>
        </div>
      )}
      <div
        className="h-1 flex-shrink-0"
        style={{
          background: `linear-gradient(90deg,${ACCENT_PINK},${ACCENT_CORAL},var(--accent-peach,#FEC288),var(--accent-yellow,#FBEF76),${ACCENT_BLUE})`,
        }}
      />

      <div className="h-[60px] px-7 flex items-center justify-between border-b border-glass-border flex-shrink-0 bg-surface-light">
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{
              background: `linear-gradient(135deg,${ACCENT_PINK},${ACCENT_CORAL})`,
              boxShadow: `0 2px 8px ${ACCENT_PINK}30`,
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
              <path
                d="M9 11l3 3L22 4"
                stroke="white"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <div>
            <span className="text-sm font-extrabold text-heading-dark tracking-tight">
              {quiz.title}
            </span>
            <span className="font-mono text-[10.5px] text-subtle ml-2.5">
              Studaxis Panic Mode
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg"
            style={{
              background: `${SUCCESS}12`,
              border: `1px solid ${SUCCESS}30`,
            }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full inline-block"
              style={{
                background: SUCCESS,
                boxShadow: `0 0 0 3px ${SUCCESS}20`,
              }}
            />
            <span
              className="font-mono text-xs font-bold"
              style={{ color: SUCCESS }}
            >
              AUTO-SAVE: ON
            </span>
          </div>
          {urgent && (
            <div
              className="px-3 py-1.5 rounded-lg font-mono text-xs font-bold animate-panic-urgent"
              style={{
                background: `${ACCENT_PINK}14`,
                border: `1px solid ${ACCENT_PINK}30`,
                color: ACCENT_PINK,
              }}
            >
              ⚠ LOW TIME
            </div>
          )}
          <div
            className="px-3 py-1.5 rounded-lg font-mono text-xs font-bold"
            style={{
              background: "var(--deep)",
              border: "1px solid var(--glass-border)",
              color: "var(--text-muted)",
            }}
          >
            {answered}/{items.length} answered
          </div>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-1 md:grid-cols-[280px_1fr_260px] overflow-hidden">
        <div className="hidden md:flex flex-col gap-5 p-6 overflow-y-auto border-r border-glass-border bg-deep/30">
          <div>
            <div className="font-mono text-[9.5px] font-bold text-subtle uppercase tracking-widest mb-3 flex items-center gap-2">
              Questions
              <div className="flex-1 h-px bg-glass-border" />
            </div>
            <div className="grid grid-cols-4 gap-1.5">
              {items.map((quest, i) => {
                const isAns = (answers[quest.id] ?? "").trim().length > 0;
                const isCur = qIdx === i;
                return (
                  <div
                    key={quest.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => setQIdx(i)}
                    onKeyDown={(e) =>
                      (e.key === "Enter" || e.key === " ") && setQIdx(i)
                    }
                    className="h-[38px] rounded-lg cursor-pointer flex items-center justify-center text-sm font-extrabold transition-all duration-150"
                    style={{
                      border: `2px solid ${isCur ? ACCENT_PINK : isAns ? SUCCESS : "var(--glass-border)"}`,
                      background: isCur
                        ? `${ACCENT_PINK}14`
                        : isAns
                          ? `${SUCCESS}12`
                          : "var(--surface-light)",
                      color: isCur ? ACCENT_PINK : isAns ? SUCCESS : "var(--text-muted)",
                    }}
                  >
                    {i + 1}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="p-10 md:p-12 pb-24 overflow-y-auto" key={qIdx}>
          <div className="flex items-center gap-2.5 mb-5">
            <span
              className="font-mono text-xs font-semibold"
              style={{ color: ACCENT_BLUE }}
            >
              QUESTION {String(qIdx + 1).padStart(2, "0")} / {items.length}
            </span>
            <span
              className="px-2 py-0.5 rounded-full text-[10.5px] font-bold"
              style={{
                background: `${ACCENT_BLUE}15`,
                color: ACCENT_BLUE,
                border: `1px solid ${ACCENT_BLUE}30`,
              }}
            >
              {q.topic}
            </span>
          </div>

          <h2 className="text-lg md:text-xl font-extrabold text-heading-dark leading-snug tracking-tight max-w-[700px] mb-9 animate-panic-slide">
            {q.question ?? q.text ?? "?"}
          </h2>

          {isMcq && q.options && q.options.length > 0 ? (
            <div className="space-y-2 max-w-[680px]">
              {q.options.map((opt, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => onAnswerChange(q.id, String(i))}
                  className={`w-full text-left px-5 py-4 rounded-xl border-2 font-medium text-sm transition-all ${
                    answers[q.id] === String(i)
                      ? "border-accent-pink bg-accent-pink/10"
                      : "border-glass-border bg-deep/30 hover:border-accent-pink/50"
                  }`}
                  style={{
                    borderColor:
                      answers[q.id] === String(i)
                        ? ACCENT_PINK
                        : undefined,
                  }}
                >
                  {String.fromCharCode(65 + i)}. {opt}
                </button>
              ))}
            </div>
          ) : (
            <>
              <textarea
                value={answers[q.id] ?? ""}
                onChange={(e) => onAnswerChange(q.id, e.target.value)}
                placeholder="Type your answer here..."
                rows={6}
                className="w-full max-w-[680px] px-5 py-4 rounded-xl border-2 border-glass-border bg-deep/30 text-primary placeholder:text-subtle focus:outline-none focus:ring-2 focus:ring-accent-pink focus:border-accent-pink resize-y font-sans text-sm leading-relaxed transition-all"
              />
              <button
                type="button"
                onClick={async () => {
                  const ans = (answers[q.id] ?? "").trim();
                  if (!ans) return;
                  setCheckingAnswer(true);
                  try {
                    const res = await postPanicGradeOne({
                      question_id: q.id,
                      question: q.question ?? q.text ?? "",
                      answer: ans,
                      topic: q.topic ?? "General",
                      expected_answer: q.expected_answer ?? q.sample_answer ?? "",
                    });
                    setOpenEndedFeedback((f) => ({
                      ...f,
                      [q.id]: { score: res.score, feedback: res.feedback },
                    }));
                  } catch {
                    setOpenEndedFeedback((f) => ({
                      ...f,
                      [q.id]: { score: 0, feedback: "Grading failed." },
                    }));
                  } finally {
                    setCheckingAnswer(false);
                  }
                }}
                disabled={checkingAnswer || !(answers[q.id] ?? "").trim()}
                className="mt-3 px-5 py-2.5 rounded-xl border border-accent-blue bg-accent-blue/10 text-accent-blue font-semibold text-sm hover:bg-accent-blue/20 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {checkingAnswer ? "Checking..." : "Check Answer"}
              </button>
              {openEndedFeedback[q.id] && (
                <div
                  className="mt-3 p-4 rounded-xl border-2 max-w-[680px]"
                  style={{
                    borderColor:
                      openEndedFeedback[q.id].score >= 7
                        ? SUCCESS
                        : openEndedFeedback[q.id].score >= 4
                          ? ACCENT_CORAL
                          : ACCENT_PINK,
                  }}
                >
                  <p
                    className="font-bold text-sm mb-1"
                    style={{
                      color:
                        openEndedFeedback[q.id].score >= 7
                          ? SUCCESS
                          : openEndedFeedback[q.id].score >= 4
                            ? ACCENT_CORAL
                            : ACCENT_PINK,
                    }}
                  >
                    {openEndedFeedback[q.id].score >= 7
                      ? "Great answer!"
                      : openEndedFeedback[q.id].score >= 4
                        ? "Partial credit"
                        : "Needs improvement"}{" "}
                    — {openEndedFeedback[q.id].score}/10
                  </p>
                  <p className="text-sm text-muted whitespace-pre-wrap">
                    {openEndedFeedback[q.id].feedback}
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        <div className="hidden md:flex flex-col items-center gap-7 p-7 border-l border-glass-border bg-deep/30">
          <CircleTimer fraction={fraction} display={display} urgent={urgent} />

          <div className="w-full">
            <div className="font-mono text-[9.5px] font-bold text-subtle uppercase tracking-widest mb-2.5 text-center">
              Progress
            </div>
            <div className="grid grid-cols-4 gap-1.5">
              {items.map((_, i) => {
                const done = (answers[items[i].id] ?? "").trim().length > 0;
                const cur = i === qIdx;
                const bg = cur
                  ? `linear-gradient(135deg,${ACCENT_PINK},${ACCENT_CORAL})`
                  : done
                    ? SUCCESS
                    : "var(--glass-border)";
                return (
                  <div
                    key={i}
                    className="h-2 rounded transition-all duration-300"
                    style={{
                      background: bg,
                      boxShadow: cur
                        ? `0 0 8px ${ACCENT_PINK}50`
                        : done
                          ? `0 0 6px ${SUCCESS}30`
                          : "none",
                    }}
                  />
                );
              })}
            </div>
            <div className="text-center mt-2 text-xs text-subtle font-semibold">
              {answered} of {items.length} answered
            </div>
          </div>

          <div className="mt-auto w-full flex flex-col gap-2">
            {submitError && (
              <p className="text-sm font-medium" style={{ color: "var(--error)" }}>
                {submitError}
              </p>
            )}
            <LoadingSpinner loading={submitting} message="Submitting...">
              <button
                type="button"
                onClick={() => setConfirm(true)}
                disabled={submitting}
                className="w-full h-12 rounded-xl border-none font-extrabold text-sm cursor-pointer transition-all hover:-translate-y-0.5 disabled:opacity-60 disabled:cursor-not-allowed text-white"
                style={{
                  background: `linear-gradient(135deg,${ACCENT_PINK},${ACCENT_CORAL})`,
                  boxShadow: `0 3px 14px ${ACCENT_PINK}38`,
                }}
              >
                Submit Exam
              </button>
            </LoadingSpinner>
            <div className="text-center text-[10.5px] text-subtle font-medium">
              {items.length - answered} questions unanswered
            </div>
          </div>
        </div>
      </div>

      <div className="md:hidden fixed bottom-5 left-1/2 -translate-x-1/2 flex gap-0.5 p-0.5 rounded-xl z-10 border border-glass-border bg-deep/80 shadow-soft">
        <button
          type="button"
          onClick={prev}
          disabled={qIdx === 0}
          className="px-5 py-3 rounded-lg font-mono text-sm font-bold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          style={{
            background: qIdx === 0 ? "var(--glass-border)" : "var(--surface-light)",
            color: "var(--text-muted)",
          }}
        >
          ← Prev
        </button>
        <button
          type="button"
          onClick={next}
          disabled={qIdx === items.length - 1}
          className="px-5 py-3 rounded-lg font-mono text-sm font-bold text-white disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          style={{
            background:
              qIdx === items.length - 1
                ? "var(--glass-border)"
                : `linear-gradient(135deg,${ACCENT_PINK},${ACCENT_CORAL})`,
            boxShadow:
              qIdx < items.length - 1 ? `0 2px 10px ${ACCENT_PINK}30` : "none",
          }}
        >
          Next →
        </button>
      </div>

      {confirm && (
        <div
          className="fixed inset-0 z-[1000] flex items-center justify-center backdrop-blur-sm"
          style={{ background: "rgba(13,27,42,0.45)" }}
        >
          <div className="w-[380px] content-card rounded-card overflow-hidden shadow-soft animate-panic-pop">
            <div
              className="h-1"
              style={{
                background: `linear-gradient(90deg,${ACCENT_PINK},${ACCENT_CORAL},var(--accent-peach,#FEC288))`,
              }}
            />
            <div className="p-7">
              <div className="text-center mb-5">
                <div
                  className="w-14 h-14 rounded-2xl mx-auto mb-3 flex items-center justify-center"
                  style={{
                    background: `linear-gradient(135deg,${ACCENT_PINK},${ACCENT_CORAL})`,
                    boxShadow: `0 4px 16px ${ACCENT_PINK}35`,
                  }}
                >
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M9 11l3 3L22 4"
                      stroke="white"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
                <h3 className="text-lg font-black text-heading-dark mb-1.5">
                  Submit Exam?
                </h3>
                <p className="text-sm text-muted leading-relaxed">
                  You've answered <strong className="text-heading-dark">{answered}</strong> of{" "}
                  <strong className="text-heading-dark">{items.length}</strong> questions.{" "}
                  {items.length - answered > 0 && (
                    <span
                      className="font-semibold"
                      style={{ color: ACCENT_PINK }}
                    >
                      {items.length - answered} will be left unanswered.
                    </span>
                  )}
                </p>
              </div>
              <div className="flex gap-2.5">
                <button
                  type="button"
                  onClick={() => {
                    setConfirm(false);
                    onSubmit(false);
                  }}
                  disabled={submitting}
                  className="flex-1 h-11 rounded-xl border-none font-bold text-sm cursor-pointer disabled:opacity-60 text-white"
                  style={{
                    background: `linear-gradient(135deg,${ACCENT_PINK},${ACCENT_CORAL})`,
                    boxShadow: `0 3px 12px ${ACCENT_PINK}35`,
                  }}
                >
                  Submit Now
                </button>
                <button
                  type="button"
                  onClick={() => setConfirm(false)}
                  className="flex-1 h-11 rounded-xl border border-glass-border bg-deep/50 font-semibold text-sm text-muted cursor-pointer"
                >
                  Keep Going
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const PANIC_EXAM_STORAGE_KEY = "panic_exam";

/* ═══ Root controller ═══ */
export function PanicModePage() {
  const { setExamActive } = usePanicExam();
  const [quiz, setQuiz] = useState<{
    id: string;
    title: string;
    items: QuizItem[];
    question_type?: "mcq" | "open_ended";
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [phase, setPhase] = useState<"setup" | "lobby" | "exam" | "results">("setup");
  const [durationMinutes, setDurationMinutes] = useState(15);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [timeUp, setTimeUp] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [results, setResults] = useState<QuizSubmitResult[]>([]);
  const [weakTopicsText, setWeakTopicsText] = useState<string | null>(null);
  const [recommendationText, setRecommendationText] = useState<string | null>(null);
  const [setupLoading, setSetupLoading] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);

  // Restore exam from localStorage on mount (session persists across refresh)
  useEffect(() => {
    try {
      const raw = localStorage.getItem(PANIC_EXAM_STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw) as { quiz?: unknown; phase?: string; answers?: Record<string, string>; durationMinutes?: number };
      const q = data?.quiz as { id?: string; title?: string; items?: unknown[]; question_type?: string } | undefined;
      if (q?.id && Array.isArray(q.items) && q.items.length > 0) {
        setQuiz({ id: q.id, title: q.title ?? "Panic Mode", items: q.items as QuizItem[], question_type: q.question_type === "mcq" ? "mcq" : "open_ended" });
        if (data.phase === "exam" && typeof data.answers === "object" && data.answers !== null) {
          setPhase("exam");
          setAnswers(data.answers);
          setExamActive(true);
        } else if (data.phase === "lobby") {
          setPhase("lobby");
        }
        if (typeof data.durationMinutes === "number") setDurationMinutes(data.durationMinutes);
      }
    } catch {
      // ignore invalid stored data
    } finally {
      setLoading(false);
    }
  }, [setExamActive]);

  // Persist exam to localStorage whenever quiz or phase/answers change (so refresh restores session)
  useEffect(() => {
    if (!quiz || phase === "setup" || phase === "results") {
      if (phase === "results") {
        try {
          localStorage.removeItem(PANIC_EXAM_STORAGE_KEY);
        } catch {
          // ignore
        }
      }
      return;
    }
    try {
      localStorage.setItem(
        PANIC_EXAM_STORAGE_KEY,
        JSON.stringify({ quiz, phase, answers, durationMinutes })
      );
    } catch {
      // ignore quota or parse errors
    }
  }, [quiz, phase, answers, durationMinutes]);

  // Fix: if quiz is null, always reset phase to setup (guards against stale phase from any source)
  useEffect(() => {
    if (!quiz && phase !== "setup") {
      setPhase("setup");
    }
  }, [quiz, phase]);

  const handleSetupLoad = useCallback(
    (loadedQuiz: { id: string; title: string; items: QuizItem[]; question_type?: "mcq" | "open_ended" }) => {
      setQuiz(loadedQuiz);
      setSetupError(null);
      setPhase("lobby");
    },
    []
  );

  const handleUseDefault = useCallback(() => {
    setLoading(true);
    setSetupError(null);
    getQuiz("panic")
      .then(setQuiz)
      .then(() => setPhase("lobby"))
      .catch(() => setSetupError("Could not load default questions."))
      .finally(() => setLoading(false));
  }, []);

  const startExam = () => {
    setExamActive(true);
    const el = document.documentElement;
    if (el.requestFullscreen) el.requestFullscreen().catch(() => {});
    else if ((el as HTMLElement & { webkitRequestFullscreen?: () => void }).webkitRequestFullscreen) {
      (el as HTMLElement & { webkitRequestFullscreen: () => void }).webkitRequestFullscreen();
    }
    if (quiz) {
      const initial: Record<string, string> = {};
      quiz.items.forEach((q) => (initial[q.id] = ""));
      setAnswers(initial);
    }
    setPhase("exam");
  };

  const handleSubmit = useCallback(async (wasTimeUp?: boolean) => {
    if (!quiz) return;
    if (wasTimeUp) setTimeUp(true);
    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await postQuizSubmit("panic", {
        answers: quiz.items.map((q) => ({
          question_id: q.id,
          answer: answers[q.id] ?? "",
        })),
        items: quiz.items,
      });
      setResults(res.results);
      setWeakTopicsText(res.weak_topics_text ?? null);
      setRecommendationText(res.recommendation_text ?? null);
      if (document.exitFullscreen) document.exitFullscreen().catch(() => {});
      else if ((document as Document & { webkitExitFullscreen?: () => void }).webkitExitFullscreen) {
        (document as Document & { webkitExitFullscreen: () => void }).webkitExitFullscreen();
      }
      setPhase("results");
      setExamActive(false);
    } catch (e) {
      enqueueSyncItem({
        type: "quiz_result",
        payload: {
          quizId: "panic",
          answers: quiz.items.map((q) => ({ question_id: q.id, answer: answers[q.id] ?? "" })),
          items: quiz.items,
        },
      });
      setResults(
        quiz.items.map((q) => ({
          question_id: q.id,
          correct: false,
          score: 0,
          correct_answer: "",
          explanation: "Saved locally. Will sync when online.",
        }))
      );
      if (document.exitFullscreen) document.exitFullscreen().catch(() => {});
      else if ((document as Document & { webkitExitFullscreen?: () => void }).webkitExitFullscreen) {
        (document as Document & { webkitExitFullscreen: () => void }).webkitExitFullscreen();
      }
      setPhase("results");
      setExamActive(false);
      setSubmitError(null);
    } finally {
      setSubmitting(false);
    }
  }, [quiz, answers, setExamActive]);

  const handleAnswerChange = (qid: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [qid]: value }));
  };

  const retake = () => {
    setExamActive(false);
    setPhase("setup");
    setQuiz(null);
    setAnswers({});
    setResults([]);
    setWeakTopicsText(null);
    setRecommendationText(null);
    setTimeUp(false);
  };

  if (phase === "setup") {
    return (
      <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
        <Setup
          onLoad={handleSetupLoad}
          loading={setupLoading}
          error={setupError}
          onErrorClear={() => setSetupError(null)}
          setLoading={setSetupLoading}
          setError={setSetupError}
          onUseDefault={handleUseDefault}
        />
      </PageChrome>
    );
  }

  if (loading || !quiz) {
    return (
      <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold text-primary">Panic Mode</h2>
          <LoadingSpinner
            loading={loading}
            message={loading ? "Loading exam..." : "No exam available."}
          />
        </div>
      </PageChrome>
    );
  }

  const hasItems = quiz.items.length > 0;
  if (!hasItems) {
    return (
      <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold text-primary">Panic Mode</h2>
          <div className="content-card rounded-card p-5 border border-glass-border">
            <p className="text-primary/80">No panic mode questions available.</p>
          </div>
        </div>
      </PageChrome>
    );
  }

  if (phase === "lobby") {
    return (
      <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
        <Lobby
          quiz={quiz}
          durationMinutes={durationMinutes}
          onDurationChange={setDurationMinutes}
          onStart={startExam}
        />
      </PageChrome>
    );
  }

  if (phase === "exam") {
    return (
      <ExamScreen
        quiz={quiz}
        durationMinutes={durationMinutes}
        answers={answers}
        onAnswerChange={handleAnswerChange}
        onSubmit={handleSubmit}
        submitting={submitting}
        submitError={submitError}
      />
    );
  }

  return (
    <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
      <Results
        quiz={quiz}
        answers={answers}
        results={results}
        timeUp={timeUp}
        weakTopicsText={weakTopicsText}
        recommendationText={recommendationText}
        onRetake={retake}
      />
    </PageChrome>
  );
}
