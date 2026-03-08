import { useState } from 'react';
import { Icon } from '../components/icons/Icon';
import type { Teacher } from '../context/TeacherContext';
import '../styles/onboarding.css';

const DEFAULT_TEACHER: Omit<Teacher, 'classCode' | 'teacherId'> = {
  name: '',
  email: '',
  subject: 'Physics',
  grade: 'Grade 10',
  school: '',
  city: '',
  board: 'CBSE',
  className: '',
  numStudents: '',
};

interface LoginProps {
  onComplete: (data: Teacher) => void;
}

export function Login({ onComplete }: LoginProps) {
  const [teacherId, setTeacherId] = useState('');
  const [classCode, setClassCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const tid = teacherId.trim();
    const code = classCode.trim().toUpperCase();
    if (!tid) {
      setError('Please enter your Teacher ID.');
      return;
    }
    if (!code || code.length < 3) {
      setError('Please enter a valid Class Code (e.g., CS101).');
      return;
    }
    setLoading(true);
    const teacher: Teacher = {
      ...DEFAULT_TEACHER,
      teacherId: tid,
      name: tid,
      className: code,
      classCode: code,
    };
    onComplete(teacher);
    setLoading(false);
  };

  return (
    <div className="onboarding-root">
      <div className="onboarding-container">
        <div className="onboarding-logo fade-up">
          <div className="onboarding-logo-icon">📐</div>
          <div className="onboarding-logo-title">Studaxis for Teachers</div>
          <div className="onboarding-logo-sub">Dual-Brain AI Platform · Sign in</div>
        </div>

        <div className="onboarding-card fade-up-3">
          <form onSubmit={handleSubmit} className="onboarding-content">
            <h2>Sign In</h2>
            <p>Enter your credentials to access the teacher dashboard.</p>
            <div className="onboard-form" style={{ marginTop: 16 }}>
              <div>
                <label className="label">Teacher ID</label>
                <input
                  className="input"
                  placeholder="e.g. T001, priya.sharma"
                  value={teacherId}
                  onChange={(e) => setTeacherId(e.target.value)}
                  autoComplete="username"
                  disabled={loading}
                />
              </div>
              <div>
                <label className="label">Class Code</label>
                <input
                  className="input"
                  placeholder="e.g. CS101, PHYS11A"
                  value={classCode}
                  onChange={(e) => setClassCode(e.target.value.toUpperCase())}
                  autoComplete="off"
                  disabled={loading}
                />
                <p className="onboard-class-code-hint" style={{ marginTop: 6 }}>
                  Share this code with students · They enter it in Settings → Class Code
                </p>
              </div>
              {error && (
                <div className="notif-banner notif-error" style={{ marginTop: 12 }}>
                  <div className="notif-banner-icon">⚠️</div>
                  <div className="notif-banner-text">{error}</div>
                </div>
              )}
            </div>
            <div className="onboarding-actions" style={{ marginTop: 24 }}>
              <button
                type="submit"
                className="btn btn-primary onboarding-next"
                disabled={loading}
              >
                {loading ? (
                  <div className="spinner" />
                ) : (
                  <>
                    <Icon name="arrow_right" size={15} />
                    Sign In →
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        <p className="onboarding-footer">
          🔒 MVP auth · Cognito coming in Phase 2 · Data syncs via AWS AppSync
        </p>
      </div>
    </div>
  );
}
