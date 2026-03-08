/**
 * Quiz home page — Assigned by Teacher, then Quiz from Resources (Textbook, Web Link, File, Paste).
 * Generate buttons call appropriate API; on success navigate to /quiz/{quiz_id}.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import {
  postQuizGenerate,
  postQuizGenerateFromUrl,
  postQuizGenerateFromText,
  postQuizGenerateFromFile,
  getTextbooks,
  getStudentAssignments,
  type TextbooksResponse,
} from "../services/api";
import {
  loadAssignmentsFromStorage,
  saveAssignmentsToStorage,
  type AssignmentItem,
} from "../services/storage";
import { PageChrome } from "../components";
import "./Quiz.css";

const SUBJECTS = [
  "General",
  "Physics",
  "Chemistry",
  "Biology",
  "Maths",
  "Computer Science",
  "History",
  "English",
] as const;

const SOURCE_TABS = [
  { id: "topic" as const, icon: "💡", label: "Quick Topic" },
  { id: "textbook" as const, icon: "📚", label: "Textbook" },
  { id: "weblink" as const, icon: "🌐", label: "Web Link" },
  { id: "file" as const, icon: "📄", label: "Upload File" },
  { id: "paste" as const, icon: "✏️", label: "Paste Text" },
];

const COUNTS = [5, 10, 15, 20] as const;
const DIFFICULTIES = ["Beginner", "Intermediate", "Expert"] as const;
const PASTE_MIN = 150;
const PASTE_MAX = 3000;
const ALLOWED_EXT = [".pdf", ".ppt", ".pptx"];

export function QuizPage() {
  const navigate = useNavigate();
  const { profile, connectivityStatus } = useAuth();
  const [assignments, setAssignments] = useState<AssignmentItem[]>([]);
  const [textbooks, setTextbooks] = useState<TextbooksResponse["textbooks"]>(() => {
    try {
      return JSON.parse(localStorage.getItem("studaxis_textbooks_cache") ?? "[]");
    } catch {
      return [];
    }
  });
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  // Quiz from resources state
  const [sourceTab, setSourceTab] = useState<"topic" | "textbook" | "weblink" | "file" | "paste">("topic");
  const [topicInput, setTopicInput] = useState("");
  const [subject, setSubject] = useState("General");
  const [selectedTextbook, setSelectedTextbook] = useState("");
  const [weblinkUrl, setWeblinkUrl] = useState("");
  const [pasteText, setPasteText] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [qType, setQType] = useState<"mcq" | "open_ended">("mcq");
  const [count, setCount] = useState(10);
  const [difficulty, setDifficulty] = useState("Beginner");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isTeacherLinked = profile.profile_mode === "teacher_linked";
  const showAssignments = isTeacherLinked && assignments.length > 0;

  const loadAssignments = useCallback(async () => {
    const local = loadAssignmentsFromStorage();
    setAssignments(local);
    if (isTeacherLinked && profile.class_code) {
      try {
        const remote = await getStudentAssignments(profile.class_code);
        if (remote?.length) {
          const merged = remote.map((r) => ({
            id: r.id,
            quiz_id: r.quiz_id,
            title: r.title,
            due_date: r.due_date ?? "",
            assigned_at: r.assigned_at ?? "",
            status: (local.find((a) => a.id === r.id)?.status ?? r.status ?? "pending") as AssignmentItem["status"],
          }));
          saveAssignmentsToStorage(merged);
          setAssignments(merged);
        }
      } catch {
        setAssignments(local);
      }
    }
  }, [isTeacherLinked, profile.class_code]);

  useEffect(() => {
    loadAssignments();
  }, [loadAssignments]);

  useEffect(() => {
    getTextbooks()
      .then((r) => {
        const books = r.textbooks || [];
        setTextbooks(books);
        localStorage.setItem("studaxis_textbooks_cache", JSON.stringify(books));
      })
      .catch(() => {}); // already showing cached data
  }, []);

  const handleGenerate = async () => {
    setGenError(null);
    if (!topicInput.trim()) {
      setGenError("Field required");
      return;
    }
    if (sourceTab === "textbook") {
      if (!selectedTextbook || !selectedTextbook.trim()) {
        setGenError("Select a textbook first.");
        return;
      }
    } else if (sourceTab === "weblink") {
      if (!weblinkUrl.trim()) {
        setGenError("Enter a valid URL.");
        return;
      }
      if (connectivityStatus === "offline") {
        setGenError("You need to be connected to use web links.");
        return;
      }
    } else if (sourceTab === "file") {
      if (!uploadFile) {
        setGenError("Select or drop a PDF or PPT file.");
        return;
      }
      const ext = uploadFile.name.toLowerCase().slice(uploadFile.name.lastIndexOf("."));
      if (!ALLOWED_EXT.some((e) => ext === e)) {
        setGenError("Only PDF and PPT files are supported.");
        return;
      }
    } else if (sourceTab === "paste") {
      if (pasteText.trim().length < PASTE_MIN) {
        setGenError("Please paste at least a paragraph of text to generate a quiz from.");
        return;
      }
    }
    setGenerating(true);
    try {
      let res: { id: string };
      if (sourceTab === "topic") {
        res = await postQuizGenerate({
          source: "topic",
          subject,
          topic_text: topicInput.trim(),
          question_type: qType,
          num_questions: count,
          difficulty,
        });
      } else if (sourceTab === "textbook") {
        res = await postQuizGenerate({
          source: "materials",
          subject,
          source_ids: [selectedTextbook],
          topic_text: topicInput.trim(),
          question_type: qType,
          num_questions: count,
          difficulty,
        });
      } else if (sourceTab === "weblink") {
        res = await postQuizGenerateFromUrl({
          url: weblinkUrl.trim(),
          subject,
          topic_text: topicInput.trim(),
          num_questions: count,
          question_type: qType,
          difficulty,
        });
      } else if (sourceTab === "file" && uploadFile) {
        res = await postQuizGenerateFromFile({
          file: uploadFile,
          subject,
          topic_text: topicInput.trim(),
          num_questions: count,
          question_type: qType,
          difficulty,
        });
      } else {
        res = await postQuizGenerateFromText({
          text: pasteText.trim(),
          subject,
          topic_text: topicInput.trim(),
          num_questions: count,
          question_type: qType,
          difficulty,
        });
      }
      navigate(`/quiz/${res.id}`);
    } catch (e) {
      setGenError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const ext = f.name.toLowerCase().slice(f.name.lastIndexOf("."));
    if (!ALLOWED_EXT.some((ex) => ext === ex)) {
      setGenError("Only PDF and PPT files are supported");
      setUploadFile(null);
    } else {
      setGenError(null);
      setUploadFile(f);
    }
    e.target.value = "";
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (!f) return;
    const ext = f.name.toLowerCase().slice(f.name.lastIndexOf("."));
    if (!ALLOWED_EXT.some((ex) => ext === ex)) {
      setGenError("Only PDF and PPT files are supported");
      setUploadFile(null);
    } else {
      setGenError(null);
      setUploadFile(f);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => setIsDragOver(false);

  const isPastDue = (due: string) => {
    if (!due) return false;
    try {
      const d = new Date(due);
      const today = new Date();
      today.setHours(23, 59, 59, 999);
      return d.getTime() < today.getTime();
    } catch {
      return false;
    }
  };

  const statusColor = (s: string) => {
    if (s === "completed") return "#10b981";
    if (s === "in_progress") return "#00a8e8";
    return "#9ca3af";
  };

  return (
    <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
      <div className="quiz-home">
        <h1 className="quiz-home__title">Quiz</h1>

        {showAssignments && (
          <section className="quiz-home__section">
            <h2 className="quiz-home__section-title">Assigned by Teacher</h2>
            <div className="quiz-home__cards">
              {assignments.map((a) => (
                <div key={a.id} className="quiz-home__card quiz-home__card--assignment">
                  <div className="quiz-home__card-header">
                    <span className="quiz-home__card-title">{a.title}</span>
                    <span
                      className="quiz-home__card-due"
                      style={{ color: isPastDue(a.due_date) ? "#FA5C5C" : undefined }}
                    >
                      Due {a.due_date || "—"}
                    </span>
                  </div>
                  <span
                    className="quiz-home__chip"
                    style={{ background: `${statusColor(a.status)}20`, color: statusColor(a.status) }}
                  >
                    {a.status}
                  </span>
                  <button
                    type="button"
                    className="quiz-home__btn quiz-home__btn--primary"
                    onClick={() => navigate(`/quiz/${a.quiz_id}`)}
                  >
                    Start Quiz →
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="quiz-home__section">
          <h2 className="quiz-home__section-title">Quiz from Resources</h2>
          <div className="quiz-home__form">
            <div className="quiz-home__field">
              <label>Source</label>
              <div className="quiz-home__pills">
                {SOURCE_TABS.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    className={`quiz-home__pill ${sourceTab === s.id ? "quiz-home__pill--on" : ""}`}
                    onClick={() => { setSourceTab(s.id); setGenError(null); }}
                  >
                    {s.icon} {s.label}
                  </button>
                ))}
              </div>
            </div>

            {sourceTab === "textbook" && (
              <div className="quiz-home__field">
                <label>Textbook</label>
                <select
                  value={selectedTextbook}
                  onChange={(e) => setSelectedTextbook(e.target.value)}
                  className="quiz-home__input"
                >
                  <option value="">— Select textbook —</option>
                  {textbooks.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>
            )}

            {sourceTab === "weblink" && (
              <div className="quiz-home__field">
                <label>Paste a URL…</label>
                <input
                  type="url"
                  className="quiz-home__input"
                  placeholder="https://example.com/article"
                  value={weblinkUrl}
                  onChange={(e) => { setWeblinkUrl(e.target.value); setGenError(null); }}
                />
                {sourceTab === "weblink" && genError && (
                  <p className="quiz-home__error" style={{ marginTop: 8 }} role="alert">{genError}</p>
                )}
              </div>
            )}

            {sourceTab === "file" && (
              <div className="quiz-home__field">
                <label>Upload file (PDF or PPT)</label>
                <div
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onClick={() => fileInputRef.current?.click()}
                  style={{
                    border: `2px dashed ${isDragOver ? "var(--accent-blue, #00a8e8)" : "var(--glass-border, #e2e8f0)"}`,
                    background: isDragOver ? "rgba(0,168,232,0.05)" : "var(--surface-light, #f8fafc)",
                    padding: 24,
                    borderRadius: 12,
                    cursor: "pointer",
                    textAlign: "center",
                  }}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.ppt,.pptx"
                    onChange={handleFileSelect}
                    style={{ display: "none" }}
                  />
                  {uploadFile ? (
                    <span>{uploadFile.name}</span>
                  ) : (
                    <span>Drag & drop PDF or PPT here, or click to browse</span>
                  )}
                </div>
              </div>
            )}

            {sourceTab === "paste" && (
              <div className="quiz-home__field">
                <label>Paste your notes or article text…</label>
                <textarea
                  className="quiz-home__input"
                  placeholder="Paste your notes, an article, or any text here…"
                  value={pasteText}
                  onChange={(e) => {
                    const v = e.target.value;
                    if (v.length <= PASTE_MAX) setPasteText(v);
                    setGenError(null);
                  }}
                  maxLength={PASTE_MAX}
                  rows={6}
                  style={{ resize: "vertical" }}
                />
                <p style={{ fontSize: 12, color: "var(--primary-60)", marginTop: 4 }}>{pasteText.length} / {PASTE_MAX}</p>
                {sourceTab === "paste" && genError && (
                  <p className="quiz-home__error" style={{ marginTop: 8 }} role="alert">{genError}</p>
                )}
              </div>
            )}

            <div className="quiz-home__field">
              <label>Topic or concept</label>
              <input
                type="text"
                className="quiz-home__input"
                placeholder="e.g. Photosynthesis, Newton's Laws, World War II..."
                value={topicInput}
                onChange={(e) => { setTopicInput(e.target.value); setGenError(null); }}
                required
              />
            </div>
            <div className="quiz-home__field">
              <label>Subject</label>
              <select value={subject} onChange={(e) => setSubject(e.target.value)}>
                {SUBJECTS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div className="quiz-home__field">
              <label>Question type</label>
              <div className="quiz-home__toggle">
                <button
                  type="button"
                  className={qType === "mcq" ? "quiz-home__toggle--on" : ""}
                  onClick={() => setQType("mcq")}
                >
                  MCQ
                </button>
                <button
                  type="button"
                  className={qType === "open_ended" ? "quiz-home__toggle--on" : ""}
                  onClick={() => setQType("open_ended")}
                >
                  Open Ended
                </button>
              </div>
            </div>
            <div className="quiz-home__field">
              <label>Count</label>
              <div className="quiz-home__count">
                {COUNTS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    className={count === c ? "quiz-home__toggle--on" : ""}
                    onClick={() => setCount(c)}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>
            <div className="quiz-home__field">
              <label>Difficulty</label>
              <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
                {DIFFICULTIES.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
            <button
              type="button"
              className="quiz-home__btn quiz-home__btn--primary quiz-home__btn--block"
              onClick={handleGenerate}
              disabled={generating}
            >
              {generating ? "🧠 Generating questions..." : "Generate Quiz →"}
            </button>
          </div>
        </section>

        {genError && (sourceTab !== "weblink" && sourceTab !== "paste") && (
          <p className="quiz-home__error" role="alert">
            {genError}
          </p>
        )}
      </div>
    </PageChrome>
  );
}
