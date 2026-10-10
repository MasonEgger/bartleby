// ABOUTME: Tailwind config for the material theme: palette, type, dark mode, prose.
// ABOUTME: Colors and fonts read --bb-* token variables so theme.tokens can recolor it.
//
// Fidelity target
//   The look and layout of mkdocs-material: an indigo header bar, navigation
//   tabs under it, a left section sidebar, a right table of contents, and a
//   quiet reading column in a Roboto-style face. Visual intent was confirmed
//   against the mkdocs-material checkout; no CSS was copied (Bartleby
//   reimplements, it does not port).
//
// Palette decisions
//   primary  #3f51b5  Material indigo 500: header bar, links in light mode.
//   accent   #536dfe  Material indigo A200: hover, focus rings, active TOC entry.
//   light    white page, near-black text at roughly 87% opacity, muted text at 54%.
//   dark     "slate": #1e2129 page, #262a35 surfaces, text at 87% white. The
//            primary color keeps the header; links lighten toward white.
//   Every color is a CSS variable with a fallback, so an empty theme.tokens map
//   still renders. Overridable tokens: color.primary, color.accent, color.bg,
//   color.text, color.bg-dark, color.text-dark, font.text, font.code, radius.
//   Dark mode is switched by [data-theme="dark"] on <html> (the color-mode toggle).
//
// Type decisions
//   Roboto when installed, then the system UI stack (no webfont download).
//   Code uses Roboto Mono, then the system monospace stack. Prose copy is
//   0.9375rem on a 1.7 line height; top-level headings are light (300), as in
//   Material.
//
// Typography plugin
//   `prose` is themed through --tw-prose-* variables that point at the semantic
//   variables from tailwind.css. Because those variables flip with data-theme,
//   `prose-invert` maps to the same values and stays in sync with dark mode.

const fs = require("fs");
const path = require("path");

// safelist.txt: one class per line, "#" starts a comment.
const safelist = fs
  .readFileSync(path.join(__dirname, "safelist.txt"), "utf8")
  .split("\n")
  .map((line) => line.trim())
  .filter((line) => line !== "" && !line.startsWith("#"));

const proseVariables = {
  "--tw-prose-body": "var(--bm-text)",
  "--tw-prose-headings": "var(--bm-heading)",
  "--tw-prose-lead": "var(--bm-text-muted)",
  "--tw-prose-links": "var(--bm-link)",
  "--tw-prose-bold": "var(--bm-heading)",
  "--tw-prose-counters": "var(--bm-text-muted)",
  "--tw-prose-bullets": "var(--bm-text-faint)",
  "--tw-prose-hr": "var(--bm-border)",
  "--tw-prose-quotes": "var(--bm-text)",
  "--tw-prose-quote-borders": "var(--bm-accent)",
  "--tw-prose-captions": "var(--bm-text-muted)",
  "--tw-prose-code": "var(--bm-code-text)",
  "--tw-prose-pre-code": "var(--bm-text)",
  "--tw-prose-pre-bg": "var(--bm-code-bg)",
  "--tw-prose-th-borders": "var(--bm-border)",
  "--tw-prose-td-borders": "var(--bm-border)",
};

/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["selector", '[data-theme="dark"]'],
  content: [],
  safelist,
  theme: {
    extend: {
      colors: {
        primary: "var(--bm-primary)",
        "primary-dark": "var(--bm-primary-dark)",
        accent: "var(--bm-accent)",
        surface: "var(--bm-surface)",
        page: "var(--bm-bg)",
      },
      fontFamily: {
        sans: [
          "var(--bb-font-text, Roboto, -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif)",
        ],
        mono: [
          "var(--bb-font-code, 'Roboto Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace)",
        ],
      },
      borderRadius: {
        theme: "var(--bm-radius)",
      },
      typography: {
        DEFAULT: {
          css: {
            ...proseVariables,
            maxWidth: "none",
            fontSize: "0.9375rem",
            lineHeight: "1.7",
            h1: { fontWeight: "300", letterSpacing: "-0.01em" },
            h2: { fontWeight: "300", letterSpacing: "-0.01em" },
            h3: { fontWeight: "500" },
            a: { textDecoration: "none", fontWeight: "400" },
            "a:hover": { color: "var(--bm-accent)", textDecoration: "underline" },
            "code::before": { content: '""' },
            "code::after": { content: '""' },
            code: {
              backgroundColor: "var(--bm-code-bg)",
              padding: "0.1em 0.4em",
              borderRadius: "var(--bm-radius)",
              fontWeight: "400",
            },
            "pre code": { backgroundColor: "transparent", padding: "0" },
            pre: {
              borderRadius: "var(--bm-radius)",
              border: "1px solid var(--bm-border)",
            },
            "thead th": { fontWeight: "500" },
          },
        },
        invert: { css: proseVariables },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
