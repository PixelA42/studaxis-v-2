/**
 * Profile page — display and edit profile (name, mode, class code). Persisted via AuthContext.
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { PageChrome, GlassCard } from "../components";
import { useAuth } from "../contexts/AuthContext";

export function ProfilePage() {
  const navigate = useNavigate();
  const { profile, setProfile, logout } = useAuth();
  const [editName, setEditName] = useState(profile.profile_name || "");
  const [editClassCode, setEditClassCode] = useState(profile.class_code || "");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setEditName(profile.profile_name || "");
    setEditClassCode(profile.class_code || "");
  }, [profile.profile_name, profile.class_code]);

  const name = profile.profile_name || "Student";
  const modeLabel =
    profile.profile_mode === "solo" || !profile.profile_mode
      ? "Solo Learner"
      : profile.profile_mode === "teacher_linked_provisional"
        ? "Class Linked (Pending)"
        : "Class Linked";

  const handleSave = () => {
    const newName = editName.trim() || name;
    if (!newName) return;
    setProfile({
      profile_name: newName,
      class_code: editClassCode.trim() || null,
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleSignOut = () => {
    logout();
    navigate("/", { replace: true });
  };

  const initials = name
    .trim()
    .split(/\s+/)
    .map((s) => s[0])
    .join("")
    .toUpperCase()
    .slice(0, 2) || "S";

  return (
    <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold text-primary">Profile</h2>

        <div className="flex items-center gap-4 p-5 rounded-xl border border-glass-border bg-surface-light/50">
          <div
            className="w-16 h-16 rounded-xl bg-accent-blue/20 border border-accent-blue/40 flex items-center justify-center text-accent-blue font-semibold text-2xl"
            aria-hidden
          >
            {initials}
          </div>
          <div>
            <p className="text-primary font-medium text-lg">{name}</p>
            <p className="text-primary/70 text-sm">{modeLabel}</p>
          </div>
        </div>

        <GlassCard title="Profile Information">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <span className="text-primary/60 text-sm block mb-1">Display Name</span>
              <span className="text-primary font-medium">{name}</span>
            </div>
            <div>
              <span className="text-primary/60 text-sm block mb-1">Learning Mode</span>
              <span className="text-primary font-medium">{modeLabel}</span>
            </div>
            {profile.class_code && (
              <div className="sm:col-span-2">
                <span className="text-primary/60 text-sm block mb-1">Class Code</span>
                <span className="text-primary font-mono">{profile.class_code}</span>
              </div>
            )}
          </div>
        </GlassCard>

        <GlassCard title="Edit Profile">
          <div className="space-y-4">
            <div>
              <label htmlFor="profile-name" className="block text-sm font-medium text-primary/90 mb-2">
                Display name
              </label>
              <input
                id="profile-name"
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="Your name"
                className="w-full max-w-md px-4 py-2 rounded-lg border border-glass-border bg-surface-light text-primary placeholder:text-primary/50 focus:outline-none focus:ring-2 focus:ring-accent-blue"
              />
            </div>
            <div>
              <label htmlFor="profile-class-code" className="block text-sm font-medium text-primary/90 mb-2">
                Class code (optional)
              </label>
              <input
                id="profile-class-code"
                type="text"
                value={editClassCode}
                onChange={(e) => setEditClassCode(e.target.value)}
                placeholder="e.g. ABC123"
                className="w-full max-w-md px-4 py-2 rounded-lg border border-glass-border bg-surface-light text-primary placeholder:text-primary/50 focus:outline-none focus:ring-2 focus:ring-accent-blue font-mono"
              />
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleSave}
                className="px-5 py-2.5 rounded-xl font-medium text-deep bg-accent-blue hover:bg-accent-blue/90 focus:outline-none focus:ring-2 focus:ring-accent-blue"
              >
                Save Changes
              </button>
              {saved && <span className="text-green-400 text-sm self-center">Saved.</span>}
            </div>
          </div>
        </GlassCard>

        <GlassCard title="Account">
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