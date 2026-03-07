/**
 * Feature card — bento tile for dashboard (AI Chat, Quiz, Flashcards, Panic Mode).
 */

import { type ReactNode } from "react";

export interface FeatureCardProps {
  icon: ReactNode;
  iconColor?: "blue" | "orange" | "green" | "red";
  title: string;
  description: string;
  meta?: string;
  variant?: "default" | "ai" | "flashcards" | "panic";
  children?: ReactNode;
}

const iconColorClasses = {
  blue: "text-accent-blue bg-accent-blue/10 border-accent-blue/30",
  orange: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  green: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  red: "text-red-400 bg-red-500/10 border-red-500/30",
};

export function FeatureCard({
  icon,
  iconColor = "blue",
  title,
  description,
  meta,
  children,
}: FeatureCardProps) {
  return (
    <div className="glass-panel rounded-xl p-5 border border-glass-border hover:border-glass-border/80 transition-colors">
      <div className="flex items-start gap-4">
        <div
          className={`flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center text-xl border ${iconColorClasses[iconColor]}`}
          aria-hidden
        >
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-primary">{title}</h3>
          <p className="text-sm text-primary/70 mt-1">{description}</p>
          {meta && (
            <p className="text-xs text-primary/50 mt-2 font-mono">{meta}</p>
          )}
          {children && <div className="mt-4">{children}</div>}
        </div>
      </div>
    </div>
  );
}
