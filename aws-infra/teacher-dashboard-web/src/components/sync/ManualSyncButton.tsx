
interface ManualSyncButtonProps {
  onClick: () => void;
  disabled?: boolean;
  isSyncing?: boolean;
}

export function ManualSyncButton({ onClick, disabled = false, isSyncing = false }: ManualSyncButtonProps) {
  return (
    <button
      type="button"
      className="btn btn--primary manual-sync-btn"
      onClick={onClick}
      disabled={disabled || isSyncing}
      aria-label={isSyncing ? 'Syncing…' : 'Trigger manual sync'}
    >
      {isSyncing ? (
        <>
          <span className="manual-sync-btn__spinner" aria-hidden="true" />
          Syncing…
        </>
      ) : (
        <>🔄 Sync Now</>
      )}
    </button>
  );
}
