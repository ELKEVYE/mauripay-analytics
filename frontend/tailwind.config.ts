import type { Config } from "tailwindcss";

/**
 * MauriPay Analytics — design tokens.
 *
 * Five hues only:
 *   - a neutral off-white ground + white surfaces + hairline borders
 *   - `anchor`  : confident blue for primary actions and navigation
 *   - `accent`  : deep cyan — secondary chart series / marks only
 *   - `alert`   : one signal red, reserved for anomalies, fraud, and service errors
 *
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}", "./tests/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#F3F6FB",
        surface: "#FFFFFF",
        hairline: "#DFE6F0",
        ink: {
          DEFAULT: "#14243B",
          muted: "#52647C",
          faint: "#718198",
        },
        anchor: {
          DEFAULT: "#2457C5",
          strong: "#1C4196",
          weak: "#EBF1FF",
        },
        accent: {
          DEFAULT: "#0E7490",
          ink: "#155E75",
        },
        alert: {
          DEFAULT: "#B42332",
          weak: "#FFF0F1",
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', '"Segoe UI"', "system-ui", "-apple-system", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(20, 36, 59, 0.04), 0 1px 3px rgba(20, 36, 59, 0.06)",
        "card-hover": "0 2px 6px rgba(20, 36, 59, 0.06), 0 8px 20px -6px rgba(20, 36, 59, 0.10)",
        pop: "0 16px 40px -16px rgba(20, 36, 59, 0.22)",
      },
    },
  },
  plugins: [],
} satisfies Config;
