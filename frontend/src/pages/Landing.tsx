/**
 * Landing page — hero, Features & Services in pastel cards, Get Started → auth or dashboard.
 */

import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Icons } from "../components/icons";

/* Chunky color blocks — reference proportions (25% of layout) */
const FEATURE_CARD_STYLES = [
  { bgClass: "bg-chunk-pink" },
  { bgClass: "bg-chunk-blue" },
  { bgClass: "bg-chunk-yellow" },
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
    <div className="min-h-screen flex flex-col bg-deep p-6 md:p-10">
      <div className="ambient-glow" aria-hidden />
      <div className="relative z-10 w-full max-w-4xl mx-auto flex flex-col gap-12 md:gap-16">
        {/* Hero — content card with depth */}
        <div className="content-card rounded-card border border-glass-border p-10 flex flex-col items-center text-center">
          <h1 className="text-3xl md:text-5xl font-extrabold font-anchor-bold text-heading-dark leading-tight">
            Organize{" "}
            <span className="text-chunk-blue">everything</span>
            <br />
            in your{" "}
            <span className="text-chunk-pink">learning</span>
          </h1>
          <p className="text-heading-dark/80 mt-4 text-lg font-semibold">
            AI-powered offline tutor that works anywhere, anytime — even at 0
            kbps.
          </p>
          <div className="flex flex-wrap justify-center gap-3 mt-6">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-chunk-pink/30 text-heading-dark font-semibold text-xs">
              {Icons.offline} 100% Offline
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-chunk-blue/30 text-heading-dark font-semibold text-xs">
              {Icons.ai} Llama 3.2 on-device
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-chunk-yellow/30 text-heading-dark font-semibold text-xs">
              {Icons.book} RAG-grounded
            </span>
          </div>
          <div className="mt-8">
            <Link
              to={userLoggedIn ? "/home" : "/auth"}
              className="inline-flex px-8 py-3 rounded-xl bg-chunk-blue text-heading-dark font-extrabold hover:opacity-90 transition-opacity shadow-card"
            >
              Get Started →
            </Link>
          </div>
        </div>

        {/* Features — chunky color blocks (25% of layout) */}
        <section className="text-center">
          <h2 className="text-2xl md:text-3xl font-extrabold font-anchor-bold text-heading-dark mb-6">
            Our <span className="text-chunk-blue">Features</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 justify-items-center">
            {features.map((f, i) => {
              const { bgClass } = FEATURE_CARD_STYLES[i];
              return (
                <div
                  key={f.title}
                  className={`${bgClass} rounded-card p-5 text-heading-dark shadow-card transition-all duration-300 ease hover:-translate-y-1 hover:shadow-soft w-full max-w-sm text-center flex flex-col items-center`}
                >
                  <div className="w-10 h-10 rounded-lg bg-white/90 flex items-center justify-center text-xl text-heading-dark mb-3 [&>svg]:text-heading-dark">
                    {f.icon}
                  </div>
                  <h3 className="font-extrabold font-anchor-bold text-heading-dark">{f.title}</h3>
                  <p className="text-sm font-semibold text-heading-dark/85 mt-1">{f.description}</p>
                </div>
              );
            })}
          </div>
        </section>

        {/* Services — chunky color blocks */}
        <section className="text-center">
          <h2 className="text-2xl md:text-3xl font-extrabold font-anchor-bold text-heading-dark mb-6">
            How It <span className="text-chunk-yellow">Works</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 justify-items-center">
            {services.map((s, i) => {
              const { bgClass } = FEATURE_CARD_STYLES[i];
              return (
                <div
                  key={s.title}
                  className={`${bgClass} rounded-card p-5 text-heading-dark shadow-card transition-all duration-300 ease hover:-translate-y-1 hover:shadow-soft w-full max-w-sm text-center flex flex-col items-center`}
                >
                  <div className="w-10 h-10 rounded-lg bg-white/90 flex items-center justify-center text-xl text-heading-dark mb-3 [&>svg]:text-heading-dark">
                    {s.icon}
                  </div>
                  <h3 className="font-extrabold font-anchor-bold text-heading-dark">{s.title}</h3>
                  <p className="text-sm font-semibold text-heading-dark/85 mt-1">{s.description}</p>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
