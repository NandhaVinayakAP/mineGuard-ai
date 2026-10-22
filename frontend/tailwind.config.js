/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: "#0B2545",
          light: "#13355E",
          dark: "#071A33",
        },
        teal: {
          DEFAULT: "#0F8B8D",
          light: "#57BFC1",
          dark: "#0A6567",
        },
        warn: {
          DEFAULT: "#E8792D",
          light: "#F2A05F",
        },
        crit: {
          DEFAULT: "#D64545",
          light: "#E87A7A",
        },
        panel: "#F5F6F8",
        line: "#E2E5EA",
        ink: "#1E2530",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(11,37,69,0.06), 0 1px 6px rgba(11,37,69,0.06)",
      },
    },
  },
  plugins: [],
};
