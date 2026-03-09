
interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  className?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon = '📋', title, description, className = '', action }: EmptyStateProps) {
  return (
    <div
      className={`empty-state ${className}`}
      role="status"
      aria-label={`Empty: ${title}`}
    >
      <span className="empty-state__icon" aria-hidden="true">
        {icon}
      </span>
      <h3 className="empty-state__title">{title}</h3>
      {description && <p className="empty-state__description">{description}</p>}
      {action && <div className="empty-state__action" style={{ marginTop: 16 }}>{action}</div>}
    </div>
  );
}
