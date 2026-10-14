// ABOUTME: Tailwind config for the scrivener theme: palette, type, dark mode, prose.
// ABOUTME: Colors and fonts read --bb-* token variables so theme.tokens can recolor it.
//
// Design direction (revised after the first-use review, 2026-10-10)
//
//   Source. Named for Melville's "Bartleby, the Scrivener". The first pass
//   leaned on the story (ruled foolscap, a red double margin rule, serif text,
//   italics); next to the unslop-ui checklist that read as generated
//   decoration. This pass keeps the name and drops the costume.
//
//   Rules. One accent color, used only for "you are here" (active tab,
//   current sidebar page, current TOC heading) and links. Hairline borders in
//   a neutral mix of the text color. No double rules, no margin bar, no
//   gradients, no shadows beyond the search modal, no icons in admonitions,
//   no italics outside quotes and captions.
//
//   Palette, light. Neutral paper, near-black ink, one blue.
//     paper     #FAFAF9   page background (--bb-color-bg)
//     surface   ink 4% over paper: code, panels, hover wash
//     ink       #1F2328   text and headings (--bb-color-text)
//     muted     ink 72% over paper: metadata, secondary text
//     ruling    ink 14% over paper: hairlines, table rows, borders
//     accent    #1F5FBF   current place, search marks (--bb-color-accent)
//     link      #1F5FBF   (--bb-color-primary)
//   Palette, dark.
//     paper     #16181D   (--bb-color-bg-dark)
//     ink       #E6E6E3   (--bb-color-text-dark)
//     accent    the light accent lifted toward #C2D6FF
//
//   Type. No webfonts. Text and ui share the system sans stack
//   (ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, ...);
//   headings are the same face at weight 600. Code uses "Cascadia Code",
//   "SF Mono", ui-monospace, Menlo, Consolas, monospace.
//     scale     1.0625rem (17px) body on a 1.75rem line; steps 0.8125, 0.9375,
//               1.0625, 1.3125, 1.625, 2.25rem. Measure 66ch.
//
//   Rhythm. One "ruling" of 1.75rem is the line height and the base unit. Block
//   spacing is whole rulings (1.75rem) or half rulings (0.875rem). Padding in
//   components uses the half ruling and its halves (0.4375rem).
//
//   Radius. 2px (--bb-radius).
//
//   Layout. Reading column 66ch; sidebar on the left in the ui face; table of
//   contents on the right, quiet. Left-aligned, ragged right.
//
//   markwright hooks. markwright emits class hooks and ships no CSS, so tailwind.css
//   styles them here: a muted marker wash for highlights, a header strip for fence
//   labels, a faint wash over the whole block per fence environment (the one place
//   several hues appear, since environments exist to be told apart), hairline
//   cards for embeds, ink-on-paper controls for the slideshow and image compare.
//
//   Overridable tokens: color.primary, color.accent, color.bg, color.text,
//   color.bg-dark, color.text-dark, font.text, font.ui, font.code, radius.
//   Dark mode is switched by [data-theme="dark"] on <html> (the color-mode toggle).

// Typography plugin
//   `prose` is themed through --tw-prose-* variables that point at the semantic
//   variables from tailwind.css, which flip with data-theme, so `prose-invert`
//   maps to the same values and stays in sync with dark mode.

const fs = require("fs");
const path = require("path");

// safelist.txt: one class per line, "#" starts a comment.
const safelist = fs
  .readFileSync(path.join(__dirname, "safelist.txt"), "utf8")
  .split("\n")
  .map((line) => line.trim())
  .filter((line) => line !== "" && !line.startsWith("#"));

const proseVariables = {
  "--tw-prose-body": "var(--sc-ink)",
  "--tw-prose-headings": "var(--sc-ink)",
  "--tw-prose-lead": "var(--sc-muted)",
  "--tw-prose-links": "var(--sc-link)",
  "--tw-prose-bold": "var(--sc-ink)",
  "--tw-prose-counters": "var(--sc-muted)",
  "--tw-prose-bullets": "var(--sc-muted)",
  "--tw-prose-hr": "var(--sc-ruling)",
  "--tw-prose-quotes": "var(--sc-muted)",
  "--tw-prose-quote-borders": "var(--sc-muted)",
  "--tw-prose-captions": "var(--sc-muted)",
  "--tw-prose-code": "var(--sc-ink)",
  "--tw-prose-pre-code": "var(--sc-ink)",
  "--tw-prose-pre-bg": "var(--sc-surface)",
  "--tw-prose-th-borders": "var(--sc-ink)",
  "--tw-prose-td-borders": "var(--sc-ruling)",
};

