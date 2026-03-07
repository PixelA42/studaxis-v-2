/**
 * Stat card — glass tile with icon, value, label, optional progress (Thermal Vitreous).
 */

import { type ReactNode } from "react";

export interface StatCardProps {
  icon: ReactNode;
  iconColor?: "orange" | "blue" | "green" | "red";
  value: string;
  label: string;
  sub?: string;
  progressPct?: number;
  progressLabel?: string;
  emptyHint?: string;
}

const iconColorClasses = {
  orange: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  blue: "text-accent-blue bg-accent-blue/10 border-accent-blue/30",
  green: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  red: "text-red-400 bg-red-500/10 border-red-500/30",
};

export function StatCard({
  icon,
  iconColor = "blue",
  value,
  label,
  sub,
  progressPct,
  progressLabel,
  emptyHint,
}: StatCardProps) {
  return (
    <div className="glass-panel rounded-xl p-5 border border-glass-border">
      <div className="flex items-start gap-4">
        <div
          className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center text-lg border ${iconColorClasses[iconColor]}`}
          aria-hidden
        >
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-2xl font-semibold text-primary tabular-nums">
            {value}
          </p>
          <p className="text-sm font-medium text-primary/80">{label}</p>
          {sub && (
            <p className="text-xs text-primary/60 mt-0.5">{sub}</p>
          )}
          {progressPct != null && (
            <div className="mt-3" role="progressbar" aria-valuenow={progressPct} aria-label={progressLabel}>
              <div className="h-1.5 rounded-full bg-surface-light overflow-hidden">
                <div
                  className="h-full bg-accent-blue rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(100, progressPct)}%` }}
                />
              </div>
              {progressLabel && (
                <p className="text-xs text-primary/50 mt-1">{progressLabel}</p>
              )}
            </div>
          )}
          {emptyHint && (
            <p className="text-xs text-primary/50 mt-2 italic">{emptyHint}</p>
          )}
        </div>
      </div>
    </div>
  );
}
