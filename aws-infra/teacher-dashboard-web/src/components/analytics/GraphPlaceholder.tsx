import { memo } from 'react';
import { GlassCard } from '../dashboard/GlassCard';

interface GraphPlaceholderProps {
  title: string;
  height?: number;
}

function GraphPlaceholderComponent({ title, height = 280 }: GraphPlaceholderProps) {
  return (
    <GlassCard>
      <h3 className="graph-placeholder__title">{title}</h3>
      <div
        className="graph-placeholder__area"
        style={{ minHeight: height }}
        role="img"
        aria-label={`Chart placeholder for ${title}`}
      >
        <span className="graph-placeholder__text">Chart area — data integration pending</span>
      </div>
    </GlassCard>
  );
}

export const GraphPlaceholder = memo(GraphPlaceholderComponent);
