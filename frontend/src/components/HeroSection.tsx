import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";

const AnimatedUnderline = ({
  color,
  delay = 0,
  style = "straight",
}: {
  color: string;
  delay?: number;
  style?: "straight" | "wave";
}) => {
  const [drawn, setDrawn] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setDrawn(true), delay);
    return () => clearTimeout(t);
  }, [delay]);

  if (style === "wave") {
    return (
      <svg
        viewBox="0 0 300 12"
        preserveAspectRatio="none"
        style={{
          position: "absolute",
          bottom: "-6px",
          left: 0,
          width: "100%",
          height: "12px",
          overflow: "visible",
        }}
      >
        <path
          d="M0,6 Q37.5,0 75,6 Q112.5,12 150,6 Q187.5,0 225,6 Q262.5,12 300,6"
          fill="none"
          stroke={color}
          strokeWidth="3.5"
          strokeLinecap="round"
          strokeDasharray="320"
          strokeDashoffset={drawn ? 0 : 320}
          style={{
            transition: `stroke-dashoffset 0.9s cubic-bezier(0.16,1,0.3,1) ${delay}ms`,
          }}
        />
      </svg>
    );
  }

  return (
    <svg
      viewBox="0 0 300 6"
      preserveAspectRatio="none"
      style={{
        position: "absolute",
        bottom: "-4px",
        left: 0,
        width: "100%",
        height: "10px",
        overflow: "visible",
      }}
    >
      <rect
        x="0"
        y="2"
        width="300"
        height="5"
        rx="3"
        fill={color}
        style={{
          transformOrigin: "left center",
          transform: drawn ? "scaleX(1)" : "scaleX(0)",
          transition: `transform 0.85s cubic-bezier(0.16,1,0.3,1) ${delay}ms`,
        }}
      />
    </svg>
  );
};

