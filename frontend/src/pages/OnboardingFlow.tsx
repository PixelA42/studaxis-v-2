/**
 * Onboarding flow — first-launch experience styled like OnboardingFlow.jsx.
 * Steps: login → role → profile → setup (subject + grade) → done.
 * Uses Thermal Vitreous color scheme (--accent-pink, --accent-coral, --accent-blue).
 */

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { flushSync } from "react-dom";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../contexts/AppStateContext";
import { useAuth } from "../contexts/AuthContext";
import {
  checkEmail,
  postCompleteOnboarding,
  postRequestOtp,
  postSignup,
  postVerifyOtp,
  updateUserStats,
  verifyClassCode,
} from "../services/api";

const TEACHER_DASHBOARD_URL =
  import.meta.env.VITE_TEACHER_DASHBOARD_URL || "https://main.d1wt8qoele8s90.amplifyapp.com";

type Step = "login" | "otp" | "role" | "profile" | "setup" | "done";

/* ── Icons ── */
const EyeIcon = ({ open }: { open: boolean }) =>
  open ? (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path
        d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"
        stroke="currentColor"
        strokeWidth="2"
      />
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" />
    </svg>
  ) : (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path
        d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24M1 1l22 22"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );

const CheckIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
    <path
      d="M20 6L9 17l-5-5"
      stroke="white"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const PersonIcon = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
    <path
      d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"
      stroke="currentColor"
      strokeWidth="2"
    />
    <circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="2" />
  </svg>
);

const EmailIcon = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
    <path
      d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"
      stroke="currentColor"
      strokeWidth="2"
    />
    <polyline points="22,6 12,13 2,6" stroke="currentColor" strokeWidth="2" />
  </svg>
);

const LockIcon = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
    <rect x="3" y="11" width="18" height="11" rx="2" stroke="currentColor" strokeWidth="2" />
    <path d="M7 11V7a5 5 0 0110 0v4" stroke="currentColor" strokeWidth="2" />
  </svg>
);

const CodeIcon = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
    <path d="M9 9l-3 3 3 3M15 9l3 3-3 3M13 6l-2 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

const GoogleIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24">
    <path fill="#FBBB00" d="M5.27 12.28A7 7 0 0112 5a6.86 6.86 0 014.83 1.95L19.5 4.27A11 11 0 001.07 10.71z" />
    <path fill="#518EF8" d="M21.8 10.5H12v3.5h5.66a5.5 5.5 0 01-2.35 3.42l2.7 2.08A11 11 0 0023 12c0-.52-.07-1.03-.2-1.5z" />
    <path fill="#28B446" d="M7.11 14.6A7 7 0 0112 19a6.8 6.8 0 004.01-1.3l-2.7-2.08A3.5 3.5 0 017.11 14.6z" />
    <path fill="#F14336" d="M5.27 11.72L2.57 9.5A11 11 0 001 12a10.93 10.93 0 001.07 4.71l2.7-2.08A7 7 0 015.27 11.72z" />
  </svg>
);

const AppleIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
    <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z" />
  </svg>
);

const PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
const PASSWORD_RULES = [
  { id: "length", label: "At least 8 characters", test: (p: string) => p.length >= 8 },
  { id: "upper", label: "One uppercase letter", test: (p: string) => /[A-Z]/.test(p) },
  { id: "lower", label: "One lowercase letter", test: (p: string) => /[a-z]/.test(p) },
  { id: "number", label: "One digit", test: (p: string) => /\d/.test(p) },
  { id: "special", label: "One special (@$!%*?&)", test: (p: string) => /[@$!%*?&]/.test(p) },
] as const;

/* ── OTP 6-box input ── */
function OTPInput({
  value,
  onChange,
  accent,
}: {
  value: string;
  onChange: (v: string) => void;
  accent: string;
}) {
  const refs = [useRef<HTMLInputElement>(null), useRef<HTMLInputElement>(null), useRef<HTMLInputElement>(null), useRef<HTMLInputElement>(null), useRef<HTMLInputElement>(null), useRef<HTMLInputElement>(null)];

  const handleChange = (i: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value.replace(/\D/g, "").slice(-1);
    const arr = (value + "      ").slice(0, 6).split("");
    arr[i] = v;
    onChange(arr.join("").trimEnd());
    if (v && i < 5) refs[i + 1].current?.focus();
  };
  const handleKey = (i: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !value[i] && i > 0) refs[i - 1].current?.focus();
    if (e.key === "ArrowLeft" && i > 0) refs[i - 1].current?.focus();
    if (e.key === "ArrowRight" && i < 5) refs[i + 1].current?.focus();
  };
  const handlePaste = (e: React.ClipboardEvent) => {
    const p = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (p) {
      onChange(p);
      refs[Math.min(p.length, 5)].current?.focus();
    }
    e.preventDefault();
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", gap: "10px" }}>
      {Array.from({ length: 6 }).map((_, i) => {
        const filled = !!(value[i] && value[i].trim());
        return (
          <input
            key={i}
            ref={refs[i]}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={value[i] || ""}
            onChange={(e) => handleChange(i, e)}
            onKeyDown={(e) => handleKey(i, e)}
            onPaste={handlePaste}
            placeholder="•"
            style={{
              width: "48px",
              height: "56px",
              textAlign: "center",
              fontSize: "22px",
              fontWeight: 800,
              color: "var(--text-primary, #0d1b2a)",
              fontFamily: "inherit",
              background: filled ? `linear-gradient(135deg,rgba(250,92,92,0.07),rgba(253,138,107,0.07))` : "var(--surface-light, #f8f9fc)",
              border: `2px solid ${filled ? accent : "var(--glass-border, #e8edf5)"}`,
              borderRadius: "14px",
              outline: "none",
              boxShadow: filled ? "0 2px 12px rgba(250,92,92,0.15)" : "0 1px 4px rgba(0,0,0,0.04)",
              transition: "all .18s ease",
              transform: filled ? "scale(1.06)" : "scale(1)",
              caretColor: accent,
            }}
            onFocus={(e) => {
              e.target.style.borderColor = accent;
              e.target.style.boxShadow = `0 0 0 4px ${accent}20`;
              e.target.style.background = "var(--surface-light, #fff)";
            }}
            onBlur={(e) => {
              e.target.style.borderColor = filled ? accent : "var(--glass-border, #e8edf5)";
              e.target.style.boxShadow = filled ? "0 2px 12px rgba(250,92,92,0.15)" : "0 1px 4px rgba(0,0,0,0.04)";
              e.target.style.background = filled ? "linear-gradient(135deg,rgba(250,92,92,0.07),rgba(253,138,107,0.07))" : "var(--surface-light, #f8f9fc)";
            }}
          />
        );
      })}
    </div>
  );
}

