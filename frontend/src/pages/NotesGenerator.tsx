/**
 * Notes Generator — generate structured study notes from pasted text.
 * Uses local Ollama via /api/notes/generate. Fully offline — no cloud required.
 */

import { useState, useEffect } from "react";
import { PageChrome } from "../components";
import {
  generateNotes,
  generateNotesFromTextbook,
  getTextbooks,
  getOllamaModels,
  type TextbooksResponse,
  type OllamaModelsResponse,
} from "../services/api";
import { useNotification } from "../contexts/NotificationContext";
import { Icons } from "../components/icons";
import {
  loadSavedNotesFromStorage,
  saveNoteToStorage,
  deleteSavedNote,
  type SavedNote,
} from "../services/storage";
import "./NotesGenerator.css";

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

const STYLES = [
  { id: "summary" as const, label: "Summary", desc: "Concise bullet points" },
  { id: "detailed" as const, label: "Detailed", desc: "Full notes with headings" },
  { id: "revision" as const, label: "Revision", desc: "Exam tips and definitions" },
];

const PASTE_MIN = 100;

function renderNotes(text: string) {
  if (!text) return null;
  return text.split("\n").map((line, i) => {
    if (!line.trim()) return <div key={i} style={{ height: 10 }} />;
    if (line.startsWith("#### "))
      return <p key={i} style={{ fontWeight: 700, fontSize: 13, color: "var(--text-primary)", marginBottom: 2 }}>{line.replace("#### ", "")}</p>;
    if (line.startsWith("### "))
      return <p key={i} style={{ fontWeight: 800, fontSize: 14, color: "var(--text-primary)", marginTop: 12, marginBottom: 4 }}>{line.replace("### ", "")}</p>;
    if (line.startsWith("## "))
      return <p key={i} style={{ fontWeight: 900, fontSize: 16, color: "var(--text-primary)", marginTop: 16, marginBottom: 6, borderBottom: "1.5px solid var(--border-color)", paddingBottom: 4 }}>{line.replace("## ", "")}</p>;
    if (line.startsWith("# "))
      return <p key={i} style={{ fontWeight: 900, fontSize: 18, color: "var(--text-primary)", marginTop: 16, marginBottom: 8 }}>{line.replace("# ", "")}</p>;
    if (line.startsWith("* ") || line.startsWith("- "))
      return <div key={i} style={{ display: "flex", gap: 8, marginBottom: 3, paddingLeft: 8 }}><span style={{ color: "#FA5C5C", fontWeight: 700, flexShrink: 0 }}>•</span><span style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7 }}>{line.replace(/^[\*\-] /, "")}</span></div>;
    if (line.startsWith("**") && line.endsWith("**"))
      return <p key={i} style={{ fontWeight: 700, fontSize: 13, color: "var(--text-primary)", marginBottom: 3 }}>{line.replace(/\*\*/g, "")}</p>;
    return <p key={i} style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.75, marginBottom: 3 }}>{line}</p>;
  });
}

