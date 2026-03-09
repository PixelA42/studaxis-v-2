import { useState, useEffect } from 'react';
import { Icon } from '../components/icons/Icon';
import { GlassCard } from '../components/dashboard/GlassCard';
import { EmptyState } from '../components/shared/EmptyState';
import { useNavigate } from 'react-router-dom';
import { useClass } from '../context/ClassContext';
import { useTeacher } from '../context/TeacherContext';
import { listAssignmentsForClass, deleteAssignment, type Assignment } from '../lib/assignmentApi';

export function Assignments() {
  const navigate = useNavigate();
  const { activeClass } = useClass();
  const { teacher } = useTeacher();
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAssignments = async () => {
    if (!activeClass?.class_code) {
      setAssignments([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await listAssignmentsForClass(activeClass.class_code, teacher?.teacherId || teacher?.classCode);
      setAssignments(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load assignments');
      setAssignments([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAssignments();
  }, [activeClass?.class_code, teacher?.teacherId]);

  const handleDelete = async (assignmentId: string) => {
    if (!teacher || !confirm('Remove this assignment?')) return;
    try {
      await deleteAssignment(assignmentId, teacher.teacherId || teacher.classCode || '');
      await loadAssignments();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete');
    }
  };

  const total = assignments.length;
  const quizCount = assignments.filter((a) => a.content_type === 'quiz').length;
  const notesCount = assignments.filter((a) => a.content_type === 'notes').length;

  const statItems = [
    { icon: '📤', label: 'Total', value: String(total), color: 'rgba(253,138,107,0.1)', tc: 'var(--sd-accent-coral)' },
    { icon: '📝', label: 'Quizzes', value: String(quizCount), color: 'rgba(0,168,232,0.1)', tc: 'var(--sd-accent-blue)' },
    { icon: '📚', label: 'Notes', value: String(notesCount), color: 'rgba(16,185,129,0.1)', tc: 'var(--sd-green)' },
  ];

  return (
    <main id="main-content" className="page-assignments" role="main">
      <div className="page-header-flex">
        <div>
          <h1 className="page-title">Assignments</h1>
          <p className="page-sub">
            {activeClass
              ? `Assigned to ${activeClass.class_name} (${activeClass.class_code}). Students see these on sync.`
              : 'Select a class from the header to see its assignments.'}
          </p>
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
        {statItems.map((s, i) => (
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

      {error && (
        <div className="notif-banner notif-error" style={{ marginBottom: 12 }}>
          {error}
        </div>
      )}

      {!activeClass?.class_code ? (
        <GlassCard>
          <EmptyState
            icon="🏫"
            title="Select a class"
            description="Use the class selector in the header to pick a class. Assignments for that class will appear here."
          />
        </GlassCard>
      ) : loading ? (
        <GlassCard>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 24 }}>
            <span className="loading loading-spinner loading-md" />
            <span>Loading assignments…</span>
          </div>
        </GlassCard>
      ) : assignments.length === 0 ? (
        <GlassCard>
          <EmptyState
            icon="📤"
            title="No assignments yet"
            description="Generate a quiz or notes and assign it to this class. It will appear here and sync to students."
          />
          <div style={{ display: 'flex', gap: 10, marginTop: 8, flexWrap: 'wrap' }}>
            <button type="button" className="btn btn-primary" onClick={() => navigate('/notes')}>
              <Icon name="note" size={14} /> Generate Notes
            </button>
            <button type="button" className="btn btn-primary" onClick={() => navigate('/quiz')}>
              <Icon name="spark" size={14} /> Generate Quiz
            </button>
          </div>
        </GlassCard>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {assignments.map((a) => (
            <GlassCard key={a.assignment_id} className="assignment-stat-card" style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, minWidth: 0 }}>
                <span
                  style={{
                    padding: '6px 10px',
                    borderRadius: 8,
                    fontSize: 12,
                    fontWeight: 600,
                    background: a.content_type === 'quiz' ? 'var(--sd-accent-subtle)' : 'rgba(16,185,129,0.15)',
                    color: a.content_type === 'quiz' ? 'var(--sd-accent)' : 'var(--sd-green)',
                  }}
                >
                  {a.content_type === 'quiz' ? '📝 Quiz' : '📚 Notes'}
                </span>
                <div style={{ minWidth: 0 }}>
                  <div className="assignment-stat-value" style={{ fontSize: 15, marginBottom: 2 }}>
                    {a.title}
                  </div>
                  <div className="assignment-stat-label" style={{ fontSize: 12 }}>
                    {a.class_code && (
                      <span style={{ marginRight: 12 }}>
                        Class: <strong>{a.class_code}</strong>
                      </span>
                    )}
                    {a.description && <span>{a.description}</span>}
                    <span style={{ marginLeft: 8, color: 'var(--sd-grey)' }}>
                      {a.created_at ? new Date(a.created_at).toLocaleDateString() : ''}
                    </span>
                  </div>
                </div>
              </div>
              <button
                type="button"
                className="btn btn-ghost"
                style={{ fontSize: 12, color: 'var(--sd-grey)' }}
                onClick={() => handleDelete(a.assignment_id)}
              >
                Remove
              </button>
            </GlassCard>
          ))}
        </div>
      )}
    </main>
  );
}
