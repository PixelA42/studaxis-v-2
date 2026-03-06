import { useCallback, useMemo, useState } from 'react';
import { MetricTile } from '../components/dashboard/MetricTile';
import { GlassCard } from '../components/dashboard/GlassCard';
import { CloudSyncStatus } from '../components/dashboard/CloudSyncStatus';
import { StudentSyncOverview } from '../components/sync/StudentSyncOverview';
import { RecentSyncActivity } from '../components/sync/RecentSyncActivity';
import { StaleDataWarning } from '../components/sync/StaleDataWarning';
import { SkeletonCard } from '../components/shared/Skeleton';
import type { SyncState, DashboardMetrics } from '../types';

// Mock/placeholder data — no backend logic
const DEMO_METRICS: DashboardMetrics = {
  totalClasses: 4,
  activeStudents: 32,
  assignmentCompletionRate: 78,
  recentActivityCount: 12,
};

const DEMO_RECENT_ACTIVITY = [
  { id: '1', studentName: 'Student A', action: 'Completed Algebra quiz', timestamp: new Date(Date.now() - 120000).toISOString(), type: 'quiz' as const },
  { id: '2', studentName: 'Student B', action: 'Synced progress', timestamp: new Date(Date.now() - 900000).toISOString(), type: 'sync' as const },
  { id: '3', studentName: 'Student C', action: 'Started Flashcards', timestamp: new Date(Date.now() - 3600000).toISOString(), type: 'content' as const },
  { id: '4', studentName: 'Student D', action: 'Maintained 15-day streak', timestamp: new Date(Date.now() - 7200000).toISOString(), type: 'streak' as const },
];

const DEMO_STUDENT_SYNC = [
  { id: 'STU001', name: 'Student A', lastSync: new Date(Date.now() - 600000).toISOString(), status: 'connected' as const, pendingItems: 0 },
  { id: 'STU002', name: 'Student B', lastSync: new Date(Date.now() - 1800000).toISOString(), status: 'connected' as const, pendingItems: 0 },
  { id: 'STU003', name: 'Student C', lastSync: new Date(Date.now() - 90000000).toISOString(), status: 'offline' as const, pendingItems: 3 },
  { id: 'STU004', name: 'Student D', lastSync: new Date(Date.now() - 3600000).toISOString(), status: 'connected' as const, pendingItems: 0 },
  { id: 'STU005', name: 'Student E', lastSync: null, status: 'offline' as const, pendingItems: 0 },
];

export function DashboardOverview() {
  const [loading] = useState(false);
  const [syncState, setSyncState] = useState<SyncState>({
    status: 'connected',
    lastSyncTimestamp: new Date().toISOString(),
  });

  const handleManualSync = () => {
    setSyncState((s) => ({ ...s, status: 'syncing' }));
    setTimeout(() => {
      setSyncState({
        status: 'connected',
        lastSyncTimestamp: new Date().toISOString(),
      });
    }, 1500);
  };

  const metrics = DEMO_METRICS;
  const recentActivity = DEMO_RECENT_ACTIVITY;
  const studentSync = DEMO_STUDENT_SYNC;
  
  // Get stale students (not synced in 24h)
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

  const handleStudentClick = useCallback((studentId: string) => {
    console.log('Student clicked:', studentId);
  }, []);

  return (
    <main id="main-content" className="page-dashboard" role="main">
      <h1 className="page-title">Dashboard Overview</h1>
      
      {/* Stale data warning */}
      {staleStudents.length > 0 && (
        <StaleDataWarning studentNames={staleStudents} />
      )}

      {/* Bento grid — metrics */}
      <section aria-label="Key metrics" className="bento-section">
        <div className="bento-grid">
          {loading ? (
            <>
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : (
            <>
              <MetricTile
                label="Total Classes"
                value={metrics.totalClasses}
                subText="Active this term"
                icon="🏫"
              />
              <MetricTile
                label="Active Students"
                value={metrics.activeStudents}
                subText="Synced in last 24h"
                icon="👥"
              />
              <MetricTile
                label="Assignment Completion"
                value={`${metrics.assignmentCompletionRate}%`}
                subText="Class average"
                icon="📝"
              />
              <MetricTile
                label="Recent Activity"
                value={metrics.recentActivityCount}
                subText="Last 24 hours"
                icon="📊"
              />
            </>
          )}
        </div>
      </section>

      {/* Student Sync Overview + Recent Activity */}
      <section className="bento-section bento-section--row" aria-label="Sync overview">
        <div className="bento-section__half">
          <GlassCard>
            <h2 className="card-title">Student Sync Status</h2>
            <p className="card-sub">Device connectivity overview</p>
            <StudentSyncOverview
              students={studentSync}
              onStudentClick={handleStudentClick}
            />
          </GlassCard>
        </div>
        <div className="bento-section__half">
          <GlassCard>
            <RecentSyncActivity activities={recentActivity} maxItems={8} />
          </GlassCard>
        </div>
      </section>

      {/* Cloud Sync Status */}
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
