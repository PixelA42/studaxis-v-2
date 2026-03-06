import { memo } from 'react';
import { GlassCard } from './GlassCard';

interface MetricTileProps {
  label: string;
  value: string | number;
  subText?: string;
  icon?: string;
  isLoading?: boolean;
}

function MetricTileComponent({ label, value, subText, icon, isLoading }: MetricTileProps) {
  return (
    <GlassCard variant="stat">
      {icon && <span className="metric-tile__icon" aria-hidden="true">{icon}</span>}
      <span className="metric-tile__label">{label}</span>
      {isLoading ? (
        <div className="metric-tile__skeleton" aria-busy="true" aria-label="Loading" />
      ) : (
        <span className="metric-tile__value">{value}</span>
      )}
      {subText && !isLoading && (
        <span className="metric-tile__sub">{subText}</span>
      )}
    </GlassCard>
  );
}

export const MetricTile = memo(MetricTileComponent);
