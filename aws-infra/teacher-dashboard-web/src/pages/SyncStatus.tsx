import { useEffect, useState } from 'react';
import { GlassCard } from '../components/dashboard/GlassCard';
import { EmptyState } from '../components/shared/EmptyState';
import { useTeacher } from '../context/TeacherContext';
import { checkAppSyncConnectivity } from '../lib/appsync';

type ServiceStatus = 'checking' | 'connected' | 'error' | 'pending';

interface StatusItem {
  svc: string;
  desc: string;
  status: ServiceStatus;
  icon: string;
}

export function SyncStatus() {
  const { teacher } = useTeacher();
  const classCode = teacher?.classCode ?? '';
  const [statusItems, setStatusItems] = useState<StatusItem[]>([
    { svc: 'DynamoDB', desc: 'Sync metadata store', status: 'checking', icon: '🗄️' },
    { svc: 'S3 Bucket', desc: 'Quiz & payload storage', status: 'pending', icon: '📦' },
    { svc: 'API Gateway', desc: 'Quiz generation endpoint', status: 'pending', icon: '🔌' },
    { svc: 'AppSync', desc: 'GraphQL delta sync', status: 'checking', icon: '🔄' },
  ]);

  useEffect(() => {
    let mounted = true;
    checkAppSyncConnectivity(classCode).then((result) => {
      if (!mounted) return;
      setStatusItems((prev) =>
        prev.map((s) => {
          if (s.svc === 'AppSync') {
            return { ...s, status: (result.ok ? 'connected' : 'error') as ServiceStatus };
          }
          if (s.svc === 'DynamoDB') {
            return { ...s, status: (result.ok ? 'connected' : 'pending') as ServiceStatus };
          }
          return s;
        })
      );
    });
    return () => { mounted = false; };
  }, [classCode]);

  function chipClass(status: ServiceStatus): string {
    if (status === 'connected') return 'chip chip-green';
    if (status === 'error') return 'chip chip-red';
    if (status === 'checking') return 'chip chip-blue';
    return 'chip chip-grey';
  }

  function statusLabel(status: ServiceStatus): string {
    if (status === 'connected') return 'Connected';
    if (status === 'error') return 'Error';
    if (status === 'checking') return 'Checking…';
    return 'Pending';
  }

  return (
    <main id="main-content" className="page-sync" role="main">
      <div className="page-header-block">
        <h1 className="page-title">AWS Sync Status</h1>
        <p className="page-sub">Real-time status of your cloud infrastructure connections.</p>
      </div>

      <div className="notif-banner notif-info">
        <div className="notif-banner-icon">🔧</div>
        <div>
          <div className="notif-banner-title">Cloud sync status</div>
          <div className="notif-banner-text">
            AppSync and DynamoDB are verified via listStudentProgresses. S3 and API Gateway are used by the quiz pipeline.
          </div>
        </div>
      </div>

      <div className="sync-status-grid">
        {statusItems.map((s, i) => (
          <GlassCard key={i} className="sync-status-card">
            <div className="sync-status-icon">{s.icon}</div>
            <div className="sync-status-content">
              <div className="sync-status-svc">{s.svc}</div>
              <div className="sync-status-desc">{s.desc}</div>
            </div>
            <span className={chipClass(s.status)}>{statusLabel(s.status)}</span>
          </GlassCard>
        ))}
      </div>

      <GlassCard className="sync-queue-card">
        <div className="sync-queue-title">Sync Queue</div>
        <EmptyState
          icon="✅"
          title="Queue is empty"
          description="Pending mutations appear here when students submit data offline. They sync automatically when connectivity is restored."
        />
      </GlassCard>
    </main>
  );
}
