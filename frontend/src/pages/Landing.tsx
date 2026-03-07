/**
 * Landing page — hero, Features & Services in pastel cards, Get Started → auth or dashboard.
 */

import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Icons } from "../components/icons";

/* Solid-card palette: pastel tokens — no white, no glassmorphism */
const FEATURE_CARD_STYLES = [
  { bgClass: "bg-pastel-pink" },
  { bgClass: "bg-pastel-blue" },
  { bgClass: "bg-pastel-yellow" },
] as const;

const features = [
  {
    title: "AI Tutor Chat",
    description: "Ask questions from your textbooks and get curriculum-grounded answers — fully offline.",
    icon: Icons.ai,
  },
  {
    title: "Quick Quiz",
    description: "Test your knowledge with AI-generated questions. Get instant grading and feedback.",
    icon: Icons.quiz,
  },
  {
    title: "Flashcards",
    description: "Spaced-repetition review. Mark cards Easy or Hard to schedule the next review.",
    icon: Icons.cards,
  },
];

const services = [
  {
    title: "100% Offline",
    description: "Works anywhere, anytime — even at 0 kbps. No internet required after setup.",
    icon: Icons.offline,
  },
  {
    title: "Llama 3.2 On-Device",
    description: "Powerful AI runs locally on your machine. Privacy-first, no cloud dependency.",
    icon: Icons.ai,
  },
  {
    title: "RAG-Grounded",
    description: "Answers grounded in your textbooks. No hallucinations from external sources.",
    icon: Icons.book,
  },
];

export function LandingPage() {
  const { userLoggedIn } = useAuth();

  return (
    <div className="min-h-screen flex flex-col p-6 md:p-10">
      <div className="ambient-glow" aria-hidden />
      <div className="relative z-10 w-full max-w-4xl mx-auto flex flex-col gap-12 md:gap-16">
        {/* Hero */}
        <div className="glass-panel shadow-soft rounded-2xl border border-glass-border p-10 text-center">
          <h1 className="text-3xl md:text-5xl font-extrabold text-primary leading-tight">
            Organize{" "}
            <span className="text-pastel-blue">everything</span>
            <br />
            in your{" "}
            <span className="text-pastel-pink">learning</span>
          </h1>
          <p className="text-primary/70 mt-4 text-lg">
            AI-powered offline tutor that works anywhere, anytime — even at 0
            kbps.
          </p>
          <div className="flex flex-wrap justify-center gap-3 mt-6">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-pastel-pink/40 text-heading-dark/90 text-xs font-medium">
              {Icons.offline} 100% Offline
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-pastel-blue/40 text-heading-dark/90 text-xs font-medium">
              {Icons.ai} Llama 3.2 on-device
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-pastel-yellow/40 text-heading-dark/90 text-xs font-medium">
              {Icons.book} RAG-grounded
            </span>
          </div>
          <div className="mt-8">
            <Link
              to={userLoggedIn ? "/dashboard" : "/auth"}
              className="inline-flex px-8 py-3 rounded-xl bg-accent-blue text-deep font-semibold hover:opacity-90 transition-opacity shadow-soft"
            >
              Get Started →
            </Link>
          </div>
        </div>

        {/* Features — Solid Card spec: pastel backgrounds, text-main-light, no glassmorphism */}
        <section>
          <h2 className="text-2xl md:text-3xl font-extrabold text-primary mb-6">
            Our <span className="text-accent-blue">Features</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {features.map((f, i) => {
              const { bgClass } = FEATURE_CARD_STYLES[i];
              return (
                <div
                  key={f.title}
                  className={`${bgClass} rounded-2xl p-5 text-main-light shadow-[0_10px_25px_-5px_rgba(0,0,0,0.1)] transition-all duration-300 ease hover:-translate-y-2 hover:shadow-[0_20px_25px_-5px_rgba(0,0,0,0.15)]`}
                >
                  <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center text-xl text-main-light mb-3 [&>svg]:text-main-light">
                    {f.icon}
                  </div>
                  <h3 className="font-bold text-main-light">{f.title}</h3>
                  <p className="text-sm text-main-light mt-1">{f.description}</p>
                </div>
              );
            })}
          </div>
        </section>

        {/* Services — Solid Card spec: pastel backgrounds, text-main-light, no glassmorphism */}
        <section>
          <h2 className="text-2xl md:text-3xl font-extrabold text-primary mb-6">
            How It <span className="text-accent-warm-4">Works</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {services.map((s, i) => {
              const { bgClass } = FEATURE_CARD_STYLES[i];
              return (
                <div
                  key={s.title}
                  className={`${bgClass} rounded-2xl p-5 text-main-light shadow-[0_10px_25px_-5px_rgba(0,0,0,0.1)] transition-all duration-300 ease hover:-translate-y-2 hover:shadow-[0_20px_25px_-5px_rgba(0,0,0,0.15)]`}
                >
                  <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center text-xl text-main-light mb-3 [&>svg]:text-main-light">
                    {s.icon}
                  </div>
                  <h3 className="font-bold text-main-light">{s.title}</h3>
                  <p className="text-sm text-main-light mt-1">{s.description}</p>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
