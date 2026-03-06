import type { ReactNode } from 'react';

interface GlassCardProps {
  children: ReactNode;
  variant?: 'primary' | 'stat' | 'banner';
  className?: string;
  onClick?: () => void;
  as?: keyof JSX.IntrinsicElements;
}

export function GlassCard({
  children,
  variant = 'primary',
  className = '',
  onClick,
  as: Component = 'div',
}: GlassCardProps) {
  const classNames = [
    'glass-card',
    variant !== 'primary' && `glass-card--${variant}`,
    onClick && 'glass-card--clickable',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <Component
      className={classNames}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
    >
      {children}
    </Component>
  );
}
