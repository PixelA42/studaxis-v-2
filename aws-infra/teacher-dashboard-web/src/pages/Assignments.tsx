import { Icon } from '../components/icons/Icon';
import { GlassCard } from '../components/dashboard/GlassCard';
import { EmptyState } from '../components/shared/EmptyState';
import { useNavigate } from 'react-router-dom';

const STAT_ITEMS = [
  { icon: '📤', label: 'Pending', value: '0', color: 'rgba(253,138,107,0.1)', tc: 'var(--sd-accent-coral)' },
  { icon: '⏳', label: 'In Progress', value: '0', color: 'rgba(0,168,232,0.1)', tc: 'var(--sd-accent-blue)' },
  { icon: '✅', label: 'Completed', value: '0', color: 'rgba(16,185,129,0.1)', tc: 'var(--sd-green)' },
];

export function Assignments() {
  const navigate = useNavigate();
  return (
    <main id="main-content" className="page-assignments" role="main">
      <div className="page-header-flex">
        <div>
          <h1 className="page-title">Assignments</h1>
          <p className="page-sub">Assigned quizzes and notes push to student devices on next sync.</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button type="button" className="btn btn-ghost" onClick={() => navigate('/notes')}>
            <Icon name="note" size={15} /> Assign Notes
          </button>
          <button type="button" className="btn btn-primary" onClick={() => navigate('/quiz')}>
            <Icon name="plus" size={15} /> Assign Quiz
          </button>
        </div>
      </div>

      <div className="assignments-stats">
        {STAT_ITEMS.map((s, i) => (
          <GlassCard key={i} className="assignment-stat-card">
            <div className="assignment-stat-icon" style={{ background: s.color }}>
              {s.icon}
            </div>
            <div>
              <div className="assignment-stat-value">{s.value}</div>
              <div className="assignment-stat-label">{s.label}</div>
            </div>
          </GlassCard>
        ))}
      </div>

      <GlassCard>
        <EmptyState
          icon="📤"
          title="No assignments yet"
          description="Generate a quiz with Bedrock and assign it to your class. Students receive it automatically when they come online."
        />
        <div style={{ display: 'flex', gap: 10, marginTop: 8, flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => navigate('/notes')}
          >
            <Icon name="note" size={14} /> Generate Notes
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => navigate('/quiz')}
          >
            <Icon name="spark" size={14} /> Generate Quiz
          </button>
        </div>
      </GlassCard>
    </main>
  );
}
