import { useState } from 'react';
import { GlassCard } from '../components/dashboard/GlassCard';
import { useTheme } from '../context/ThemeContext';
import { useTeacher } from '../context/TeacherContext';

export function Settings() {
  const { theme, toggleTheme } = useTheme();
  const { teacher } = useTeacher();
  const [aws, setAws] = useState({
    region: 'ap-south-1',
    table: 'studaxis-student-sync',
    bucket: '',
    apiUrl: '',
  });

  const upd = (k: string, v: string) => setAws((p) => ({ ...p, [k]: v }));

  return (
    <main id="main-content" className="page-settings" role="main">
      <div className="page-header-block">
        <h1 className="page-title">Settings</h1>
        <p className="page-sub">Configure your AWS infrastructure and teaching preferences.</p>
      </div>

      {/* AWS Config */}
      <GlassCard className="settings-section">
        <div className="settings-section-header">
          <span className="settings-section-icon">☁️</span>
          <div>
            <div className="settings-section-title">AWS Configuration</div>
            <div className="settings-section-sub">
              Connect to your DynamoDB, S3, and API Gateway endpoints.
            </div>
          </div>
        </div>
        <div className="settings-aws-grid">
          <div>
            <label className="label">AWS Region</label>
            <select className="select" value={aws.region} onChange={(e) => upd('region', e.target.value)}>
              {['ap-south-1', 'us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'].map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">DynamoDB Table</label>
            <input
              className="input"
              placeholder="studaxis-student-sync"
              value={aws.table}
              onChange={(e) => upd('table', e.target.value)}
            />
          </div>
          <div>
            <label className="label">S3 Bucket Name</label>
            <input
              className="input"
              placeholder="studaxis-payloads-prod"
              value={aws.bucket}
              onChange={(e) => upd('bucket', e.target.value)}
            />
          </div>
          <div>
            <label className="label">API Gateway URL</label>
            <input
              className="input"
              placeholder="https://xxxxx.execute-api.ap-south-1.amazonaws.com/prod"
              value={aws.apiUrl}
              onChange={(e) => upd('apiUrl', e.target.value)}
            />
          </div>
        </div>
        <button type="button" className="btn btn-blue">Test Connection</button>
      </GlassCard>

      {/* Teacher Profile */}
      <GlassCard className="settings-section">
        <div className="settings-section-title">Teacher Profile</div>
        <div className="settings-profile-grid">
          {[
            { l: 'Full Name', v: teacher?.name, k: 'name' },
            { l: 'Email', v: teacher?.email, k: 'email' },
            { l: 'School', v: teacher?.school, k: 'school' },
            { l: 'Subject', v: teacher?.subject, k: 'subject' },
          ].map((f) => (
            <div key={f.k}>
              <label className="label">{f.l}</label>
              <input className="input" defaultValue={f.v || ''} readOnly />
            </div>
          ))}
        </div>
        <button type="button" className="btn btn-primary" style={{ marginTop: 20 }}>
          Save Changes
        </button>
      </GlassCard>

      {/* Privacy */}
      <GlassCard className="settings-section">
        <div className="settings-section-title">🔒 Privacy & Data</div>
        <div className="settings-privacy-text">
          <strong style={{ color: 'var(--sd-dark)' }}>What syncs to AWS:</strong> Anonymized progress summaries,
          quiz scores, streak counts, last sync timestamps.
          <br />
          <strong style={{ color: 'var(--sd-dark)' }}>What never leaves the device:</strong> Chat transcripts, raw
          quiz answers, personal learning notes, AI conversation history.
          <br />
          <strong style={{ color: 'var(--sd-dark)' }}>Encryption:</strong> DynamoDB uses AWS-managed keys. S3 uses
          SSE-S3 (AES-256). All transport over HTTPS/TLS.
        </div>
      </GlassCard>

      {/* Appearance */}
      <GlassCard className="settings-section">
        <h2 className="card-title">Appearance</h2>
        <p className="card-sub">Theme and display preferences</p>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={toggleTheme}
          aria-pressed={theme === 'dark'}
        >
          {theme === 'light' ? '🌙 Dark mode' : '☀️ Light mode'}
        </button>
      </GlassCard>
    </main>
  );
}