/* ── Countdown ── */
function Countdown({ seconds, onDone }: { seconds: number; onDone: () => void }) {
  const [t, setT] = useState(seconds);
  useEffect(() => {
    if (t <= 0) {
      onDone();
      return;
    }
    const id = setTimeout(() => setT(t - 1), 1000);
    return () => clearTimeout(id);
  }, [t, onDone]);
  return (
    <span style={{ fontWeight: 700, color: "var(--accent-pink, #FA5C5C)" }}>
      {Math.floor(t / 60)}:{String(t % 60).padStart(2, "0")}
    </span>
  );
}

/* ── Shared styles (Thermal Vitreous) ── */
const ACCENT = "var(--accent-pink, #FA5C5C)";
const ACCENT_CORAL = "var(--accent-coral, #FD8A6B)";
const ACCENT_PEACH = "var(--accent-peach, #FEC288)";
const ACCENT_BLUE = "var(--accent-blue, #00A8E8)";

export type OnboardingStartFrom = "login" | "otp" | "role";

export function OnboardingFlow({
  onComplete,
  startFrom = "login",
}: {
  onComplete?: () => void;
  startFrom?: OnboardingStartFrom;
}) {
  const navigate = useNavigate();
  const initialStep: Step =
    startFrom === "login" ? "login" : startFrom === "otp" ? "otp" : "role";
  const [step, setStep] = useState<Step>(initialStep);
  const [tab, setTab] = useState<"signin" | "signup">("signin");
  const [signupSubStep, setSignupSubStep] = useState<"email" | "details">("email");
  const [showPass, setShowPass] = useState(false);
  const [passwordVal, setPasswordVal] = useState("");
  const [remember, setRemember] = useState(false);

  useEffect(() => {
    if (tab === "signup" && signupSubStep === "details") {
      setPasswordVal(formRef.current.password);
    }
  }, [tab, signupSubStep]);
  const [error, setError] = useState("");
  const [classVerifyError, setClassVerifyError] = useState("");
  const [verifyingClass, setVerifyingClass] = useState(false);
  const [subjectTick, setSubjectTick] = useState(0);
  const [gradeTick, setGradeTick] = useState(0);

  const formRef = useRef({
    name: "",
    email: "",
    password: "",
    username: "",
    classCode: "",
    subjects: [] as string[],
    grade: "" as string | null,
    mode: "solo" as "solo" | "teacher_linked" | "teacher_linked_provisional",
  });

  const { setBootComplete, markVersionSeen } = useAppState();
  const { setProfile, profile, login } = useAuth();

  const [otp, setOtp] = useState("");
  const [otpErr, setOtpErr] = useState("");
  const [otpOk, setOtpOk] = useState(false);
  const [canResend, setCanResend] = useState(false);
  const [resendKey, setResendKey] = useState(0);
  const [verifying, setVerifying] = useState(false);

  const progress: Record<Step, number> = {
    login: 16,
    otp: 32,
    role: 48,
    profile: 64,
    setup: 80,
    done: 100,
  };
  const pct = useMemo(() => progress[step] ?? 0, [step]);

  const handleComplete = useCallback(() => {
    setBootComplete();
    markVersionSeen();
    onComplete?.();
  }, [setBootComplete, markVersionSeen, onComplete]);

  const toggleSubject = useCallback((subject: string) => {
    const current = formRef.current.subjects;
    const already = current.includes(subject);
    formRef.current.subjects = already
      ? current.filter((s) => s !== subject)
      : [...current, subject];
    setSubjectTick((t) => t + 1);
  }, []);

  const handleStartLearning = useCallback(async () => {
    const f = formRef.current;
    const profileData = {
      profile_name: (f.name || profile.profile_name || "Learner").trim() || "Learner",
      role: (profile.user_role || "student") as "student" | "teacher",
      mode: (profile.profile_mode || "solo") as "solo" | "teacher_linked" | "teacher_linked_provisional",
      class_code: profile.class_code || null,
      class_id: profile.class_id || null,
      subjects: f.subjects.length > 0 ? f.subjects.join(",") : null,
      grade: f.grade || null,
    };
    await postCompleteOnboarding(profileData);
    setProfile({
      profile_name: profileData.profile_name,
      profile_mode: profileData.mode,
      class_code: profileData.class_code,
      class_id: profileData.class_id,
      user_role: profileData.role,
      onboarding_complete: true,
    });
    navigate("/dashboard");
  }, [profile, setProfile, navigate]);

  /* ── Card wrapper ── */
  const Card = ({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) => (
    <div
      style={{
        width: wide ? 520 : 420,
        maxWidth: "calc(100vw - 32px)",
        background: "var(--surface-light, #fff)",
        borderRadius: "24px",
        boxShadow: "0 8px 48px rgba(0,0,0,0.10), 0 2px 12px rgba(0,0,0,0.06)",
        padding: "36px 32px",
        animation: "popIn .35s cubic-bezier(0.16,1,0.3,1)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "4px",
          background: `linear-gradient(90deg,${ACCENT},${ACCENT_CORAL},${ACCENT_PEACH},#FBEF76,${ACCENT_BLUE})`,
        }}
      />
      {children}
    </div>
  );

  const ProgressBar = () => (
    <div style={{ marginBottom: "28px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
        <span
          style={{
            fontSize: "11px",
            fontWeight: 700,
            color: "var(--text-muted, #9ca3af)",
            letterSpacing: "0.5px",
            textTransform: "uppercase",
          }}
        >
          {step === "login"
            ? "Sign In"
            : step === "otp"
              ? "Verify Email"
              : step === "role"
                ? "Choose Role"
                : step === "profile"
                  ? "Your Profile"
                  : step === "setup"
                    ? "Preferences"
                    : "All Set!"}
        </span>
        <span style={{ fontSize: "11px", fontWeight: 700, color: ACCENT }}>{pct}%</span>
      </div>
      <div
        style={{
          height: "5px",
          background: "var(--glass-border, #f1f3f8)",
          borderRadius: "10px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            borderRadius: "10px",
            background: `linear-gradient(90deg,${ACCENT},${ACCENT_CORAL},${ACCENT_PEACH})`,
            transition: "width .6s cubic-bezier(0.16,1,0.3,1)",
          }}
        />
      </div>
    </div>
  );

  const Input = ({
    icon,
    placeholder,
    type = "text",
    defaultValue,
    value,
    onChange,
    right,
  }: {
    icon: React.ReactNode;
    placeholder: string;
    type?: string;
    defaultValue?: string;
    value?: string;
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    right?: React.ReactNode;
  }) => (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "10px",
        border: "1.5px solid var(--glass-border, #e8edf5)",
        borderRadius: "12px",
        height: "50px",
        padding: "0 14px",
        background: "var(--surface-light, #fafbfc)",
        transition: "border .2s",
      }}
      onFocus={(e) => (e.currentTarget.style.borderColor = ACCENT)}
      onBlur={(e) => (e.currentTarget.style.borderColor = "var(--glass-border, #e8edf5)")}
    >
      <span style={{ color: "var(--text-muted, #9ca3af)", flexShrink: 0 }}>{icon}</span>
      <input
        type={type}
        placeholder={placeholder}
        {...(value !== undefined ? { value } : { defaultValue: defaultValue ?? "" })}
        onChange={onChange}
        style={{
          flex: 1,
          border: "none",
          background: "transparent",
          fontSize: "13.5px",
          color: "var(--text-primary, #0d1b2a)",
          fontFamily: "inherit",
          outline: "none",
        }}
      />
      {right}
    </div>
  );

  const PrimaryBtn = ({
    children,
    onClick,
    disabled,
    loading = false,
    style: s = {},
  }: {
    children: React.ReactNode;
    onClick: () => void;
    disabled?: boolean;
    loading?: boolean;
    style?: React.CSSProperties;
  }) => (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || loading}
      style={{
        width: "100%",
        height: "50px",
        borderRadius: "12px",
        border: "none",
        background: disabled || loading ? "var(--glass-border, #e5e7eb)" : `linear-gradient(135deg,${ACCENT},${ACCENT_CORAL})`,
        color: disabled || loading ? "var(--text-muted, #9ca3af)" : "#fff",
        fontSize: "15px",
        fontWeight: 700,
        cursor: disabled ? "not-allowed" : "pointer",
        fontFamily: "inherit",
        letterSpacing: "-0.2px",
        boxShadow: disabled ? "none" : "0 4px 16px rgba(250,92,92,0.35)",
        transition: "all .18s ease",
        ...s,
      }}
      onMouseEnter={(e) => {
        if (!disabled) {
          e.currentTarget.style.transform = "translateY(-1px)";
          e.currentTarget.style.boxShadow = "0 6px 22px rgba(250,92,92,0.42)";
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = "";
        e.currentTarget.style.boxShadow = disabled ? "none" : "0 4px 16px rgba(250,92,92,0.35)";
      }}
    >
      {loading ? (
        <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
          <span style={{ width: 18, height: 18, border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "#fff", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
          Verifying…
        </span>
      ) : (
        children
      )}
    </button>
  );

  const Label = ({ children }: { children: React.ReactNode }) => (
    <div
      style={{
        fontSize: "13px",
        fontWeight: 700,
        color: "var(--text-primary, #0d1b2a)",
        marginBottom: "7px",
        letterSpacing: "-0.1px",
      }}
    >
      {children}
    </div>
  );

  const Divider = () => (
    <div style={{ display: "flex", alignItems: "center", gap: "12px", margin: "2px 0" }}>
      <div style={{ flex: 1, height: "1px", background: "var(--glass-border, #f1f3f8)" }} />
      <span style={{ fontSize: "12px", color: "var(--text-muted, #9ca3af)", fontWeight: 500 }}>
        Or With
      </span>
      <div style={{ flex: 1, height: "1px", background: "var(--glass-border, #f1f3f8)" }} />
    </div>
  );

  const SocialBtn = ({ icon, label }: { icon: React.ReactNode; label: string }) => (
    <button
      type="button"
      style={{
        flex: 1,
        height: "46px",
        border: "1.5px solid var(--glass-border, #e8edf5)",
        borderRadius: "12px",
        background: "var(--surface-light, #fafbfc)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "8px",
        fontSize: "13px",
        fontWeight: 600,
        color: "var(--text-primary, #374151)",
        cursor: "pointer",
        fontFamily: "inherit",
        transition: "all .18s",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = ACCENT;
        e.currentTarget.style.background = "rgba(250,92,92,0.04)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "var(--glass-border, #e8edf5)";
        e.currentTarget.style.background = "var(--surface-light, #fafbfc)";
      }}
    >
      {icon}
      {label}
    </button>
  );

  const BackBtn = ({ onClick }: { onClick: () => void }) => (
    <button
      type="button"
      onClick={onClick}
      style={{
        width: "100%",
        marginTop: "10px",
        height: "38px",
        border: "none",
        background: "none",
        fontSize: "13px",
        fontWeight: 600,
        color: "var(--text-muted, #9ca3af)",
        cursor: "pointer",
        fontFamily: "inherit",
        transition: "color .15s",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.color = ACCENT)}
      onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-muted, #9ca3af)")}
    >
      ← Back
    </button>
  );

  const Logo = ({ small = false }: { small?: boolean }) => (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "10px",
        marginBottom: small ? "16px" : "24px",
      }}
    >
      <div
        style={{
          width: small ? 32 : 40,
          height: small ? 32 : 40,
          borderRadius: small ? "10px" : "13px",
          background: `linear-gradient(135deg,${ACCENT},${ACCENT_CORAL},${ACCENT_PEACH})`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 3px 12px rgba(250,92,92,0.35)",
          flexShrink: 0,
        }}
      >
        <svg width={small ? 16 : 20} height={small ? 16 : 20} viewBox="0 0 24 24" fill="none">
          <path
            d="M12 2L15 8.5L22 9.5L17 14.5L18.5 21.5L12 18L5.5 21.5L7 14.5L2 9.5L9 8.5L12 2Z"
            fill="white"
          />
        </svg>
      </div>
      {!small && (
        <div>
          <div
            style={{
              fontSize: "18px",
              fontWeight: 900,
              color: "var(--text-primary, #0d1b2a)",
              letterSpacing: "-0.5px",
              lineHeight: 1.1,
            }}
          >
            Studaxis
          </div>
          <div style={{ fontSize: "10.5px", color: "var(--text-muted, #9ca3af)", fontWeight: 500 }}>
            AI-powered · Offline-first
          </div>
        </div>
      )}
      {small && (
        <span
          style={{
            fontSize: "15px",
            fontWeight: 900,
            color: "var(--text-primary, #0d1b2a)",
            letterSpacing: "-0.4px",
          }}
        >
          Studaxis
        </span>
      )}
    </div>
  );

  const headStyle: React.CSSProperties = {
    fontSize: "20px",
    fontWeight: 900,
    color: "var(--text-primary, #0d1b2a)",
    letterSpacing: "-0.5px",
    marginBottom: "6px",
  };
  const subStyle: React.CSSProperties = {
    fontSize: "13px",
    color: "var(--text-muted, #6b7280)",
    lineHeight: 1.55,
    fontWeight: 400,
  };

  const [requestingOtp, setRequestingOtp] = useState(false);

  const handleEmailCheckContinue = async () => {
    const emailVal = formRef.current.email.trim();
    if (!emailVal) {
      setError("Please enter your email.");
      return;
    }
    setError("");
    setRequestingOtp(true);
    try {
      const { exists } = await checkEmail(emailVal);
      if (exists) {
        setTab("signin");
        formRef.current.email = emailVal;
        setError("Account found. Please sign in.");
      } else {
        setSignupSubStep("details");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to check email.");
    } finally {
      setRequestingOtp(false);
    }
  };

  const handleLoginContinue = async () => {
    setError("");
    if (tab === "signup" && signupSubStep === "email") {
      await handleEmailCheckContinue();
      return;
    }
    const { email: e, password: p, name: n, username: u } = formRef.current;
    if (tab === "signin") {
      if (!e.trim() || !p) {
        setError("Please enter email and password.");
        return;
      }
      setRequestingOtp(true);
      try {
        await postRequestOtp({ email: e.trim() });
        setStep("otp");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to send OTP.");
      } finally {
        setRequestingOtp(false);
      }
    } else {
      if (!n.trim() || !e.trim() || !p || !u.trim()) {
        setError("Please fill all fields.");
        return;
      }
      if (!PASSWORD_REGEX.test(p)) {
        setError("Password must have 8+ chars, 1 upper, 1 lower, 1 number, 1 special (@$!%*?&), only letters/numbers/@$!%*?&.");
        return;
      }
      setRequestingOtp(true);
      try {
        await postSignup({
          email: e.trim().toLowerCase(),
          username: u.trim(),
          password: p,
        });
        setStep("otp");
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Signup failed.";
        if (msg === "Email Already Exists, Please Sign In") {
          setTab("signin");
          formRef.current.email = e.trim().toLowerCase();
          setError("Account already exists. Please sign in.");
        } else {
          setError(msg);
        }
      } finally {
        setRequestingOtp(false);
      }
    }
  };

  // ─────────────────────────────────────────────────────────────────────────
  // FIX: flushSync forces login() + setProfile() state updates to commit to
  // the React tree *synchronously* before navigate() runs. Without this,
  // React 18 batches the setUser() call from login() with the navigate()
  // transition, so ProtectedRoute on /onboarding sees isAuthenticated=false
  // on its first render and bounces the user away.
  // ─────────────────────────────────────────────────────────────────────────
  const handleOtpVerify = async () => {
    if (otp.replace(/\s/g, "").length < 6) {
      setOtpErr("Please enter all 6 digits.");
      return;
    }
    setVerifying(true);
    setOtpErr("");
    try {
      const res = await postVerifyOtp({
        email: formRef.current.email.trim(),
        otp: otp.replace(/\s/g, ""),
      });

      // Flush auth state synchronously so isAuthenticated is true
      // by the time navigate("/onboarding") renders ProtectedRoute.
      flushSync(() => {
        login(res.access_token, { email: formRef.current.email.trim().toLowerCase() });
        setProfile({ onboarding_complete: res.onboarding_complete ?? false });
        if (tab === "signup") {
          const { name: n, username: u } = formRef.current;
          setProfile({ profile_name: n.trim() || u || undefined });
        }
      });

      setOtpOk(true);
      navigate("/onboarding", { replace: true });
    } catch (err) {
      setOtpErr(err instanceof Error ? err.message : "Verification failed.");
    } finally {
      setVerifying(false);
    }
  };

  const handleSkipLogin = () => {
    setStep("role");
  };

  const handleResendOtp = async () => {
    if (!formRef.current.email.trim()) return;
    setCanResend(false);
    setResendKey((k) => k + 1);
    setOtp("");
    setOtpErr("");
    try {
      await postRequestOtp({ email: formRef.current.email.trim() });
    } catch (err) {
      setOtpErr(err instanceof Error ? err.message : "Failed to resend OTP.");
      setCanResend(true);
    }
  };

  /* ── STEP: LOGIN ── */
  if (step === "login") {
    return (
      <Shell>
        <Card>
          <Logo />
          <div
            style={{
              display: "flex",
              background: "var(--surface-light, #f8f9fc)",
              borderRadius: "12px",
              padding: "4px",
              marginBottom: "24px",
            }}
          >
            {(["signin", "signup"] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => {
                      setTab(t);
                      if (t === "signup") setSignupSubStep("email");
                    }}
                style={{
                  flex: 1,
                  height: "38px",
                  borderRadius: "9px",
                  border: "none",
                  cursor: "pointer",
                  fontFamily: "inherit",
                  fontSize: "13px",
                  fontWeight: 700,
                  transition: "all .2s",
                  background: tab === t ? "var(--surface-light, #fff)" : "transparent",
                  color: tab === t ? "var(--text-primary, #0d1b2a)" : "var(--text-muted, #9ca3af)",
                  boxShadow: tab === t ? "0 2px 8px rgba(0,0,0,0.08)" : "none",
                }}
              >
                {t === "signin" ? "Sign In" : "Sign Up"}
              </button>
            ))}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {tab === "signup" && signupSubStep === "details" && (
              <div>
                <Label>Full Name</Label>
                <Input
                  icon={<PersonIcon />}
                  placeholder="Enter your name"
                  defaultValue={formRef.current.name}
                  onChange={(e) => { formRef.current.name = e.target.value; }}
                />
              </div>
            )}
            {tab === "signup" && signupSubStep === "details" && (
              <div>
                <Label>Username</Label>
                <Input
                  icon={<PersonIcon />}
                  placeholder="Choose a username"
                  defaultValue={formRef.current.username}
                  onChange={(e) => { formRef.current.username = e.target.value.replace(/[^a-zA-Z0-9_]/g, ""); }}
                />
              </div>
            )}
            <div>
              <Label>Email</Label>
              <Input
                icon={<EmailIcon />}
                placeholder="Enter your email"
                type="email"
                defaultValue={formRef.current.email}
                onChange={(e) => { formRef.current.email = e.target.value; }}
              />
            </div>
            {(tab === "signin" || (tab === "signup" && signupSubStep === "details")) && (
            <div>
              <Label>Password</Label>
              <Input
                icon={<LockIcon />}
                type={showPass ? "text" : "password"}
                placeholder={tab === "signup" ? "8+ chars, 1 upper, 1 lower, 1 number, 1 special (@$!%*?&)" : "Enter your password"}
                value={passwordVal}
                onChange={(e) => {
                  const v = e.target.value;
                  formRef.current.password = v;
                  setPasswordVal(v);
                }}
                right={
                  <button
                    type="button"
                    onClick={() => setShowPass(!showPass)}
                    style={{
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      color: "var(--text-muted, #9ca3af)",
                      padding: 0,
                      display: "flex",
                    }}
                    aria-label={showPass ? "Hide password" : "Show password"}
                  >
                    <EyeIcon open={showPass} />
                  </button>
                }
              />
              {tab === "signup" && signupSubStep === "details" && (
                <div style={{ marginTop: "8px", display: "flex", flexDirection: "column", gap: "4px" }}>
                  {PASSWORD_RULES.filter((r) => !r.label.includes("Only letters, numbers")).map((r) => (
                    <div key={r.id} style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px" }}>
                      <span style={{
                        width: 14, height: 14, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
                        background: r.test(passwordVal) ? "var(--accent-pink, #fa5c5c)" : "var(--glass-border, #e5e7eb)",
                        color: r.test(passwordVal) ? "#fff" : "transparent",
                        fontSize: 10, fontWeight: 700,
                      }}>
                        {r.test(passwordVal) ? "✓" : ""}
                      </span>
                      <span style={{ color: r.test(passwordVal) ? "var(--text-primary)" : "var(--text-muted, #6b7280)" }}>{r.label}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            )}

            {tab === "signin" && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <label
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "7px",
                    cursor: "pointer",
                    fontSize: "13px",
                    color: "var(--text-primary, #374151)",
                    fontWeight: 500,
                  }}
                >
                  <div
                    onClick={() => setRemember(!remember)}
                    onKeyDown={(e) => e.key === "Enter" && setRemember(!remember)}
                    role="button"
                    tabIndex={0}
                    style={{
                      width: "17px",
                      height: "17px",
                      borderRadius: "5px",
                      border: "1.5px solid var(--glass-border, #e5e7eb)",
                      background: remember ? `linear-gradient(135deg,${ACCENT},${ACCENT_CORAL})` : "var(--surface-light, #fff)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      cursor: "pointer",
                    }}
                  >
                    {remember && <CheckIcon />}
                  </div>
                  Remember me
                </label>
              </div>
            )}

            {error && (
              <p style={{ fontSize: "13px", color: "var(--error, #ef4444)" }} role="alert">
                {error}
              </p>
            )}

            <div style={{ marginTop: "6px" }}>
              <PrimaryBtn onClick={handleLoginContinue} loading={requestingOtp}>
                {tab === "signin" ? "Continue →" : "Create Account →"}
              </PrimaryBtn>
            </div>

            <button
              type="button"
              onClick={handleSkipLogin}
              style={{
                background: "none",
                border: "none",
                fontSize: "13px",
                color: "var(--text-muted, #6b7280)",
                cursor: "pointer",
                textDecoration: "underline",
              }}
            >
              Skip for now (use offline)
            </button>

            <p style={{ textAlign: "center", fontSize: "13px", color: "var(--text-muted, #6b7280)", margin: "4px 0" }}>
              {tab === "signin" ? "Don't have an account?" : "Already have an account?"}{" "}
              <span
                onClick={() => setTab(tab === "signin" ? "signup" : "signin")}
                style={{ color: ACCENT, fontWeight: 700, cursor: "pointer" }}
              >
                {tab === "signin" ? "Sign Up" : "Sign In"}
              </span>
            </p>

            <Divider />

            <div style={{ display: "flex", gap: "10px" }}>
              <SocialBtn icon={<GoogleIcon />} label="Google" />
              <SocialBtn icon={<AppleIcon />} label="Apple" />
            </div>
          </div>
        </Card>
      </Shell>
    );
  }

  /* ── STEP: OTP ── */
  if (step === "otp") {
    return (
      <Shell>
        <Card>
          <ProgressBar />
          <div style={{ textAlign: "center", marginBottom: "20px" }}>
            <div style={{ position: "relative", width: "64px", height: "64px", margin: "0 auto 16px" }}>
              <div
                style={{
                  position: "absolute",
                  inset: "-6px",
                  borderRadius: "50%",
                  background: "rgba(250,92,92,0.1)",
                  animation: otpOk ? "none" : "ringPulse 2s ease infinite",
                }}
              />
              <div
                style={{
                  width: "64px",
                  height: "64px",
                  borderRadius: "18px",
                  background: otpOk ? "linear-gradient(135deg,#10b981,#34d399)" : `linear-gradient(135deg,${ACCENT},${ACCENT_CORAL})`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: otpOk ? "0 6px 24px rgba(16,185,129,0.4)" : "0 6px 24px rgba(250,92,92,0.4)",
                  transition: "all .4s ease",
                  transform: otpOk ? "scale(1.1) rotate(5deg)" : "scale(1)",
                }}
              >
                {otpOk ? (
                  <CheckIcon />
                ) : (
                  <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
                    <rect x="3" y="11" width="18" height="11" rx="2" stroke="white" strokeWidth="2" />
                    <path d="M7 11V7a5 5 0 0110 0v4" stroke="white" strokeWidth="2" />
                    <circle cx="12" cy="16" r="1" fill="white" />
                  </svg>
                )}
              </div>
            </div>
            <h2 style={{ ...headStyle, textAlign: "center" }}>{otpOk ? "Verified! ✓" : "Check your email"}</h2>
            <p style={{ ...subStyle, textAlign: "center", marginTop: "4px" }}>
              {otpOk ? "Redirecting you now…" : "We sent a 6-digit code to"}
            </p>
            {!otpOk && <p style={{ fontSize: "13.5px", fontWeight: 700, color: "var(--text-primary, #0d1b2a)", marginTop: "4px" }}>{formRef.current.email || "your email"}</p>}
          </div>

          {!otpOk && (
            <>
              <div style={{ marginBottom: "20px" }}>
                <OTPInput value={otp} onChange={setOtp} accent={ACCENT} />
              </div>

              {otpErr && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "7px",
                    background: "rgba(250,92,92,0.07)",
                    border: "1px solid rgba(250,92,92,0.2)",
                    borderRadius: "10px",
                    padding: "10px 14px",
                    marginBottom: "14px",
                  }}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="#FA5C5C" strokeWidth="2" />
                    <path d="M12 8v4M12 16h.01" stroke="#FA5C5C" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                  <span style={{ fontSize: "12.5px", color: "#FA5C5C", fontWeight: 600 }}>{otpErr}</span>
                </div>
              )}

              <PrimaryBtn onClick={handleOtpVerify} disabled={otp.replace(/\s/g, "").length < 6} loading={verifying}>
                {verifying ? "Verifying…" : "Verify Code →"}
              </PrimaryBtn>

              <div style={{ textAlign: "center", marginTop: "18px" }}>
                {!canResend ? (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px", fontSize: "13px", color: "var(--text-muted, #9ca3af)" }}>
                    Resend in{" "}
                    <Countdown key={resendKey} seconds={30} onDone={() => setCanResend(true)} />
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => void handleResendOtp()}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "7px",
                      padding: "9px 20px",
                      borderRadius: "10px",
                      border: "1.5px solid var(--glass-border, #e8edf5)",
                      background: "var(--surface-light, #fafbfc)",
                      fontSize: "13px",
                      fontWeight: 700,
                      color: "var(--text-primary, #374151)",
                      cursor: "pointer",
                      fontFamily: "inherit",
                      transition: "all .18s",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = ACCENT;
                      e.currentTarget.style.color = ACCENT;
                      e.currentTarget.style.background = "rgba(250,92,92,0.04)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = "var(--glass-border, #e8edf5)";
                      e.currentTarget.style.color = "var(--text-primary, #374151)";
                      e.currentTarget.style.background = "var(--surface-light, #fafbfc)";
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                      <path d="M4 4v5h5M20 20v-5h-5M4.07 15a9 9 0 1 0 .29-4.88" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    Resend Code
                  </button>
                )}
              </div>

              <div
                style={{
                  marginTop: "14px",
                  padding: "10px 14px",
                  borderRadius: "10px",
                  background: "rgba(0,168,232,0.06)",
                  border: "1px solid rgba(0,168,232,0.15)",
                  display: "flex",
                  alignItems: "center",
                  gap: "7px",
                }}
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="#00a8e8" strokeWidth="2" />
                  <path d="M12 16v-4M12 8h.01" stroke="#00a8e8" strokeWidth="2" strokeLinecap="round" />
                </svg>
                <span style={{ fontSize: "11.5px", color: "#0077a8", fontWeight: 500 }}>
                  Demo: enter any 6 digits (e.g. <b>123456</b>) to continue
                </span>
              </div>

              <BackBtn onClick={() => setStep("login")} />
            </>
          )}
        </Card>
      </Shell>
    );
  }

  /* ── STEP: ROLE ── */
  if (step === "role") {
    return (
      <Shell>
        <Card wide>
          <ProgressBar />
          <Logo small />
          <h2 style={headStyle}>Who are you?</h2>
          <p style={subStyle}>Select your role to personalise your experience.</p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px", margin: "24px 0" }}>
            {[
              {
                id: "student" as const,
                emoji: "🎓",
                title: "Student",
                desc: "Learn offline with AI tutoring, quizzes & flashcards.",
                color: ACCENT,
              },
              {
                id: "teacher" as const,
                emoji: "👩‍🏫",
                title: "Teacher",
                desc: "Manage classes & generate curriculum via the web dashboard.",
                color: ACCENT_BLUE,
              },
            ].map((r) => (
              <div
                key={r.id}
                onClick={() => setProfile({ user_role: r.id })}
                onKeyDown={(e) => e.key === "Enter" && setProfile({ user_role: r.id })}
                role="button"
                tabIndex={0}
                style={{
                  padding: "22px 18px",
                  borderRadius: "16px",
                  cursor: "pointer",
                  border: `2px solid ${profile.user_role === r.id ? r.color : "var(--glass-border, #e8edf5)"}`,
                  background: profile.user_role === r.id ? `${r.color}08` : "var(--surface-light, #fafbfc)",
                  transition: "all .2s",
                  position: "relative",
                }}
              >
                {profile.user_role === r.id && (
                  <div
                    style={{
                      position: "absolute",
                      top: "12px",
                      right: "12px",
                      width: "20px",
                      height: "20px",
                      borderRadius: "50%",
                      background: `linear-gradient(135deg,${r.color},${r.color}bb)`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <CheckIcon />
                  </div>
                )}
                <div style={{ fontSize: "32px", marginBottom: "10px", display: "flex", justifyContent: "center" }}>
                  {r.id === "student" ? (
                    <img src="/studaxis-logo.png" alt="" className="circular-logo" style={{ width: 40, height: 40, borderRadius: "50%", objectFit: "cover" }} aria-hidden />
                  ) : (
                    r.emoji
                  )}
                </div>
                <div style={{ fontSize: "15px", fontWeight: 800, color: "var(--text-primary, #0d1b2a)", marginBottom: "5px" }}>
                  {r.title}
                </div>
                <div style={{ fontSize: "12.5px", color: "var(--text-muted, #6b7280)", lineHeight: 1.5 }}>{r.desc}</div>
              </div>
            ))}
          </div>
          <PrimaryBtn
            disabled={!profile.user_role}
            onClick={() => {
              if (profile.user_role === "teacher") setStep("done");
              else setStep("profile");
            }}
          >
            Continue →
          </PrimaryBtn>
          {startFrom !== "role" && <BackBtn onClick={() => setStep("login")} />}
        </Card>
      </Shell>
    );
  }

  /* ── STEP: PROFILE ── */
  const mode = profile.profile_mode === "solo" ? "solo" : profile.profile_mode === "teacher_linked" || profile.profile_mode === "teacher_linked_provisional" ? "linked" : null;
  if (step === "profile") {
    return (
      <Shell>
        <Card wide>
          <ProgressBar />
          <Logo small />
          <h2 style={headStyle}>Set up your profile</h2>
          <p style={subStyle}>Personalise your learning environment.</p>

          <div style={{ display: "flex", flexDirection: "column", gap: "14px", margin: "20px 0" }}>
            <div>
              <Label>Your Name / Nickname</Label>
              <Input
                icon={<PersonIcon />}
                placeholder="What should we call you?"
                defaultValue={formRef.current.name || profile.profile_name || ""}
                onChange={(e) => { formRef.current.name = e.target.value; }}
              />
            </div>
            <div>
              <Label>Learning Mode</Label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                {[
                  { id: "solo" as const, icon: "🧑‍💻", title: "Solo Learner", desc: "Independent self-study" },
                  { id: "linked" as const, icon: "🏫", title: "Join a Class", desc: "Teacher-linked student" },
                ].map((m) => (
                  <div
                    key={m.id}
                    onClick={() => setProfile({ profile_mode: m.id === "solo" ? "solo" : "teacher_linked_provisional" })}
                    onKeyDown={(e) =>
                      e.key === "Enter" &&
                      setProfile({ profile_mode: m.id === "solo" ? "solo" : "teacher_linked_provisional" })
                    }
                    role="button"
                    tabIndex={0}
                    style={{
                      padding: "14px 16px",
                      borderRadius: "13px",
                      cursor: "pointer",
                      border: `2px solid ${mode === m.id ? ACCENT_CORAL : "var(--glass-border, #e8edf5)"}`,
                      background: mode === m.id ? "rgba(253,138,107,0.06)" : "var(--surface-light, #fafbfc)",
                      transition: "all .18s",
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                    }}
                  >
                    <span style={{ fontSize: "22px" }}>{m.icon}</span>
                    <div>
                      <div style={{ fontSize: "13px", fontWeight: 800, color: "var(--text-primary, #0d1b2a)" }}>
                        {m.title}
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--text-muted, #9ca3af)" }}>{m.desc}</div>
                    </div>
                    {mode === m.id && (
                      <div
                        style={{
                          marginLeft: "auto",
                          width: "18px",
                          height: "18px",
                          borderRadius: "50%",
                          background: `linear-gradient(135deg,${ACCENT_CORAL},${ACCENT_PEACH})`,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          flexShrink: 0,
                        }}
                      >
                        <CheckIcon />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {mode === "linked" && (
              <div style={{ animation: "popIn .3s ease" }}>
                <Label>Class Code</Label>
                <Input
                  icon={<CodeIcon />}
                  placeholder="Enter 6-character code from your teacher (e.g. ABC123)"
                  defaultValue={formRef.current.classCode || profile.class_code || ""}
                  onChange={(e) => {
                    formRef.current.classCode = e.target.value.toUpperCase();
                    setClassVerifyError("");
                  }}
                />
                {classVerifyError && (
                  <p style={{ fontSize: "12px", color: "var(--error, #ef4444)", marginTop: "6px" }} role="alert">
                    {classVerifyError}
                  </p>
                )}
              </div>
            )}
          </div>

          <PrimaryBtn
            disabled={
              !(formRef.current.name || profile.profile_name)?.trim() ||
              !mode ||
              (mode === "linked" && (formRef.current.classCode || profile.class_code || "").length < 4) ||
              verifyingClass
            }
            loading={verifyingClass}
            onClick={async () => {
              const n = (formRef.current.name || profile.profile_name || "").trim();
              const cc = mode === "linked" ? (formRef.current.classCode || profile.class_code || "").trim().toUpperCase() : null;
              setClassVerifyError("");
              if (mode === "linked" && cc) {
                setVerifyingClass(true);
                try {
                  const verified = await verifyClassCode(cc);
                  if (verified) {
                    setProfile({
                      profile_name: n || null,
                      profile_mode: "teacher_linked_provisional",
                      class_code: verified.class_code,
                      class_id: verified.class_id,
                    });
                    setStep("setup");
                  } else {
                    setClassVerifyError("Class code not found. Check the code and try again.");
                  }
                } catch {
                  setClassVerifyError("Could not verify class code. Check your connection or try again.");
                } finally {
                  setVerifyingClass(false);
                }
              } else {
                setProfile({
                  profile_name: n || null,
                  profile_mode: mode === "solo" ? "solo" : "teacher_linked_provisional",
                  class_code: cc || null,
                  class_id: null,
                });
                setStep("setup");
              }
            }}
          >
            Continue →
          </PrimaryBtn>
          <BackBtn onClick={() => setStep("role")} />
        </Card>
      </Shell>
    );
  }

  /* ── STEP: SETUP (subject + grade) ── */
  if (step === "setup") {
    return (
      <Shell>
        <Card wide>
          <ProgressBar />
          <Logo small />
          <h2 style={headStyle}>Your learning preferences</h2>
          <p style={subStyle}>Helps us tailor AI explanations and quizzes just for you.</p>

          <div style={{ margin: "20px 0 14px" }} key={`subjects-${subjectTick}`}>
            <Label>Primary Subject</Label>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: "8px" }}>
              {[
                { id: "physics", label: "Physics", emoji: "⚡", color: ACCENT },
                { id: "chemistry", label: "Chemistry", emoji: "🧪", color: ACCENT_CORAL },
                { id: "biology", label: "Biology", emoji: "🌿", color: "#10b981" },
                { id: "math", label: "Math", emoji: "📐", color: ACCENT_BLUE },
                { id: "history", label: "History", emoji: "📜", color: ACCENT_PEACH },
                { id: "english", label: "English", emoji: "📖", color: "#8b5cf6" },
              ].map((s) => (
                <div
                  key={s.id}
                  onClick={() => toggleSubject(s.id)}
                  onKeyDown={(e) => e.key === "Enter" && toggleSubject(s.id)}
                  role="button"
                  tabIndex={0}
                  style={{
                    padding: "12px 10px",
                    borderRadius: "12px",
                    textAlign: "center",
                    cursor: "pointer",
                    border: `2px solid ${formRef.current.subjects.includes(s.id) ? s.color : "var(--glass-border, #e8edf5)"}`,
                    background: formRef.current.subjects.includes(s.id) ? `${s.color}10` : "var(--surface-light, #fafbfc)",
                    transition: "all .18s",
                  }}
                >
                  <div style={{ fontSize: "22px", marginBottom: "4px" }}>{s.emoji}</div>
                  <div
                    style={{
                      fontSize: "11.5px",
                      fontWeight: 700,
                      color: formRef.current.subjects.includes(s.id) ? s.color : "var(--text-primary, #374151)",
                    }}
                  >
                    {s.label}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: "20px" }} key={`grade-${gradeTick}`}>
            <Label>Grade / Level</Label>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              {["Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12", "College"].map((g) => (
                <div
                  key={g}
                  onClick={() => { formRef.current.grade = g; setGradeTick((t) => t + 1); }}
                  onKeyDown={(e) => e.key === "Enter" && (formRef.current.grade = g, setGradeTick((t) => t + 1))}
                  role="button"
                  tabIndex={0}
                  style={{
                    padding: "8px 16px",
                    borderRadius: "20px",
                    cursor: "pointer",
                    fontSize: "12.5px",
                    fontWeight: 600,
                    border: `2px solid ${formRef.current.grade === g ? ACCENT : "var(--glass-border, #e8edf5)"}`,
                    background: formRef.current.grade === g ? "rgba(250,92,92,0.08)" : "var(--surface-light, #fafbfc)",
                    color: formRef.current.grade === g ? ACCENT : "var(--text-primary, #374151)",
                    transition: "all .18s",
                  }}
                >
                  {g}
                </div>
              ))}
            </div>
          </div>

          <PrimaryBtn
            disabled={formRef.current.subjects.length === 0 || !formRef.current.grade}
            onClick={async () => {
              const f = formRef.current;
              await updateUserStats({
                preferences: { subject: f.subjects[0] || undefined, grade: f.grade || undefined },
              });
              setStep("done");
            }}
          >
            Finish Setup 🎉
          </PrimaryBtn>
          <BackBtn onClick={() => setStep("profile")} />
        </Card>
      </Shell>
    );
  }

  /* ── STEP: DONE ── */
  const displayName = (formRef.current.name || profile.profile_name || "Learner").trim() || "Learner";
  const doneMode =
    profile.profile_mode === "solo"
      ? "solo"
      : profile.profile_mode === "teacher_linked" || profile.profile_mode === "teacher_linked_provisional"
        ? "linked"
        : "solo";
  return (
    <Shell>
      <Card>
        <div style={{ textAlign: "center", padding: "16px 0 8px" }}>
          {profile.user_role === "teacher" ? (
            <>
              <div style={{ fontSize: "56px", marginBottom: "16px" }}>👩‍🏫</div>
              <h2 style={{ ...headStyle, textAlign: "center" }}>Teacher Account Detected</h2>
              <p style={{ ...subStyle, textAlign: "center", marginBottom: "28px" }}>
                The local Studaxis app is for students only. Please use the web dashboard to manage your classes and
                generate content.
              </p>
              <PrimaryBtn
                style={{
                  background: `linear-gradient(135deg,${ACCENT_BLUE},#0077b6)`,
                  boxShadow: "0 4px 16px rgba(0,168,232,0.35)",
                }}
                onClick={() => {
                  window.open(TEACHER_DASHBOARD_URL, "_blank");
                  handleComplete();
                }}
              >
                Open Teacher Dashboard →
              </PrimaryBtn>
              <p style={{ marginTop: "14px", fontSize: "12px", color: "var(--text-muted, #9ca3af)", textAlign: "center" }}>
                You can close this window after opening the dashboard.
              </p>
            </>
          ) : (
            <>
              <div style={{ position: "relative", marginBottom: "20px", height: "60px" }}>
                {[ACCENT, ACCENT_CORAL, ACCENT_PEACH, "#FBEF76", ACCENT_BLUE, "#10b981"].map((c, i) => (
                  <div
                    key={i}
                    style={{
                      position: "absolute",
                      width: "10px",
                      height: "10px",
                      borderRadius: "50%",
                      background: c,
                      top: `${Math.sin(i * 1.05) * 20 + 20}px`,
                      left: `${i * 16 + 6}%`,
                      animation: `confettiFall .6s ease ${i * 0.08}s both`,
                    }}
                  />
                ))}
                <div
                  style={{
                    position: "absolute",
                    left: "50%",
                    top: "50%",
                    transform: "translate(-50%,-50%)",
                    width: "60px",
                    height: "60px",
                    borderRadius: "18px",
                    background: `linear-gradient(135deg,${ACCENT},${ACCENT_CORAL},${ACCENT_PEACH})`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    boxShadow: "0 6px 24px rgba(250,92,92,0.4)",
                    fontSize: "28px",
                    padding: 0,
                    overflow: "hidden",
                  }}
                >
                  <img src="/studaxis-logo.png" alt="" className="circular-logo" style={{ width: 56, height: 56, borderRadius: "50%", objectFit: "cover" }} aria-hidden />
                </div>
              </div>
              <h2 style={{ ...headStyle, textAlign: "center", fontSize: "22px" }}>
                Welcome, {displayName}! 🚀
              </h2>
              <p style={{ ...subStyle, textAlign: "center", margin: "8px auto 24px", maxWidth: "300px" }}>
                Your offline AI tutor is ready. All features work at 0 kbps — no internet needed.
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "24px" }}>
                {[
                  { icon: "🤖", text: "AI Tutor · Llama 3.2 · RAG-grounded", color: ACCENT_BLUE },
                  {
                    icon: "📋",
                    text: `Mode: ${doneMode === "solo" ? "Solo Learner" : "Teacher-linked"}${profile.class_code ? ` · ${profile.class_code}` : ""}`,
                    color: ACCENT_CORAL,
                  },
                  {
                    icon: "📚",
                    text: `Subject: ${formRef.current.subjects.length > 0 ? formRef.current.subjects.map((s) => s.charAt(0).toUpperCase() + s.slice(1)).join(", ") : "All"} · ${formRef.current.grade || ""}`,
                    color: ACCENT,
                  },
                ].map((item, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                      background: `${item.color}08`,
                      border: `1px solid ${item.color}25`,
                      borderRadius: "10px",
                      padding: "10px 14px",
                    }}
                  >
                    <span style={{ fontSize: "16px" }}>{item.icon}</span>
                    <span style={{ fontSize: "12.5px", fontWeight: 600, color: "var(--text-primary, #374151)" }}>
                      {item.text}
                    </span>
                  </div>
                ))}
              </div>

              <PrimaryBtn onClick={handleStartLearning}>Start Learning →</PrimaryBtn>
            </>
          )}
        </div>
      </Card>
    </Shell>
  );
}

/* ── Shell (full-page background) ── */
function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="onboarding-shell min-h-screen w-full flex items-center justify-center relative overflow-hidden p-6 font-sans"
      style={{
        fontFamily: "'Inter','Plus Jakarta Sans','DM Sans',sans-serif",
      }}
    >
      <style>{`
        @keyframes popIn{from{opacity:0;transform:scale(0.96) translateY(10px)}to{opacity:1;transform:scale(1) translateY(0)}}
        @keyframes confettiFall{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:translateY(0)}}
        @keyframes ringPulse{0%,100%{transform:scale(1);opacity:.6}50%{transform:scale(1.18);opacity:.15}}
        @keyframes spin{to{transform:rotate(360deg)}}
        input::placeholder{color:var(--text-muted,#9ca3af);}
      `}</style>
      <div
        style={{
          position: "fixed",
          top: "-80px",
          right: "-60px",
          width: "360px",
          height: "360px",
          background: "radial-gradient(circle,rgba(254,194,136,0.22) 0%,transparent 70%)",
          borderRadius: "50%",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "fixed",
          bottom: "-100px",
          left: "-80px",
          width: "420px",
          height: "420px",
          background: "radial-gradient(circle,rgba(250,92,92,0.1) 0%,transparent 70%)",
          borderRadius: "50%",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "fixed",
          top: "40%",
          left: "5%",
          width: "220px",
          height: "220px",
          background: "radial-gradient(circle,rgba(0,168,232,0.07) 0%,transparent 70%)",
          borderRadius: "50%",
          pointerEvents: "none",
        }}
      />
      {children}
    </div>
  );
}
