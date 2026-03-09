import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Icon } from '../components/icons/Icon';
import type { Teacher } from '../context/TeacherContext';
import { teacherLogin } from '../lib/teacherApi';
import '../styles/onboarding.css';

interface LoginProps {
  onComplete: (data: Teacher, options?: { token?: string }) => void;
}

export function Login({ onComplete }: LoginProps) {
  const [teacherId, setTeacherId] = useState('');
  const [classCode, setClassCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const tid = teacherId.trim() || undefined;
    const code = classCode.trim().toUpperCase();
    if (!code || code.length < 3) {
      setError('Please enter a valid Class Code (e.g., CS101, ABC123).');
      return;
    }
    setLoading(true);
    try {
      const res = await teacherLogin(code, tid);
      onComplete(res.teacher, { token: res.access_token });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Login failed';
      setError(msg || 'Class code not found. Complete setup first if you\'re a new teacher.');
    } finally {
      setLoading(false);
    }
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
              <div>
                <label className="label">Teacher ID (optional, for offline sign-in)</label>
                <input
                  className="input"
                  placeholder="e.g. T001, priya.sharma"
                  value={teacherId}
                  onChange={(e) => setTeacherId(e.target.value)}
                  autoComplete="username"
                  disabled={loading}
                />
                <p className="onboard-class-code-hint" style={{ marginTop: 6 }}>
                  Only needed when backend is unavailable — we load your profile from the server by class code.
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
        <p className="onboarding-footer" style={{ marginTop: 8 }}>
          New teacher? <Link to="/onboard" className="btn btn-ghost" style={{ padding: '4px 8px', fontSize: 12 }}>Complete setup →</Link>
        </p>
      </div>
    </div>
  );
}
