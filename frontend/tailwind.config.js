/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}", "./node_modules/@foundry/ui/src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b1016", panel: "#121a24", panel2: "#16202c", line: "#243141",
        cy: "#7dd3fc", vi: "#0ea5e9", ind: "#38bdf8", prism: "#0ea5e9",
        ink: "#e7eef6", dim: "#93a4b6", faint: "#657688",
        ok: "#22c55e", warn: "#f4b860", bad: "#ef4444",
      },
      boxShadow: {
        glow: "0 0 40px -10px rgba(14,165,233,0.40)",
      },
    },
  },
  plugins: [],
};
