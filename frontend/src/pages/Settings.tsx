/**
 * Settings page — Cloud Sync, Appearance, Learning Preferences, Deployment, Account.
 * Phase 7: All toggles persist via PUT /api/user/stats.
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { PageChrome, GlassCard } from "../components";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";
import { getUserStats, updateUserStats } from "../services/api";
import type { UserStats } from "../services/api";

export function SettingsPage() {
  const navigate = useNavigate();
  const { profile, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const [stats, setStats] = useState<UserStats | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getUserStats().then(setStats).catch(() => setStats(null));
  }, []);

  const preferences = stats?.preferences ?? {};
  const syncEnabled = preferences.sync_enabled ?? true;
  const difficultyLevel = preferences.difficulty_level ?? "Beginner";

  const handleSyncToggle = async (next: boolean) => {
    setSaving(true);
    try {
      await updateUserStats({ preferences: { ...preferences, sync_enabled: next } });
      setStats((s) => (s ? { ...s, preferences: { ...(s.preferences ?? {}), sync_enabled: next } } : null));
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
            Version, diagnostics, sync readiness, and errors. Placeholders until runtime values are wired.
          </p>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-primary/60 block">App Version</span>
              <span className="text-primary font-mono">1.0.0</span>
            </div>
            <div>
              <span className="text-primary/60 block">Environment</span>
              <span className="text-primary">Local</span>
            </div>
            <div>
              <span className="text-primary/60 block">Sync State</span>
              <span className="text-primary">{syncEnabled ? "Enabled" : "Disabled"}</span>
            </div>
            <div>
              <span className="text-primary/60 block">Safe Mode</span>
              <span className="text-primary">Off</span>
            </div>
          </div>
          <p className="text-xs text-primary/50 mt-4">Safe Mode disables AI and background sync for troubleshooting.</p>
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
          <p className="text-sm text-primary/70">
            Storage manager placeholder. In the full implementation this will list local textbooks, embeddings, and study assets.
          </p>
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
