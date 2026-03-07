/**
 * Empty state — centred message when no data (Thermal Vitreous).
 */

import { type ReactNode } from "react";

export interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({
  title,
  description,
  icon = "📭",
  action,
}: EmptyStateProps) {
  return (
    <div
      className="content-card rounded-card p-10 text-center border border-glass-border"
      role="status"
    >
      <div className="text-4xl mb-4 opacity-80" aria-hidden>
        {icon}
      </div>
      <h3 className="text-lg font-extrabold font-anchor-bold text-heading-dark">{title}</h3>
      {description && (
        <p className="text-sm font-semibold text-heading-dark/75 mt-2 max-w-md mx-auto">
          {description}
        </p>
      )}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
