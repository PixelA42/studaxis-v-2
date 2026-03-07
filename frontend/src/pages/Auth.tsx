/**
 * Auth page — sign in form; on submit set userLoggedIn and navigate to dashboard.
 */

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export function AuthPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!username.trim() || !password.trim()) {
      setError("Please enter username and password.");
      return;
    }
    login(username, password);
    navigate("/dashboard", { replace: true });
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="ambient-glow" aria-hidden />
      <div className="relative z-10 w-full max-w-md">
        <div className="glass-panel rounded-2xl border border-glass-border p-8 text-center">
          <div className="text-4xl mb-4" aria-hidden>
            🎓
          </div>
          <h1 className="text-xl font-semibold text-primary">Welcome back</h1>
          <p className="text-sm text-primary/70 mt-1">
            Sign in to continue your learning journey
          </p>
          <form onSubmit={handleSubmit} className="mt-6 space-y-4 text-left">
            <div>
              <label className="block text-sm text-primary/80 mb-1">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                className="w-full px-4 py-2.5 rounded-xl bg-surface-light border border-glass-border text-primary placeholder:text-primary/40"
                autoComplete="username"
              />
            </div>
            <div>
              <label className="block text-sm text-primary/80 mb-1">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                className="w-full px-4 py-2.5 rounded-xl bg-surface-light border border-glass-border text-primary placeholder:text-primary/40"
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
                className="flex-1 py-2.5 rounded-xl bg-accent-blue text-deep font-semibold hover:opacity-90 transition-opacity"
              >
                Sign In
              </button>
              <Link
                to="/"
                className="flex-1 py-2.5 rounded-xl border border-glass-border text-primary/80 font-medium hover:bg-surface-light transition-colors text-center"
              >
                Back
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
