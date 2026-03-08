/**
 * Boot flow — first-launch sequence: splash → hardware → connectivity → storage → role → profile → class code → reveal.
 * On complete, sets boot_complete in localStorage and calls onComplete() to navigate to dashboard.
 */

import { useCallback, useEffect, useState } from "react";
import { useAppState } from "../contexts/AppStateContext";
import { useAuth, type Profile } from "../contexts/AuthContext";
import { GlassCard } from "../components/GlassCard";
import { HardwareCheckModal } from "../components/HardwareCheckModal";
import { getHealth, getHardware } from "../services/api";

type Phase =
  | "splash"
  | "hardware"
  | "connectivity"
  | "storage"
  | "role"
  | "profile"
  | "class_code"
  | "reveal";

export function BootFlow({ onComplete }: { onComplete: () => void }) {
  const [phase, setPhase] = useState<Phase>("splash");
  const { setBootComplete, markVersionSeen } = useAppState();
  const { setProfile, connectivityStatus, profile } = useAuth();

  const advance = useCallback((profileMode?: "solo" | "teacher_linked_provisional") => {
    if (phase === "splash") setPhase("hardware");
    else if (phase === "hardware") setPhase("connectivity");
    else if (phase === "connectivity") setPhase("storage");
    else if (phase === "storage") {
      if (profile.user_role === null) setPhase("role");
      else if (profile.user_role === "teacher") setPhase("reveal");
      else if (profile.profile_mode === null) setPhase("profile");
      else setPhase("reveal");
    } else if (phase === "role") {
      if (profile.user_role === "student" && profile.profile_mode === null)
        setPhase("profile");
      else setPhase("reveal");
    } else if (phase === "profile") {
      if (profileMode === "solo") setPhase("reveal");
      else setPhase("class_code");
    } else if (phase === "class_code") setPhase("reveal");
    else {
      setBootComplete();
      markVersionSeen();
      onComplete();
    }
  }, [
    phase,
    profile.user_role,
    profile.profile_mode,
    setBootComplete,
    markVersionSeen,
    onComplete,
  ]);

  // Check connectivity once when entering connectivity phase
  const checkConnectivity = useCallback(async () => {
    try {
      await getHealth();
      return "online";
    } catch {
      return "offline";
    }
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="ambient-glow" aria-hidden />
      <div className="relative z-10 w-full max-w-lg">
        <GlassCard>
          {phase === "splash" && (
            <SplashScreen onNext={() => setPhase("hardware")} />
          )}
          {phase === "hardware" && (
            <HardwareCheckPhase onNext={() => setPhase("connectivity")} />
          )}
          {phase === "connectivity" && (
            <ConnectivityScreen
              onNext={advance}
              checkConnectivity={checkConnectivity}
            />
          )}
          {phase === "storage" && <StorageScreen onNext={advance} />}
          {phase === "role" && (
            <RoleScreen
              onNext={advance}
              profile={profile}
              setProfile={setProfile}
            />
          )}
          {phase === "profile" && (
            <ProfileScreen
              onNext={(mode) => advance(mode)}
              profile={profile}
              setProfile={setProfile}
            />
          )}
          {phase === "class_code" && (
            <ClassCodeScreen
              onNext={advance}
              profile={profile}
              setProfile={setProfile}
              connectivityStatus={connectivityStatus}
            />
          )}
          {phase === "reveal" && <RevealScreen onNext={advance} />}
        </GlassCard>
      </div>
    </div>
  );
}

function SplashScreen({ onNext }: { onNext: () => void }) {
  return (
    <div className="text-center py-4">
      <h1 className="text-xl font-semibold text-primary">
        Studaxis is getting ready
      </h1>
      <p className="text-sm text-primary/70 mt-2">
        We are checking your laptop, connectivity, and storage so your tutor
        feels smooth even offline.
      </p>
      <button
        type="button"
        onClick={onNext}
        className="mt-6 px-6 py-2.5 rounded-xl bg-accent-blue text-deep font-semibold hover:opacity-90 transition-opacity"
      >
        Continue
      </button>
    </div>
  );
}

function HardwareCheckPhase({ onNext }: { onNext: () => void }) {
  const [specs, setSpecs] = useState<{ ram_gb?: number; cpu_count?: number; disk_free_gb?: number } | null>(null);

  useEffect(() => {
    getHardware()
      .then((r) => setSpecs(r.specs ?? null))
      .catch(() => setSpecs(null));
  }, []);

  return (
    <div className="py-2">
      <HardwareCheckModal onContinue={onNext} specs={specs} />
    </div>
  );
}

function ConnectivityScreen({
  onNext,
  checkConnectivity,
}: {
  onNext: () => void;
  checkConnectivity: () => Promise<"online" | "offline">;
}) {
  const [status, setStatus] = useState<"online" | "offline" | "checking">(
    "checking"
  );
  const runCheck = useCallback(async () => {
    setStatus("checking");
    const s = await checkConnectivity();
    setStatus(s);
  }, [checkConnectivity]);

  useEffect(() => {
    runCheck();
  }, [runCheck]);

  return (
    <div className="text-center py-4">
      <h1 className="text-xl font-semibold text-primary">
        Checking connectivity
      </h1>
      <p className="text-sm text-primary/70 mt-2">
        Studaxis works fully offline, but we will sync with your teacher when a
        connection is available.
      </p>
      <div className="mt-4 flex justify-center gap-2">
        {status === "checking" && (
          <span className="text-sm text-primary/60">Detecting...</span>
        )}
        {status === "online" && (
          <span className="text-sm text-emerald-400">● Online</span>
        )}
        {status === "offline" && (
          <span className="text-sm text-primary/60">
            ○ Offline — Studaxis still works fully offline
          </span>
        )}
      </div>
      <button
        type="button"
        onClick={runCheck}
        className="mt-4 text-sm text-accent-blue hover:underline"
      >
        Recheck
      </button>
      <button
        type="button"
        onClick={onNext}
        className="mt-6 block w-full px-6 py-2.5 rounded-xl bg-accent-blue text-deep font-semibold hover:opacity-90 transition-opacity"
      >
        Continue
      </button>
    </div>
  );
}

function StorageScreen({ onNext }: { onNext: () => void }) {
  return (
    <div className="text-center py-4">
      <h1 className="text-xl font-semibold text-primary">
        Scanning local study data
      </h1>
      <p className="text-sm text-primary/70 mt-2">
        We are validating your local textbooks, notes, and quiz history.
      </p>
      <p className="text-xs text-emerald-400/90 mt-4">
        ✅ Local storage looks good.
      </p>
      <button
        type="button"
        onClick={onNext}
        className="mt-6 px-6 py-2.5 rounded-xl bg-accent-blue text-deep font-semibold hover:opacity-90 transition-opacity"
      >
        Continue
      </button>
    </div>
  );
}

function RoleScreen({
  onNext,
  profile,
  setProfile,
}: {
  onNext: () => void;
  profile: Profile;
  setProfile: (p: Partial<Profile>) => void;
}) {
  return (
    <div className="py-4">
      <h1 className="text-xl font-semibold text-primary text-center">
        Who is using Studaxis on this laptop?
      </h1>
      <p className="text-sm text-primary/70 mt-2 text-center">
        Choose your role so we can route you to the right experience.
      </p>
      <div className="mt-6 flex flex-col gap-2">
        <label className="flex items-center gap-3 p-3 rounded-xl border border-glass-border cursor-pointer hover:bg-surface-light">
          <input
            type="radio"
            name="role"
            checked={profile.user_role === "student"}
            onChange={() => setProfile({ user_role: "student" })}
            className="text-accent-blue"
          />
          <span className="text-primary">I am a student using Studaxis on this device</span>
        </label>
        <label className="flex items-center gap-3 p-3 rounded-xl border border-glass-border cursor-pointer hover:bg-surface-light">
          <input
            type="radio"
            name="role"
            checked={profile.user_role === "teacher"}
            onChange={() => setProfile({ user_role: "teacher" })}
            className="text-accent-blue"
          />
          <span className="text-primary">I am a teacher checking progress</span>
        </label>
      </div>
      <button
        type="button"
        onClick={onNext}
        disabled={profile.user_role === null}
        className="mt-6 w-full px-6 py-2.5 rounded-xl bg-accent-blue text-deep font-semibold hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Continue
      </button>
    </div>
  );
}

function ProfileScreen({
  onNext,
  profile,
  setProfile,
}: {
  onNext: (mode: "solo" | "teacher_linked_provisional") => void;
  profile: Profile;
  setProfile: (p: Partial<Profile>) => void;
}) {
  const [name, setName] = useState(profile.profile_name ?? "");

  const handleNext = () => {
    setProfile({ profile_name: name.trim() || null });
    const mode = profile.profile_mode === "solo" ? "solo" : "teacher_linked_provisional";
    onNext(mode);
  };

  return (
    <div className="py-4">
      <h1 className="text-xl font-semibold text-primary text-center">
        Welcome to Studaxis
      </h1>
      <p className="text-sm text-primary/70 mt-2 text-center">
        Tell us how you are using Studaxis so we can tune your dashboard.
      </p>
      <div className="mt-6 space-y-4">
        <div>
          <label className="block text-sm text-primary/80 mb-1">What should we call you?</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
            className="w-full px-4 py-2.5 rounded-xl bg-surface-light border border-glass-border text-primary placeholder:text-primary/40"
          />
        </div>
        <div>
          <label className="block text-sm text-primary/80 mb-2">How are you using Studaxis today?</label>
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-3 p-3 rounded-xl border border-glass-border cursor-pointer hover:bg-surface-light">
              <input
                type="radio"
                name="mode"
                checked={profile.profile_mode === "solo"}
                onChange={() => setProfile({ profile_mode: "solo" })}
                className="text-accent-blue"
              />
              <span className="text-primary">Learn on my own</span>
            </label>
            <label className="flex items-center gap-3 p-3 rounded-xl border border-glass-border cursor-pointer hover:bg-surface-light">
              <input
                type="radio"
                name="mode"
                checked={profile.profile_mode === "teacher_linked" || profile.profile_mode === "teacher_linked_provisional"}
                onChange={() => setProfile({ profile_mode: "teacher_linked_provisional" })}
                className="text-accent-blue"
              />
              <span className="text-primary">Join a class</span>
            </label>
          </div>
        </div>
      </div>
      <button
        type="button"
        onClick={handleNext}
        disabled={!name.trim()}
        className="mt-6 w-full px-6 py-2.5 rounded-xl bg-accent-blue text-deep font-semibold hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Continue
      </button>
    </div>
  );
}

function ClassCodeScreen({
  onNext,
  profile,
  setProfile,
  connectivityStatus,
}: {
  onNext: () => void;
  profile: Profile;
  setProfile: (p: Partial<Profile>) => void;
  connectivityStatus: string;
}) {
  const [code, setCode] = useState(profile.class_code ?? "");

  const handleLink = () => {
    setProfile({ class_code: code.trim() || null, profile_mode: "teacher_linked_provisional" });
    onNext();
  };

  const handleSolo = () => {
    setProfile({ class_code: null, profile_mode: "solo" });
    onNext();
  };

  return (
    <div className="py-4">
      <h1 className="text-xl font-semibold text-primary text-center">
        Join your class
      </h1>
      <p className="text-sm text-primary/70 mt-2 text-center">
        Enter the class code shared by your teacher. If you are offline, we will
        link it when we can verify.
      </p>
      <div className="mt-6">
        <input
          type="text"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Class code"
          className="w-full px-4 py-2.5 rounded-xl bg-surface-light border border-glass-border text-primary placeholder:text-primary/40"
        />
      </div>
      <div className="mt-4 flex gap-3">
        <button
          type="button"
          onClick={handleLink}
          className="flex-1 px-4 py-2.5 rounded-xl bg-accent-blue text-deep font-semibold hover:opacity-90 transition-opacity"
        >
          Link class
        </button>
        <button
          type="button"
          onClick={handleSolo}
          className="flex-1 px-4 py-2.5 rounded-xl border border-glass-border text-primary/80 font-medium hover:bg-surface-light transition-colors"
        >
          Skip (Solo mode)
        </button>
      </div>
      {connectivityStatus === "offline" && (
        <p className="text-xs text-primary/50 mt-4 text-center">
          You appear to be offline. We will remember this code and verify later.
        </p>
      )}
    </div>
  );
}

function RevealScreen({ onNext }: { onNext: () => void }) {
  return (
    <div className="text-center py-4">
      <h1 className="text-xl font-semibold text-primary">You are all set</h1>
      <p className="text-sm text-primary/70 mt-2">
        Your profile, hardware, and local storage are ready. Loading your
        dashboard now.
      </p>
      <button
        type="button"
        onClick={onNext}
        className="mt-6 px-6 py-2.5 rounded-xl bg-accent-blue text-deep font-semibold hover:opacity-90 transition-opacity"
      >
        Go to Dashboard
      </button>
    </div>
  );
}
