import { useState, useRef, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon } from '../components/icons/Icon';
import { useTeacher } from '../context/TeacherContext';
import { useClass } from '../context/ClassContext';
import { GlassCard } from '../components/dashboard/GlassCard';
import { EmptyState } from '../components/shared/EmptyState';

const NOTES_API_BASE = import.meta.env.VITE_API_GATEWAY_URL || '';
const SHOW_TEACHER_NOTES = import.meta.env.VITE_SHOW_TEACHER_NOTES === 'true';

const ACCEPTED_TYPES = '.pdf,.ppt,.pptx,.doc,.docx,.txt';
const isAcceptedFile = (f: File) => /\.(pdf|ppt|pptx|doc|docx|txt)$/i.test(f.name);

/** Renders structured notes: headings, bullets, key terms, collapsible sections */
function NotesRenderer({
  text,
  collapsible = true,
}: {
  text: string;
  collapsible?: boolean;
}) {
  const lines = text.split('\n');
  const sections: { heading: string; content: string[] }[] = [];
  let current = { heading: '', content: [] as string[] };

  for (const line of lines) {
    const h2 = line.match(/^##\s+(.+)$/);
    const h1 = line.match(/^#\s+(.+)$/);
    const heading = h2?.[1] ?? h1?.[1];

    if (heading) {
      if (current.heading || current.content.length) {
        sections.push({ ...current, content: [...current.content] });
      }
      current = { heading, content: [] };
    } else {
      current.content.push(line);
    }
  }
  if (current.heading || current.content.length) {
    sections.push(current);
  }

  const renderInline = (s: string) => {
    // **bold** / key terms
    const parts: React.ReactNode[] = [];
    let last = 0;
    const re = /\*\*([^*]+)\*\*/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(s)) !== null) {
      parts.push(s.slice(last, m.index));
      parts.push(<mark key={m.index} className="notes-key-term">{m[1]}</mark>);
      last = m.index + m[0].length;
    }
    parts.push(s.slice(last));
    return parts;
  };

  if (sections.length === 0) {
    return (
      <div className="notes-output-plain">
        {text.split('\n').map((l, i) => (
          <p key={i}>{l || <br />}</p>
        ))}
      </div>
    );
  }

  return (
    <div className="notes-output-structured">
      {sections.map((sec, i) => {
        const items = sec.content
          .filter((l) => l.trim())
          .map((l) => {
            const trimmed = l.trim();
            const bullet = trimmed.match(/^[-*]\s+(.+)$/);
            if (bullet) {
              return { type: 'bullet' as const, text: bullet[1] };
            }
            return { type: 'paragraph' as const, text: trimmed };
          });
        const bullets: string[] = [];
        const bodyElements: ReactNode[] = [];
        items.forEach((item) => {
          if (item.type === 'bullet') {
            bullets.push(item.text);
          } else {
            if (bullets.length) {
              bodyElements.push(
                <ul key={bodyElements.length} className="notes-bullet-list">
                  {bullets.map((b, j) => (
                    <li key={j}>{renderInline(b)}</li>
                  ))}
                </ul>
              );
              bullets.length = 0;
            }
            bodyElements.push(
              <p key={bodyElements.length} className="notes-paragraph">
                {renderInline(item.text)}
              </p>
            );
          }
        });
        if (bullets.length) {
          bodyElements.push(
            <ul key={bodyElements.length} className="notes-bullet-list">
              {bullets.map((b, j) => (
                <li key={j}>{renderInline(b)}</li>
              ))}
            </ul>
          );
        }
        const body = (
          <div className="notes-section-body">
            {bodyElements}
          </div>
        );

        if (collapsible && sec.heading && items.length > 0) {
          return (
            <details key={i} className="notes-section-collapsible" open={i === 0}>
              <summary className="notes-section-heading">{sec.heading}</summary>
              {body}
            </details>
          );
        }
        return (
          <div key={i} className="notes-section">
            {sec.heading && <h3 className="notes-section-heading">{sec.heading}</h3>}
            {body}
          </div>
        );
      })}
    </div>
  );
}

/** Placeholder teacher note for "Notes by Teacher" section */
interface TeacherNote {
  id: string;
  title: string;
  teacherName: string;
  timestamp: string;
  excerpt: string;
  bookmarked?: boolean;
}

const PLACEHOLDER_TEACHER_NOTES: TeacherNote[] = [
  {
    id: '1',
    title: 'Laws of Thermodynamics — Summary',
    teacherName: 'Dr. Smith',
    timestamp: '2 days ago',
    excerpt: 'First law: Energy cannot be created or destroyed...',
  },
];

