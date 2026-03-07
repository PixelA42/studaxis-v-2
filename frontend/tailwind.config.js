/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      /* Thermal Vitreous design tokens — .kiro/DOCS_NEW/ARCHITECTURE_NEW.md */
      colors: {
        deep: "var(--deep)",
        "surface-light": "var(--surface-light)",
        "glass-border": "var(--glass-border)",
        "accent-blue": "#00A8E8",
        primary: "var(--text-primary)",
        muted: "var(--text-muted)",
        subtle: "var(--text-subtle)",
        success: "#22c55e",
        error: "#ef4444",
        warn: "#f59e0b",
        /* Pastel accent palette */
        "pastel-pink": "#FFB5C5",
        "pastel-blue": "#A8D8EA",
        "pastel-yellow": "#FFEAA7",
        "heading-dark": "#000000",
        "main-light": "#0F172A",
        /* Warm accent palette (solid-card aesthetic) */
        "accent-warm-1": "#FA5C5C",
        "accent-warm-2": "#FD8A6B",
        "accent-warm-3": "#FEC288",
        "accent-warm-4": "#FBEF76",
        /* Chunky color blocks — use as large solid fills */
        "chunk-pink": "#FA5C5C",
        "chunk-coral": "#FD8A6B",
        "chunk-peach": "#FEC288",
        "chunk-yellow": "#FBEF76",
        "chunk-blue": "#00A8E8",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      backdropBlur: {
        glass: "24px",
      },
      boxShadow: {
        glass: "0 8px 32px 0 rgba(0, 0, 0, 0.2)",
        "glass-subtle": "0 4px 24px -4px rgba(0, 0, 0, 0.15)",
        "card": "0 10px 25px -5px rgba(0, 0, 0, 0.08)",
        soft: "0 20px 60px -15px rgba(0, 0, 0, 0.15), 0 10px 30px -10px rgba(0, 0, 0, 0.1)",
        "soft-light": "0 25px 70px -20px rgba(15, 23, 42, 0.12), 0 12px 35px -12px rgba(15, 23, 42, 0.08)",
      },
      borderRadius: {
        card: "16px",
      },
      fontWeight: {
        anchor: "700",
        "anchor-bold": "800",
      },
      width: {
        sidebar: "var(--sidebar-width)",
        "sidebar-collapsed": "var(--sidebar-width-collapsed)",
      },
      backgroundImage: {
        "ambient-glow":
          "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(0, 168, 232, 0.08), transparent)",
      },
    },
  },
  plugins: [],
};
