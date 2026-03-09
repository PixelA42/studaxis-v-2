import { useEffect, useState } from 'react';
import { GlassCard } from '../components/dashboard/GlassCard';
import { EmptyState } from '../components/shared/EmptyState';
import { useClass } from '../context/ClassContext';
import { checkAppSyncConnectivity } from '../lib/appsync';

type ServiceStatus = 'checking' | 'connected' | 'error' | 'pending';

type ServiceKey = 'DynamoDB' | 'S3' | 'API_GATEWAY' | 'AppSync';

interface StatusItem {
  key: ServiceKey;
  svc: string;
  desc: string;
  status: ServiceStatus;
  icon: string;
}

const INITIAL_STATUS_ITEMS: StatusItem[] = [
  { key: 'DynamoDB', svc: 'Student Progress Database', desc: 'Securely tracks student streaks, scores, and analytics.', status: 'checking', icon: '🗄️' },
  { key: 'S3', svc: 'Cloud Storage Library', desc: 'Stores your generated quizzes, PDFs, and learning materials.', status: 'pending', icon: '📦' },
  { key: 'API_GATEWAY', svc: 'AI Curriculum Engine (Bedrock)', desc: 'Powers the automated generation of assessments and quizzes.', status: 'pending', icon: '🤖' },
  { key: 'AppSync', svc: 'Live Roster Connection', desc: 'Receives offline student updates the moment they connect to Wi-Fi.', status: 'checking', icon: '🔄' },
];

export function SyncStatus() {
  const { activeClass } = useClass();
  const classCode = activeClass?.class_code ?? '';
  const [statusItems, setStatusItems] = useState<StatusItem[]>(INITIAL_STATUS_ITEMS);

  useEffect(() => {
    let mounted = true;
    checkAppSyncConnectivity(classCode).then((result) => {
      if (!mounted) return;
      setStatusItems((prev) =>
        prev.map((s) => {
          if (s.key === 'AppSync') {
            return { ...s, status: (result.ok ? 'connected' : 'error') as ServiceStatus };
          }
          if (s.key === 'DynamoDB') {
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
        <h1 className="page-title">Platform Health & Status</h1>
        <p className="page-sub">Real-time status of your platform connections.</p>
      </div>

      <div className="notif-banner notif-info">
        <div className="notif-banner-icon">👋</div>
        <div>
          <div className="notif-banner-title">Invite Your Students</div>
          <div className="notif-banner-text">
            Share your unique Class Code{' '}
            <strong style={{ fontFamily: 'monospace', letterSpacing: 2 }}>{classCode || '—'}</strong>
            {' '}with your students. Their offline progress will appear here automatically when they sync.
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
        <div className="sync-queue-title">Pending Student Updates</div>
        <EmptyState
          icon="✅"
          title="All student data is up to date"
          description="When students work offline, their updates will appear here once they connect to Wi-Fi. They sync automatically when connectivity is restored."
        />
      </GlassCard>
    </main>
  );
}
