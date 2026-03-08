import { useState, useEffect } from 'react';
import { GlassCard } from '../components/dashboard/GlassCard';
import { useTeacher } from '../context/TeacherContext';
import { useTheme } from '../context/ThemeContext';

export function Settings() {
  const { teacher, setTeacher } = useTeacher();
  const { theme, setTheme } = useTheme();
  const [teacherName, setTeacherName] = useState('');
  const [activeClassCode, setActiveClassCode] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setTeacherName(teacher?.name ?? '');
    setActiveClassCode(teacher?.classCode ?? '');
  }, [teacher]);

  const handleSaveProfile = () => {
    const updated = teacher
      ? { ...teacher, name: teacherName, classCode: activeClassCode }
      : {
          name: teacherName,
          classCode: activeClassCode,
          email: '',
          subject: '',
          grade: '',
          school: '',
          city: '',
          board: '',
          className: '',
          numStudents: '',
        };
    setTeacher(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <main id="main-content" className="page-settings" role="main">
      <div className="page-header-block">
        <h1 className="page-title">Settings</h1>
        <p className="page-sub">Manage your profile and view system status.</p>
      </div>

      {/* Account & Roster */}
      <GlassCard className="settings-section">
        <div className="settings-section-header">
          <span className="settings-section-icon" aria-hidden>👤</span>
          <div>
            <div className="settings-section-title">Account & Roster</div>
            <div className="settings-section-sub">
              Your display name and class code for filtering roster and AppSync queries.
            </div>
          </div>
        </div>
        <div className="settings-profile-grid">
          <div>
            <label className="label" htmlFor="teacher-name">Teacher Name</label>
            <input
              id="teacher-name"
              className="input"
              type="text"
              placeholder="e.g. Mr. Sharma"
              value={teacherName}
              onChange={(e) => setTeacherName(e.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="active-class-code">Active Class Code</label>
            <input
              id="active-class-code"
              className="input"
              type="text"
              placeholder="e.g. CS101"
              value={activeClassCode}
              onChange={(e) => setActiveClassCode(e.target.value)}
            />
          </div>
        </div>
        <button
          type="button"
          className="btn btn-primary settings-save-btn"
          onClick={handleSaveProfile}
          disabled={saved}
        >
          {saved ? 'Saved ✓' : 'Save Profile'}
        </button>
      </GlassCard>

      {/* Appearance */}
      <GlassCard className="settings-section">
        <div className="settings-section-header">
          <span className="settings-section-icon" aria-hidden>🎨</span>
          <div>
            <div className="settings-section-title">Appearance</div>
            <div className="settings-section-sub">
              Choose light or dark theme. Matches the student app.
            </div>
          </div>
        </div>
        <div className="flex gap-4" style={{ flexWrap: 'wrap' }}>
          {(['light', 'dark'] as const).map((t) => (
            <label key={t} className="flex items-center gap-2 cursor-pointer" style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input
                type="radio"
                name="theme"
                checked={theme === t}
                onChange={() => setTheme(t)}
                className="input"
                style={{ width: 'auto' }}
              />
              <span style={{ color: 'var(--sd-dark)', textTransform: 'capitalize' }}>{t}</span>
            </label>
          ))}
        </div>
      </GlassCard>

      {/* Privacy */}
      <GlassCard className="settings-section">
        <div className="settings-section-title">🔒 Privacy & Data</div>
        <div className="settings-privacy-text">
          <strong>What syncs:</strong> Anonymized progress summaries, quiz scores, streak counts, last sync timestamps.
          <br />
          <strong>What never leaves the device:</strong> Chat transcripts, raw quiz answers, personal learning notes, AI conversation history.
          <br />
          <strong>Encryption:</strong> AWS-managed keys at rest. All transport over HTTPS/TLS.
        </div>
      </GlassCard>

      {/* System Health */}
      <GlassCard className="settings-section">
        <div className="settings-section-header">
          <span className="settings-section-icon" aria-hidden>📡</span>
          <div>
            <div className="settings-section-title">System Health</div>
            <div className="settings-section-sub">
              Read-only status. Configuration is managed via environment variables.
            </div>
          </div>
        </div>
        <div className="settings-health-grid">
          <div className="settings-health-badge" role="status">
            <span className="settings-health-dot settings-health-dot--connected" aria-hidden />
            <span className="settings-health-label">Cloud Sync</span>
            <span className="settings-health-status">Connected</span>
          </div>
          <div className="settings-health-badge" role="status">
            <span className="settings-health-dot settings-health-dot--active" aria-hidden />
            <span className="settings-health-label">Curriculum Engine (Bedrock)</span>
            <span className="settings-health-status">Active</span>
          </div>
        </div>
      </GlassCard>
    </main>
  );
}
