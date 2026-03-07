/**
 * Conflicts page — list and resolve sync conflicts. Placeholder until orchestrator wired.
 */

import { Link } from "react-router-dom";
import { PageChrome, GlassCard } from "../components";

export function ConflictsPage() {
  return (
    <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold text-primary">Conflicts</h2>
        <p className="text-primary/80">
          When local and cloud data differ, conflicts appear here. Resolve them to keep progress in sync.
        </p>
        <GlassCard title="Conflict resolution">
          <p className="text-primary/80 mb-4">
            No conflicts right now. The sync orchestrator will surface conflicts here when they occur.
          </p>
          <Link
            to="/sync"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary hover:bg-surface-light/80 font-medium text-sm"
          >
            Open Sync Status
          </Link>
        </GlassCard>
      </div>
    </PageChrome>
  );
}
