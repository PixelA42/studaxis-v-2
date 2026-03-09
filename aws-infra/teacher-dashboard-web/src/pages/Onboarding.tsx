import { useState, useRef, useEffect } from 'react';
import { Icon } from '../components/icons/Icon';
import type { Teacher } from '../context/TeacherContext';
import { postTeacherOnboard, teacherLogin } from '../lib/teacherApi';
import '../styles/onboarding.css';

const ONBOARD_STEPS = [
  { id: 'welcome', label: 'Welcome' },
  { id: 'profile', label: 'Profile' },
  { id: 'school', label: 'School' },
  { id: 'class', label: 'First Class' },
  { id: 'done', label: 'Done' },
];

interface OnboardingProps {
  onComplete: (data: Teacher, options?: { token?: string }) => void;
  /** Optional "Sign In" link for returning teachers (e.g. <Link to="/login">Sign In →</Link>) */
  signInLink?: React.ReactNode;
}

export function Onboarding({ onComplete, signInLink }: OnboardingProps) {
  const [step, setStep] = useState(0);
  const [data, setData] = useState<Partial<Teacher>>({
    name: '',
    email: '',
    subject: '',
    grade: '',
    school: '',
    city: '',
    board: '',
    className: '',
    classCode: '',
    numStudents: '',
  });
  const [loading, setLoading] = useState(false);
  const [backendError, setBackendError] = useState<string | null>(null);
  const classCode = useRef(Math.random().toString(36).slice(2, 8).toUpperCase());

  const update = (k: keyof Teacher, v: string) => setData((p) => ({ ...p, [k]: v }));

  useEffect(() => {
    update('classCode', classCode.current);
  }, []);

  const next = async () => {
    setBackendError(null);
    if (step === ONBOARD_STEPS.length - 2) {
      setLoading(true);
      try {
        const result = await postTeacherOnboard({
          name: data.name || '',
          email: data.email || '',
          subject: data.subject || '',
          grade: data.grade || '',
          school: data.school || '',
          city: data.city || '',
          board: data.board || '',
          className: data.className || '',
          classCode: data.classCode || classCode.current,
          numStudents: data.numStudents || '',
        });
        if (!result.ok) {
          setBackendError('Backend unavailable — your data will be saved locally. You can still use the dashboard.');
        }
      } catch (e) {
        setBackendError('Could not sync to backend — your data will be saved locally. Check VITE_TEACHER_BACKEND_URL if you need cloud sync.');
        console.warn('Backend teacher onboard failed (using local only):', e);
      }
      await new Promise((r) => setTimeout(r, 600));
      setLoading(false);
      setStep((s) => s + 1);
    } else if (step === ONBOARD_STEPS.length - 1) {
      const teacherData = data as Teacher;
      try {
        const res = await teacherLogin(teacherData.classCode || classCode.current, teacherData.email);
        onComplete(res.teacher, { token: res.access_token });
      } catch {
        onComplete(teacherData);
      }
    } else {
      setStep((s) => s + 1);
    }
  };

  const canNext = () => {
    if (step === 1) return data.name && data.email && data.subject;
    if (step === 2) return data.school && data.city && data.board;
    if (step === 3) return data.className && data.numStudents;
    return true;
  };

  return (
    <div className="onboarding-root">
      <div className="onboarding-container">
        <div className="onboarding-logo fade-up">
          <div className="onboarding-logo-icon">📐</div>
          <div className="onboarding-logo-title">Studaxis for Teachers</div>
          <div className="onboarding-logo-sub">Dual-Brain AI Platform — Teacher Setup</div>
        </div>

        <div className="onboarding-steps fade-up-2">
          {ONBOARD_STEPS.map((s, i) => (
            <div key={s.id} className="onboarding-step-wrap">
              <div className={`step-dot ${i < step ? 'done' : i === step ? 'active' : 'todo'}`} />
              {i < ONBOARD_STEPS.length - 1 && (
                <div className="step-line" style={{ background: i < step ? 'var(--sd-green)' : 'var(--sd-border)' }} />
              )}
            </div>
          ))}
        </div>

        <div className="onboarding-card fade-up-3">
          <div className="onboarding-content">
            {step === 0 && <StepWelcome />}
            {step === 1 && <StepProfile data={data} update={update} />}
            {step === 2 && <StepSchool data={data} update={update} />}
            {step === 3 && <StepClass data={data} update={update} code={classCode.current} />}
            {step === 4 && <StepDone data={data} />}
          </div>

          <div className="onboarding-actions">
            {step > 0 && step < ONBOARD_STEPS.length - 1 && (
              <button type="button" className="btn btn-ghost" onClick={() => setStep((s) => s - 1)}>
                <Icon name="arrow_left" size={15} /> Back
              </button>
            )}
            <button
              type="button"
              className="btn btn-primary onboarding-next"
              onClick={next}
              disabled={!canNext() || loading}
            >
              {loading ? (
                <div className="spinner" />
              ) : step === ONBOARD_STEPS.length - 1 ? (
                'Go to Dashboard →'
              ) : step === ONBOARD_STEPS.length - 2 ? (
                'Create Class →'
              ) : step === 0 ? (
                'Get Started →'
              ) : (
                'Continue →'
              )}
            </button>
          </div>
        </div>

        {backendError && (
          <div className="notif-banner notif-info" style={{ marginTop: 16 }}>
            <div className="notif-banner-icon">ℹ️</div>
            <div className="notif-banner-text">{backendError}</div>
          </div>
        )}
        <p className="onboarding-footer">
          🔒 Your data syncs via AWS AppSync · Encrypted at rest via DynamoDB
        </p>
        {signInLink && (
          <p className="onboarding-footer" style={{ marginTop: 8 }}>
            Already have an account? {signInLink}
          </p>
        )}
      </div>
    </div>
  );
}

