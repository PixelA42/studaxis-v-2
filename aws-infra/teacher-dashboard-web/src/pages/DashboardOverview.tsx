import { useMemo, useState } from 'react';
import { GlassCard } from '../components/dashboard/GlassCard';
import { CloudSyncStatus } from '../components/dashboard/CloudSyncStatus';
import { StaleDataWarning } from '../components/sync/StaleDataWarning';
import { SkeletonCard } from '../components/shared/Skeleton';
import { useTeacher } from '../context/TeacherContext';
import type { SyncState } from '../types';

const DEMO_STUDENT_SYNC = [
  { id: 'STU001', name: 'Student A', lastSync: new Date(Date.now() - 600000).toISOString(), status: 'connected' as const, pendingItems: 0 },
  { id: 'STU002', name: 'Student B', lastSync: new Date(Date.now() - 1800000).toISOString(), status: 'connected' as const, pendingItems: 0 },
  { id: 'STU003', name: 'Student C', lastSync: new Date(Date.now() - 90000000).toISOString(), status: 'offline' as const, pendingItems: 3 },
  { id: 'STU004', name: 'Student D', lastSync: new Date(Date.now() - 3600000).toISOString(), status: 'connected' as const, pendingItems: 0 },
  { id: 'STU005', name: 'Student E', lastSync: null, status: 'offline' as const, pendingItems: 0 },
];

const STATS = [
  { icon: '🏫', label: 'Total Classes', value: '—', sub: 'Active this term', color: 'rgba(250,92,92,0.1)' },
  { icon: '👥', label: 'Active Students', value: '—', sub: 'Synced in last 24h', color: 'rgba(0,168,232,0.1)' },
  { icon: '📝', label: 'Assignment Completion', value: '—%', sub: 'Class average', color: 'rgba(16,185,129,0.1)' },
  { icon: '📊', label: 'Recent Activity', value: '—', sub: 'Last 24 hours', color: 'rgba(253,138,107,0.1)' },
];

export function DashboardOverview() {
  const { teacher } = useTeacher();
  const [loading] = useState(false);
  const [syncState, setSyncState] = useState<SyncState>({
    status: 'connected',
    lastSyncTimestamp: new Date().toISOString(),
  });

  const handleManualSync = () => {
    setSyncState((s) => ({ ...s, status: 'syncing' }));
    setTimeout(() => {
      setSyncState({ status: 'connected', lastSyncTimestamp: new Date().toISOString() });
    }, 1500);
  };

  const studentSync = DEMO_STUDENT_SYNC;

  const staleStudents = useMemo(
    () =>
      studentSync
        .filter((s) => {
          if (!s.lastSync) return true;
          const hoursSince = (Date.now() - new Date(s.lastSync).getTime()) / (1000 * 60 * 60);
          return hoursSince > 24;
        })
        .map((s) => s.name),
    [studentSync]
  );

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'morning';
    if (h < 17) return 'afternoon';
    return 'evening';
  };

  return (
    <main id="main-content" className="page-dashboard" role="main">
      {/* Welcome banner — matching reference */}
      <div className="overview-welcome-banner">
        <div>
          <div className="overview-welcome-title">
            Good {greeting()}, {teacher?.name?.split(' ')[0] || 'Teacher'} 👋
          </div>
          <div className="overview-welcome-sub">
            {teacher?.school || 'Your School'} · {teacher?.subject || 'Subject'} · Class Code:{' '}
            <strong style={{ fontFamily: 'monospace', letterSpacing: 2 }}>
              {teacher?.classCode || '——'}
            </strong>
          </div>
        </div>
        <div className="overview-welcome-emoji">🎓</div>
      </div>

      {/* Stat cards */}
      <section aria-label="Key metrics" className="bento-section">
        <div className="bento-grid bento-grid--overview">
          {loading ? (
            <>
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : (
            STATS.map((s, i) => (
              <GlassCard key={i} className="overview-stat-card card-hover">
                <div className="stat-icon" style={{ background: s.color }}>
                  {s.icon}
                </div>
                <div className="stat-num">{s.value}</div>
                <div className="stat-label">{s.label}</div>
                <div className="stat-sub">{s.sub}</div>
              </GlassCard>
            ))
          )}
        </div>
      </section>

      {/* Info banner */}
      <div className="notif-banner notif-info">
        <div className="notif-banner-icon">ℹ️</div>
        <div>
          <div className="notif-banner-title">Connect Your AWS Backend</div>
          <div className="notif-banner-text">
            Stats will populate once students sync via DynamoDB. Share your class code{' '}
            <strong style={{ fontFamily: 'monospace', color: 'var(--sd-dark)' }}>
              {teacher?.classCode}
            </strong>{' '}
            to get started.
          </div>
        </div>
      </div>

      {staleStudents.length > 0 && <StaleDataWarning studentNames={staleStudents} />}

      {/* Bottom grid */}
      <section className="bento-section bento-section--row" aria-label="Sync overview">
        <div className="bento-section__half">
          <GlassCard>
            <h2 className="card-title">Recent Student Activity</h2>
            <div className="empty-state empty-state--compact">
              <div className="empty-state__icon" style={{ fontSize: 32 }}>📡</div>
              <h3 className="empty-state__title" style={{ fontSize: 14 }}>Waiting for sync</h3>
              <p className="empty-state__description" style={{ fontSize: 12 }}>
                Activity appears once students come online and sync progress data.
              </p>
            </div>
          </GlassCard>
        </div>
        <div className="bento-section__half">
          <GlassCard>
            <h2 className="card-title">Topic Performance (Class Avg)</h2>
            <div className="empty-state empty-state--compact">
              <div className="empty-state__icon" style={{ fontSize: 32 }}>📈</div>
              <h3 className="empty-state__title" style={{ fontSize: 14 }}>No quiz data yet</h3>
              <p className="empty-state__description" style={{ fontSize: 12 }}>
                Generate and assign a quiz to see topic-wise class performance here.
              </p>
            </div>
          </GlassCard>
        </div>
      </section>

      <section aria-label="Cloud sync status" className="bento-section">
        <CloudSyncStatus
          syncState={syncState}
          onManualSync={handleManualSync}
          isSyncing={syncState.status === 'syncing'}
        />
      </section>
    </main>
  );
}
