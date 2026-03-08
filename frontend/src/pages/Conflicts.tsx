/**
 * Conflicts page — list and resolve sync conflicts from ConflictAwareOrchestrator.
 */

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageChrome, GlassCard, StatusIndicator } from "../components";
import { useAuth } from "../contexts/AuthContext";
import {
  getSyncConflicts,
  resolveConflict,
  type SyncConflict,
} from "../services/api";

function formatTimeAgo(iso: string | undefined): string {
  if (!iso) return "—";
  try {
    const dt = new Date(iso.replace("Z", "+00:00"));
    const now = new Date();
    const ms = now.getTime() - dt.getTime();
    const mins = Math.floor(ms / 60000);
    const hours = Math.floor(ms / 3600000);
    const days = Math.floor(ms / 86400000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins} min ago`;
    if (hours < 24) return `${hours} hr ago`;
    return `${days} day${days !== 1 ? "s" : ""} ago`;
  } catch {
    return "—";
  }
}

function formatTimestamp(iso: string | undefined): string {
  if (!iso) return "—";
  try {
    const dt = new Date(iso.replace("Z", "+00:00"));
    return dt.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

export function ConflictsPage() {
  const { connectivityStatus } = useAuth();
  const [conflicts, setConflicts] = useState<SyncConflict[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resolving, setResolving] = useState<string | null>(null);

  const isOffline = connectivityStatus === "offline";

  const loadConflicts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getSyncConflicts();
      setConflicts(res.conflicts ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load conflicts");
      setConflicts([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOffline) {
      setError("Connect to view and resolve conflicts.");
      setLoading(false);
      setConflicts([]);
      return;
    }
    loadConflicts();
  }, [isOffline, loadConflicts]);

  const handleResolve = async (
    entityId: string,
    choice: "keep_local" | "keep_cloud" | "merge"
  ) => {
    if (isOffline) return;
    setResolving(entityId);
    try {
      await resolveConflict(entityId, choice);
      await loadConflicts();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Resolution failed");
    } finally {
      setResolving(null);
    }
  };

  return (
    <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold text-primary">Conflicts</h2>
        <p className="text-primary/80">
          When local and cloud data differ, conflicts appear here. Resolve them
          to keep progress in sync.
        </p>

        <div className="flex flex-wrap items-center gap-3 mb-4">
          <span className="text-sm text-primary/70">Connectivity</span>
          <StatusIndicator status={connectivityStatus} />
        </div>

        {loading && (
          <GlassCard title="Loading">
            <p className="text-primary/80">Fetching conflicts…</p>
          </GlassCard>
        )}

        {error && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-amber-400 text-sm">
            {error}
          </div>
        )}

        {!loading && conflicts.length === 0 && (
          <GlassCard title="Conflict resolution">
            <p className="text-primary/80 mb-4">
              No conflicts right now. All data is synchronized.
            </p>
            <Link
              to="/sync"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary hover:bg-surface-light/80 font-medium text-sm"
            >
              Open Sync Status
            </Link>
          </GlassCard>
        )}

        {!loading && conflicts.length > 0 && (
          <div className="space-y-4">
            <p className="text-amber-400 text-sm font-medium">
              {conflicts.length} conflict{conflicts.length !== 1 ? "s" : ""}{" "}
              require your attention.
            </p>
            {conflicts.map((c) => (
              <GlassCard
                key={c.entity_id}
                title={`${c.entity_type} — ${c.entity_id}`}
              >
                <div className="space-y-4">
                  <div className="flex flex-wrap gap-2 text-sm">
                    <span className="text-primary/60">
                      Detected {formatTimeAgo(c.detected_at)}
                    </span>
                    <span className="text-primary/60">•</span>
                    <span className="text-primary/60">Reason: {c.reason}</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="rounded-lg border border-glass-border bg-surface-light/50 p-4">
                      <h4 className="text-sm font-semibold text-primary mb-2">
                        📱 Local (this device)
                      </h4>
                      <p className="text-xs text-primary/60 mb-1">
                        v{c.local_version ?? "?"} •{" "}
                        {formatTimestamp(c.local_updated_at)}
                      </p>
                      <pre className="text-xs text-primary/80 overflow-x-auto max-h-32 overflow-y-auto font-mono bg-black/20 rounded p-2">
                        {JSON.stringify(c.local_data ?? {}, null, 2)}
                      </pre>
                    </div>
                    <div className="rounded-lg border border-glass-border bg-surface-light/50 p-4">
                      <h4 className="text-sm font-semibold text-primary mb-2">
                        ☁️ Cloud
                      </h4>
                      <p className="text-xs text-primary/60 mb-1">
                        v{c.cloud_version ?? "?"} •{" "}
                        {formatTimestamp(c.cloud_updated_at)}
                      </p>
                      <pre className="text-xs text-primary/80 overflow-x-auto max-h-32 overflow-y-auto font-mono bg-black/20 rounded p-2">
                        {JSON.stringify(c.cloud_data ?? {}, null, 2)}
                      </pre>
                    </div>
                  </div>

                  {c.conflicting_fields && c.conflicting_fields.length > 0 && (
                    <p className="text-xs text-primary/60">
                      Conflicting fields: {c.conflicting_fields.join(", ")}
                    </p>
                  )}

                  <div className="flex flex-wrap gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => handleResolve(c.entity_id, "keep_local")}
                      disabled={resolving === c.entity_id || isOffline}
                      className="px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary hover:bg-accent-primary/20 hover:border-accent-primary/50 font-medium text-sm disabled:opacity-50"
                    >
                      {resolving === c.entity_id ? "Resolving…" : "📱 Keep Local"}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleResolve(c.entity_id, "keep_cloud")}
                      disabled={resolving === c.entity_id || isOffline}
                      className="px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary hover:bg-accent-primary/20 hover:border-accent-primary/50 font-medium text-sm disabled:opacity-50"
                    >
                      ☁️ Keep Cloud
                    </button>
                    <button
                      type="button"
                      onClick={() => handleResolve(c.entity_id, "merge")}
                      disabled={resolving === c.entity_id || isOffline}
                      className="px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary hover:bg-accent-primary/20 hover:border-accent-primary/50 font-medium text-sm disabled:opacity-50"
                    >
                      🔀 Merge Both
                    </button>
                  </div>
                </div>
              </GlassCard>
            ))}
          </div>
        )}
      </div>
    </PageChrome>
  );
}
