/**
 * Home page — Hero section + Jump Back In (recent tools) section.
 * Uses localStorage for offline-first recent activity tracking.
 */

import { Link } from "react-router-dom";
import HeroSection from "../components/HeroSection";
import { useRecentTools, ALL_TOOLS } from "../hooks/useRecentTools";
import { Icons } from "../components/icons";

const TOOL_ICONS: Record<string, React.ReactNode> = {
  "Panic Mode": Icons.panic,
  "Flash Cards": Icons.cards,
  "AI Chat": Icons.ai,
  Quiz: Icons.quiz,
};

export function HomePage() {
  const recentTools = useRecentTools();
  const hasRecent = recentTools.length > 0;

  return (
    <div className="flex flex-col">
      {/* Hero — compact for dashboard context */}
      <div style={{ margin: "0 -24px" }}>
        <HeroSection />
      </div>

      {/* Jump Back In / Recent Activity — rounded box with gradient */}
      <section
        className="mt-8 rounded-2xl p-6 sm:p-8"
        style={{
          background: "linear-gradient(135deg, rgba(0,168,232,0.08) 0%, rgba(254,194,136,0.12) 40%, rgba(251,239,118,0.06) 100%)",
          border: "1px solid rgba(0,168,232,0.15)",
          boxShadow: "0 4px 24px rgba(0,0,0,0.04)",
        }}
      >
        <h2 className="text-xl font-bold text-heading-dark mb-4">
          {hasRecent ? "Jump Back In" : "Start Learning"}
        </h2>

        {hasRecent ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {recentTools.map((tool) => (
              <Link
                key={tool.path}
                to={tool.path}
                className="content-card border border-glass-border rounded-xl p-4 flex items-center gap-3 hover:shadow-soft hover:border-accent-blue/30 transition-all duration-200 group bg-white/60 backdrop-blur-sm"
              >
                <div className="w-10 h-10 rounded-lg bg-accent-blue/15 flex items-center justify-center text-accent-blue group-hover:bg-accent-blue/25 transition-colors">
                  {TOOL_ICONS[tool.label] ?? Icons.dashboard}
                </div>
                <div className="min-w-0 flex-1">
                  <span className="font-semibold text-heading-dark block truncate">
                    {tool.label}
                  </span>
                  <span className="text-xs text-muted">Continue</span>
                </div>
                <span className="text-accent-blue opacity-0 group-hover:opacity-100 transition-opacity">
                  →
                </span>
              </Link>
            ))}
          </div>
        ) : (
          <div className="rounded-xl p-8 text-center bg-white/50 backdrop-blur-sm border border-white/60">
            <p className="text-muted mb-6">
              Pick a tool below to start your first session.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {ALL_TOOLS.map((tool) => (
                <Link
                  key={tool.path}
                  to={tool.path}
                  className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-accent-blue/15 text-accent-blue font-semibold hover:bg-accent-blue/25 transition-colors"
                >
                  {TOOL_ICONS[tool.label] ?? Icons.dashboard}
                  {tool.label}
                </Link>
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