// Whole and half rulings; see the rhythm note above.
const ruling = "var(--sc-ruling-unit)";
const halfRuling = "calc(var(--sc-ruling-unit) / 2)";

/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["selector", '[data-theme="dark"]'],
  content: [],
  safelist,
  theme: {
    extend: {
      colors: {
        ink: "var(--sc-ink)",
        paper: "var(--sc-paper)",
        surface: "var(--sc-surface)",
        margin: "var(--sc-margin)",
        ruled: "var(--sc-ruling)",
      },
      fontFamily: {
        serif: [
          "var(--bb-font-text, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif)",
        ],
        ui: [
          "var(--bb-font-ui, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif)",
        ],
        mono: [
          "var(--bb-font-code, 'Cascadia Code', 'SF Mono', ui-monospace, Menlo, Consolas, monospace)",
        ],
      },
      borderRadius: {
        theme: "var(--sc-radius)",
      },
      typography: {
        DEFAULT: {
          css: {
            ...proseVariables,
            maxWidth: "66ch",
            fontSize: "1.0625rem",
            lineHeight: ruling,
            p: { marginTop: "0", marginBottom: ruling },
            "ul, ol": { marginTop: "0", marginBottom: ruling, paddingLeft: "1.5rem" },
            li: { marginTop: "0", marginBottom: "0" },
            "li > p": { marginTop: "0", marginBottom: "0" },
            h1: {
              fontWeight: "600",
              fontSize: "2.25rem",
              lineHeight: "calc(var(--sc-ruling-unit) * 1.5)",
              letterSpacing: "-0.015em",
              marginTop: "0",
              marginBottom: ruling,
            },
            h2: {
              fontWeight: "600",
              fontSize: "1.625rem",
              lineHeight: ruling,
              letterSpacing: "-0.01em",
              marginTop: "calc(var(--sc-ruling-unit) * 2)",
              marginBottom: ruling,
            },
            h3: {
              fontWeight: "600",
              fontSize: "1.3125rem",
              lineHeight: ruling,
              marginTop: "calc(var(--sc-ruling-unit) * 1.5)",
              marginBottom: halfRuling,
            },
            h4: {
              fontWeight: "600",
              fontSize: "1.0625rem",
              lineHeight: ruling,
              marginTop: ruling,
              marginBottom: halfRuling,
            },
            a: {
              fontWeight: "400",
              textDecoration: "underline",
              textDecorationThickness: "1px",
              textUnderlineOffset: "0.2em",
              textDecorationColor: "color-mix(in srgb, var(--sc-link) 45%, transparent)",
            },
            "a:hover": { color: "var(--sc-margin)", textDecorationColor: "var(--sc-margin)" },
            strong: { fontWeight: "600" },
            "code::before": { content: '""' },
            "code::after": { content: '""' },
            code: {
              backgroundColor: "var(--sc-surface)",
              padding: "0.05em 0.3em",
              border: "1px solid var(--sc-ruling)",
              borderRadius: "var(--sc-radius)",
              fontSize: "0.85em",
              fontWeight: "400",
            },
            "pre code": { backgroundColor: "transparent", border: "0", padding: "0", fontSize: "inherit" },
            pre: {
              marginTop: "0",
              marginBottom: ruling,
              padding: halfRuling,
              fontSize: "0.875rem",
              lineHeight: "1.5",
              borderRadius: "var(--sc-radius)",
              border: "1px solid var(--sc-ruling)",
            },
            blockquote: {
              fontStyle: "italic",
              fontWeight: "400",
              marginTop: "0",
              marginBottom: ruling,
              paddingLeft: ruling,
              borderLeftWidth: "2px",
              quotes: "none",
            },
            "blockquote p:first-of-type::before": { content: '""' },
            "blockquote p:last-of-type::after": { content: '""' },
            hr: { marginTop: ruling, marginBottom: ruling },
            table: {
              fontSize: "0.9375rem",
              lineHeight: "1.5",
              marginTop: "0",
              marginBottom: ruling,
              fontVariantNumeric: "tabular-nums",
              borderTop: "1px solid var(--sc-ink)",
              borderBottom: "1px solid var(--sc-ink)",
            },
            "thead th": {
              fontWeight: "600",
              paddingTop: "0.4375rem",
              paddingBottom: "0.4375rem",
            },
            "tbody td": { paddingTop: "0.4375rem", paddingBottom: "0.4375rem" },
            img: { marginTop: "0", marginBottom: ruling },
            figure: { marginTop: "0", marginBottom: ruling },
            figcaption: { fontStyle: "italic" },
          },
        },
        invert: { css: proseVariables },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
