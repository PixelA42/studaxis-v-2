/**
 * OllamaLoadingScreen — Studaxis loading screen shown until local AI (Ollama) is ready.
 * Parent (OllamaGate) handles polling; this component is purely presentational.
 * Design: white background (#ffffff), Studaxis brand colors for accents.
 */

import { useEffect, useState } from "react";

export function OllamaLoadingScreen(_props: { onReady?: () => void }) {
  const [progress, setProgress] = useState(0);

  // Simulated progress animation (visual feedback while waiting for Ollama)
  useEffect(() => {
    const id = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 92) return prev + 0.002;
        return Math.min(92, prev + 0.4);
      });
    }, 80);
    return () => clearInterval(id);
  }, []);

  const drift = Math.sin(Date.now() / 1000) * 0.5;
  const shownProgress = Math.min(100, progress + drift);

  return (
    <div
      className="ollama-loading-screen"
      style={{
        margin: 0,
        padding: 0,
        backgroundColor: "var(--bg-base)",
        backgroundImage: "radial-gradient(circle at 50% 50%, var(--bg-input) 0%, var(--bg-base) 100%)",
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "var(--text-primary)",
        overflow: "hidden",
        WebkitFontSmoothing: "antialiased",
      }}
    >
      <div
        className="container"
        style={{
          width: "100%",
          maxWidth: 600,
          padding: 40,
          display: "flex",
          flexDirection: "column",
          gap: "2rem",
          animation: "ollama-reveal 1.2s cubic-bezier(0.16, 1, 0.3, 1)",
        }}
      >
        <div
          className="header"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
            marginBottom: -10,
          }}
        >
          <div
            className="title"
            style={{
              fontFamily: "Inter, system-ui, sans-serif",
              fontWeight: 700,
              fontSize: "0.75rem",
              letterSpacing: "0.25em",
              textTransform: "uppercase",
              opacity: 0.6,
              color: "var(--text-primary)",
            }}
          >
            Loading Studaxis
          </div>
          <div
            className="stats"
            style={{
              fontFamily: "JetBrains Mono, ui-monospace, monospace",
              fontSize: "0.85rem",
              color: "#00A8E8",
              textShadow: "0 0 15px rgba(0, 168, 232, 0.3)",
            }}
          >
            {shownProgress.toFixed(1)}%
          </div>
        </div>

        <div
          className="glass-track"
          style={{
            position: "relative",
            height: 12,
            width: "100%",
            background: "rgba(15, 23, 42, 0.06)",
            border: "1px solid rgba(15, 23, 42, 0.12)",
            borderRadius: 100,
            overflow: "hidden",
            boxShadow:
              "inset 0 1px 1px rgba(255,255,255,0.5), 0 10px 30px rgba(0,0,0,0.06)",
          }}
        >
          <div
            className="prism-fill"
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              height: "100%",
              width: `${shownProgress}%`,
              borderRadius: 100,
              background: `linear-gradient(90deg, 
                rgba(0, 168, 232, 0.2) 0%, 
                rgba(0, 168, 232, 0.5) 50%, 
                rgba(0, 168, 232, 0.9) 100%
              )`,
              transition: "width 1s cubic-bezier(0.65, 0, 0.35, 1)",
              zIndex: 2,
            }}
          />
          <div
            className="glide-shimmer"
            style={{
              position: "absolute",
              top: 0,
              left: "-100%",
              width: "100%",
              height: "100%",
              background: `linear-gradient(
                90deg,
                transparent,
                rgba(255, 255, 255, 0.3) 20%,
                rgba(255, 255, 255, 0.8) 50%,
                rgba(255, 255, 255, 0.3) 80%,
                transparent
              )`,
              zIndex: 3,
              animation: "ollama-glide 2.5s cubic-bezier(0.4, 0, 0.2, 1) infinite",
            }}
          />
        </div>

        <div
          className="footer"
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontFamily: "JetBrains Mono, ui-monospace, monospace",
            fontSize: "0.7rem",
            letterSpacing: "0.1em",
            opacity: 0.5,
            color: "var(--text-primary)",
          }}
        >
          <span>OFFLINE_FIRST • LOCAL_AI</span>
          <span>STUDAXIS v1.0</span>
        </div>

        <div
          className="readout"
          style={{
            fontFamily: "JetBrains Mono, ui-monospace, monospace",
            fontSize: 10,
            color: "var(--text-secondary)",
            display: "flex",
            gap: 20,
            marginTop: 10,
          }}
        >
          <div
            className="readout-item"
            style={{ position: "relative", paddingLeft: 12 }}
          >
            <span
              style={{
                position: "absolute",
                left: 0,
                top: "50%",
                transform: "translateY(-50%)",
                width: 4,
                height: 4,
                background: "#00A8E8",
                borderRadius: "50%",
              }}
            />
            PHASE: Waking up your local AI tutor…
          </div>
          <div
            className="readout-item"
            style={{ position: "relative", paddingLeft: 12 }}
          >
            <span
              style={{
                position: "absolute",
                left: 0,
                top: "50%",
                transform: "translateY(-50%)",
                width: 4,
                height: 4,
                background: "#00A8E8",
                borderRadius: "50%",
              }}
            />
            ENGINE: Ollama
          </div>
          <div
            className="readout-item"
            style={{ position: "relative", paddingLeft: 12 }}
          >
            <span
              style={{
                position: "absolute",
                left: 0,
                top: "50%",
                transform: "translateY(-50%)",
                width: 4,
                height: 4,
                background: "#00A8E8",
                borderRadius: "50%",
              }}
            />
            STATUS: Connecting…
          </div>
        </div>
      </div>

      <style>{`
        @keyframes ollama-reveal {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes ollama-glide {
          0% { transform: translateX(-50%) skewX(-20deg); }
          100% { transform: translateX(150%) skewX(-20deg); }
        }
      `}</style>
    </div>
  );
}
