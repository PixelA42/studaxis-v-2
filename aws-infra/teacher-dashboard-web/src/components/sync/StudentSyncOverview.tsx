import { useMemo } from 'react';
import type { SyncStatus } from '../../types';

interface StudentSyncItem {
  id: string;
  name: string;
  lastSync: string | null;
  status: SyncStatus;
  pendingItems: number;
}

interface StudentSyncOverviewProps {
  students: StudentSyncItem[];
  onStudentClick?: (studentId: string) => void;
}

function getStatusColor(status: SyncStatus): string {
  const colors: Record<SyncStatus, string> = {
    connected: 'var(--sd-semantic-success)',
    syncing: 'var(--sd-semantic-warn)',
    error: 'var(--sd-semantic-danger)',
    offline: 'var(--sd-text-muted)',
  };
  return colors[status];
}

function formatLastSync(ts: string | null): string {
  if (!ts) return 'Never';
  try {
    const d = new Date(ts);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    
    if (diffMs < 60000) return 'Just now';
    if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)}m ago`;
    if (diffMs < 86400000) return `${Math.floor(diffMs / 3600000)}h ago`;
    if (diffMs < 604800000) return `${Math.floor(diffMs / 86400000)}d ago`;
    return d.toLocaleDateString();
  } catch {
    return 'Unknown';
  }
}

function isStale(lastSync: string | null): boolean {
  if (!lastSync) return true;
  try {
    const d = new Date(lastSync);
    const now = new Date();
    const hoursSince = (now.getTime() - d.getTime()) / (1000 * 60 * 60);
    return hoursSince > 24; // Stale if >24 hours
  } catch {
    return true;
  }
}

export function StudentSyncOverview({ students, onStudentClick }: StudentSyncOverviewProps) {
  const computedStudents = useMemo(
    () =>
      students.map((student) => {
        const stale = isStale(student.lastSync);
        return {
          ...student,
          stale,
          statusColor: getStatusColor(student.status),
          formattedLastSync: formatLastSync(student.lastSync),
        };
      }),
    [students]
  );

  const summary = useMemo(
    () =>
      computedStudents.reduce(
        (acc, student) => {
          if (student.status === 'connected') {
            acc.online += 1;
          }
          if (student.stale) {
            acc.stale += 1;
          }
          if (student.status === 'error') {
            acc.error += 1;
          }
          return acc;
        },
        { online: 0, stale: 0, error: 0 }
      ),
    [computedStudents]
  );

  return (
    <div className="student-sync-overview">
      {/* Summary badges */}
      <div className="student-sync-summary">
        <div className="student-sync-summary__item">
          <span className="student-sync-summary__count student-sync-summary__count--success">
            {summary.online}
          </span>
          <span className="student-sync-summary__label">Online</span>
        </div>
        <div className="student-sync-summary__item">
          <span className="student-sync-summary__count student-sync-summary__count--warn">
            {summary.stale}
          </span>
          <span className="student-sync-summary__label">Stale</span>
        </div>
        <div className="student-sync-summary__item">
          <span className="student-sync-summary__count student-sync-summary__count--error">
            {summary.error}
          </span>
          <span className="student-sync-summary__label">Errors</span>
        </div>
      </div>

      {/* Student list */}
      <ul className="student-sync-list" role="list">
        {computedStudents.map((student) => {
          return (
            <li key={student.id} className="student-sync-item">
              <button
                type="button"
                className="student-sync-item__button"
                onClick={() => onStudentClick?.(student.id)}
                aria-label={`View ${student.name} sync details`}
              >
                <div className="student-sync-item__avatar" aria-hidden="true">
                  {student.name.slice(0, 2).toUpperCase()}
                </div>
                <div className="student-sync-item__info">
                  <span className="student-sync-item__name">{student.name}</span>
                  <span className="student-sync-item__meta">
                    {student.formattedLastSync}
                    {student.pendingItems > 0 && (
                      <> · {student.pendingItems} pending</>
                    )}
                    {student.stale && <> · <strong>Stale</strong></>}
                  </span>
                </div>
                <div
                  className="student-sync-item__status"
                  style={{ backgroundColor: student.statusColor }}
                  role="status"
                  aria-label={`Status: ${student.status}`}
                />
              </button>
            </li>
          );
        })}
      </ul>

      {computedStudents.length === 0 && (
        <div className="student-sync-empty" role="status">
          <span className="student-sync-empty__icon" aria-hidden="true">👥</span>
          <p className="student-sync-empty__text">
            No students have synced yet
          </p>
        </div>
      )}
    </div>
  );
}
