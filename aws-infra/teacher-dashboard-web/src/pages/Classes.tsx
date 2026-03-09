import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon } from '../components/icons/Icon';
import { GlassCard } from '../components/dashboard/GlassCard';
import { EmptyState } from '../components/shared/EmptyState';
import { useTeacher } from '../context/TeacherContext';
import { useClass } from '../context/ClassContext';
import { createClass } from '../lib/teacherApi';
import type { ActiveClass, LegacyClass } from '../context/ClassContext';

function isLegacy(c: ActiveClass): c is LegacyClass {
  return 'isLegacy' in c && c.isLegacy;
}

export function Classes() {
  const { teacher } = useTeacher();
  const { classes, activeClass, setActiveClassId, refreshClasses } = useClass();
  const navigate = useNavigate();

  const [modalOpen, setModalOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState('');
  const [createdCode, setCreatedCode] = useState<string | null>(null);

  const allClasses = classes.length > 0 ? classes : (activeClass ? [activeClass] : []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = createName.trim();
    if (!name) {
      setCreateError('Enter a class name');
      return;
    }
    const teacherId = teacher?.teacherId || teacher?.classCode;
    if (!teacherId) {
      setCreateError('Not logged in');
      return;
    }
    setCreateLoading(true);
    setCreateError('');
    setCreatedCode(null);
    try {
      const cls = await createClass(teacherId, name);
      await refreshClasses();
      setCreatedCode(cls.class_code);
      setCreateName('');
      setActiveClassId(cls.class_id);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Failed to create class');
    } finally {
      setCreateLoading(false);
    }
  };

  const closeModal = () => {
    setModalOpen(false);
    setCreateName('');
    setCreateError('');
    setCreatedCode(null);
  };

  return (
    <main id="main-content" className="page-classes" role="main">
      <div className="page-header-flex">
        <div>
          <h1 className="page-title">Your Classes</h1>
          <p className="page-sub">Manage classes, share codes, view per-class analytics. Create a new class to get a unique code each time.</p>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setModalOpen(true)}
          style={{ display: 'flex', alignItems: 'center', gap: 8 }}
        >
          <Icon name="plus" size={18} />
          Create New Class
        </button>
      </div>

      {allClasses.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {allClasses.map((c) => (
            <GlassCard key={c.class_id} className="classes-card card-hover">
              <div className="classes-card-header">
                <div className="classes-card-main">
                  <div className="classes-card-icon">🏫</div>
                  <div>
                    <div className="classes-card-name">{c.class_name}</div>
                    <div className="classes-card-meta">
                      {teacher?.subject || 'Subject'} · {teacher?.grade || 'Grade'}
                    </div>
                    <div className="classes-card-chips">
                      <span className="chip chip-blue">Code: {c.class_code}</span>
                      {isLegacy(c) && <span className="chip chip-grey">legacy</span>}
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => {
                    setActiveClassId(c.class_id);
                    navigate('/students');
                  }}
                >
                  <Icon name="eye" size={15} /> View
                </button>
              </div>
            </GlassCard>
          ))}
        </div>
      ) : (
        <GlassCard>
          <EmptyState
            icon="🏫"
            title="No classes yet"
            description="Create your first class to get a unique code. Share the code with students so they can join."
            action={
              <button type="button" className="btn btn-primary" onClick={() => setModalOpen(true)}>
                <Icon name="plus" size={16} /> Create New Class
              </button>
            }
          />
        </GlassCard>
      )}

      {/* Create New Class Modal */}
      {modalOpen && (
        <div
          className="modal-backdrop"
          onClick={closeModal}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.4)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <div
            className="create-class-modal"
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'var(--sd-bg)',
              borderRadius: 16,
              padding: 24,
              maxWidth: 400,
              width: '90%',
              boxShadow: 'var(--sd-shadow-card)',
            }}
          >
            <h3 style={{ margin: '0 0 16px', fontSize: 18 }}>{createdCode ? 'Class Created' : 'Create New Class'}</h3>
            {createdCode ? (
              <div>
                <p style={{ marginBottom: 12, color: 'var(--sd-grey)' }}>
                  Share this code with students so they can join. A new code is generated every time you create a class.
                </p>
                <div
                  style={{
                    padding: 14,
                    background: 'var(--sd-accent-subtle)',
                    borderRadius: 10,
                    fontFamily: 'monospace',
                    fontSize: 20,
                    fontWeight: 600,
                    letterSpacing: 2,
                    textAlign: 'center',
                  }}
                >
                  {createdCode}
                </div>
                <button type="button" className="btn btn-primary" onClick={closeModal} style={{ marginTop: 16, width: '100%' }}>
                  Done
                </button>
              </div>
            ) : (
              <form onSubmit={handleCreate}>
                <label className="label" style={{ display: 'block', marginBottom: 6 }}>Class Name</label>
                <input
                  className="input"
                  placeholder="e.g. Physics 11A, Math Section B"
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  disabled={createLoading}
                  autoFocus
                  style={{ width: '100%', marginBottom: 12 }}
                />
                {createError && (
                  <div className="notif-banner notif-error" style={{ marginBottom: 12 }}>{createError}</div>
                )}
                <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                  <button type="button" className="btn btn-ghost" onClick={closeModal}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary" disabled={createLoading}>
                    {createLoading ? <span className="loading loading-spinner loading-sm" /> : 'Create'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