function downloadDoc(text: string, title: string) {
  const lines = text.split("\n");
  let html = `
    <html xmlns:o="urn:schemas-microsoft-com:office:office"
          xmlns:w="urn:schemas-microsoft-com:office:word"
          xmlns="http://www.w3.org/TR/REC-html40">
    <head><meta charset="utf-8"><title>${title}</title>
    <style>
      body { font-family: Calibri, sans-serif; font-size: 11pt; line-height: 1.6; margin: 2cm; }
      h1 { font-size: 18pt; font-weight: bold; color: #0d1b2a; margin-top: 16pt; }
      h2 { font-size: 15pt; font-weight: bold; color: #0d1b2a; margin-top: 14pt; border-bottom: 1pt solid #ccc; padding-bottom: 3pt; }
      h3 { font-size: 13pt; font-weight: bold; color: #333; margin-top: 10pt; }
      h4 { font-size: 11pt; font-weight: bold; margin-top: 8pt; }
      p  { margin: 4pt 0; }
      li { margin: 3pt 0; }
      ul { margin-left: 20pt; }
    </style></head><body>`;

  for (const line of lines) {
    if (!line.trim()) { html += "<br/>"; continue; }
    const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    if (line.startsWith("#### ")) html += `<h4>${esc(line.replace("#### ", ""))}</h4>`;
    else if (line.startsWith("### ")) html += `<h3>${esc(line.replace("### ", ""))}</h3>`;
    else if (line.startsWith("## ")) html += `<h2>${esc(line.replace("## ", ""))}</h2>`;
    else if (line.startsWith("# ")) html += `<h1>${esc(line.replace("# ", ""))}</h1>`;
    else if (line.startsWith("* ") || line.startsWith("- ")) html += `<ul><li>${esc(line.replace(/^[\*\-] /, ""))}</li></ul>`;
    else if (line.startsWith("**") && line.endsWith("**")) html += `<p><b>${esc(line.replace(/\*\*/g, ""))}</b></p>`;
    else html += `<p>${esc(line)}</p>`;
  }

  html += "</body></html>";

  const blob = new Blob(["\ufeff" + html], { type: "application/msword;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${(title || "notes").replace(/\s+/g, "_")}.doc`;
  a.click();
  URL.revokeObjectURL(url);
}

export function NotesGeneratorPage() {
  const { push } = useNotification();
  const [sourceTab, setSourceTab] = useState<"paste" | "textbook">("paste");
  const [pasteText, setPasteText] = useState("");
  const [textbooks, setTextbooks] = useState<TextbooksResponse["textbooks"]>([]);
  const [selectedTextbook, setSelectedTextbook] = useState("");
  const [subject, setSubject] = useState("General");
  const [topic, setTopic] = useState("");
  const [style, setStyle] = useState<"summary" | "detailed" | "revision">("summary");
  const [generating, setGenerating] = useState(false);
  const [notes, setNotes] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingTextbooks, setLoadingTextbooks] = useState(false);
  const [ollamaStatus, setOllamaStatus] = useState<OllamaModelsResponse | null>(null);
  const [savedNotes, setSavedNotes] = useState<SavedNote[]>(() => loadSavedNotesFromStorage());

  const refreshSavedNotes = () => setSavedNotes(loadSavedNotesFromStorage());

  useEffect(() => {
    getOllamaModels()
      .then(setOllamaStatus)
      .catch(() => setOllamaStatus(null));
  }, []);

  const canGenerate =
    sourceTab === "paste"
      ? pasteText.trim().length >= PASTE_MIN
      : !!selectedTextbook && textbooks.length > 0;

  const handleGenerate = async () => {
    if (!canGenerate) return;
    setGenerating(true);
    setNotes(null);
    setError(null);

    try {
      let res: { generated_text: string; subject: string; topic?: string };
      if (sourceTab === "paste") {
        const sourceText = pasteText.trim();
        if (sourceText.length < PASTE_MIN) {
          setError(`Please paste at least ${PASTE_MIN} characters of text.`);
          setGenerating(false);
          return;
        }
        res = await generateNotes({
          text: sourceText,
          subject,
          topic: topic.trim() || undefined,
          style,
        });
      } else {
        if (!selectedTextbook) {
          setError("Please select a textbook.");
          setGenerating(false);
          return;
        }
        res = await generateNotesFromTextbook({
          textbook_id: selectedTextbook,
          subject,
          topic: topic.trim() || undefined,
          style,
        });
      }
      setNotes(res.generated_text);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to generate notes.";
      setError(msg);
      push({ type: "error", title: "Notes generation failed", message: msg });
    } finally {
      setGenerating(false);
    }
  };

  const handleCopy = () => {
    if (!notes) return;
    navigator.clipboard.writeText(notes);
    push({ type: "success", title: "Copied", message: "Notes copied to clipboard." });
  };

  const handleSave = () => {
    if (!notes) return;
    const title = (topic || subject || "Notes").slice(0, 60);
    saveNoteToStorage({
      title: title || "Untitled notes",
      content: notes,
      subject,
      topic: topic.trim() || undefined,
      style,
    });
    refreshSavedNotes();
    push({ type: "success", title: "Saved", message: "Notes saved locally. Available offline." });
  };

  const handleLoadSaved = (saved: SavedNote) => {
    setNotes(saved.content);
    setSubject(saved.subject);
    setTopic(saved.topic || "");
    setStyle((saved.style as "summary" | "detailed" | "revision") || "summary");
    push({ type: "success", title: "Loaded", message: `"${saved.title}" loaded.` });
  };

  const handleDeleteSaved = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    deleteSavedNote(id);
    refreshSavedNotes();
    push({ type: "success", title: "Deleted", message: "Note removed." });
  };

  const loadTextbooks = async () => {
    setLoadingTextbooks(true);
    try {
      const r = await getTextbooks();
      setTextbooks(r.textbooks);
      if (r.textbooks.length > 0 && !selectedTextbook) {
        setSelectedTextbook(r.textbooks[0].id);
      }
    } catch {
      setTextbooks([]);
    } finally {
      setLoadingTextbooks(false);
    }
  };

  return (
    <PageChrome>
      <div className="notes-generator-page">
        <div className="notes-page-header">
          <div className="notes-header-row">
            <h1 className="notes-page-title">Notes Generator</h1>
            <span className="notes-offline-badge" title="Runs fully offline — no internet required">
              Works offline
            </span>
          </div>
          <p className="notes-page-sub">
            Generate structured study notes from your text. Uses local AI (Ollama).
            {ollamaStatus?.models?.length === 0 && (
              <span className="notes-status-warn"> — Start Ollama: <code>ollama serve</code> then <code>ollama pull llama3.2:3b-instruct</code></span>
            )}
            {ollamaStatus?.available === false && ollamaStatus?.models?.length > 0 && (
              <span className="notes-status-hint"> — Will use an available model</span>
            )}
          </p>
        </div>

        <div className="notes-layout">
          <div className="notes-form-col">
            <div className="notes-form-card content-card">
              <div className="notes-form-header">
                <span className="notes-form-icon">{Icons.notes}</span>
                <div>
                  <h2 className="notes-form-title">Create Notes</h2>
                  <p className="notes-form-sub">Paste text → Structured notes</p>
                </div>
              </div>

              <div className="notes-tabs">
                {[
                  ["paste", "Paste Text"],
                  ["textbook", "From Textbook"],
                ].map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    className={`notes-tab ${sourceTab === id ? "active" : ""}`}
                    onClick={() => {
                      setSourceTab(id as "paste" | "textbook");
                      if (id === "textbook") loadTextbooks();
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {sourceTab === "paste" && (
                <div className="notes-form-fields">
                  <label className="notes-label">Source text (min {PASTE_MIN} chars)</label>
                  <textarea
                    className="notes-textarea"
                    value={pasteText}
                    onChange={(e) => setPasteText(e.target.value)}
                    placeholder="Paste your textbook excerpt, article, or lecture notes here…"
                    rows={8}
                  />
                </div>
              )}

              {sourceTab === "textbook" && (
                <div className="notes-form-fields">
                  <label className="notes-label">Select textbook</label>
                  {loadingTextbooks ? (
                    <p className="notes-hint">Loading textbooks…</p>
                  ) : textbooks.length === 0 ? (
                  <p className="notes-hint">
                    No textbooks found. Upload one in Textbooks, or use Paste Text.
                    </p>
                  ) : (
                    <select
                      className="notes-select"
                      value={selectedTextbook}
                      onChange={(e) => setSelectedTextbook(e.target.value)}
                    >
                      {textbooks.map((tb) => (
                        <option key={tb.id} value={tb.id}>
                          {tb.name}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              )}

              <div className="notes-form-row">
                <div>
                  <label className="notes-label">Subject</label>
                  <select
                    className="notes-select"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                  >
                    {SUBJECTS.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="notes-label">Topic (optional)</label>
                  <input
                    type="text"
                    className="notes-input"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="e.g. Newton's Laws"
                  />
                </div>
              </div>

              <div className="notes-form-row">
                <label className="notes-label">Style</label>
                <div className="notes-style-options">
                  {STYLES.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      className={`notes-style-btn ${style === s.id ? "active" : ""}`}
                      onClick={() => setStyle(s.id)}
                    >
                      <span className="notes-style-label">{s.label}</span>
                      <span className="notes-style-desc">{s.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              <button
                type="button"
                className="notes-generate-btn"
                onClick={handleGenerate}
                disabled={!canGenerate || generating}
              >
                {generating ? "Generating…" : "Generate Notes"}
              </button>

              {error && <p className="notes-error">{error}</p>}
            </div>
          </div>

          <div className="notes-output-col">
            <div className="notes-output-card content-card">
              <h3 className="notes-output-title">Generated Notes</h3>
              {notes ? (
                <>
                  <div className="notes-output-actions">
                    <button type="button" className="notes-action-btn notes-action-save" onClick={handleSave}>
                      Save offline
                    </button>
                    <button type="button" className="notes-action-btn" onClick={handleCopy}>
                      Copy
                    </button>
                    <button
                      type="button"
                      className="notes-action-btn"
                      onClick={() => downloadDoc(notes, (topic || subject || "notes").slice(0, 60))}
                    >
                      ⬇ Download .doc
                    </button>
                  </div>
                  <div
                    className="notes-output-rendered"
                    style={{
                      background: "var(--bg-input)",
                      border: "1.5px solid var(--border-color)",
                      borderRadius: 12,
                      padding: "20px 24px",
                      maxHeight: 480,
                      overflowY: "auto",
                      fontFamily: "'Plus Jakarta Sans', sans-serif",
                    }}
                  >
                    {renderNotes(notes)}
                  </div>
                </>
              ) : (
                <p className="notes-output-empty">
                  Paste text and click Generate Notes to create structured study notes.
                </p>
              )}
              {savedNotes.length > 0 && (
                <div className="notes-saved-section">
                  <h4 className="notes-saved-title">Saved notes (offline)</h4>
                  <ul className="notes-saved-list">
                    {savedNotes.map((s) => (
                      <li key={s.id} className="notes-saved-item">
                        <button
                          type="button"
                          className="notes-saved-btn"
                          onClick={() => handleLoadSaved(s)}
                          title={`Load: ${s.title}`}
                        >
                          <span className="notes-saved-label">{s.title}</span>
                          <span className="notes-saved-meta">
                            {s.subject} · {new Date(s.saved_at).toLocaleDateString()}
                          </span>
                        </button>
                        <button
                          type="button"
                          className="notes-saved-delete"
                          onClick={(e) => handleDeleteSaved(e, s.id)}
                          title="Delete"
                          aria-label="Delete note"
                        >
                          ×
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </PageChrome>
  );
}
