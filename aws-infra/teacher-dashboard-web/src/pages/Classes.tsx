import { useNavigate } from 'react-router-dom';
import { Icon } from '../components/icons/Icon';
import { GlassCard } from '../components/dashboard/GlassCard';
import { EmptyState } from '../components/shared/EmptyState';
import { useTeacher } from '../context/TeacherContext';
import { useClass } from '../context/ClassContext';
import type { ActiveClass, LegacyClass } from '../context/ClassContext';

function isLegacy(c: ActiveClass): c is LegacyClass {
  return 'isLegacy' in c && c.isLegacy;
}

export function Classes() {
  const { teacher } = useTeacher();
  const { classes, activeClass, setActiveClassId } = useClass();
  const navigate = useNavigate();

  const allClasses = classes.length > 0 ? classes : (activeClass ? [activeClass] : []);

  return (
    <main id="main-content" className="page-classes" role="main">
      <div className="page-header-flex">
        <div>
          <h1 className="page-title">Your Classes</h1>
          <p className="page-sub">Manage classes, share codes, view per-class analytics. Use + Create Class in the header to add more.</p>
        </div>
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
            description="Use + Create Class in the header to create your first class and get a code students can use to join."
          />
        </GlassCard>
      )}
    </main>
  );
}
