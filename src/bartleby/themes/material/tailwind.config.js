// ABOUTME: Tailwind config for the material theme: palette, type, dark mode, prose.
// ABOUTME: Colors and fonts read --bb-* token variables so theme.tokens can recolor it.
//
// Fidelity target
//   The look and layout of mkdocs-material: a colored header bar, navigation
//   tabs under it, a left section sidebar, a right table of contents, and a
//   quiet reading column in a Roboto-style face. Visual intent was confirmed
//   against the mkdocs-material checkout; no CSS was copied (Bartleby
//   reimplements, it does not port).
//
// Palette decisions
//   primary  #1f801f  forest green (CSS forestgreen #228b22 at 92% per channel,
//            same hue): header bar and buttons. forestgreen itself is 4.39:1
//            under white text, short of WCAG AA for normal text; this shade
//            is 5.04:1.
//   link     primary at 80% toward black (#196619), so links on the white page
//            and on the #f5f5f5 surface are 7.10:1 and 6.52:1.
//   accent   #2e7d32  a softer green for hover, focus rings, and the active TOC
//            entry; 5.13:1 on white, 4.70:1 on the surface.
//   links    always underlined (1px). The link green is 2.27:1 against the body
//            text, under the 3:1 a color-only link needs (WCAG 1.4.1, G183), so
//            the underline carries the distinction and hover changes the color.
//   light    white page, near-black text at roughly 87% opacity; muted text is
//            the text at 68% into the page (4.5:1 or better on every surface it
//            sits on), faint text at 50% (3:1, for bullets and rules only).
//   dark     "slate": #1e2129 page, #262a35 surfaces, text at 87% white. The
//            primary color keeps the header; links go to #6fbf6f and the accent
//            to #8fd48f, lighter forest greens that read on the dark page.
//   tests/test_theme_contrast.py pins each pair's ratio.
//   Every color is a CSS variable with a fallback, so an empty theme.tokens map
//   still renders. Overridable tokens: color.primary, color.accent, color.bg,
//   color.text, color.bg-dark, color.text-dark, font.text, font.code, radius.
//   Dark mode is switched by [data-theme="dark"] on <html> (the color-mode toggle).
//
// markwright hooks
//   markwright emits class hooks and ships no CSS, so tailwind.css styles them
//   here: a translucent yellow marker for highlights, a title bar for fence
//   labels, a block washed with one hue per fence environment (no left rule,
//   the same as the admonitions), surface cards for embeds, and round primary
//   controls with a small elevation for the slideshow and image compare.
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
            a: {
              textDecoration: "underline",
              textDecorationThickness: "1px",
              textUnderlineOffset: "0.15em",
              fontWeight: "400",
            },
            "a:hover": { color: "var(--bm-accent)" },
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
