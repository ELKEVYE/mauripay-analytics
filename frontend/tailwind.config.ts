import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}", "./tests/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1f2933",
        "mauri-green": "#1f7a5b",
        "mauri-gold": "#c99a2e",
        "mauri-red": "#b23b3b",
        "panel": "#f7f8fa"
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "Arial", "sans-serif"]
      }
    },
  },
  plugins: [],
} satisfies Config;
