import { GlassCard } from '../components/dashboard/GlassCard';
import { EmptyState } from '../components/shared/EmptyState';

const STATUS_ITEMS = [
  { svc: 'DynamoDB', desc: 'Sync metadata store', status: 'Pending', icon: '🗄️' },
  { svc: 'S3 Bucket', desc: 'Quiz & payload storage', status: 'Pending', icon: '📦' },
  { svc: 'API Gateway', desc: 'Quiz generation endpoint', status: 'Pending', icon: '🔌' },
  { svc: 'AppSync', desc: 'GraphQL delta sync', status: 'Pending', icon: '🔄' },
];

export function SyncStatus() {
  return (
    <main id="main-content" className="page-sync" role="main">
      <div className="page-header-block">
        <h1 className="page-title">AWS Sync Status</h1>
        <p className="page-sub">Real-time status of your cloud infrastructure connections.</p>
      </div>

      <div className="notif-banner notif-info">
        <div className="notif-banner-icon">🔧</div>
        <div>
          <div className="notif-banner-title">Configure AWS Credentials</div>
          <div className="notif-banner-text">
            Add your AWS region, DynamoDB table name, and S3 bucket in Settings to enable live sync monitoring.
          </div>
        </div>
      </div>

      <div className="sync-status-grid">
        {STATUS_ITEMS.map((s, i) => (
          <GlassCard key={i} className="sync-status-card">
            <div className="sync-status-icon">{s.icon}</div>
            <div className="sync-status-content">
              <div className="sync-status-svc">{s.svc}</div>
              <div className="sync-status-desc">{s.desc}</div>
            </div>
            <span className="chip chip-grey">{s.status}</span>
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
