/**
 * Signup page — real-time validation, password requirements with dynamic checkmarks.
 * Username: alphanumeric + underscore, 3–20 chars.
 * Password: min 8 chars, 1 upper, 1 lower, 1 number, 1 special (@$!%*?&).
 */

import { useState, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
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
          met ? "bg-success/20 text-success" : "bg-surface-light text-primary/40"
        }`}
        aria-hidden
      >
        {met ? "✓" : "○"}
      </span>
      <span className={met ? "text-success" : "text-primary/60"}>{label}</span>
    </div>
  );
}

export function SignupPage() {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { signup } = useAuth();
  const navigate = useNavigate();

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

  const emailValid = useMemo(() => {
    if (!email) return null;
    return /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/.test(email.trim());
  }, [email]);

  const canSubmit =
    email.trim().length > 0 &&
    username.trim().length >= 3 &&
    usernameValid === true &&
    passwordAllMet &&
    !loading;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!canSubmit) return;
    setLoading(true);
    try {
      const res = await postSignup({
        email: email.trim().toLowerCase(),
        username: username.trim(),
        password,
      });
      signup(res);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="ambient-glow" aria-hidden />
      <div className="relative z-10 w-full max-w-md">
        <div className="glass-panel rounded-2xl border border-glass-border p-8 text-center">
          <div className="text-4xl mb-4" aria-hidden>
            🎓
          </div>
          <h1 className="text-xl font-semibold text-primary">Create account</h1>
          <p className="text-sm text-primary/70 mt-1">
            Join Studaxis to start your learning journey
          </p>
          <form onSubmit={handleSubmit} className="mt-6 space-y-4 text-left">
            <div>
              <label className="block text-sm text-primary/80 mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className={`w-full px-4 py-2.5 rounded-xl bg-surface-light border text-primary placeholder:text-primary/40 ${
                  email && emailValid === false
                    ? "border-error"
                    : "border-glass-border"
                }`}
                autoComplete="email"
              />
              {email && emailValid === false && (
                <p className="text-xs text-error mt-1">Invalid email format</p>
              )}
            </div>
            <div>
              <label className="block text-sm text-primary/80 mb-1">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value.replace(/[^a-zA-Z0-9_]/g, ""))}
                placeholder="alphanumeric and underscores, 3–20 chars"
                maxLength={20}
                className={`w-full px-4 py-2.5 rounded-xl bg-surface-light border text-primary placeholder:text-primary/40 ${
                  usernameError ? "border-error" : "border-glass-border"
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
              <label className="block text-sm text-primary/80 mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min 8 chars, 1 upper, 1 lower, 1 number, 1 special"
                className="w-full px-4 py-2.5 rounded-xl bg-surface-light border border-glass-border text-primary placeholder:text-primary/40"
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
                disabled={!canSubmit}
                className="flex-1 py-2.5 rounded-xl bg-accent-blue text-deep font-semibold hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "Creating…" : "Create account"}
              </button>
              <Link
                to="/auth/login"
                className="flex-1 py-2.5 rounded-xl border border-glass-border text-primary/80 font-medium hover:bg-surface-light transition-colors text-center"
              >
                Back to sign in
              </Link>
            </div>
          </form>
          <p className="text-sm text-primary/60 mt-4">
            Already have an account?{" "}
            <Link to="/auth/login" className="text-accent-blue hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
