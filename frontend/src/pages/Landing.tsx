/**
 * Landing page — hero, Features & Services in pastel cards, Get Started → auth or dashboard.
 */

import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import "./Landing.css";
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

function useSlideIn(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setVisible(true);
      },
      { threshold, rootMargin: "0px 0px -40px 0px" }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold]);
  return { ref, visible };
}

export function LandingPage() {
  const { userLoggedIn } = useAuth();
  const heroSlide = useSlideIn();
  const featuresSlide = useSlideIn();
  const servicesSlide = useSlideIn();

  return (
    <div className="w-full min-h-screen flex flex-col bg-deep m-0 p-0">
      <div className="ambient-glow" aria-hidden />
      <div className="relative z-10 w-full flex flex-col gap-12 md:gap-16 py-6 md:py-10">
        {/* Hero — content card with depth */}
        <div
          ref={heroSlide.ref}
          className={`content-card rounded-card border border-glass-border mx-auto max-w-[860px] w-full px-6 md:px-[60px] py-10 flex flex-col items-center text-center landing-slide ${heroSlide.visible ? "landing-slide--visible" : ""}`}
        >
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
        <section ref={featuresSlide.ref} className="text-center max-w-[900px] mx-auto px-6">
          <h2 className={`text-2xl md:text-3xl font-extrabold font-anchor-bold text-heading-dark mb-6 landing-slide ${featuresSlide.visible ? "landing-slide--visible" : ""}`}>
            Our <span className="text-chunk-blue">Features</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 justify-items-center">
            {features.map((f, i) => {
              const { bgClass } = FEATURE_CARD_STYLES[i];
              const slideDir = i === 0 ? "landing-slide-left" : i === 1 ? "landing-slide-center" : "landing-slide-right";
              const delayClass = i === 0 ? "landing-slide--delay-0" : i === 1 ? "landing-slide--delay-1" : "landing-slide--delay-2";
              return (
                <div
                  key={f.title}
                  className={`${bgClass} rounded-card p-5 text-heading-dark shadow-card transition-all duration-300 ease hover:-translate-y-1 hover:shadow-soft w-full max-w-sm text-center flex flex-col items-center ${slideDir} ${delayClass} ${featuresSlide.visible ? "landing-slide--visible" : ""}`}
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
        <section ref={servicesSlide.ref} className="text-center max-w-[900px] mx-auto px-6">
          <h2 className={`text-2xl md:text-3xl font-extrabold font-anchor-bold text-heading-dark mb-6 landing-slide ${servicesSlide.visible ? "landing-slide--visible" : ""}`}>
            How It <span className="text-chunk-yellow">Works</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 justify-items-center">
            {services.map((s, i) => {
              const { bgClass } = FEATURE_CARD_STYLES[i];
              const slideDir = i === 0 ? "landing-slide-left" : i === 1 ? "landing-slide-center" : "landing-slide-right";
              const delayClass = i === 0 ? "landing-slide--delay-0" : i === 1 ? "landing-slide--delay-1" : "landing-slide--delay-2";
              return (
                <div
                  key={s.title}
                  className={`${bgClass} rounded-card p-5 text-heading-dark shadow-card transition-all duration-300 ease hover:-translate-y-1 hover:shadow-soft w-full max-w-sm text-center flex flex-col items-center ${slideDir} ${delayClass} ${servicesSlide.visible ? "landing-slide--visible" : ""}`}
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
