import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./features/**/*.{ts,tsx}",
    "./providers/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-ibm-plex-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-ibm-plex-mono)", "monospace"],
      },
      colors: {
        base: "#080b12",
        surface: "#0f1520",
        card: "#141c2e",
        "card-hover": "#1a2338",
        border: "rgba(255,255,255,0.08)",
        "border-strong": "rgba(255,255,255,0.15)",
        ink: {
          DEFAULT: "#e8ecf4",
          secondary: "#8a93b2",
          muted: "#4a5068",
        },
        ai: {
          DEFAULT: "#0fd4b0",
          dim: "rgba(15,212,176,0.15)",
          glow: "rgba(15,212,176,0.08)",
        },
        signal: {
          blue: "#3b82f6",
          "blue-dim": "rgba(59,130,246,0.15)",
          green: "#22c55e",
          "green-dim": "rgba(34,197,94,0.15)",
          red: "#ef4444",
          "red-dim": "rgba(239,68,68,0.15)",
          amber: "#f59e0b",
          "amber-dim": "rgba(245,158,11,0.15)",
        },
      },
      backgroundImage: {
        "grid-faint":
          "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
      },
      backgroundSize: {
        grid: "48px 48px",
      },
      keyframes: {
        "pulse-ai": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.4" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "pulse-ai": "pulse-ai 2s ease-in-out infinite",
        "slide-up": "slide-up 0.3s ease-out",
        "fade-in": "fade-in 0.2s ease-out",
        shimmer: "shimmer 1.5s infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;