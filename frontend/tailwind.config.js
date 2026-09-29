/** @type {import('tailwindcss').Config} */

// Palettes are backed by CSS variables (defined in src/index.css) so that the
// light and dark themes share one set of class names. Switching theme only
// redefines the variables, so no component needs to know which theme is active.
//
// Values are raw "R G B" channel triplets so that Tailwind's opacity modifier
// (e.g. bg-slate-900/60) keeps working via the <alpha-value> placeholder.

const shade = (name) => `rgb(var(${name}) / <alpha-value>)`;

const family = (prefix, shades) =>
  Object.fromEntries(shades.map((s) => [s, shade(`--${prefix}-${s}`)]));

const SLATE = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950];
const FIVE = [100, 200, 300, 400, 500];
const FOUR = [200, 300, 400, 500];
const THREE = [300, 400, 500];

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      colors: {
        slate: family("slate", SLATE),
        cyan: family("cyan", THREE),
        amber: family("amber", FIVE),
        emerald: family("emerald", FOUR),
        rose: family("rose", FOUR),
        sky: family("sky", THREE),
        violet: family("violet", THREE),
      },
    },
  },
  plugins: [],
};
