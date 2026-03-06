import { GlassCard } from './GlassCard';
import { SyncStatusBadge } from '../sync/SyncStatusBadge';
import { SyncErrorCard } from '../sync/SyncErrorCard';
import { ManualSyncButton } from '../sync/ManualSyncButton';
import type { SyncState } from '../../types';

interface CloudSyncStatusProps {
  syncState: SyncState;
  onManualSync: () => void;
  isSyncing?: boolean;
}

function formatLastSync(ts: string | null): string {
  if (!ts) return 'Never synced';
  try {
    const d = new Date(ts);
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return 'Unknown';
  }
}

export function CloudSyncStatus({ syncState, onManualSync, isSyncing }: CloudSyncStatusProps) {
  const { status, lastSyncTimestamp, errorMessage } = syncState;

  return (
    <div className="cloud-sync-status-wrap">
      <GlassCard>
        <div className="cloud-sync-status">
          <div className="cloud-sync-status__header">
            <h3 className="cloud-sync-status__title">Cloud Sync Status</h3>
            <SyncStatusBadge
              status={status}
              lastSyncTimestamp={lastSyncTimestamp}
              size="default"
            />
          </div>
          <p className="cloud-sync-status__timestamp">
            Last sync: {formatLastSync(lastSyncTimestamp)}
          </p>
          <ManualSyncButton
            onClick={onManualSync}
            isSyncing={isSyncing}
          />
        </div>
      </GlassCard>
      {status === 'error' && errorMessage && (
        <div className="cloud-sync-status__error">
          <SyncErrorCard errorMessage={errorMessage} />
        </div>
      )}
    </div>
  );
}
