/**
 * VerifyEmail — handles email verification link from signup.
 * Reads token from ?token=, calls GET /api/auth/verify-email, shows success/error.
 */

import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { verifyEmail } from "../services/api";

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token || !token.trim()) {
      setStatus("error");
      setMessage("No verification token provided.");
      return;
    }
    setStatus("loading");
    verifyEmail(token)
      .then((res) => {
        setStatus("success");
        setMessage(res.message || "Email verified successfully.");
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err instanceof Error ? err.message : "Verification failed.");
      });
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-deep">
      <div className="ambient-glow" aria-hidden />
      <div className="relative z-10 glass-panel rounded-2xl border border-glass-border p-8 max-w-md w-full text-center">
        {status === "loading" && (
          <>
            <div className="loading-spinner mx-auto mb-4" aria-hidden />
            <h1 className="text-xl font-semibold text-primary">Verifying your email…</h1>
          </>
        )}
        {status === "success" && (
          <>
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-500/20 flex items-center justify-center">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" className="text-green-600">
                <path d="M5 13l4 4L19 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <h1 className="text-xl font-semibold text-primary">Email verified!</h1>
            <p className="text-primary/70 mt-2 text-sm">{message}</p>
            <Link
              to="/auth/login"
              className="inline-block mt-6 px-6 py-3 rounded-xl font-semibold text-white bg-accent-pink hover:opacity-90 transition"
            >
              Sign in
            </Link>
          </>
        )}
        {status === "error" && (
          <>
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/20 flex items-center justify-center">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" className="text-red-600">
                <path d="M6 18L18 6M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </div>
            <h1 className="text-xl font-semibold text-primary">Verification failed</h1>
            <p className="text-primary/70 mt-2 text-sm">{message}</p>
            <Link
              to="/auth/signup"
              className="inline-block mt-6 px-6 py-3 rounded-xl font-semibold text-white bg-accent-pink hover:opacity-90 transition"
            >
              Sign up again
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
