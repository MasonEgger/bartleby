# Bartleby

A batteries-included Python static site generator built for humans and agents.

Bartleby takes Markdown content and turns it into a fast, search-indexed, agent-readable website — with no plugin ecosystem to chase and no JavaScript build chain to maintain. Every feature most documentation sites want — feeds, sitemap, search, taxonomies, syntax highlighting, admonitions, JSON-LD, Open Graph tags, llms.txt — ships in the core.

## Why Bartleby

Most static site generators treat AI agents as an afterthought. Bartleby treats them as a first-class audience alongside human readers. Every page is published as HTML for browsers, Markdown for LLM crawlers, and JSON-LD for structured-data consumers. The site root carries `llms.txt` and `llms-full.txt` so agents can navigate the corpus without crawling page-by-page.

For human authors, the surface area is small: write Markdown with YAML front matter, configure `bartleby.yml`, and run `bartleby build`. Everything else — markdown extensions, theme, feeds, search index — is wired up by default.

## Quick start

```bash
uv pip install bartleby
bartleby new site mysite
cd mysite
bartleby new post "Hello world" --type blog
bartleby build
```

The rendered site lands in `mysite/site/`. For a live-reload preview, run `bartleby serve`.

## Features

- **Markdown** with do-markdown, pymdownx, and the standard Python-Markdown extensions
- **Built-in Material-style theme** with Tailwind-friendly CSS, Alpine.js interactivity, dark mode
- **Search** via a JSON index lunr.js consumes client-side
- **Feeds** — RSS 2.0 and Atom 1.0 per content type
- **Sitemap** + gzipped sitemap + robots.txt with AI crawler directives
- **SEO** — Open Graph, Twitter Card, canonical URLs
- **LLM output** — `llms.txt`, `llms-full.txt`, Markdown variants alongside every HTML page
- **Taxonomies** — global and per-content-type listings
- **Pagination** for listing pages
- **Cross-references** — relative `.md` links rewritten to output URLs
- **Shortcodes** — `[% ... %]` syntax for reusable Jinja2 fragments
- **Plugin hooks** via `hooks/*.py` — no entry points, no subclassing
- **CLI** with `new site`, `new post`, `build`, `validate`, `serve`
- **Dev server** with change-driven rebuilds

## Documentation

Full documentation lives in [`docs/`](docs/) and is itself a Bartleby site. Build it locally:

```bash
cd docs
uv run bartleby build
open site/index.html
```

Or read the source directly:

- [Installation](docs/content/installation.md)
- [Quickstart](docs/content/quickstart.md)
- [Concepts](docs/content/concepts/) — how Bartleby thinks about content, URLs, templates, and plugins
- [Guides](docs/content/guides/) — task-oriented walkthroughs
- [Reference](docs/content/reference/) — config, CLI, and hook APIs

## Status

Version 0.1.0. All 27 implementation steps from the original plan are complete; the project passes 272 tests under `ruff` strict and `mypy --strict`. A few items are intentionally deferred for follow-up releases:

- Real Tailwind CSS compilation (current stylesheet is hand-written structural CSS)
- Real Alpine.js, HTMX, and lunr.js vendor bundles (stubs are in place; the build pipeline emits the right `<script>` tags)
- Full icon pack vendoring (one sample SVG per pack ships today)
- ProcessPoolExecutor-based markdown parallelism (the `async_build` entry point exists; current implementation uses `asyncio.to_thread`)

## Development

```bash
git clone https://github.com/MasonEgger/bartleby.git
cd bartleby
uv sync
just check     # ruff lint + format, mypy strict, pytest
```

The `Justfile` exposes individual targets too: `just lint`, `just typecheck`, `just test`, `just format`.

## Architecture

Bartleby is 18 source modules under `src/bartleby/`, organised by build pipeline phase:

- **Config layer** — `config.py`, `authors.py`
- **Content layer** — `content.py`, `metadata.py`, `urls.py`
- **Rendering** — `markdown_pipeline.py`, `shortcodes.py`, `templates.py`, `crossrefs.py`
- **Structure** — `navigation.py`, `taxonomies.py`, `listings.py`, `pagination.py`
- **Output** — `search.py`, `feeds.py`, `sitemap.py`, `seo.py`, `llm.py`, `assets.py`, `icons.py`
- **Plugin system** — `plugins.py`
- **Orchestration** — `build.py`
- **Surfaces** — `cli.py`, `server.py`
- **Theme** — `theme/` package with templates, partials, static assets, icons

See [`spec.md`](spec.md) for the full specification and [`plan.md`](plan.md) for the 27-step implementation roadmap that produced this codebase.

## License

TBD.
