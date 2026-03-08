import { useState } from 'react';
import { Icon } from '../components/icons/Icon';
import { GlassCard } from '../components/dashboard/GlassCard';
import { EmptyState } from '../components/shared/EmptyState';
import { useTeacher } from '../context/TeacherContext';

export function Classes() {
  const { teacher } = useTeacher();
  const [showCreate, setShowCreate] = useState(false);
  const [newClass, setNewClass] = useState({ name: '', subject: '', grade: '' });

  return (
    <main id="main-content" className="page-classes" role="main">
      <div className="page-header-flex">
        <div>
          <h1 className="page-title">Your Classes</h1>
          <p className="page-sub">Manage classes, share codes, view per-class analytics.</p>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setShowCreate((p) => !p)}
        >
          <Icon name="plus" size={15} /> New Class
        </button>
      </div>

      {showCreate && (
        <GlassCard className="classes-create-card">
          <div className="card-title">Create New Class</div>
          <div className="classes-create-fields">
            <div>
              <label className="label">Class Name</label>
              <input
                className="input"
                placeholder="Physics XII-B"
                value={newClass.name}
                onChange={(e) => setNewClass((p) => ({ ...p, name: e.target.value }))}
              />
            </div>
            <div>
              <label className="label">Subject</label>
              <select
                className="select"
                value={newClass.subject}
                onChange={(e) => setNewClass((p) => ({ ...p, subject: e.target.value }))}
              >
                <option value="">Select...</option>
                {['Physics', 'Chemistry', 'Biology', 'Mathematics', 'Computer Science'].map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Grade</label>
              <select
                className="select"
                value={newClass.grade}
                onChange={(e) => setNewClass((p) => ({ ...p, grade: e.target.value }))}
              >
                <option value="">Select...</option>
                {['Grade 9', 'Grade 10', 'Grade 11', 'Grade 12'].map((g) => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="classes-create-actions">
            <button type="button" className="btn btn-primary">Create Class</button>
            <button type="button" className="btn btn-ghost" onClick={() => setShowCreate(false)}>
              Cancel
            </button>
          </div>
        </GlassCard>
      )}

      {teacher?.className ? (
        <GlassCard className="classes-card card-hover">
          <div className="classes-card-header">
            <div className="classes-card-main">
              <div className="classes-card-icon">🏫</div>
              <div>
                <div className="classes-card-name">{teacher.className}</div>
                <div className="classes-card-meta">
                  {teacher.subject} · {teacher.grade || 'Grade'}
                </div>
                <div className="classes-card-chips">
                  <span className="chip chip-blue">Code: {teacher.classCode}</span>
                  <span className="chip chip-grey">0 students joined</span>
                </div>
              </div>
            </div>
            <button type="button" className="btn btn-ghost">
              <Icon name="eye" size={15} /> View
            </button>
          </div>
          <div className="classes-card-stats">
            {[
              { l: 'Students', v: '0' },
              { l: 'Assignments', v: '0' },
              { l: 'Avg Score', v: '—%' },
            ].map((s) => (
              <div key={s.l} className="classes-card-stat">
                <div className="classes-card-stat-value">{s.v}</div>
                <div className="classes-card-stat-label">{s.l}</div>
              </div>
            ))}
          </div>
        </GlassCard>
      ) : (
        <GlassCard>
          <EmptyState
            icon="🏫"
            title="No classes yet"
            description="Create your first class to get a code your students can use to join."
          />
          <button
            type="button"
            className="btn btn-primary"
            style={{ marginTop: 8 }}
            onClick={() => setShowCreate(true)}
          >
            <Icon name="plus" size={14} /> Create First Class
          </button>
        </GlassCard>
      )}
    </main>
  );
}
