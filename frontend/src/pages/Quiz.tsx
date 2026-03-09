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
    // Topic source: use topic_input or fall back to subject (backend accepts both)
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
        const topicOrSubject = topicInput.trim() || subject;
        res = await postQuizGenerate({
          source: "topic",
          subject,
          topic_text: topicOrSubject,
          query: topicOrSubject,
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
      <div style={{ maxWidth: 640, margin: "0 auto", padding: "32px 24px 80px" }}>
        {/* Title */}
        <div style={{ marginBottom: 28 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
            <div style={{
              width: 42, height: 42, borderRadius: 13,
              background: "linear-gradient(135deg, #FA5C5C, #FD8A6B)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 20, boxShadow: "0 4px 14px rgba(250,92,92,0.3)"
            }}>🧠</div>
            <h1 style={{ fontSize: 26, fontWeight: 900, color: "var(--text-primary)", margin: 0 }}>
              Quiz Generator
            </h1>
          </div>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginLeft: 54 }}>
            Powered by Ollama · Runs fully offline on your device
          </p>
        </div>

        {showAssignments && (
          <section style={{ marginBottom: 32 }}>
            <h2 style={{ fontSize: 15, fontWeight: 800, color: "var(--text-primary)", marginBottom: 14 }}>Assigned by Teacher</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {assignments.map((a) => (
                <div key={a.id} style={{
                  background: "var(--bg-card)",
                  borderRadius: 16,
                  border: "1.5px solid var(--border-color)",
                  boxShadow: "var(--shadow-card)",
                  padding: "18px 20px 16px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 10
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)" }}>{a.title}</span>
                    <span style={{ fontSize: 13, color: isPastDue(a.due_date) ? "#FA5C5C" : "var(--text-secondary)" }}>
                      Due {a.due_date || "—"}
                    </span>
                  </div>
                  <span style={{
                    alignSelf: "flex-start",
                    fontSize: 12,
                    fontWeight: 700,
                    background: `${statusColor(a.status)}20`,
                    color: statusColor(a.status),
                    borderRadius: 8,
                    padding: "2px 10px",
                    marginBottom: 8
                  }}>{a.status}</span>
                  <button
                    type="button"
                    onClick={() => navigate(`/quiz/${a.quiz_id}`)}
                    style={{
                      marginTop: 2,
                      padding: "10px 0",
                      background: "linear-gradient(135deg, #00a8e8, #0088c7)",
                      color: "#fff",
                      border: "none",
                      borderRadius: 10,
                      fontWeight: 800,
                      fontSize: 14,
                      cursor: "pointer",
                      boxShadow: "0 2px 10px rgba(0,168,232,0.18)",
                      transition: "all 0.18s"
                    }}
                  >
                    Start Quiz →
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Card Wrapper for form */}
        <div style={{
          background: "var(--bg-card)",
          borderRadius: 20,
          border: "1.5px solid var(--border-color)",
          boxShadow: "var(--shadow-card)",
          padding: "28px 28px 24px",
          display: "flex",
          flexDirection: "column",
          gap: 24
        }}>
          {/* Source */}
          <div>
            <label style={{
              fontSize: 11,
              fontWeight: 700,
              color: "#6b7280",
              textTransform: "uppercase",
              letterSpacing: "0.07em",
              marginBottom: 10,
              display: "block"
            }}>Source</label>
            <div role="tablist" aria-label="Quiz source type" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {SOURCE_TABS.map((s) => {
                const active = sourceTab === s.id;
                return (
                  <button
                    key={s.id}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    aria-label={`Select ${s.label} as quiz source`}
                    tabIndex={active ? 0 : -1}
                    onClick={() => { setSourceTab(s.id); setGenError(null); }}
                    style={{
                      padding: "9px 16px",
                      borderRadius: 99,
                      fontWeight: 700,
                      fontSize: 13,
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 7,
                      border: "none",
                      cursor: "pointer",
                      background: active ? "linear-gradient(135deg,#FA5C5C,#FD8A6B)" : "var(--bg-hover)",
                      color: active ? "#fff" : "var(--text-secondary)",
                      boxShadow: active ? "0 4px 12px rgba(250,92,92,0.3)" : undefined,
                      transition: "all 0.18s"
                    }}
                  >
                    {s.icon} {s.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Textbook */}
          {sourceTab === "textbook" && (
            <div>
              <label style={{
                fontSize: 11,
                fontWeight: 700,
                color: "var(--text-secondary)",
                textTransform: "uppercase",
                letterSpacing: "0.07em",
                marginBottom: 10,
                display: "block"
              }}>Textbook</label>
              <select
                value={selectedTextbook}
                onChange={(e) => setSelectedTextbook(e.target.value)}
                style={{
                  width: "100%",
                  padding: "13px 16px",
                  border: "1.5px solid var(--border-color)",
                  borderRadius: 12,
                  fontSize: 14,
                  color: "var(--text-primary)",
                  background: "var(--bg-input)",
                  outline: "none",
                  cursor: "pointer",
                  appearance: "auto",
                  fontFamily: "inherit",
                  transition: "border 0.15s, box-shadow 0.15s"
                }}
                onFocus={e => e.target.style.borderColor = "#00a8e8"}
                onBlur={e => e.target.style.borderColor = "#e8edf5"}
              >
                <option value="">— Select textbook —</option>
                {textbooks.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
          )}

          {/* Weblink */}
          {sourceTab === "weblink" && (
            <div>
              <label style={{
                fontSize: 11,
                fontWeight: 700,
                color: "var(--text-secondary)",
                textTransform: "uppercase",
                letterSpacing: "0.07em",
                marginBottom: 10,
                display: "block"
              }}>Paste a URL…</label>
              <input
                type="url"
                placeholder="https://example.com/article"
                value={weblinkUrl}
                onChange={(e) => { setWeblinkUrl(e.target.value); setGenError(null); }}
                style={{
                  width: "100%",
                  padding: "14px 18px",
                  border: "1.5px solid var(--border-color)",
                  borderRadius: 12,
                  fontSize: 14,
                  color: "var(--text-primary)",
                  background: "var(--bg-input)",
                  outline: "none",
                  fontFamily: "inherit",
                  transition: "border 0.15s, box-shadow 0.15s"
                }}
                onFocus={e => e.target.style.borderColor = "#00a8e8"}
                onBlur={e => e.target.style.borderColor = "#e8edf5"}
              />
              {sourceTab === "weblink" && genError && (
                <p style={{ fontSize: 13, color: "#FA5C5C", marginTop: 8 }} role="alert">{genError}</p>
              )}
            </div>
          )}

          {/* File */}
          {sourceTab === "file" && (
            <div>
              <label style={{
                fontSize: 11,
                fontWeight: 700,
                color: "var(--text-secondary)",
                textTransform: "uppercase",
                letterSpacing: "0.07em",
                marginBottom: 10,
                display: "block"
              }}>Upload file (PDF or PPT)</label>
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: `2px dashed ${isDragOver ? "#00a8e8" : "var(--border-color)"}`,
                  background: isDragOver ? "rgba(0,168,232,0.05)" : "var(--bg-input)",
                  padding: 24,
                  borderRadius: 12,
                  cursor: "pointer",
                  textAlign: "center",
                  fontSize: 14,
                  color: "var(--text-primary)",
                  fontFamily: "inherit",
                  transition: "border 0.15s, box-shadow 0.15s"
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

          {/* Paste */}
          {sourceTab === "paste" && (
            <div>
              <label style={{
                fontSize: 11,
                fontWeight: 700,
                color: "var(--text-secondary)",
                textTransform: "uppercase",
                letterSpacing: "0.07em",
                marginBottom: 10,
                display: "block"
              }}>Paste your notes or article text…</label>
              <textarea
                placeholder="Paste your notes, an article, or any text here…"
                value={pasteText}
                onChange={(e) => {
                  const v = e.target.value;
                  if (v.length <= PASTE_MAX) setPasteText(v);
                  setGenError(null);
                }}
                maxLength={PASTE_MAX}
                rows={6}
                style={{
                  width: "100%",
                  padding: "14px 18px",
                  border: "1.5px solid var(--border-color)",
                  borderRadius: 12,
                  fontSize: 14,
                  color: "var(--text-primary)",
                  background: "var(--bg-input)",
                  outline: "none",
                  fontFamily: "inherit",
                  resize: "vertical",
                  transition: "border 0.15s, box-shadow 0.15s"
                }}
                onFocus={e => e.target.style.borderColor = "#00a8e8"}
                onBlur={e => e.target.style.borderColor = "#e8edf5"}
              />
              <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 6 }}>{pasteText.length} / {PASTE_MAX}</p>
              {sourceTab === "paste" && genError && (
                <p style={{ fontSize: 13, color: "#FA5C5C", marginTop: 8 }} role="alert">{genError}</p>
              )}
            </div>
          )}

          {/* Topic */}
          <div>
            <label style={{
              fontSize: 11,
              fontWeight: 700,
              color: "var(--text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.07em",
              marginBottom: 10,
              display: "block"
            }}>Topic or concept (optional)</label>
            <input
              type="text"
              placeholder="e.g. Photosynthesis, Newton's Laws, World War II..."
              value={topicInput}
              onChange={(e) => { setTopicInput(e.target.value); setGenError(null); }}
              aria-describedby="quiz-topic-hint"
              style={{
                width: "100%",
                padding: "14px 18px",
                border: "1.5px solid var(--border-color)",
                borderRadius: 12,
                fontSize: 14,
                color: "var(--text-primary)",
                background: "var(--bg-input)",
                outline: "none",
                fontFamily: "inherit",
                transition: "border 0.15s, box-shadow 0.15s"
              }}
              onFocus={e => e.target.style.borderColor = "#00a8e8"}
              onBlur={e => e.target.style.borderColor = "#e8edf5"}
            />
            <p id="quiz-topic-hint" style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 6 }}>
              Quick Topic: enter a concept or leave blank to use the subject below. Optional for other sources.
            </p>
          </div>

          {/* Subject */}
          <div>
            <label style={{
              fontSize: 11,
              fontWeight: 700,
              color: "var(--text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.07em",
              marginBottom: 10,
              display: "block"
            }}>Subject</label>
            <select
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              style={{
                width: "100%",
                padding: "13px 16px",
                border: "1.5px solid var(--border-color)",
                borderRadius: 12,
                fontSize: 14,
                color: "var(--text-primary)",
                background: "var(--bg-input)",
                outline: "none",
                cursor: "pointer",
                appearance: "auto",
                fontFamily: "inherit",
                transition: "border 0.15s, box-shadow 0.15s"
              }}
              onFocus={e => e.target.style.borderColor = "#00a8e8"}
              onBlur={e => e.target.style.borderColor = "#e8edf5"}
            >
              {SUBJECTS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* Question Type Toggle */}
          <div>
            <label style={{
              fontSize: 11,
              fontWeight: 700,
              color: "var(--text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.07em",
              marginBottom: 10,
              display: "block"
            }} id="quiz-qtype-label">Question type</label>
            <div role="group" aria-labelledby="quiz-qtype-label" style={{
              display: "inline-flex",
              background: "var(--bg-hover)",
              borderRadius: 99,
              padding: 4
            }}>
              <button
                type="button"
                onClick={() => setQType("mcq")}
                aria-pressed={qType === "mcq"}
                aria-label="Multiple choice questions"
                style={{
                  padding: "8px 22px",
                  borderRadius: 99,
                  border: "none",
                  fontWeight: 700,
                  fontSize: 13,
                  fontFamily: "inherit",
                  cursor: "pointer",
                  background: qType === "mcq" ? "var(--bg-card)" : "transparent",
                  color: qType === "mcq" ? "var(--text-primary)" : "var(--text-secondary)",
                  boxShadow: qType === "mcq" ? "0 2px 8px rgba(0,0,0,0.1)" : undefined,
                  transition: "all 0.18s"
                }}
              >
                MCQ
              </button>
              <button
                type="button"
                onClick={() => setQType("open_ended")}
                aria-pressed={qType === "open_ended"}
                aria-label="Open-ended questions"
                style={{
                  padding: "8px 22px",
                  borderRadius: 99,
                  border: "none",
                  fontWeight: 700,
                  fontSize: 13,
                  fontFamily: "inherit",
                  cursor: "pointer",
                  background: qType === "open_ended" ? "var(--bg-card)" : "transparent",
                  color: qType === "open_ended" ? "var(--text-primary)" : "var(--text-secondary)",
                  boxShadow: qType === "open_ended" ? "0 2px 8px rgba(0,0,0,0.1)" : undefined,
                  transition: "all 0.18s"
                }}
              >
                Open Ended
              </button>
            </div>
          </div>

          {/* Count Buttons */}
          <div>
            <label style={{
              fontSize: 11,
              fontWeight: 700,
              color: "var(--text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.07em",
              marginBottom: 10,
              display: "block"
            }} id="quiz-count-label">Count</label>
            <div role="group" aria-labelledby="quiz-count-label" style={{ display: "flex", gap: 10 }}>
              {COUNTS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setCount(c)}
                  aria-pressed={count === c}
                  aria-label={`${c} questions`}
                  style={{
                    width: 52,
                    height: 44,
                    borderRadius: 12,
                    fontWeight: 800,
                    fontSize: 15,
                    fontFamily: "inherit",
                    border: "none",
                    cursor: "pointer",
                    background: count === c ? "linear-gradient(135deg,#00a8e8,#0088c7)" : "var(--bg-hover)",
                    color: count === c ? "#fff" : "var(--text-secondary)",
                    boxShadow: count === c ? "0 4px 10px rgba(0,168,232,0.3)" : undefined,
                    transition: "all 0.18s"
                  }}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          {/* Difficulty */}
          <div>
            <label style={{
              fontSize: 11,
              fontWeight: 700,
              color: "var(--text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.07em",
              marginBottom: 10,
              display: "block"
            }}>Difficulty</label>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
              style={{
                width: "100%",
                padding: "13px 16px",
                border: "1.5px solid var(--border-color)",
                borderRadius: 12,
                fontSize: 14,
                color: "var(--text-primary)",
                background: "var(--bg-input)",
                outline: "none",
                cursor: "pointer",
                appearance: "auto",
                fontFamily: "inherit",
                transition: "border 0.15s, box-shadow 0.15s"
              }}
              onFocus={e => e.target.style.borderColor = "#00a8e8"}
              onBlur={e => e.target.style.borderColor = "#e8edf5"}
            >
              {DIFFICULTIES.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Generate Button */}
        <button
          type="button"
          onClick={handleGenerate}
          disabled={generating}
          aria-label={generating ? "Generating quiz, please wait" : "Generate quiz"}
          aria-busy={generating}
          style={{
            width: "100%",
            padding: 16,
            background: "linear-gradient(135deg, #FA5C5C, #FD8A6B)",
            color: "white",
            border: "none",
            borderRadius: 14,
            fontSize: 15,
            fontWeight: 800,
            cursor: generating ? "not-allowed" : "pointer",
            boxShadow: "0 6px 20px rgba(250,92,92,0.35)",
            transition: "all 0.18s",
            fontFamily: "inherit",
            letterSpacing: "0.01em",
            marginTop: 16
          }}
          onMouseOver={e => { e.currentTarget.style.boxShadow = "0 8px 28px rgba(250,92,92,0.45)"; e.currentTarget.style.transform = "translateY(-1px)"; }}
          onMouseOut={e => { e.currentTarget.style.boxShadow = "0 6px 20px rgba(250,92,92,0.35)"; e.currentTarget.style.transform = "none"; }}
        >
          {generating ? "🧠 Generating questions..." : "Generate Quiz →"}
        </button>

        {genError && (
          <p style={{ fontSize: 14, color: "#FA5C5C", marginTop: 18, fontWeight: 600 }} role="alert">
            {genError}
          </p>
        )}
      </div>
    </PageChrome>
  );
}
