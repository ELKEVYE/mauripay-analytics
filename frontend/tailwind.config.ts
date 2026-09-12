import type { Config } from "tailwindcss";

/**
 * MauriPay Analytics — design tokens.
 *
 * Five hues only:
 *   - a neutral off-white ground + white surfaces + hairline borders
 *   - `anchor`  : deep institutional green (Mauritanian financial identity)
 *   - `accent`  : muted Mauritanian gold — secondary chart series / marks only
 *   - `alert`   : one signal red, reserved exclusively for detected anomalies / fraud
 *
 * If `alert` shows up anywhere that is not a detected anomaly, it is a bug.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}", "./tests/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#F5F7F6",
        surface: "#FFFFFF",
        hairline: "#E4E7E5",
        ink: {
          DEFAULT: "#16211D",
          muted: "#5C6B65",
          faint: "#8A9A93",
        },
        anchor: {
          DEFAULT: "#0C5C4C",
          strong: "#0A4A3D",
          weak: "#EAF1EE",
        },
        accent: {
          DEFAULT: "#A67C3D",
          ink: "#7A5A28",
        },
        alert: {
          DEFAULT: "#B42318",
          weak: "#FBEAE8",
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', '"Segoe UI"', "system-ui", "-apple-system", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(20, 33, 29, 0.04), 0 1px 3px rgba(20, 33, 29, 0.06)",
        "card-hover": "0 2px 6px rgba(20, 33, 29, 0.06), 0 8px 20px -6px rgba(20, 33, 29, 0.10)",
        pop: "0 16px 40px -16px rgba(20, 33, 29, 0.22)",
      },
    },
  },
  plugins: [],
} satisfies Config;
