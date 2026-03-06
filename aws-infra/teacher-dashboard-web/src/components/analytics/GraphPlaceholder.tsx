import { GlassCard } from '../dashboard/GlassCard';

interface GraphPlaceholderProps {
  title: string;
  height?: number;
}

export function GraphPlaceholder({ title, height = 280 }: GraphPlaceholderProps) {
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