export function NotesGenerator() {
  const { teacher } = useTeacher();
  const { activeClass, classes } = useClass();
  const navigate = useNavigate();
  const [sourceTab, setSourceTab] = useState<'text' | 'textbook'>('text');
  const [viewTab, setViewTab] = useState<'generated' | 'teacher'>('generated');
  const [form, setForm] = useState({
    subject: teacher?.subject || 'Physics',
    topic: '',
    chapter: '',
    difficulty: 'medium' as 'easy' | 'medium' | 'hard',
    source: 'paste' as 'paste' | 'upload',
    pasteText: '',
    style: 'summary' as 'summary' | 'detailed' | 'revision' | 'flashcard' | 'mindmap',
    assignTo: 'all',
  });
  const [generating, setGenerating] = useState(false);
  const [notes, setNotes] = useState<string | null>(null);
  const [notesS3Url, setNotesS3Url] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const upd = (k: string, v: string) => setForm((p) => ({ ...p, [k]: v }));

  const addFiles = (files: FileList | null) => {
    if (!files) return;
    const valid = Array.from(files).filter(isAcceptedFile);
    setUploadedFiles((prev) => [...prev, ...valid]);
    // For .txt files, read and populate paste text (API uses source_material)
    const txt = valid.find((f) => /\.txt$/i.test(f.name));
    if (txt) {
      const r = new FileReader();
      r.onload = () => {
        setForm((p) => ({ ...p, pasteText: (r.result as string) || '' }));
      };
      r.readAsText(txt);
    }
  };

  const removeFile = (index: number) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    addFiles(e.dataTransfer.files);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const canGenerate =
    form.topic.trim().length > 0 &&
    (form.source === 'paste'
      ? form.pasteText.trim().length > 0
      : uploadedFiles.length > 0 || form.pasteText.trim().length > 0);

  const generate = async () => {
    if (!canGenerate) return;
    setGenerating(true);
    setNotes(null);
    setNotesS3Url(null);
    setError(null);

    const targetClassId =
      form.assignTo === 'all'
        ? (activeClass?.class_id || activeClass?.class_code || '').trim()
        : form.assignTo;
    if (!targetClassId) {
      setError('Select a class in "Push To Class" or set your class code in Settings.');
      setGenerating(false);
      return;
    }

    if (!NOTES_API_BASE) {
      setError('API Gateway URL not configured (VITE_API_GATEWAY_URL).');
      setGenerating(false);
      return;
    }

    const sourceMaterial =
      form.source === 'paste'
        ? form.pasteText.trim()
        : form.pasteText.trim() ||
          '';
    const payload = {
      subject: form.subject,
      topic: form.topic.trim(),
      chapter: form.chapter.trim() || undefined,
      difficulty: form.difficulty,
      source_material: sourceMaterial,
      note_style: form.style,
      target_class_id: targetClassId,
    };

    try {
      const url = NOTES_API_BASE.replace(/\/$/, '') + '/teacher/generateNotes';
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(90000),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data?.error || `HTTP ${res.status}: ${res.statusText}`);
      }

      const generatedText = data?.generated_text ?? data?.content ?? '';
      const s3Url = data?.s3_url ?? null;

      setNotes(generatedText || '(No content returned)');
      setNotesS3Url(s3Url || null);
    } catch (e) {
      if (e instanceof Error) {
        if (e.name === 'AbortError') {
          setError('Request timed out (90s). Try again.');
        } else {
          setError(e.message);
        }
      } else {
        setError('Failed to generate notes. Check network and API config.');
      }
    } finally {
      setGenerating(false);
    }
  };

  const handleCopy = () => {
    if (!notes) return;
    navigator.clipboard.writeText(notes);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadNotes = () => {
    if (!notes) return;
    const blob = new Blob([notes], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `notes-${form.topic.replace(/[^a-zA-Z0-9-_]/g, '-').slice(0, 40) || 'notes'}-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handlePushNotes = () => {
    navigate('/assignments');
  };

  return (
    <main id="main-content" className="page-notes" role="main">
      <div className="page-header-block">
        <h1 className="page-title">Notes Generator</h1>
        <p className="page-sub">
          Generate structured study notes from text or uploaded resources. Push to student devices on sync.
        </p>
      </div>

      <div className="notes-layout">
        <div className="notes-form-col">
          <GlassCard className="notes-form-card">
            <div className="notes-form-header">
              <div className="notes-form-icon">📝</div>
              <div>
                <div className="notes-form-title">Create Notes</div>
                <div className="notes-form-sub">Text or Textbook → Structured Notes</div>
              </div>
            </div>

            <div className="notes-tabs">
              {[
                ['text', 'Generate from Text'],
                ['textbook', 'Generate from Textbook'],
              ].map(([v, label]) => (
                <button
                  key={v}
                  type="button"
                  className={`notes-tab ${sourceTab === v ? 'active' : ''}`}
                  onClick={() => setSourceTab(v as 'text' | 'textbook')}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="notes-form-fields">
              <div className="notes-form-row">
                <div>
                  <label className="label">Subject</label>
                  <select
                    className="select"
                    value={form.subject}
                    onChange={(e) => upd('subject', e.target.value)}
                  >
                    {['Physics', 'Chemistry', 'Biology', 'Mathematics', 'Computer Science', 'History', 'English'].map(
                      (s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      )
                    )}
                  </select>
                </div>
                <div>
                  <label className="label">Note Style</label>
                  <select
                    className="select"
                    value={form.style}
                    onChange={(e) => upd('style', e.target.value)}
                  >
                    <option value="summary">Summary Notes</option>
                    <option value="detailed">Detailed Explanation</option>
                    <option value="revision">Revision Sheet</option>
                    <option value="flashcard">Flashcard-style</option>
                    <option value="mindmap">Mind Map Outline</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="label">Topic / Chapter *</label>
                <input
                  className="input"
                  placeholder="e.g. Laws of Thermodynamics, Chapter 12..."
                  value={form.topic}
                  onChange={(e) => upd('topic', e.target.value)}
                />
              </div>

              {sourceTab === 'textbook' && (
                <div className="notes-form-row">
                  <div>
                    <label className="label">Chapter (optional)</label>
                    <input
                      className="input"
                      placeholder="Chapter 5"
                      value={form.chapter}
                      onChange={(e) => upd('chapter', e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="label">Difficulty Level</label>
                    <select
                      className="select"
                      value={form.difficulty}
                      onChange={(e) => upd('difficulty', e.target.value)}
                    >
                      <option value="easy">Easy</option>
                      <option value="medium">Medium</option>
                      <option value="hard">Hard</option>
                    </select>
                  </div>
                </div>
              )}

              <div>
                <label className="label">Source Material</label>
                {sourceTab === 'text' ? (
                  <textarea
                    className="input notes-textarea"
                    rows={6}
                    placeholder="Paste your lecture notes, textbook excerpt, or any material here..."
                    value={form.pasteText}
                    onChange={(e) => upd('pasteText', e.target.value)}
                  />
                ) : (
                  <>
                    <textarea
                      className="input notes-textarea"
                      rows={4}
                      placeholder="Paste excerpt from your textbook, or upload a .txt file (content will appear here)..."
                      value={form.pasteText}
                      onChange={(e) => upd('pasteText', e.target.value)}
                      style={{ marginBottom: 12 }}
                    />
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept={ACCEPTED_TYPES}
                      multiple
                      className="sr-only"
                      onChange={(e) => {
                        addFiles(e.target.files);
                        e.target.value = '';
                      }}
                      aria-label="Upload PDF, PPT, or document"
                    />
                    <div
                      role="button"
                      tabIndex={0}
                      className={`notes-upload-area ${isDragging ? 'notes-upload-area--dragging' : ''}`}
                      onClick={() => fileInputRef.current?.click()}
                      onDragOver={handleDragOver}
                      onDragLeave={handleDragLeave}
                      onDrop={handleDrop}
                      onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
                    >
                      <div className="notes-upload-icon">📎</div>
                      <div className="notes-upload-text">Drop PDF, PPT, or document here, or click to browse</div>
                      <div className="notes-upload-hint">Supported: PDF, PPT, PPTX, DOC, DOCX, TXT</div>
                    </div>
                    {uploadedFiles.length > 0 && (
                      <ul className="notes-upload-list">
                        {uploadedFiles.map((f, i) => (
                          <li key={`${f.name}-${i}`} className="notes-upload-item">
                            <span className="notes-upload-item-name">{f.name}</span>
                            <span className="notes-upload-item-size">
                              {(f.size / 1024).toFixed(1)} KB
                            </span>
                            <button
                              type="button"
                              className="btn btn-ghost btn-sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                removeFile(i);
                              }}
                              aria-label={`Remove ${f.name}`}
                            >
                              <Icon name="x" size={14} />
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </>
                )}
              </div>

              <div>
                <label className="label">Push To Class</label>
                <select
                  className="select"
                  value={form.assignTo}
                  onChange={(e) => upd('assignTo', e.target.value)}
                >
                  <option value="all">
                    {activeClass ? `${activeClass.class_name} (active)` : 'Select class'}
                  </option>
                  {(classes.length > 0 ? classes : activeClass ? [activeClass] : []).map((c) => (
                    <option key={c.class_id} value={c.class_id}>
                      {c.class_name} ({c.class_code})
                    </option>
                  ))}
                </select>
              </div>

              {error && (
                <div className="notif-banner notif-error">
                  <div className="notif-banner-icon">⚠️</div>
                  <div className="notif-banner-text">{error}</div>
                </div>
              )}

              <button
                type="button"
                className="btn btn-blue notes-generate-btn"
                onClick={generate}
                disabled={generating || !canGenerate}
              >
                {generating ? (
                  <>
                    <div className="spinner" />
                    Generating notes...
                  </>
                ) : (
                  <>
                    <Icon name="note" size={15} />
                    Generate Notes
                  </>
                )}
              </button>
            </div>
          </GlassCard>
        </div>

        <div className="notes-output-col">
          {SHOW_TEACHER_NOTES && (
            <div className="notes-view-tabs">
              {[
                ['generated', 'Generated Notes'],
                ['teacher', 'Notes by Teacher'],
              ].map(([v, label]) => (
                <button
                  key={v}
                  type="button"
                  className={`notes-tab notes-tab-sm ${viewTab === v ? 'active' : ''}`}
                  onClick={() => setViewTab(v as 'generated' | 'teacher')}
                >
                  {label}
                </button>
              ))}
            </div>
          )}

          {viewTab === 'teacher' && SHOW_TEACHER_NOTES ? (
            <GlassCard className="notes-teacher-card">
              <div className="notes-teacher-header">
                <h3 className="notes-teacher-title">Notes by Teacher</h3>
                <p className="notes-teacher-desc">
                  Notes shared or uploaded by your teacher. Visually distinct from AI-generated notes.
                </p>
              </div>
              {PLACEHOLDER_TEACHER_NOTES.length > 0 ? (
                <ul className="notes-teacher-list">
                  {PLACEHOLDER_TEACHER_NOTES.map((n) => (
                    <li key={n.id} className="notes-teacher-item">
                      <div className="notes-teacher-item-header">
                        <span className="notes-teacher-item-title">{n.title}</span>
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          aria-label="Bookmark"
                          title="Bookmark"
                        >
                          <Icon name={n.bookmarked ? 'check' : 'plus'} size={14} />
                        </button>
                      </div>
                      <div className="notes-teacher-item-meta">
                        {n.teacherName} · {n.timestamp}
                      </div>
                      <p className="notes-teacher-item-excerpt">{n.excerpt}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState
                  icon="📖"
                  title="No teacher notes yet"
                  description="When your teacher shares notes to the class, they will show up here."
                  className="empty-state--compact"
                />
              )}
            </GlassCard>
          ) : (
            <GlassCard className="notes-output-card">
              <div className="notes-output-header">
                <div className="notes-output-title">Generated Notes</div>
                {notes && (
                  <div className="notes-output-actions">
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={handleCopy}
                    >
                      <Icon name="copy" size={12} /> {copied ? 'Copied!' : 'Copy'}
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={handleDownloadNotes}
                    >
                      <Icon name="download" size={12} /> Export
                    </button>
                    {notesS3Url && (
                      <a
                        href={notesS3Url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-ghost btn-sm"
                      >
                        <Icon name="arrow_right" size={12} /> View in S3
                      </a>
                    )}
                    <button
                      type="button"
                      className="btn btn-blue btn-sm"
                      onClick={handlePushNotes}
                    >
                      <Icon name="send" size={12} /> Push
                    </button>
                  </div>
                )}
              </div>
              {notes ? (
                <div className="notes-output-wrapper">
                  <NotesRenderer text={notes} collapsible />
                </div>
              ) : generating ? (
                <div className="notes-loading-state">
                  <div className="spinner spinner-dark" />
                  <div className="notes-loading-text">Generating your notes...</div>
                </div>
              ) : (
                <EmptyState
                  icon="📝"
                  title="Notes will appear here"
                  description="Choose source, enter topic, and click Generate Notes."
                />
              )}
            </GlassCard>
          )}
        </div>
      </div>
    </main>
  );
}
