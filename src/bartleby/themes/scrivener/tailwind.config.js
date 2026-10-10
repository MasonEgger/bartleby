// ABOUTME: Tailwind config for the scrivener theme: palette, type, dark mode, prose.
// ABOUTME: Colors and fonts read --bb-* token variables so theme.tokens can recolor it.
//
// Design direction (Step 11, for Mason's reaction before Steps 12-14)
//
//   Source. Named for Melville's "Bartleby, the Scrivener": a law-copyist on
//   Wall Street, "pallidly neat, pitiably respectable, incurably forlorn", who
//   faces a dead brick wall and would prefer not to. The theme borrows the
//   scrivener's desk, not the story's gloom: ruled foolscap, iron-gall ink,
//   the red margin line, the ledger.
//
//   Three adjectives. Ruled, pallid, unhurried.
//
//   The one memorable thing: the double rule. A pair of thin lines
//   (3px double) is the theme's only ornament and it always means "this is
//   where you are". It runs down the left edge of the reading column like the
//   margin of legal foolscap, underlines the active tab, marks the current
//   page in the sidebar and the current heading in the table of contents, and
//   closes the header and footer like a ledger total. Nothing else is
//   decorated. No gradients, no shadows beyond the search modal, no icons in
//   admonitions, no pills.
//
//   Palette, light ("foolscap"). Cool ash paper, not cream.
//     paper     #EEF0EB   page background (--bb-color-bg)
//     surface   #F6F7F3   code, panels, hover wash
//     ink       #1B2231   text and headings, iron-gall blue-black (--bb-color-text)
//     muted     #566074   metadata, secondary text
//     ruling    #BCC8D6   ledger-blue hairlines under h2, table rows, borders
//     margin    #9B2C32   oxblood: the double rule, hover, search marks (--bb-color-accent)
//     link      #2A4B7C   iron blue (--bb-color-primary)
//   Palette, dark ("chambers by lamp").
//     paper     #151A22   (--bb-color-bg-dark)
//     surface   #1C222C
//     ink       #DCD9CE   warm bone (--bb-color-text-dark)
//     muted     #9AA3B2
//     ruling    #2E3745
//     margin    #D2666B   lifted oxblood
//     link      #93B3E0
//
//   Type. No webfonts; every stack is system-installed.
//     text      Charter, "Iowan Old Style", "Palatino Linotype", Palatino,
//               "Book Antiqua", Georgia, serif. Body and headings. Headings are
//               the same face at weight 600, so the page reads as one hand.
//     ui        "Gill Sans", "Gill Sans MT", Optima, Candara, "Segoe UI",
//               sans-serif. Navigation, metadata, buttons, tags. A humanist
//               sans reads as a clerk's lettering, not a product UI.
//     code      "Cascadia Code", "SF Mono", ui-monospace, Menlo, Consolas, monospace.
//     scale     1.0625rem (17px) body on a 1.75rem line; steps 0.8125, 0.9375,
//               1.0625, 1.3125, 1.625, 2.25rem. Measure 66ch.
//
//   Rhythm. One "ruling" of 1.75rem is the line height and the base unit. Block
//   spacing is whole rulings (1.75rem) or half rulings (0.875rem), so text
//   sits on the lines of a ruled page. Padding in components uses the half
//   ruling and its halves (0.4375rem).
//
//   Radius. 2px (--bb-radius). Cut paper, not rounded cards.
//
//   Layout. Reading column 66ch with the margin rule at its left; sidebar on
//   the left as an index in the ui face; table of contents on the right,
//   quiet. Left-aligned, ragged right, no justification.
//
//   Overridable tokens: color.primary, color.accent, color.bg, color.text,
//   color.bg-dark, color.text-dark, font.text, font.ui, font.code, radius.
//   Dark mode is switched by [data-theme="dark"] on <html> (the color-mode toggle).
//
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
          "var(--bb-font-text, Charter, 'Iowan Old Style', 'Palatino Linotype', Palatino, 'Book Antiqua', Georgia, serif)",
        ],
        ui: [
          "var(--bb-font-ui, 'Gill Sans', 'Gill Sans MT', Optima, Candara, 'Segoe UI', sans-serif)",
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
              paddingBottom: "0.2rem",
              borderBottom: "1px solid var(--sc-ruling)",
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
              fontStyle: "italic",
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
              borderLeftWidth: "3px",
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
              fontStyle: "italic",
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
