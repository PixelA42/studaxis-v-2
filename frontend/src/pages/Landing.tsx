/**
 * Landing page — hero glass card, Get Started → auth or dashboard (Thermal Vitreous).
 */

import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export function LandingPage() {
  const { userLoggedIn } = useAuth();

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="ambient-glow" aria-hidden />
      <div className="relative z-10 w-full max-w-2xl">
        <div className="glass-panel rounded-2xl border border-glass-border p-10 text-center">
          <h1 className="text-3xl md:text-4xl font-bold text-primary leading-tight">
            Organize{" "}
            <span className="text-accent-blue">everything</span>
            <br />
            in your{" "}
            <span className="text-accent-blue underline decoration-accent-blue/50">
              learning
            </span>
          </h1>
          <p className="text-primary/70 mt-4 text-lg">
            AI-powered offline tutor that works anywhere, anytime — even at 0
            kbps.
          </p>
          <div className="flex flex-wrap justify-center gap-3 mt-6">
            <span className="px-3 py-1.5 rounded-full border border-glass-border text-xs font-medium text-primary/80">
              ⚡ 100% Offline
            </span>
            <span className="px-3 py-1.5 rounded-full border border-glass-border text-xs font-medium text-primary/80">
              🤖 Llama 3.2 on-device
            </span>
            <span className="px-3 py-1.5 rounded-full border border-glass-border text-xs font-medium text-primary/80">
              📚 RAG-grounded
            </span>
          </div>
          <div className="mt-8">
            <Link
              to={userLoggedIn ? "/dashboard" : "/auth/login"}
              className="inline-flex px-8 py-3 rounded-xl bg-accent-blue text-deep font-semibold hover:opacity-90 transition-opacity"
            >
              Get Started →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
