import type { SyncStatus } from '../../types';

interface SyncStatusBadgeProps {
  status: SyncStatus;
  lastSyncTimestamp: string | null;
  size?: 'default' | 'compact';
}

const STATUS_LABELS: Record<SyncStatus, string> = {
  connected: 'Connected',
  syncing: 'Syncing',
  error: 'Error',
  offline: 'Offline',
};

function formatTimestamp(ts: string | null): string {
  if (!ts) return 'Never synced';
  try {
    const d = new Date(ts);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    if (diffMs < 60000) return 'Just now';
    if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)}m ago`;
    if (diffMs < 86400000) return `${Math.floor(diffMs / 3600000)}h ago`;
    return d.toLocaleDateString();
  } catch {
    return 'Unknown';
  }
}

export function SyncStatusBadge({
  status,
  lastSyncTimestamp,
  size = 'default',
}: SyncStatusBadgeProps) {
  const statusClass = `sync-badge sync-badge--${status}`;
  const statusLabel = STATUS_LABELS[status];

  return (
    <div className={`${statusClass} sync-badge--${size}`} role="status" aria-live="polite">
      <span className="sync-badge__dot" aria-hidden="true" />
      <span className="sync-badge__label">{statusLabel}</span>
      {size === 'default' && (
        <span className="sync-badge__timestamp">
          {formatTimestamp(lastSyncTimestamp)}
        </span>
      )}
    </div>
  );
}
