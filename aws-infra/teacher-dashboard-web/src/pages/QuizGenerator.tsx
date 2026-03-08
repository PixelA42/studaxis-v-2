import { useState } from 'react';
import { Icon } from '../components/icons/Icon';
import { useTeacher } from '../context/TeacherContext';
import { GlassCard } from '../components/dashboard/GlassCard';
import { EmptyState } from '../components/shared/EmptyState';

export function QuizGenerator() {
  const { teacher } = useTeacher();
  const [form, setForm] = useState({
    textbook: '',
    topic: '',
    subject: teacher?.subject || 'Physics',
    type: 'mcq' as 'mcq' | 'open' | 'mix',
    count: 10,
    difficulty: 'medium' as 'easy' | 'medium' | 'hard',
    assignTo: 'all',
  });
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState<{
    quiz_id: string;
    title: string;
    count: number;
    difficulty: string;
    s3_key: string;
  } | null>(null);

  const upd = (k: string, v: string | number) => setForm((p) => ({ ...p, [k]: v }));

  const generate = async () => {
    setGenerating(true);
    await new Promise((r) => setTimeout(r, 2000));
    setGenerating(false);
    setGenerated({
      quiz_id: 'QZ-' + Date.now(),
      title: `${form.subject}: ${form.topic || 'General'} Quiz`,
      count: form.count,
      difficulty: form.difficulty,
      s3_key: `quizzes/QZ-${Date.now()}.json`,
    });
  };

  return (
    <main id="main-content" className="page-quiz" role="main">
      <div className="page-header-block">
        <h1 className="page-title">AI Quiz Generator</h1>
        <p className="page-sub">
          Powered by Amazon Bedrock · Generated quizzes save to S3 and push to students on sync.
        </p>
      </div>

      <div className="quiz-layout">
        <div className="quiz-form-col">
          <GlassCard className="quiz-form-card">
            <div className="quiz-form-header">
              <div className="quiz-form-icon">🧠</div>
              <div>
                <div className="quiz-form-title">Bedrock Quiz Generation</div>
                <div className="quiz-form-sub">API Gateway → Lambda → Bedrock → S3</div>
              </div>
            </div>

            <div className="quiz-form-fields">
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
                  placeholder="Paste relevant textbook excerpt to ground the quiz... Bedrock will use this as RAG context."
                  style={{ resize: 'vertical' }}
                />
              </div>

              <div>
                <label className="label">Question Type</label>
                <div className="toggle-group">
                  {[
                    ['mcq', 'Multiple Choice'],
                    ['open', 'Open Ended'],
                    ['mix', 'Mixed'],
                  ].map(([v, l]) => (
                    <button
                      key={v}
                      type="button"
                      className={`toggle-btn ${form.type === v ? 'active' : ''}`}
                      onClick={() => upd('type', v)}
                    >
                      {l}
                    </button>
                  ))}
                </div>
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
                  <option value="all">All Classes</option>
                  {teacher?.className && (
                    <option value={teacher.classCode}>{teacher.className}</option>
                  )}
                </select>
              </div>

              <button
                type="button"
                className="btn btn-primary quiz-generate-btn"
                onClick={generate}
                disabled={generating}
              >
                {generating ? (
                  <>
                    <div className="spinner" />
                    Generating with Bedrock...
                  </>
                ) : (
                  <>
                    <Icon name="spark" size={15} />
                    Generate Quiz with Bedrock
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
                  <div className="quiz-result-sub">Saved to S3 · Ready to assign</div>
                </div>
              </div>
              <div className="quiz-result-meta">
                <div className="quiz-result-name">{generated.title}</div>
                <div className="quiz-result-chips">
                  <span className="chip chip-blue">{generated.count} questions</span>
                  <span className="chip chip-orange">{generated.difficulty}</span>
                  <span className="chip chip-grey">S3: {generated.s3_key}</span>
                </div>
              </div>
              <div className="quiz-result-actions">
                <button type="button" className="btn btn-primary">
                  <Icon name="arrow_right" size={14} /> Assign to Class
                </button>
                <button type="button" className="btn btn-ghost">
                  <Icon name="eye" size={15} />
                </button>
              </div>
            </GlassCard>
          ) : (
            <GlassCard>
              <EmptyState
                icon="🧠"
                title="Ready to Generate"
                description="Fill in the form and Bedrock will create your quiz. Results save to S3 automatically."
              />
            </GlassCard>
          )}

          <GlassCard className="quiz-aws-card">
            <div className="quiz-aws-title">⚡ AWS Flow</div>
            {[
              ['API Gateway', 'Validates & routes request'],
              ['Quiz Lambda', 'Orchestrates generation'],
              ['Amazon Bedrock', 'Generates quiz content'],
              ['S3 Bucket', 'Stores quiz JSON'],
              ['DynamoDB', 'Records assignment state'],
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
