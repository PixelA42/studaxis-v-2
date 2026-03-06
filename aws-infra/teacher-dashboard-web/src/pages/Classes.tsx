import { GlassCard } from '../components/dashboard/GlassCard';
import { EmptyState } from '../components/shared/EmptyState';

const DEMO_CLASSES = [
  { id: '1', name: 'Class 10-A', studentCount: 28, subject: 'Mathematics' },
  { id: '2', name: 'Class 10-B', studentCount: 32, subject: 'Science' },
  { id: '3', name: 'Class 11-A', studentCount: 25, subject: 'Mathematics' },
];

export function Classes() {
  const classes = DEMO_CLASSES;

  return (
    <main id="main-content" className="page-classes" role="main">
      <h1 className="page-title">Classes</h1>

      {classes.length === 0 ? (
        <GlassCard>
          <EmptyState
            icon="🏫"
            title="No classes yet"
            description="Create a class to start managing students and assignments."
          />
        </GlassCard>
      ) : (
        <div className="classes-grid">
          {classes.map((c) => (
            <GlassCard key={c.id}>
              <h2 className="card-title">{c.name}</h2>
              <p className="card-sub">{c.subject}</p>
              <p className="classes-card__count">
                <strong>{c.studentCount}</strong> students
              </p>
            </GlassCard>
          ))}
        </div>
      )}
    </main>
  );
}
