/**
 * Offline-first: Sync queue badge count for nav.
 * Backend queue when online; frontend localStorage queue when offline.
 */
import { useEffect, useState } from "react";
import { getSyncStatus } from "../services/api";
import { loadSyncQueue } from "../services/storage";

const POLL_INTERVAL_MS = 15000;

export function useSyncQueueCount(): number {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const update = () => {
      getSyncStatus()
        .then((s) => setCount(s?.queue?.total ?? 0))
        .catch(() => setCount(loadSyncQueue().length));
    };

    update();
    const id = setInterval(update, POLL_INTERVAL_MS);
    const onQueueChange = () => update();
    window.addEventListener("sync-queue-updated", onQueueChange);
    return () => {
      clearInterval(id);
      window.removeEventListener("sync-queue-updated", onQueueChange);
    };
  }, []);

  return count;
}
