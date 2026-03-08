import { useMemo, useState, useEffect, useCallback } from 'react';
import { GlassCard } from '../components/dashboard/GlassCard';
import { CloudSyncStatus } from '../components/dashboard/CloudSyncStatus';
import { StaleDataWarning } from '../components/sync/StaleDataWarning';
import { SkeletonCard } from '../components/shared/Skeleton';
import { useTeacher } from '../context/TeacherContext';
import { checkAppSyncConnectivity, listStudentProgresses, triggerBackendSyncIfConfigured, type StudentProgress } from '../lib/appsync';
import type { SyncState } from '../types';

export function DashboardOverview() {
  const { teacher } = useTeacher();
  const classCode = teacher?.classCode ?? '';
  const [loading, setLoading] = useState(true);
  const [students, setStudents] = useState<StudentProgress[]>([]);
  const [syncState, setSyncState] = useState<SyncState>({
    status: 'connected',
    lastSyncTimestamp: null,
  });

  const refreshSyncStatus = useCallback(async () => {
    const result = await checkAppSyncConnectivity(classCode);
    setSyncState((s) => ({
      ...s,
      status: result.ok ? 'connected' : 'error',
      lastSyncTimestamp: result.ok ? result.lastSyncTimestamp : s.lastSyncTimestamp,
      errorMessage: result.error,
    }));
  }, [classCode]);

  const refreshStudents = useCallback(async () => {
    try {
      const items = await listStudentProgresses(classCode || '');
      setStudents(items);
    } catch {
      // Keep previous data on error
    }
  }, [classCode]);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    Promise.all([refreshSyncStatus(), refreshStudents()]).finally(() => {
      if (mounted) setLoading(false);
    });
    return () => { mounted = false; };
  }, [refreshSyncStatus, refreshStudents]);

  const handleManualSync = useCallback(async () => {
    setSyncState((s) => ({ ...s, status: 'syncing' }));
    triggerBackendSyncIfConfigured(); // optional: POST /api/sync if VITE_TEACHER_BACKEND_URL set
    const result = await checkAppSyncConnectivity(classCode);
    setSyncState({
      status: result.ok ? 'connected' : 'error',
      lastSyncTimestamp: result.ok ? result.lastSyncTimestamp : null,
      errorMessage: result.error,
    });
    if (result.ok) refreshStudents();
  }, [classCode, refreshStudents]);

  const studentSync = students.map((s) => ({
    id: s.user_id,
    name: s.user_id,
    lastSync: s.last_sync_timestamp || null,
    status: (() => {
      if (!s.last_sync_timestamp) return 'offline' as const;
      const hours = (Date.now() - new Date(s.last_sync_timestamp).getTime()) / (1000 * 60 * 60);
      return hours < 24 ? ('connected' as const) : ('offline' as const);
    })(),
    pendingItems: 0,
  }));

  const STATS = useMemo(() => {
    const active24h = studentSync.filter((s) => s.status === 'connected').length;
    return [
      { icon: '🏫', label: 'Total Classes', value: classCode ? '1' : '—', sub: 'Active this term', color: 'rgba(250,92,92,0.1)' },
      { icon: '👥', label: 'Active Students', value: String(students.length), sub: 'Synced in last 24h', color: 'rgba(0,168,232,0.1)' },
      { icon: '📝', label: 'Assignment Completion', value: '—%', sub: 'Class average', color: 'rgba(16,185,129,0.1)' },
      { icon: '📊', label: 'Recent Activity', value: String(active24h), sub: 'Last 24 hours', color: 'rgba(253,138,107,0.1)' },
    ];
  }, [classCode, students.length, studentSync]);

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
            {students.length === 0 ? (
              <div className="empty-state empty-state--compact">
                <div className="empty-state__icon" style={{ fontSize: 32 }}>📡</div>
                <h3 className="empty-state__title" style={{ fontSize: 14 }}>Waiting for sync</h3>
                <p className="empty-state__description" style={{ fontSize: 12 }}>
                  Activity appears once students come online and sync progress data.
                </p>
              </div>
            ) : (
              <ul className="recent-activity-list" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {students.slice(0, 5).map((s) => (
                  <li key={s.user_id} style={{ padding: '8px 0', borderBottom: '1px solid var(--sd-border)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span><code style={{ fontSize: 12 }}>{s.user_id}</code></span>
                      <span style={{ fontSize: 12, color: 'var(--sd-muted)' }}>
                        Streak: {s.current_streak ?? 0} · Last sync: {s.last_sync_timestamp ? new Date(s.last_sync_timestamp).toLocaleDateString() : '—'}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
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
