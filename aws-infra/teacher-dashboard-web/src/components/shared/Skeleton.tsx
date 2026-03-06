
interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  variant?: 'text' | 'rect' | 'circle';
  className?: string;
  'aria-label'?: string;
}

export function Skeleton({
  width,
  height,
  variant = 'rect',
  className = '',
  'aria-label': ariaLabel = 'Loading',
}: SkeletonProps) {
  const style: React.CSSProperties = {};
  if (width) style.width = typeof width === 'number' ? `${width}px` : width;
  if (height) style.height = typeof height === 'number' ? `${height}px` : height;

  return (
    <div
      role="status"
      aria-busy="true"
      aria-label={ariaLabel}
      className={`skeleton skeleton--${variant} ${className}`.trim()}
      style={style}
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="glass-card glass-card--stat" style={{ minHeight: 100 }}>
      <Skeleton width="60%" height={12} variant="text" className="skeleton-mb" />
      <Skeleton width="80%" height={32} variant="text" />
    </div>
  );
}
