import { GlassCard } from '../components/dashboard/GlassCard';
import { EmptyState } from '../components/shared/EmptyState';
import type { StudentSyncInfo, PartialSyncStatus } from '../types';

/**
 * Placeholder student data.
 * syncStatus and lastSync use placeholder tokens — no backend logic.
 */
const PLACEHOLDER_STUDENTS: (StudentSyncInfo & { avgScore: number; streak: number })[] = [
  {
    id: 'STU001',
    name: 'Student A',
    avgScore: 87,
    streak: 12,
    syncStatus: '[STUDENT_SYNC_STATUS]',
    lastSync: '[LAST_SYNC_TIME]',
    partialSyncStatus: 'fully_synced',
  },
  {
    id: 'STU002',
    name: 'Student B',
    avgScore: 92,
    streak: 15,
    syncStatus: '[STUDENT_SYNC_STATUS]',
    lastSync: '[LAST_SYNC_TIME]',
  },
  {
    id: 'STU003',
    name: 'Student C',
    avgScore: 61,
    streak: 0,
    syncStatus: '[STUDENT_SYNC_STATUS]',
    lastSync: '[LAST_SYNC_TIME]',
    partialSyncStatus: 'metadata_pending',
  },
];

const SYNC_BADGE_MAP: Record<string, { className: string; label: string; tooltip: string }> = {
  connected:  { className: 'student-sync-badge--connected', label: 'Synced',       tooltip: 'All data synced normally' },
  syncing:    { className: 'student-sync-badge--syncing',   label: 'Syncing',      tooltip: 'Sync in progress' },
  error:      { className: 'student-sync-badge--error',     label: 'Error',        tooltip: 'Sync encountered an error' },
  offline:    { className: 'student-sync-badge--offline',   label: 'Offline',      tooltip: 'Student device is offline' },
};

const PARTIAL_LABELS: Record<PartialSyncStatus, { label: string; tooltip: string } | null> = {
  fully_synced:     null,
  data_only:        { label: 'Data only', tooltip: 'Payload uploaded but metadata not yet synced' },
  metadata_pending: { label: 'Metadata pending', tooltip: 'Data payload uploaded but metadata not yet synced' },
  unknown:          { label: 'Unknown', tooltip: 'Partial sync state is unknown' },
};

function SyncBadge({ syncStatus }: { syncStatus: string }) {
  const config = SYNC_BADGE_MAP[syncStatus];

  if (config) {
    return (
      <span
        className={`student-sync-badge ${config.className}`}
        role="status"
        aria-label={`Sync: ${config.label}`}
        title={config.tooltip}
      >
        <span className="student-sync-badge__dot" aria-hidden="true" />
        {config.label}
      </span>
    );
  }

  return (
    <span
      className="student-sync-badge student-sync-badge--placeholder"
      role="status"
      aria-label={`Sync: ${syncStatus}`}
      title="Sync state provided by cloud backend"
    >
      <span className="student-sync-badge__dot" aria-hidden="true" />
      {syncStatus}
    </span>
  );
}

function PartialSyncBadge({ status }: { status?: PartialSyncStatus }) {
  if (!status) return <span className="students-list__meta">—</span>;
  const config = PARTIAL_LABELS[status];
  if (!config) return <span className="students-list__meta">—</span>;

  return (
    <span
      className="student-sync-badge student-sync-badge--partial"
      title={config.tooltip}
      aria-label={config.tooltip}
    >
      <span className="student-sync-badge__dot" aria-hidden="true" />
      {config.label}
    </span>
  );
}

export function Students() {
  const students = PLACEHOLDER_STUDENTS;

  return (
    <main id="main-content" className="page-students" role="main">
      <h1 className="page-title">Students</h1>

      {students.length === 0 ? (
        <GlassCard>
          <EmptyState
            icon="👥"
            title="No students yet"
            description="Students will appear here once they sync their devices."
          />
        </GlassCard>
      ) : (
        <GlassCard>
          <h2 className="card-title">Student List</h2>
          <p className="card-sub">Sync status and academic metrics — placeholder data</p>
          <ul className="students-list" role="list">
            {students.map((s) => (
              <li key={s.id} className="students-list__item">
                <span className="students-list__avatar" aria-hidden="true">
                  {s.name.slice(0, 2).toUpperCase()}
                </span>
                <div className="students-list__info">
                  <span className="students-list__name">{s.name}</span>
                  <span className="students-list__meta">
                    Avg: {s.avgScore}% · Streak: {s.streak} · Last sync: {s.lastSync ?? 'Never'}
                  </span>
                </div>
                <div className="students-list__sync-col">
                  <SyncBadge syncStatus={s.syncStatus} />
                  <PartialSyncBadge status={s.partialSyncStatus} />
                </div>
              </li>
            ))}
          </ul>
        </GlassCard>
      )}
    </main>
  );
}
