/**
 * VerifyOTP — OTP verification screen after signup.
 * Reads email from location.state; redirects to /login if missing.
 * 6-digit OTP input with auto-advance, backspace, and paste support.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { postVerifyOtp, postRequestOtp } from "../services/api";

const OTP_LENGTH = 6;
const RESEND_COOLDOWN_SEC = 30;

export function VerifyOTP() {
  const location = useLocation();
  const navigate = useNavigate();
  const { afterOTPVerified, setProfile } = useAuth();
  const email = (location.state as { email?: string } | null)?.email ?? "";
  const [digits, setDigits] = useState<string[]>(Array(OTP_LENGTH).fill(""));
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const hasEmail = Boolean(email && typeof email === "string" && email.trim());

  useEffect(() => {
    if (!hasEmail) {
      navigate("/auth/login", { replace: true });
    }
  }, [hasEmail, navigate]);

  const otpString = digits.join("");

  const handleDigitChange = useCallback(
    (idx: number, value: string) => {
      if (!/^\d*$/.test(value)) return;
      const char = value.slice(-1);
      const next = [...digits];
      next[idx] = char;
      setDigits(next);
      setError("");
      if (char && idx < OTP_LENGTH - 1) {
        inputRefs.current[idx + 1]?.focus();
      }
    },
    [digits]
  );

  const handleKeyDown = useCallback(
    (idx: number, e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Backspace" && !digits[idx] && idx > 0) {
        inputRefs.current[idx - 1]?.focus();
        const next = [...digits];
        next[idx - 1] = "";
        setDigits(next);
      }
    },
    [digits]
  );

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      e.preventDefault();
      const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, OTP_LENGTH);
      if (!pasted) return;
      const arr = pasted.split("");
      const next = [...digits];
      for (let i = 0; i < OTP_LENGTH; i++) {
        next[i] = arr[i] ?? "";
      }
      setDigits(next);
      setError("");
      const lastFilled = Math.min(pasted.length, OTP_LENGTH) - 1;
      inputRefs.current[lastFilled]?.focus();
    },
    [digits]
  );

  const handleVerify = async () => {
    if (otpString.length !== OTP_LENGTH || loading) return;
    setError("");
    setLoading(true);
    try {
      const res = await postVerifyOtp({ email: email.trim().toLowerCase(), otp: otpString });
      afterOTPVerified(res.access_token);
      setProfile({ onboarding_complete: res.onboarding_complete ?? false });
      navigate(res.onboarding_complete ? "/dashboard" : "/onboarding", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0) return;
    setError("");
    try {
      await postRequestOtp({ email: email.trim().toLowerCase() });
      setResendCooldown(RESEND_COOLDOWN_SEC);
      const id = setInterval(() => {
        setResendCooldown((prev) => {
          if (prev <= 1) {
            clearInterval(id);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resend OTP.");
    }
  };

  if (!hasEmail) {
    return null;
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="ambient-glow" aria-hidden />
      <div className="relative z-10 w-full max-w-md">
        <div className="solid-card rounded-2xl p-8 text-center shadow-soft">
          <div className="logo-container">
            <img src="frontend\public\studaxis-logo.png" alt="" className="circular-logo" aria-hidden />
          </div>
          <h1 className="text-xl font-semibold text-primary">Verify your email</h1>
          <p className="text-sm text-muted mt-1">
            Enter the 6-digit code sent to {email}
          </p>
          <div className="mt-6 flex justify-center gap-2" onPaste={handlePaste}>
            {digits.map((d, i) => (
              <input
                key={i}
                ref={(el) => {
                  inputRefs.current[i] = el;
                }}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={d}
                onChange={(e) => handleDigitChange(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                className="w-11 h-12 text-center text-lg font-semibold rounded-xl border border-accent-warm-3/40 bg-deep/30 text-primary focus:border-accent-warm-2 focus:ring-2 focus:ring-accent-warm-2/30 focus:outline-none"
                aria-label={`Digit ${i + 1}`}
              />
            ))}
          </div>
          {error && (
            <p className="text-sm text-error mt-3" role="alert">
              {error}
            </p>
          )}
          <div className="mt-6 space-y-3">
            <button
              type="button"
              onClick={handleVerify}
              disabled={otpString.length !== OTP_LENGTH || loading}
              className="w-full py-2.5 rounded-xl bg-accent-warm-2 text-heading-dark font-semibold hover:bg-accent-warm-3 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Verifying…" : "Verify"}
            </button>
            <button
              type="button"
              onClick={handleResend}
              disabled={resendCooldown > 0 || loading}
              className="w-full py-2.5 rounded-xl border border-accent-warm-3/50 text-primary font-medium hover:bg-accent-warm-3/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {resendCooldown > 0 ? `Resend OTP (${resendCooldown}s)` : "Resend OTP"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
