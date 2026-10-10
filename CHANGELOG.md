# Changelog

All notable changes to Bartleby are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed (Breaking)

The default theme is now `scrivener`, which replaces the old built-in look.
Set `theme.name: material` to keep an indigo, mkdocs-material style layout.

The `theme:` section of `bartleby.yml` now uses Bartleby-native names.
Old mkdocs-material names are a `ConfigError` that names the replacement.

| Old | New |
| --- | --- |
| `theme.features: navigation.tabs` | `nav.tabs` |
| `theme.features: navigation.sections` | `nav.sidebar` |
| `theme.features: navigation.indexes` | `nav.section-index` |
| `theme.features: navigation.top` | `nav.back-to-top` |
| `theme.palette` (for example `primary`, `accent`) | `theme.tokens` (for example `color.primary`, `color.accent`) |
| `theme.font` (for example `text`, `code`) | `theme.tokens` (for example `font.text`, `font.code`) |

The native feature names are `search`, `search.highlight`, `nav.tabs`, `nav.sidebar`, `nav.section-index`, `nav.back-to-top`, `content.code.copy`, and `color-mode.toggle`.
Any other mkdocs-material feature (`navigation.footer`, `navigation.tracking`, `content.code.annotate`, `content.code.select`, `content.tabs.link`, `content.tooltips`, `content.footnote.tooltips`, `content.action.edit`, `content.action.view`, `search.suggest`, `search.share`, `toc.follow`) is not a Bartleby feature and is rejected.

`page.excerpt` is now plain text, and the rendered excerpt moved to `page.excerpt_html`.
Listings render the HTML; feeds and `llms.txt` use the plain text.
A theme template that printed `post.excerpt | safe` must print `post.excerpt_html | safe`.

### Changed

Errors name the file, the key path or id, and a concrete fix, in one shape: `<file>: <key path>: <message> (fix: <hint>)`.
`bartleby.yml` now rejects unknown top-level keys, unknown metadata field types, and a non-list `choices`.
Invalid YAML in `bartleby.yml`, `.authors.yml`, `theme.yml`, and page front matter is a clean error, not a traceback.
A duplicated author id is an `author_error`.
A build with no `content/` directory fails and says how to fix it.
A page that would overwrite `schema.json` or `content-index.json` is an `agent_surface_error` with exit code 1.

`--quiet` hides warnings and the text confirmation of `new`, `build`, and `generate-skill`.
`--verbose` logs per-phase progress to stderr, and the two flags cannot be combined.
`ai.skills.regenerate_on_build` rewrites the skills after `bartleby build`.
`theme.logo` and `theme.favicon` render in all three bundled themes.
They are paths relative to `static/`, or full URLs.

`bartleby new site` writes a site that builds with no warnings on the default theme.
The scaffold sets `theme.name: scrivener` with seven native features and a Home and Blog nav.
It includes a published sample post with an author, a tag, and a description, and a Welcome home page that links to it.
`validate` and `lint` are clean on a fresh scaffold, and the quickstart and installation pages match what it prints.

`llms.txt` and `llms-full.txt` use absolute URLs, and each page summary is one line.
`urls.absolute_url` is the one place that builds an absolute URL, so the sitemap, feeds, SEO tags, `llms.txt`, and `content-index.json` agree.
`schema.json` has a `theme` block with the theme name, its `extends` chain, and three feature lists: `enabled`, `implemented`, and `active`.
`active` is the intersection and is the list an agent should rely on.
The four agent files are byte-identical across builds of the same content.

Generated skills (`bartleby-write`, `bartleby-review`, `bartleby-ops`) are built from the same introspection as `schema.json`.
They list real source directories, fields, authors, taxonomy terms, the active theme and its feature split, and commands with their real flags.
Generated skills contain no placeholders.

`export --include-html` returns real rendered HTML from the build's own render path.
During that export `on_startup` receives `"export"`, and the page hooks fire.

The public reference docs (hooks, config schema, template context, CLI, theme manifest, agent output formats) were corrected against the code.
`tests/test_docs_reference.py` compares 26 surfaces in both directions, so a change to code or docs that drifts apart fails the suite.
The docs site builds on the Scrivener theme, with a corrected listing, excerpt, and tag display, and a new `errors.md` reference page.

### Removed (Breaking)

`theme.color_mode.toggle` is a `ConfigError`.
The `color-mode.toggle` feature is the only switch for the light and dark toggle.
`ai.skills.include_examples` is a `ConfigError`, because generated skills never included examples.
`bartleby serve --dirty` is gone.
Incremental rebuilds are a non-goal, and the flag always ran a full rebuild.

### Added

- `theme.name`, `theme.path`, and `theme.package` select a theme; set at most one.
- `theme.tokens` is a flat map of dotted design-token names to CSS values.
- A feature enabled in `theme.features` that the active theme does not implement logs a build warning. The build still succeeds.
- The single hardwired `theme/` package is replaced by a theme system.
  A theme is a directory with a `theme.yml` manifest, and it can build on another theme with `extends`.
- Three themes ship with Bartleby.
  `base` holds the shared templates, scripts, and icons that every other theme builds on.
  `material` is an indigo header bar, navigation tabs, a section sidebar, and a table of contents, in the style of mkdocs-material.
  `scrivener` is the default: ruled paper, a serif reading column, and a double-rule margin, with a light and a dark palette.
- Both `material` and `scrivener` ship compiled CSS, so a site builds with no Tailwind install and no custom CSS.
  Each has a section sidebar that folds behind a toggle on narrow screens, search with `?h=` result highlighting, and a color-mode toggle.
- `bartleby theme eject` copies the active theme, flattened, into one editable directory (`themes/<name>` by default; `--to` and `--force` are available).
  Point `theme.path` at that directory and edit the templates directly.
- `bartleby theme inspect` lists every theme file with the layer that provides it, so you can see which files a project, an ejected theme, or a bundled theme supplies.

### Fixed

- Every published page has a Markdown variant, including pages with an empty body.
  The `text/markdown` alternate link renders only when the variant exists, so `ai.markdown_variants: false` no longer leaves a link that returns 404.
- JSON-LD is `Article` for posts, `CollectionPage` for generated listing and taxonomy pages, and `WebPage` otherwise.
  Each carries `name` alongside `headline`.
- Any build or `export --include-html` `BuildError` after `on_startup` now fires `on_build_error` and then `on_shutdown`, once each.
  That includes a missing `content/` directory, metadata validation, a strict-mode cross-reference failure, and an asset collision.
  Before, some of these skipped both, so a plugin that opened a resource in `on_startup` never got to release it.
- A successful `export --include-html` fires `on_shutdown` exactly once, as a build does.
- Relative `.md` links in a listing intro (`content/{type}/index.md`) now resolve to the target page's URL.
  Before, they were left as `.md` links that returned 404.
- Excerpts no longer show literal backticks and other Markdown syntax (see the breaking change for `page.excerpt` above).
- Taxonomy pages scoped to a content type are titled by their scope ("Tags in Guides"), so they no longer look like duplicates of the global tag pages.
- A listing row for a page without a date drops the date column in `scrivener`.
- Posts with no date, author, or reading time no longer render an empty meta paragraph under the title.
- Posts and listings in both bundled themes now get the section sidebar and table of contents that pages get.
  The sidebar needs the section's pages listed under it in `nav`, because `nav` keeps a content-type directory as one link.

## [0.1.0] - 2026-10-05

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
