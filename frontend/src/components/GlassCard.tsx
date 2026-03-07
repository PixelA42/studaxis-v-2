import { type ReactNode } from "react";

export interface GlassCardProps {
  children: ReactNode;
  title?: string;
  className?: string;
  /** Optional class for the content wrapper (default: p-5 text-primary) */
  contentClassName?: string;
}

/**
 * Reusable glass card — Thermal Vitreous design system.
 * Standard UI container replacing Streamlit card/container with glass-panel styling.
 */
export function GlassCard({
  children,
  title,
  className = "",
  contentClassName = "p-5 text-heading-dark",
}: GlassCardProps) {
  return (
    <div className={`content-card rounded-card overflow-hidden border border-glass-border ${className}`}>
      {title && (
        <div className="px-5 py-3 border-b border-glass-border">
          <h3 className="text-heading-dark font-sans font-bold text-base">
            {title}
          </h3>
        </div>
      )}
      <div className={contentClassName}>{children}</div>
    </div>
  );
}
