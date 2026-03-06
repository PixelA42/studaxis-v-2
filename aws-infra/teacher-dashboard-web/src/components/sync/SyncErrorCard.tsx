import { GlassCard } from '../dashboard/GlassCard';

interface SyncErrorCardProps {
  errorMessage: string;
}

export function SyncErrorCard({ errorMessage }: SyncErrorCardProps) {
  return (
    <GlassCard variant="banner" className="sync-error-card">
      <div className="sync-error-card__content">
        <span className="sync-error-card__icon" aria-hidden="true">⚠️</span>
        <div>
          <h3 className="sync-error-card__title">Sync Error</h3>
          <p className="sync-error-card__message">{errorMessage}</p>
        </div>
      </div>
    </GlassCard>
  );
}
