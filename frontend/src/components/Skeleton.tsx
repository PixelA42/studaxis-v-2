/**
 * Skeleton — loading placeholder for stats, cards, lists.
 * Thermal Vitreous style.
 */

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  variant?: "text" | "rect" | "circle";
  className?: string;
  "aria-label"?: string;
}

export function Skeleton({
  width,
  height,
  variant = "rect",
  className = "",
  "aria-label": ariaLabel = "Loading",
}: SkeletonProps) {
  const style: React.CSSProperties = {};
  if (width) style.width = typeof width === "number" ? `${width}px` : width;
  if (height) style.height = typeof height === "number" ? `${height}px` : height;

  return (
    <div
      role="status"
      aria-busy="true"
      aria-label={ariaLabel}
      className={`skeleton skeleton-${variant} rounded animate-pulse ${className}`.trim()}
      style={{
        ...style,
        backgroundColor: "var(--glass-border)",
      }}
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="content-card border border-glass-border rounded-2xl p-4" style={{ minHeight: 120 }}>
      <Skeleton width="50%" height={14} variant="text" className="mb-3" aria-label="Loading stat label" />
      <Skeleton width="70%" height={32} variant="text" aria-label="Loading stat value" />
      <Skeleton width="40%" height={10} variant="text" className="mt-2" aria-label="Loading sub" />
    </div>
  );
}