export default function HeroSection() {
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouse = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth - 0.5) * 14;
      const y = (e.clientY / window.innerHeight - 0.5) * 10;
      setMousePos({ x, y });
    };
    window.addEventListener("mousemove", handleMouse);
    return () => window.removeEventListener("mousemove", handleMouse);
  }, []);

  return (
    <div
      style={{
        minHeight: "70vh",
        background: "#ffffff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'Inter', system-ui, sans-serif",
        overflow: "hidden",
        position: "relative",
      }}
    >
      <style>{`
        /* Local fonts only — Inter loaded via index.css for offline support */
        * { box-sizing: border-box; margin: 0; padding: 0; }

        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(28px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes floatBlob {
          0%, 100% { transform: translateY(0px) scale(1); }
          50%       { transform: translateY(-18px) scale(1.04); }
        }
        .cta-btn {
          background: #0d1b2a;
          color: #fff;
          border: none;
          border-radius: 50px;
          padding: 16px 36px;
          font-size: 16px;
          font-weight: 700;
          font-family: inherit;
          letter-spacing: -0.2px;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 10px;
          transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s;
          box-shadow: 0 4px 20px rgba(13,27,42,0.18);
          animation: fadeUp 0.7s cubic-bezier(0.16,1,0.3,1) 0.7s both;
        }
        .cta-btn:hover {
          transform: translateY(-2px) scale(1.03);
          box-shadow: 0 8px 32px rgba(13,27,42,0.22);
          background: #1a2d42;
        }
        .cta-btn .arrow {
          width: 28px; height: 28px;
          background: rgba(255,255,255,0.12);
          border-radius: 50%;
          display: flex; align-items: center; justify-content: center;
          font-size: 15px;
          transition: transform 0.2s;
        }
        .cta-btn:hover .arrow { transform: translateX(3px); }

        .tag-pill {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          background: #fff8f0;
          border: 1.5px solid #FEC288;
          border-radius: 50px;
          padding: 7px 16px;
          font-size: 12.5px;
          font-weight: 600;
          color: #c05c00;
          letter-spacing: 0.3px;
          animation: fadeUp 0.7s cubic-bezier(0.16,1,0.3,1) 0s both;
          margin-bottom: 32px;
        }
        .tag-dot {
          width: 7px; height: 7px; border-radius: 50%;
          background: linear-gradient(135deg, #FA5C5C, #FD8A6B);
          flex-shrink: 0;
        }
      `}</style>

      {/* Ambient blobs */}
      <div
        style={{
          position: "absolute",
          top: "-80px",
          right: "-60px",
          width: "420px",
          height: "420px",
          background:
            "radial-gradient(circle, rgba(254,194,136,0.28) 0%, transparent 70%)",
          borderRadius: "50%",
          animation: "floatBlob 7s ease-in-out infinite",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: "-100px",
          left: "-80px",
          width: "500px",
          height: "500px",
          background:
            "radial-gradient(circle, rgba(250,92,92,0.12) 0%, transparent 70%)",
          borderRadius: "50%",
          animation: "floatBlob 9s ease-in-out infinite 1s",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: "30%",
          left: "5%",
          width: "260px",
          height: "260px",
          background:
            "radial-gradient(circle, rgba(0,168,232,0.07) 0%, transparent 70%)",
          borderRadius: "50%",
          pointerEvents: "none",
        }}
      />

      {/* Main content */}
      <div
        ref={containerRef}
        style={{
          textAlign: "center",
          padding: "0 24px",
          maxWidth: "900px",
          transform: `translate(${mousePos.x * 0.4}px, ${mousePos.y * 0.3}px)`,
          transition: "transform 0.5s cubic-bezier(0.23,1,0.32,1)",
        }}
      >
        {/* Tag */}
        <div className="tag-pill">
          <span className="tag-dot" />
          AI-Powered · Works Offline · Anywhere
        </div>

        {/* Headline row 1 */}
        <div
          style={{
            fontSize: "clamp(3rem, 9vw, 6.2rem)",
            fontWeight: 900,
            lineHeight: 1.0,
            color: "#0d1b2a",
            letterSpacing: "-0.04em",
            animation: "fadeUp 0.7s cubic-bezier(0.16,1,0.3,1) 0.1s both",
            marginBottom: "0.15em",
          }}
        >
          <span>organize </span>
          <span style={{ position: "relative", display: "inline-block" }}>
            everything
            <span
              style={{
                position: "absolute",
                bottom: "8px",
                left: "-4px",
                right: "-4px",
                height: "18px",
                background:
                  "linear-gradient(90deg, #FBEF76cc, #FEC288aa)",
                borderRadius: "3px",
                zIndex: -1,
                transformOrigin: "left",
                animation: "fadeIn 0.6s ease 1s both",
              }}
            />
          </span>
        </div>

        {/* Headline row 2 */}
        <div
          style={{
            fontSize: "clamp(3rem, 9vw, 6.2rem)",
            fontWeight: 900,
            lineHeight: 1.05,
            color: "#0d1b2a",
            letterSpacing: "-0.04em",
            animation: "fadeUp 0.7s cubic-bezier(0.16,1,0.3,1) 0.2s both",
            marginBottom: "1.1em",
          }}
        >
          <span>in your </span>
          <span
            style={{
              position: "relative",
              display: "inline-block",
              color: "#00a8e8",
            }}
          >
            learning
            <AnimatedUnderline color="#00a8e8" delay={900} style="wave" />
          </span>
        </div>

        {/* Subtext */}
        <p
          style={{
            fontSize: "clamp(0.95rem, 2vw, 1.1rem)",
            color: "#7a8598",
            fontWeight: 400,
            lineHeight: 1.65,
            maxWidth: "460px",
            margin: "0 auto 2.5rem",
            animation: "fadeUp 0.7s cubic-bezier(0.16,1,0.3,1) 0.45s both",
            letterSpacing: "0.1px",
          }}
        >
          AI-powered offline tutor that works anywhere, anytime
        </p>

        {/* CTA */}
        <Link to="/dashboard" className="cta-btn" style={{ textDecoration: "none" }}>
          Get Started
          <span className="arrow">→</span>
        </Link>

        {/* Social proof row */}
        <div
          style={{
            marginTop: "48px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "28px",
            animation: "fadeUp 0.7s cubic-bezier(0.16,1,0.3,1) 0.9s both",
          }}
        >
          {[
            { val: "Secure", label: "Cloud Sync" },
            { val: "AI-Powered", label: "Study Recommendations" },
            { val: "Offline", label: "Learning Support" },
          ].map((stat, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: "2px",
              }}
            >
              <span
                style={{
                  fontSize: "1.25rem",
                  fontWeight: 800,
                  background:
                    i === 0
                      ? "linear-gradient(135deg, #FA5C5C, #FD8A6B)"
                      : i === 1
                        ? "linear-gradient(135deg, #FD8A6B, #FEC288)"
                        : "linear-gradient(135deg, #FEC288, #FBEF76)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  letterSpacing: "-0.5px",
                }}
              >
                {stat.val}
              </span>
              <span
                style={{
                  fontSize: "11.5px",
                  color: "#9ca3af",
                  fontWeight: 500,
                  letterSpacing: "0.5px",
                }}
              >
                {stat.label}
              </span>
            </div>
          ))}

          <div
            style={{
              width: "1px",
              height: "32px",
              background: "#e5e7eb",
              margin: "0 4px",
            }}
          />

          {/* Avatars */}
          <div
            style={{ display: "flex", alignItems: "center", gap: "4px" }}
          >
            <div style={{ display: "flex" }}>
              {["#FA5C5C", "#00a8e8", "#FBEF76", "#FD8A6B"].map((c, i) => (
                <div
                  key={i}
                  style={{
                    width: "28px",
                    height: "28px",
                    borderRadius: "50%",
                    background: c,
                    border: "2.5px solid #fff",
                    marginLeft: i === 0 ? 0 : "-8px",
                    zIndex: 4 - i,
                    position: "relative",
                  }}
                />
              ))}
            </div>
            <span
              style={{
                fontSize: "12px",
                color: "#6b7280",
                fontWeight: 500,
                marginLeft: "6px",
              }}
            >
              Unlock your learning potential
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
