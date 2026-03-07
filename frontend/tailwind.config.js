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
        deep: "#05070a",
        "surface-light": "var(--surface-light)",
        "glass-border": "var(--glass-border)",
        "accent-blue": "#00A8E8",
        primary: "#ffffff",
        muted: "var(--text-muted)",
        subtle: "var(--text-subtle)",
        success: "#22c55e",
        error: "#ef4444",
        warn: "#f59e0b",
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
