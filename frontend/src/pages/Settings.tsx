/**
 * Settings page — Cloud Sync, Appearance, Learning Preferences, Deployment, Account.
 * Phase 7: All toggles persist via PUT /api/user/stats.
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { PageChrome, GlassCard } from "../components";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";
import {
  getUserStats,
  updateUserStats,
  getDataExport,
  postDataClear,
  getDiagnostics,
  getStorageFiles,
} from "../services/api";
import type { UserStats, DiagnosticsResponse, StorageFileItem } from "../services/api";

export function SettingsPage() {
  const navigate = useNavigate();
  const { profile, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const [stats, setStats] = useState<UserStats | null>(null);
  const [saving, setSaving] = useState(false);
  const [storageLoading, setStorageLoading] = useState(false);
  const [storageAction, setStorageAction] = useState<"export" | "clear" | null>(null);
  const [diagnostics, setDiagnostics] = useState<DiagnosticsResponse | null>(null);
  const [storageFiles, setStorageFiles] = useState<StorageFileItem[]>([]);
  const [safeMode, setSafeMode] = useState(false);

  useEffect(() => {
    getUserStats().then(setStats).catch(() => setStats(null));
    getDiagnostics().then(setDiagnostics).catch(() => setDiagnostics(null));
    getStorageFiles().then((r) => setStorageFiles(r.files)).catch(() => setStorageFiles([]));
  }, []);

  const preferences = stats?.preferences ?? {};
  const syncEnabled = preferences.sync_enabled ?? true;
  const difficultyLevel = preferences.difficulty_level ?? "Beginner";

  const refreshDiagnostics = () => {
    getDiagnostics().then(setDiagnostics).catch(() => setDiagnostics(null));
  };

  const handleSyncToggle = async (next: boolean) => {
    setSaving(true);
    try {
      await updateUserStats({ preferences: { ...preferences, sync_enabled: next } });
      setStats((s) => (s ? { ...s, preferences: { ...(s.preferences ?? {}), sync_enabled: next } } : null));
      refreshDiagnostics();
    } finally {
      setSaving(false);
    }
  };

  const handleDifficultyChange = async (next: string) => {
    setSaving(true);
    try {
      await updateUserStats({ preferences: { ...preferences, difficulty_level: next } });
      setStats((s) => (s ? { ...s, preferences: { ...(s.preferences ?? {}), difficulty_level: next } } : null));
    } finally {
      setSaving(false);
    }
  };

  const handleSignOut = () => {
    logout();
    navigate("/", { replace: true });
  };

  const handleExportData = async () => {
    setStorageLoading(true);
    setStorageAction("export");
    try {
      const data = await getDataExport();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `studaxis-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
      alert(err instanceof Error ? err.message : "Export failed.");
    } finally {
      setStorageLoading(false);
      setStorageAction(null);
    }
  };

  const handleClearData = async () => {
    if (!window.confirm("Clear all local study data? This will reset stats, flashcards, and profile. Your account will remain. This cannot be undone.")) {
      return;
    }
    setStorageLoading(true);
    setStorageAction("clear");
    try {
      await postDataClear();
      setStats(null);
      window.location.reload();
    } catch (err) {
      console.error("Clear failed:", err);
      alert(err instanceof Error ? err.message : "Clear failed.");
    } finally {
      setStorageLoading(false);
      setStorageAction(null);
    }
  };

  const profileName = profile.profile_name || "Student";
  const modeLabel = profile.profile_mode === "solo" || !profile.profile_mode ? "Solo" : "Class Linked";

  return (
    <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold text-primary">Settings</h2>
        <p className="text-primary/80">
          Deployment readiness, diagnostics, sync, and personal preferences.
        </p>

        <GlassCard title="Cloud Sync">
          <p className="text-sm text-primary/70 mb-4">
            Control how your progress syncs with the cloud. Disabling keeps all data local.
          </p>
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={syncEnabled}
              onChange={(e) => handleSyncToggle(e.target.checked)}
              disabled={saving}
              className="rounded border-glass-border bg-deep text-accent-blue focus:ring-accent-blue"
            />
            <span className="text-primary">Enable Cloud Sync</span>
          </label>
          {!syncEnabled && (
            <p className="text-sm text-primary/60 mt-2">Cloud sync is disabled. Progress stays on this device.</p>
          )}
        </GlassCard>

        <GlassCard title="Deployment Readiness">
          <p className="text-sm text-primary/70 mb-4">
            Version, diagnostics, and sync readiness from the backend.
          </p>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-primary/60 block">App Version</span>
              <span className="text-primary font-mono">{diagnostics?.app_version ?? "—"}</span>
            </div>
            <div>
              <span className="text-primary/60 block">Environment</span>
              <span className="text-primary">{diagnostics?.environment ?? "—"}</span>
            </div>
            <div>
              <span className="text-primary/60 block">Sync State</span>
              <span className="text-primary">{diagnostics?.sync_state ?? (syncEnabled ? "Enabled" : "Disabled")}</span>
            </div>
            <div>
              <span className="text-primary/60 block">Sync Readiness</span>
              <span className="text-primary">{diagnostics?.sync_readiness ?? "—"}</span>
            </div>
            <div>
              <span className="text-primary/60 block">Last Sync</span>
              <span className="text-primary font-mono text-xs">
                {diagnostics?.last_sync_timestamp
                  ? new Date(diagnostics.last_sync_timestamp).toLocaleString()
                  : "Never"}
              </span>
            </div>
            <div>
              <span className="text-primary/60 block">Safe Mode</span>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={safeMode}
                  onChange={(e) => setSafeMode(e.target.checked)}
                  className="rounded border-glass-border bg-deep text-accent-blue focus:ring-accent-blue"
                />
                <span className="text-primary">{safeMode ? "On" : "Off"}</span>
              </label>
            </div>
          </div>
          <p className="text-xs text-primary/50 mt-4">Safe Mode disables AI and background sync for troubleshooting. (UI only for now.)</p>
        </GlassCard>

        <GlassCard title="Appearance">
          <p className="text-sm text-primary/70 mb-4">Theme.</p>
          <div className="flex gap-4">
            {(["light", "dark"] as const).map((t) => (
              <label key={t} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="theme"
                  checked={theme === t}
                  onChange={() => setTheme(t)}
                  className="border-glass-border bg-deep text-accent-blue focus:ring-accent-blue"
                />
                <span className="text-primary capitalize">{t}</span>
              </label>
            ))}
          </div>
        </GlassCard>

        <GlassCard title="Learning Preferences">
          <p className="text-sm text-primary/70 mb-4">Default difficulty for AI explanations.</p>
          <select
            value={difficultyLevel}
            onChange={(e) => handleDifficultyChange(e.target.value)}
            disabled={saving}
            className="w-full max-w-xs px-4 py-2 rounded-lg border border-glass-border bg-surface-light text-primary focus:outline-none focus:ring-2 focus:ring-accent-blue"
          >
            <option value="Beginner">Beginner</option>
            <option value="Intermediate">Intermediate</option>
            <option value="Expert">Expert</option>
          </select>
        </GlassCard>

        <GlassCard title="Privacy & Data">
          <p className="text-sm text-primary/80">
            All learning data is stored locally. Cloud sync uploads only progress summaries (scores, streaks) — never chat transcripts or quiz answers.
          </p>
        </GlassCard>

        <GlassCard title="Storage">
          <p className="text-sm text-primary/70 mb-4">
            Local data files, textbooks, and study assets. Export for backup or clear to start fresh.
          </p>
          {storageFiles.length > 0 ? (
            <ul className="space-y-2 mb-4">
              {storageFiles.map((f) => (
                <li
                  key={f.name}
                  className="flex items-start justify-between gap-4 py-2 px-3 rounded-lg bg-surface-light/50 border border-glass-border"
                >
                  <div className="min-w-0 flex-1">
                    <span className="text-primary font-mono text-sm">{f.name}</span>
                    <p className="text-primary/60 text-xs mt-0.5 truncate">{f.description}</p>
                  </div>
                  <span className="text-primary/70 text-xs font-mono shrink-0">{f.size_human}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-primary/60 mb-4">No storage files found.</p>
          )}
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleExportData}
              disabled={storageLoading}
              className="px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary hover:bg-surface-light/80 font-medium disabled:opacity-50"
            >
              {storageLoading && storageAction === "export" ? "Exporting…" : "Export Data"}
            </button>
            <button
              type="button"
              onClick={handleClearData}
              disabled={storageLoading}
              className="px-4 py-2 rounded-xl border border-red-500/50 bg-red-500/10 text-red-400 hover:bg-red-500/20 font-medium disabled:opacity-50"
            >
              {storageLoading && storageAction === "clear" ? "Clearing…" : "Clear Local Data"}
            </button>
          </div>
        </GlassCard>

        <GlassCard title="Account">
          <div className="space-y-2 mb-4">
            <div>
              <span className="text-primary/60 text-sm block">Name</span>
              <span className="text-primary">{profileName}</span>
            </div>
            <div>
              <span className="text-primary/60 text-sm block">Mode</span>
              <span className="text-primary">{modeLabel}</span>
            </div>
          </div>
          <button
            type="button"
            onClick={handleSignOut}
            className="px-4 py-2 rounded-xl border border-glass-border bg-surface-light text-primary hover:bg-surface-light/80 font-medium"
          >
            Sign Out
          </button>
        </GlassCard>
      </div>
    </PageChrome>
  );
}
