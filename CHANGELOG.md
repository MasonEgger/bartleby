# Changelog

All notable changes to Bartleby are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

Remediation cycle addressing 20 confirmed findings from a multi-agent code review of the v1 branch (R1 through R17 in `spec.md`; some requirements cover more than one defect). R2 through R17 (19 findings) were code or test fixes; R1 was re-verified on the project's pinned Python 3.14 and dispositioned as not-a-defect (see below).

- R1 (CLI importability) does not reproduce on Python 3.14: PEP 758 legalizes the unparenthesized `except` tuple in `linting.py`, so the CLI already imports cleanly on the pinned interpreter and `linting.py` is left unchanged. An import-health regression gate (`tests/test_import_health.py`) was added so a real future import or syntax error in any module still fails the suite.
- `bartleby theme compile` always failed on a clean machine because the release checksum map was empty.
- CLI failures could surface a raw Python traceback instead of a clean, structured error.
- `bartleby serve` now serves the configured `output_dir`, not a hardcoded `site/`, and live reload is fully wired: a watchdog observer triggers rebuilds and a WebSocket channel reloads the browser.
- Cross-references now resolve before the lint orphan pass runs, so a page linked only via a `.md` crossref is no longer reported as orphaned.
- Draft pages and their co-located assets are excluded from production output everywhere, including the previously-missed shared-directory asset path; two pages sharing a bundle directory with a co-located asset now fail the build loudly instead of guessing an association.
- JSON-LD output is valid even when a page title contains characters that could break naive string interpolation (embedded quotes, `<`, `>`, `&`).
- Icon pack defaults merge with project overrides instead of being replaced by them.
- Listing intro content (`content/{type}/index.md`) now renders as HTML instead of being dropped.
- Shortcode protection covers multi-backtick inline code spans, not just single-backtick ones.
- Shortcode discovery checks all three documented lookup locations instead of only one.
- The aggregate site-wide feed is advertised in `schema.json`.
- The `hooks/` `sys.path` insertion is scoped to the discovery loop instead of leaking into the rest of the process.
- The temporary build directory is always cleaned up, including on a failed build.
- `static_file_count` counts only files actually copied, not every candidate considered.
- The end-to-end smoke test now exercises a custom `output_dir`, a draft page with a co-located asset, and a quoted title through both a build and a serve cycle, so this class of regression fails the smoke gate again if it recurs.

## [0.1.0] - 2026-06-23

First public release. Bartleby builds Markdown content into a static site with
search, feeds, taxonomies, an LLM-readable output layer, and an agent CLI.

### Added

#### Content and rendering

- Markdown rendering via Python-Markdown, pymdownx, and do-markdown, with the
  do-markdown fence preprocessor ordered ahead of pymdownx superfences.
- YAML front matter parsing into typed dataclasses, with author resolution and
  byline support.
- Co-located page assets (Hugo-style page bundles) that follow the page output
  URL rather than the source path.
- Shortcodes via `[% ... %]` syntax backed by Jinja2 fragments.
- Cross-references: relative `.md` links rewritten to output URLs.
- Five-level template lookup cascade with per-page `template:` overrides.
- Taxonomies (global and per-content-type), listing pages, and pagination.

#### Theme

- Built-in Material-style theme with dark mode.
- Vendored Alpine.js, HTMX, and lunr.js bundles with recorded versions and
  licenses (`THIRD-PARTY-NOTICES`).
- Hybrid Tailwind pipeline: package-built CSS shipped by default, with a
  `bartleby theme compile` command that resolves, caches, and SHA-256-verifies
  the standalone Tailwind CLI. The build prefers a compiled `.bartleby/theme.css`
  with no implicit download.
- Full icon packs with build-time tree-shaking; unused packs emit zero files.

#### Output layer

- Client-side search backed by a JSON index consumed by lunr.js.
- RSS 2.0 and Atom 1.0 feeds per content type plus a site-wide aggregate feed
  (`site.feed`) with contextual auto-discovery.
- Sitemap (plus gzipped variant) and `robots.txt` with AI-crawler directives.
- SEO output: Open Graph, Twitter Card, canonical URLs, JSON-LD.
- LLM output: `llms.txt`, `llms-full.txt`, and a Markdown variant alongside
  every HTML page.
- Standalone `404.html`.
- Static agent surface: `schema.json` and `content-index.json`, with curated
  public fields, per-page alternate links, and an `ai.agent_surface` toggle.

#### Plugin system

- All 16 plugin hook events fire with the documented arguments and return-value
  semantics; `BasePlugin` exposes matching no-op methods.
- Plugin discovery from `hooks/*.py` and from `bartleby.plugins` entry points,
  merged through one registration path with priority-then-registration ordering
  and a config disable list. Hook files can import sibling helper modules.

#### CLI and agent surface

- Commands: `new site`, `new post`, `build`, `validate`, `serve`, `theme
  compile`, `schema`, `content list`, `content get`, `render`, `lint`, `export`,
  `generate-skill`.
- `--output json` on every command, with stable result shapes and exit codes.
- `build --dry-run` reports what would be written without touching the output
  directory.
- Schema introspection for content types, authors, and taxonomies (public
  author fields only).
- `lint` checks broken links, missing descriptions, and orphan pages, with
  opt-in `--check-external`.
- `export` to JSONL, JSON, and CSV; deterministic skill generation.

#### Dev server

- Live reload with full rebuild on change across all watched paths, hook and
  config reload, last-good-build retention on failure, and an `--events` JSON
  stream. Reload wiring is serve-only and absent from production builds.

#### Build semantics

- Per-page errors are collected rather than failing on the first; the existing
  output directory is left untouched on failure and replaced via an atomic swap
  on success. Config errors fail fast.
- Clean error reporting (no traceback) with `BARTLEBY_DEBUG` to re-enable
  tracebacks; `on_build_error` fires once with the collected list.
- Configurable output directory (no longer hardcoded to `site/`).
- `validate` dry-runs URL generation and checks template existence for
  `template:` overrides and cross-references.

### Project

- Licensed under MIT.
- Python 3.14+, managed with uv; ruff, mypy (strict), and pytest for quality.

[Unreleased]: https://github.com/MasonEgger/bartleby/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/MasonEgger/bartleby/releases/tag/v0.1.0
