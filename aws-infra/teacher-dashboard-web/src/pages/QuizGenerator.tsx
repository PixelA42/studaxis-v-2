import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon } from '../components/icons/Icon';
import { useTeacher } from '../context/TeacherContext';
import { useClass } from '../context/ClassContext';
import { GlassCard } from '../components/dashboard/GlassCard';
import { EmptyState } from '../components/shared/EmptyState';
import { exportToDocx } from '../lib/quizToDocx';

const API_URL = import.meta.env.VITE_API_GATEWAY_URL || '';

export function QuizGenerator() {
  const { teacher } = useTeacher();
  const { activeClass, classes } = useClass();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    textbookId: '',
    topic: '',
    subject: teacher?.subject || 'Physics',
    type: 'mcq' as 'mcq' | 'open' | 'mix',
    count: 10,
    difficulty: 'medium' as 'easy' | 'medium' | 'hard',
    assignTo: 'all',
    textbookContext: '',
  });
  const [generating, setGenerating] = useState(false);
  const [downloadingDocx, setDownloadingDocx] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generated, setGenerated] = useState<{
    title: string;
    count: number;
    difficulty: string;
    s3_url?: string;
    quizData?: Record<string, unknown>;
  } | null>(null);

  const upd = (k: string, v: string | number) => setForm((p) => ({ ...p, [k]: v }));

  const generate = async () => {
    setGenerating(true);
    setError(null);
    setGenerated(null);

    const payload = {
      textbook_id: form.textbookId || undefined,
      topic: form.topic.trim() || form.subject,
      difficulty: form.difficulty,
      num_questions: Math.min(Math.max(1, form.count), 20),
      textbook_context: form.textbookContext.trim() || undefined,
    };

    try {
      if (!API_URL) {
        throw new Error('API Gateway URL not configured (VITE_API_GATEWAY_URL)');
      }
      const res = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(60000), // 60s Bedrock can be slow
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data?.error || `HTTP ${res.status}: ${res.statusText}`);
      }

      const s3_url = data?.s3_url as string | undefined;
      const questions = data?.questions as unknown[] | undefined;
      const quiz_title = data?.quiz_title as string | undefined;
      const title = quiz_title || `${form.subject}: ${form.topic || 'General'} Quiz`;

      setGenerated({
        title,
        count: questions?.length ?? payload.num_questions,
        difficulty: (data?.difficulty as string) ?? form.difficulty,
        s3_url: s3_url || undefined,
        quizData: (data as Record<string, unknown>) ?? undefined,
      });
    } catch (e) {
      if (e instanceof Error) {
        if (e.name === 'AbortError') setError('Request timed out (60s). Try fewer questions.');
        else setError(e.message);
      } else {
        setError('Failed to generate quiz. Check network and API config.');
      }
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = () => {
    if (!generated) return;
    if (generated.s3_url) {
      window.open(generated.s3_url, '_blank', 'noopener,noreferrer');
      return;
    }
    if (generated.quizData) {
      const blob = new Blob([JSON.stringify(generated.quizData, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `quiz-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const handleDownloadDocx = async () => {
    if (!generated) return;
    setDownloadingDocx(true);
    setError(null);
    try {
      let quizData = generated.quizData;
      if (!quizData && generated.s3_url) {
        const res = await fetch(generated.s3_url, { mode: 'cors' });
        if (!res.ok) throw new Error(`Failed to fetch quiz from S3 (${res.status}). Try downloading JSON first.`);
        quizData = (await res.json()) as Record<string, unknown>;
      }
      const safeTitle = (generated.title || 'quiz').replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 50);
      await exportToDocx(quizData, `${safeTitle}.docx`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to export DOCX.';
      setError(msg.includes('fetch') ? `${msg} (CORS may block S3. Use JSON download.)` : msg);
      alert(msg);
    } finally {
      setDownloadingDocx(false);
    }
  };

  return (
    <main id="main-content" className="page-quiz" role="main">
      <div className="page-header-block">
        <h1 className="page-title">AI Quiz Generator</h1>
        <p className="page-sub">
          AI-powered quiz via Amazon Bedrock · API Gateway → Lambda · Results ready to assign.
        </p>
      </div>

      <div className="quiz-layout">
        <div className="quiz-form-col">
          <GlassCard className="quiz-form-card">
            <div className="quiz-form-header">
              <div className="quiz-form-icon">🧠</div>
              <div>
                <div className="quiz-form-title">AI Quiz Generation</div>
                <div className="quiz-form-sub">Request → API Gateway → Bedrock → Store</div>
              </div>
            </div>

            <div className="quiz-form-fields">
              <div>
                <label className="label">Textbook ID (optional)</label>
                <input
                  className="input"
                  placeholder="e.g. PHYS-101, NCERT-X"
                  value={form.textbookId}
                  onChange={(e) => upd('textbookId', e.target.value)}
                />
              </div>

              <div className="quiz-form-row">
                <div>
                  <label className="label">Subject</label>
                  <select className="select" value={form.subject} onChange={(e) => upd('subject', e.target.value)}>
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
                  <label className="label">Difficulty</label>
                  <select className="select" value={form.difficulty} onChange={(e) => upd('difficulty', e.target.value)}>
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="label">Topic or Chapter</label>
                <input
                  className="input"
                  placeholder="e.g. Newton's Laws of Motion, Chapter 5..."
                  value={form.topic}
                  onChange={(e) => upd('topic', e.target.value)}
                />
              </div>

              <div>
                <label className="label">Textbook Context (optional)</label>
                <textarea
                  className="input"
                  rows={3}
                  placeholder="Paste relevant textbook excerpt to ground the quiz..."
                  value={form.textbookContext}
                  onChange={(e) => upd('textbookContext', e.target.value)}
                  style={{ resize: 'vertical' }}
                />
              </div>

              <div>
                <label className="label">Number of Questions</label>
                <div className="quiz-count-btns">
                  {[5, 10, 15, 20].map((n) => (
                    <button
                      key={n}
                      type="button"
                      className={`quiz-count-btn ${form.count === n ? 'active' : ''}`}
                      onClick={() => upd('count', n)}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="label">Assign To</label>
                <select className="select" value={form.assignTo} onChange={(e) => upd('assignTo', e.target.value)}>
                  <option value="all">{activeClass ? activeClass.class_name : 'Select class'}</option>
                  {(classes.length > 0 ? classes : activeClass ? [activeClass] : []).map((c) => (
                    <option key={c.class_id} value={c.class_code}>{c.class_name}</option>
                  ))}
                </select>
              </div>

              {error && (
                <div className="notif-banner notif-error" style={{ marginBottom: 12 }}>
                  <div className="notif-banner-icon">⚠️</div>
                  <div className="notif-banner-text">{error}</div>
                </div>
              )}

              <button
                type="button"
                className="btn btn-primary quiz-generate-btn"
                onClick={generate}
                disabled={generating}
              >
                {generating ? (
                  <>
                    <div className="spinner" />
                    Generating quiz...
                  </>
                ) : (
                  <>
                    <Icon name="spark" size={15} />
                    Generate Quiz
                  </>
                )}
              </button>
            </div>
          </GlassCard>
        </div>

        <div className="quiz-sidebar-col">
          {generated ? (
            <GlassCard className="quiz-result-card">
              <div className="quiz-result-header">
                <div className="quiz-result-icon">✅</div>
                <div>
                  <div className="quiz-result-title">Quiz Generated!</div>
                  <div className="quiz-result-sub">
                    {generated.s3_url ? 'Ready to download from S3' : 'Ready to download'}
                  </div>
                </div>
              </div>
              <div className="quiz-result-meta">
                <div className="quiz-result-name">{generated.title}</div>
                <div className="quiz-result-chips">
                  <span className="chip chip-blue">{generated.count} questions</span>
                  <span className="chip chip-orange">{generated.difficulty}</span>
                </div>
              </div>
              <div className="quiz-result-actions" style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => navigate('/assignments')}
                >
                  <Icon name="send" size={14} /> Assign to Class
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleDownloadDocx}
                  disabled={downloadingDocx}
                >
                  {downloadingDocx ? <div className="spinner" style={{ width: 14, height: 14 }} /> : '📄'}
                  {downloadingDocx ? ' Exporting...' : ' Download as Word (.docx)'}
                </button>
                <button type="button" className="btn btn-ghost" onClick={handleDownload}>
                  {generated.s3_url ? (
                    <>
                      <Icon name="arrow_right" size={14} /> View / Download JSON
                    </>
                  ) : (
                    <>
                      <Icon name="arrow_right" size={14} /> Download JSON
                    </>
                  )}
                </button>
              </div>
            </GlassCard>
          ) : (
            <GlassCard>
              <EmptyState
                icon="🧠"
                title="Ready to Generate"
                description="Fill in topic and settings. The AI will create your quiz via Bedrock."
              />
            </GlassCard>
          )}

          <GlassCard className="quiz-aws-card">
            <div className="quiz-aws-title">⚡ Quiz Pipeline</div>
            {[
              ['API Gateway', 'Validates & routes request'],
              ['Lambda', 'Orchestrates generation'],
              ['Amazon Bedrock', 'Generates quiz content'],
              ['Response', 'JSON or S3 presigned URL'],
            ].map(([svc, desc], i) => (
              <div key={i} className="quiz-aws-row">
                <div
                  className={`quiz-aws-dot ${generating ? 'pulse' : ''}`}
                  style={{ background: generating ? 'var(--sd-accent-coral)' : 'var(--sd-green)' }}
                />
                <div>
                  <div className="quiz-aws-svc">{svc}</div>
                  <div className="quiz-aws-desc">{desc}</div>
                </div>
              </div>
            ))}
          </GlassCard>
        </div>
      </div>
    </main>
  );
}