function StepWelcome() {
  const features = [
    { icon: '⚡', label: 'AI Quiz Generation via Amazon Bedrock' },
    { icon: '📊', label: 'Real-time student progress from DynamoDB' },
    { icon: '🔁', label: 'Automatic sync when students come online' },
    { icon: '🎓', label: 'Assign quizzes that push to student devices' },
  ];
  return (
    <div className="onboard-step-content onboard-step-center">
      <div className="onboard-step-emoji">👩‍🏫</div>
      <h2>Welcome to Studaxis for Teachers</h2>
      <p>
        Set up your teacher account in 2 minutes. You&apos;ll get a class code your students can use to link their
        accounts, and access to the cloud dashboard powered by Amazon Bedrock.
      </p>
      <div className="onboard-features">
        {features.map((f) => (
          <div key={f.icon} className="onboard-feature">
            <span className="onboard-feature-icon">{f.icon}</span>
            <span>{f.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function StepProfile({ data, update }: { data: Partial<Teacher>; update: (k: keyof Teacher, v: string) => void }) {
  return (
    <div className="onboard-step-content">
      <h2>Your Profile</h2>
      <p>This is how students and parents will see you.</p>
      <div className="onboard-form">
        <div>
          <label className="label">Full Name</label>
          <input
            className="input"
            placeholder="Dr. Priya Sharma"
            value={data.name || ''}
            onChange={(e) => update('name', e.target.value)}
          />
        </div>
        <div>
          <label className="label">Email</label>
          <input
            className="input"
            placeholder="priya@school.edu.in"
            type="email"
            value={data.email || ''}
            onChange={(e) => update('email', e.target.value)}
          />
        </div>
        <div className="onboard-form-row">
          <div>
            <label className="label">Primary Subject</label>
            <select className="select" value={data.subject || ''} onChange={(e) => update('subject', e.target.value)}>
              <option value="">Select...</option>
              {['Physics', 'Chemistry', 'Biology', 'Mathematics', 'Computer Science', 'History', 'English', 'Geography'].map(
                (s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                )
              )}
            </select>
          </div>
          <div>
            <label className="label">Grade Level</label>
            <select className="select" value={data.grade || ''} onChange={(e) => update('grade', e.target.value)}>
              <option value="">Select...</option>
              {['Grade 8', 'Grade 9', 'Grade 10', 'Grade 11', 'Grade 12', 'Undergraduate'].map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}

function StepSchool({ data, update }: { data: Partial<Teacher>; update: (k: keyof Teacher, v: string) => void }) {
  return (
    <div className="onboard-step-content">
      <h2>School Details</h2>
      <p>Helps us tailor curriculum and sync settings.</p>
      <div className="onboard-form">
        <div>
          <label className="label">School Name</label>
          <input
            className="input"
            placeholder="Kendriya Vidyalaya, Sector 12"
            value={data.school || ''}
            onChange={(e) => update('school', e.target.value)}
          />
        </div>
        <div className="onboard-form-row">
          <div>
            <label className="label">City</label>
            <input
              className="input"
              placeholder="Bengaluru"
              value={data.city || ''}
              onChange={(e) => update('city', e.target.value)}
            />
          </div>
          <div>
            <label className="label">Board</label>
            <select className="select" value={data.board || ''} onChange={(e) => update('board', e.target.value)}>
              <option value="">Select...</option>
              {['CBSE', 'ICSE', 'State Board', 'IB', 'IGCSE', 'Other'].map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="onboard-privacy">
          <div className="onboard-privacy-title">🔒 Privacy Notice</div>
          <div className="onboard-privacy-text">
            All student learning data stays on-device. Only anonymized progress summaries sync to DynamoDB. No chat
            transcripts or quiz answers are uploaded.
          </div>
        </div>
      </div>
    </div>
  );
}

function StepClass({
  data,
  update,
  code,
}: {
  data: Partial<Teacher>;
  update: (k: keyof Teacher, v: string) => void;
  code: string;
}) {
  return (
    <div className="onboard-step-content">
      <h2>Create Your First Class</h2>
      <p>Students enter your class code to link their Studaxis account to your class.</p>
      <div className="onboard-form">
        <div>
          <label className="label">Class Name</label>
          <input
            className="input"
            placeholder="Physics XI-A · 2026"
            value={data.className || ''}
            onChange={(e) => update('className', e.target.value)}
          />
        </div>
        <div>
          <label className="label">Expected Students</label>
          <input
            className="input"
            type="number"
            placeholder="35"
            value={data.numStudents || ''}
            onChange={(e) => update('numStudents', e.target.value)}
          />
        </div>
        <div>
          <label className="label">Your Class Code</label>
          <div className="onboard-class-code">{code}</div>
          <p className="onboard-class-code-hint">
            Share this code with students · They enter it in Settings → Class Code
          </p>
        </div>
      </div>
    </div>
  );
}

function StepDone({ data }: { data: Partial<Teacher> }) {
  const nextSteps = [
    { icon: '📋', t: 'Go to Dashboard', s: 'View class overview and student stats' },
    { icon: '🧠', t: 'Generate a Quiz with Bedrock AI', s: 'Create your first AI-powered assessment' },
    { icon: '📤', t: 'Assign to Class', s: 'Push quiz to student devices on sync' },
  ];
  return (
    <div className="onboard-step-content onboard-step-center">
      <div className="onboard-done-icon">
        <Icon name="check" size={32} color="white" />
      </div>
      <h2>You&apos;re all set, {data.name?.split(' ')[0] || 'Teacher'}!</h2>
      <p>
        Your teacher account is ready. Your first class <strong>{data.className}</strong> has been created with code{' '}
        <strong style={{ color: 'var(--sd-accent-pink)' }}>{data.classCode}</strong>.
      </p>
      <div className="onboard-next-steps">
        {nextSteps.map((item, i) => (
          <div key={i} className="onboard-next-step">
            <span className="onboard-next-step-icon">{item.icon}</span>
            <div>
              <div className="onboard-next-step-title">{item.t}</div>
              <div className="onboard-next-step-sub">{item.s}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
