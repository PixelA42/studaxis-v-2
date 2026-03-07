/**
 * Auth component — unified Sign Up (multi-step) and Sign In.
 * Defaults to Sign Up view when not authenticated.
 * Uses solid-card design: warm colors, high-contrast text, no glassmorphism.
 */

import { useState, useMemo, useEffect } from "react";
import { useNavigate, useLocation, Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { postSignup } from "../services/api";

const USERNAME_REGEX = /^[a-zA-Z0-9_]{3,20}$/;

const PASSWORD_RULES = [
  { id: "length", label: "At least 8 characters", test: (p: string) => p.length >= 8 },
  { id: "upper", label: "One uppercase letter", test: (p: string) => /[A-Z]/.test(p) },
  { id: "lower", label: "One lowercase letter", test: (p: string) => /[a-z]/.test(p) },
  { id: "number", label: "One number", test: (p: string) => /\d/.test(p) },
  { id: "special", label: "One special character (@$!%*?&)", test: (p: string) => /[@$!%*?&]/.test(p) },
] as const;

function CheckItem({ met, label }: { met: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span
        className={`inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
          met ? "bg-success/20 text-success" : "bg-accent-warm-3/20 text-subtle"
        }`}
        aria-hidden
      >
        {met ? "✓" : "○"}
      </span>
      <span className={met ? "text-success" : "text-muted"}>{label}</span>
    </div>
  );
}

type AuthMode = "signup" | "signin";
type SignupStep = 1 | 2;

export function Auth() {
  const location = useLocation();
  const [mode, setMode] = useState<AuthMode>("signup");
  const [step, setStep] = useState<SignupStep>(1);
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [usernameOrEmail, setUsernameOrEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { isAuthenticated, profile, signup, loginWithCredentials } = useAuth();
  const navigate = useNavigate();

  // Already registered/logged in → go to dashboard or onboarding based on completion
  if (isAuthenticated) {
    return <Navigate to={profile.onboarding_complete ? "/dashboard" : "/onboarding"} replace />;
  }

  // URL-based mode: /auth/login → Sign In, /auth or /auth/signup → Sign Up
  useEffect(() => {
    if (location.pathname === "/auth/login") setMode("signin");
    else setMode("signup");
  }, [location.pathname]);

  const emailValid = useMemo(() => {
    if (!email) return null;
    return /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/.test(email.trim());
  }, [email]);

  const usernameValid = useMemo(() => {
    if (!username) return null;
    return USERNAME_REGEX.test(username.trim());
  }, [username]);

  const usernameError = useMemo(() => {
    if (!username) return null;
    const t = username.trim();
    if (t.length < 3) return "At least 3 characters";
    if (t.length > 20) return "At most 20 characters";
    if (!/^[a-zA-Z0-9_]+$/.test(t)) return "Only letters, numbers, and underscores";
    return null;
  }, [username]);

  const passwordChecks = useMemo(
    () => PASSWORD_RULES.map((r) => ({ ...r, met: r.test(password) })),
    [password]
  );
  const passwordAllMet = useMemo(
    () => passwordChecks.every((c) => c.met),
    [passwordChecks]
  );

  const canSignupStep1 = email.trim().length > 0 && emailValid === true;
  const canSignupStep2 =
    email.trim().length > 0 &&
    username.trim().length >= 3 &&
    usernameValid === true &&
    passwordAllMet &&
    !loading;

  const canLogin =
    usernameOrEmail.trim().length > 0 &&
    loginPassword.length > 0 &&
    !loading;

  const handleSignupStep1Next = () => {
    setError("");
    if (canSignupStep1) setStep(2);
    else if (email && emailValid === false) setError("Please enter a valid email.");
  };

  const handleSignupBack = () => {
    setError("");
    if (step === 2) setStep(1);
    else navigate("/", { replace: true });
  };

  const handleSignInBack = () => {
    setError("");
    navigate("/", { replace: true });
  };

  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!canSignupStep2) return;
    setLoading(true);
    try {
      const res = await postSignup({
        email: email.trim().toLowerCase(),
        username: username.trim(),
        password,
      });
      signup(res);
      navigate("/onboarding", { replace: true, state: { startFrom: "otp", email: email.trim().toLowerCase() } });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Signup failed. Please try again.";
      setError(msg);
      // Already registered → redirect to login
      if (typeof msg === "string" && /already (exists|registered)/i.test(msg)) {
        navigate("/auth/login", { replace: true });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!canLogin) return;
    setLoading(true);
    try {
      await loginWithCredentials(usernameOrEmail.trim(), loginPassword);
      navigate(profile.onboarding_complete ? "/dashboard" : "/onboarding", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const switchToSignIn = () => {
    setMode("signin");
    setError("");
    setUsernameOrEmail("");
    setLoginPassword("");
    navigate("/auth/login", { replace: true });
  };

  const switchToSignUp = () => {
    setMode("signup");
    setStep(1);
    setError("");
    setEmail("");
    setUsername("");
    setPassword("");
    navigate("/auth/signup", { replace: true });
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="ambient-glow" aria-hidden />
      <div className="relative z-10 w-full max-w-md">
        <div className="solid-card rounded-2xl p-8 text-center shadow-soft">
          <div className="text-4xl mb-4" aria-hidden>
            🎓
          </div>

          {mode === "signup" ? (
            <>
              <h1 className="text-xl font-semibold text-primary">
                {step === 1 ? "Create account" : "Almost there"}
              </h1>
              <p className="text-sm text-muted mt-1">
                {step === 1
                  ? "Enter your email to get started"
                  : "Choose a username and password"}
              </p>

              {step === 1 && (
                <div className="mt-6 space-y-4 text-left">
                  <div>
                    <label className="block text-sm font-medium text-primary mb-1">
                      Email
                    </label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      className={`w-full px-4 py-2.5 rounded-xl border text-primary placeholder:text-subtle bg-deep/30 ${
                        email && emailValid === false
                          ? "border-error"
                          : "border-accent-warm-3/40"
                      }`}
                      autoComplete="email"
                    />
                    {email && emailValid === false && (
                      <p className="text-xs text-error mt-1">Invalid email format</p>
                    )}
                  </div>
                  {error && (
                    <p className="text-sm text-error" role="alert">
                      {error}
                    </p>
                  )}
                  <div className="flex gap-3 pt-2">
                    <button
                      type="button"
                      onClick={handleSignupStep1Next}
                      disabled={!canSignupStep1}
                      className="flex-1 py-2.5 rounded-xl bg-accent-warm-2 text-heading-dark font-semibold hover:bg-accent-warm-3 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                    <button
                      type="button"
                      onClick={handleSignupBack}
                      className="flex-1 py-2.5 rounded-xl border border-accent-warm-3/50 text-primary font-medium hover:bg-accent-warm-3/10 transition-colors"
                    >
                      Back
                    </button>
                  </div>
                </div>
              )}

              {step === 2 && (
                <form onSubmit={handleSignupSubmit} className="mt-6 space-y-4 text-left">
                  <div>
                    <label className="block text-sm font-medium text-primary mb-1">
                      Email
                    </label>
                    <input
                      type="email"
                      value={email}
                      readOnly
                      className="w-full px-4 py-2.5 rounded-xl border border-accent-warm-3/40 bg-deep/20 text-primary/80"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-primary mb-1">
                      Unique Username
                    </label>
                    <input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value.replace(/[^a-zA-Z0-9_]/g, ""))}
                      placeholder="alphanumeric and underscores, 3–20 chars"
                      maxLength={20}
                      className={`w-full px-4 py-2.5 rounded-xl border text-primary placeholder:text-subtle bg-deep/30 ${
                        usernameError ? "border-error" : "border-accent-warm-3/40"
                      }`}
                      autoComplete="username"
                    />
                    {usernameError && (
                      <p className="text-xs text-error mt-1">{usernameError}</p>
                    )}
                    {username && usernameValid && (
                      <p className="text-xs text-success mt-1">✓ Valid username</p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-primary mb-1">
                      Password
                    </label>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Min 8 chars, 1 upper, 1 lower, 1 number, 1 special"
                      className="w-full px-4 py-2.5 rounded-xl border border-accent-warm-3/40 text-primary placeholder:text-subtle bg-deep/30"
                      autoComplete="new-password"
                    />
                    <div className="mt-2 space-y-1.5">
                      {passwordChecks.map((c) => (
                        <CheckItem key={c.id} met={c.met} label={c.label} />
                      ))}
                    </div>
                  </div>
                  {error && (
                    <p className="text-sm text-error" role="alert">
                      {error}
                    </p>
                  )}
                  <div className="flex gap-3 pt-2">
                    <button
                      type="submit"
                      disabled={!canSignupStep2}
                      className="flex-1 py-2.5 rounded-xl bg-accent-warm-2 text-heading-dark font-semibold hover:bg-accent-warm-3 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loading ? "Creating…" : "Create account"}
                    </button>
                    <button
                      type="button"
                      onClick={handleSignupBack}
                      className="flex-1 py-2.5 rounded-xl border border-accent-warm-3/50 text-primary font-medium hover:bg-accent-warm-3/10 transition-colors"
                    >
                      Back
                    </button>
                  </div>
                </form>
              )}

              <p className="text-sm text-muted mt-4">
                Already have an account?{" "}
                <button
                  type="button"
                  onClick={switchToSignIn}
                  className="text-accent-warm-2 font-medium hover:underline"
                >
                  Sign In
                </button>
              </p>
            </>
          ) : (
            <>
              <h1 className="text-xl font-semibold text-primary">Welcome back</h1>
              <p className="text-sm text-muted mt-1">
                Sign in to continue your learning journey
              </p>
              <form onSubmit={handleLoginSubmit} className="mt-6 space-y-4 text-left">
                <div>
                  <label className="block text-sm font-medium text-primary mb-1">
                    Username or email
                  </label>
                  <input
                    type="text"
                    value={usernameOrEmail}
                    onChange={(e) => setUsernameOrEmail(e.target.value)}
                    placeholder="Enter your username or email"
                    className="w-full px-4 py-2.5 rounded-xl border border-accent-warm-3/40 text-primary placeholder:text-subtle bg-deep/30"
                    autoComplete="username"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-primary mb-1">
                    Password
                  </label>
                  <input
                    type="password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="w-full px-4 py-2.5 rounded-xl border border-accent-warm-3/40 text-primary placeholder:text-subtle bg-deep/30"
                    autoComplete="current-password"
                  />
                </div>
                {error && (
                  <p className="text-sm text-error" role="alert">
                    {error}
                  </p>
                )}
                <div className="flex gap-3 pt-2">
                  <button
                    type="submit"
                    disabled={!canLogin}
                    className="flex-1 py-2.5 rounded-xl bg-accent-warm-2 text-heading-dark font-semibold hover:bg-accent-warm-3 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? "Signing in…" : "Sign in"}
                  </button>
                  <button
                    type="button"
                    onClick={handleSignInBack}
                    className="flex-1 py-2.5 rounded-xl border border-accent-warm-3/50 text-primary font-medium hover:bg-accent-warm-3/10 transition-colors"
                  >
                    Back
                  </button>
                </div>
              </form>
              <p className="text-sm text-muted mt-4">
                Don&apos;t have an account?{" "}
                <button
                  type="button"
                  onClick={switchToSignUp}
                  className="text-accent-warm-2 font-medium hover:underline"
                >
                  Create account
                </button>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
