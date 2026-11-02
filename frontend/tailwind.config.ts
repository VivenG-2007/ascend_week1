import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#12263F",
        teal: { 700: "#0F766E", 800: "#115E59" },
        mist: "#EEF2F6",
        amberink: "#92400E",
        amberwash: "#FEF3C7",
      },
      fontFamily: {
        // Nirmala UI (Windows) and Noto Sans Telugu (Android/Linux) render Telugu without a web-font download.
        sans: ['"Segoe UI"', '"Nirmala UI"', '"Noto Sans Telugu"', "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
