/**
 * Sync Status page — last sync, connectivity, queue, manual sync trigger.
 */

import { useState, useEffect } from "react";
import { PageChrome, GlassCard, StatusIndicator } from "../components";
import { useAuth } from "../contexts/AuthContext";
import { getSyncStatus, postSync } from "../services/api";
import { loadSyncQueue } from "../services/storage";

function formatLastSync(iso: string | null | undefined): string {
  if (!iso) return "Never";
  try {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffM = Math.floor(diffMs / 60000);
    if (diffM < 1) return "Just now";
    if (diffM < 60) return `${diffM}m ago`;
    const diffH = Math.floor(diffM / 60);
    if (diffH < 24) return `${diffH}h ago`;
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  } catch {
    return "Unknown";
  }
}

export function SyncPage() {
  const { connectivityStatus } = useAuth();
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [queueTotal, setQueueTotal] = useState<number | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const loadStatus = () => {
    if (connectivityStatus !== "online") return;
    getSyncStatus()
      .then((s) => {
        setLastSync(s?.last_sync_timestamp ?? null);
        setQueueTotal(s?.queue?.total ?? null);
      })
      .catch(() => {
        setLastSync(null);
        setQueueTotal(null);
      });
  };

  useEffect(() => {
    loadStatus();
  }, [connectivityStatus]);

  const handleSyncNow = async () => {
    if (connectivityStatus === "offline") return;
    setSyncing(true);
    setSyncMessage(null);
    try {
      const res = await postSync();
      setSyncMessage(res.message ?? (res.ok ? "Sync triggered." : "Sync failed."));
      if (res.ok) loadStatus();
    } catch (e) {
      setSyncMessage(e instanceof Error ? e.message : "Sync request failed.");
    } finally {
      setSyncing(false);
    }
  };

  const isOffline = connectivityStatus === "offline";
  const canSync = !isOffline && !syncing;
  const frontendQueueCount = loadSyncQueue().length;

  return (
    <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold text-primary">Sync Status</h2>
        <p className="text-primary/80">
          Cloud sync state and manual sync trigger. Data syncs when connectivity is available.
        </p>

        <GlassCard title="Status">
          <div className="flex flex-wrap items-center gap-4">
            <span className="text-primary/70">Connectivity</span>
            <StatusIndicator status={connectivityStatus} />
          </div>
        </GlassCard>

        <GlassCard title="Cloud Sync">
          <div className="space-y-4">
            <div>
              <span className="text-primary/60 text-sm block">Last sync</span>
              <span className="text-primary font-medium">{formatLastSync(lastSync)}</span>
            </div>
            {queueTotal !== null && queueTotal > 0 && (
              <div>
                <span className="text-primary/60 text-sm block">Backend queue</span>
                <span className="text-primary font-medium">{queueTotal} item{queueTotal !== 1 ? "s" : ""} pending</span>
              </div>
            )}
            {frontendQueueCount > 0 && (
              <div>
                <span className="text-primary/60 text-sm block">Pending upload</span>
                <span className="text-primary font-medium">{frontendQueueCount} item{frontendQueueCount !== 1 ? "s" : ""} (flashcards, quiz) will sync when online</span>
              </div>
            )}
            {syncMessage && (
              <p className={`text-sm ${syncMessage.toLowerCase().includes("fail") ? "text-amber-400" : "text-primary/80"}`}>
                {syncMessage}
              </p>
            )}
            <button
              type="button"
              onClick={handleSyncNow}
              disabled={!canSync}
              className="px-5 py-2.5 rounded-xl font-medium text-deep bg-accent-blue hover:bg-accent-blue/90 focus:outline-none focus:ring-2 focus:ring-accent-blue disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {syncing ? "Syncing…" : "Sync Now"}
            </button>
            {isOffline && (
              <p className="text-sm text-primary/60">Data will sync when online.</p>
            )}
          </div>
        </GlassCard>

        <GlassCard title="About">
          <p className="text-sm text-primary/80">
            Progress is queued when offline and syncs automatically when you're back online. Sync uploads progress summaries (scores, streaks) to the cloud.
          </p>
        </GlassCard>
      </div>
    </PageChrome>
  );
}
