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
  pastelBg?: "pink" | "blue" | "yellow";
  children?: ReactNode;
}

const iconColorClasses = {
  blue: "text-accent-blue bg-accent-blue/10 border-accent-blue/30",
  orange: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  green: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  red: "text-red-400 bg-red-500/10 border-red-500/30",
};

/* Chunky color blocks — large solid fills per reference (25% of layout) */
const chunkBgClasses = {
  pink: "bg-chunk-pink",
  blue: "bg-chunk-blue",
  yellow: "bg-chunk-yellow",
};

export function FeatureCard({
  icon,
  iconColor = "blue",
  title,
  description,
  meta,
  pastelBg,
  children,
}: FeatureCardProps) {
  const isChunk = !!pastelBg;
  const bgClass = pastelBg ? chunkBgClasses[pastelBg] : "content-card";
  const textClass = isChunk ? "text-heading-dark" : "text-primary";
  const subTextClass = isChunk ? "text-heading-dark/80" : "text-primary/70";
  const metaClass = isChunk ? "text-heading-dark/70" : "text-primary/50";
  return (
    <div className={`${bgClass} rounded-card p-5 shadow-card hover:shadow-soft transition-shadow ${!isChunk ? "border border-glass-border" : ""}`}>
      <div className="flex items-start gap-4">
        <div
          className={`flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center text-xl border ${iconColorClasses[iconColor]}`}
          aria-hidden
        >
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className={`font-extrabold font-anchor-bold ${textClass}`}>{title}</h3>
          <p className={`text-sm font-medium ${subTextClass} mt-1`}>{description}</p>
          {meta && (
            <p className={`text-xs font-mono mt-2 ${metaClass}`}>{meta}</p>
          )}
          {children && <div className="mt-4">{children}</div>}
        </div>
      </div>
    </div>
  );
}
