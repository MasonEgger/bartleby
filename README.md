# Bartleby

An agents-first, batteries-included Python static site generator: every page published for humans and the agents that read them.

Bartleby takes Markdown content and turns it into a fast, search-indexed, agent-readable website, with no plugin ecosystem to chase and no JavaScript build chain to maintain. Every feature most documentation sites want (feeds, sitemap, search, taxonomies, syntax highlighting, admonitions, JSON-LD, Open Graph tags, llms.txt) ships in the core.

## Why Bartleby

Most static site generators treat AI agents as an afterthought. Bartleby treats them as a first-class audience alongside human readers. Every page is published as HTML for browsers, Markdown for LLM crawlers, and JSON-LD for structured-data consumers. The site root carries `llms.txt` and `llms-full.txt` so agents can navigate the corpus without crawling page-by-page.

For human authors, the surface area is small: write Markdown with YAML front matter, configure `bartleby.yml`, and run `bartleby build`. Everything else (Markdown extensions, theme, feeds, search index) is wired up by default.

## Quick start

```bash
uv pip install bartleby-ssg
bartleby new site mysite
cd mysite
bartleby serve
```

`new site` lists what it created and the next command:

```text
Created site at mysite/
  README.md
  bartleby.yml
  content/
  hooks/
  static/
  templates/
Next: cd mysite && bartleby serve
```

`serve` builds the site, prints its URL, and rebuilds and reloads the browser each time you save a file:

```text
Built 2 pages (12 static files) into site/
Serving at http://127.0.0.1:8000/
Press Ctrl+C to stop
```

The scaffold is a docs-shaped site: a home page that says what to do next, and a feature tour that shows each Markdown feature as its source followed by the result.
Its `bartleby.yml` is small, with the site title and URL, the nav, and the theme features.
`bartleby build` writes the rendered site to `mysite/site/`.

Add what you need as you go:

- `bartleby new site --full-config mysite` writes every option Bartleby accepts, each at its default with a one-line comment.
- `bartleby new site --blog mysite` starts with a blog and a sample post.
- `bartleby enable blog news` adds a blog to an existing site, and `bartleby disable news` turns it off.
  Each enabled blog publishes its own RSS and Atom feeds, plus one combined feed for the site.
- `bartleby config show`, `config get`, `config set`, and `--set key.path=value` read and change config without opening the file.

New posts are drafts until you set `draft: false` in the front matter.

The default theme is `scrivener`.
Set `theme.name: material` in `bartleby.yml` to switch to the Material look.

## Features

- **Markdown** with markwright, pymdownx, and the standard Python-Markdown extensions
- **Three bundled themes**: `scrivener` (the default), `material`, and the shared `base`; compiled CSS ships in the wheel, so no Tailwind install is needed
- **Theme system**: select a theme by `theme.name`, `theme.path`, or `theme.package`; compose with `extends`; `bartleby theme eject` and `bartleby theme inspect` expose every file
- **Dark mode** and a light/dark toggle in every bundled theme
- **Search** via a JSON index lunr.js consumes client-side
- **Feeds**: RSS 2.0 and Atom 1.0 per content type
- **Sitemap** + gzipped sitemap + robots.txt with AI crawler directives
- **SEO**: Open Graph, Twitter Card, canonical URLs, JSON-LD
- **Agent output**: `llms.txt`, `llms-full.txt`, `schema.json`, `content-index.json`, and a Markdown variant alongside every published page
- **Generated skills**: `bartleby generate-skill` writes write, review, and ops skills from your site's real shape
- **Taxonomies**: global and per-content-type listings
- **Pagination** for listing pages
- **Cross-references**: relative `.md` links rewritten to output URLs
- **Shortcodes**: `[% ... %]` syntax for reusable Jinja2 fragments
- **Plugin hooks**: 16 events, from `hooks/*.py` or `bartleby.plugins` entry points
- **CLI** with `new`, `build`, `validate`, `serve`, `schema`, `content`, `render`, `lint`, `export`, `generate-skill`, `theme`, `config`, `enable`, and `disable`; every command takes `--output json`
- **Dev server** on Starlette and uvicorn, with change-driven rebuilds and live reload on the same port

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
- [Concepts](docs/content/concepts/): how Bartleby thinks about content, URLs, templates, and plugins
- [Guides](docs/content/guides/): task-oriented walkthroughs
- [Reference](docs/content/reference/): config, CLI, and hook APIs

The plugin hooks, the `bartleby.yml` schema, the template context and base-theme blocks, the theme manifest and feature names, the `bartleby` commands and flags, and the agent output formats are stable for 0.x, and the CHANGELOG calls out any breaking change to them.

## Status

Version 0.1.0 is on PyPI as `bartleby-ssg`.
The branch after it replaces the single hardwired theme with a theme system and three bundled themes, rewrites the error messages, makes the scaffold a docs-shaped site with a feature tour, adds a three-column docs layout, a `config` command group, `enable` and `disable` for content types, and a dev server with same-port live reload, fixes the agent files and generated skills, and documents the public interfaces.
`just check` runs ruff lint and format, mypy strict on `src/`, the full pytest suite, and an end-to-end smoke test.
See the [CHANGELOG](CHANGELOG.md) for the full list, including the breaking changes to `theme:` config.

A few items are intentionally deferred:

- Parallel build; the build is synchronous and documented as such
- Incremental rebuilds (the dev server always runs a full rebuild)
- `bartleby migrate mkdocs`, a one-shot config converter
- Additional bundled themes beyond `base`, `material`, and `scrivener`

## Development

```bash
git clone https://github.com/MasonEgger/bartleby.git
cd bartleby
uv sync
just check     # ruff lint + format, mypy strict, pytest, e2e smoke
```

The `Justfile` exposes individual targets too: `just lint`, `just typecheck`, `just test`, `just smoke`, `just format`.

## Architecture

Bartleby is 34 source modules under `src/bartleby/`, organised by build pipeline phase:

- **Config layer**: `config.py`, `authors.py`, `errors.py`
- **Content layer**: `content.py`, `metadata.py`, `urls.py`, `content_query.py`
- **Rendering**: `markdown_pipeline.py`, `shortcodes.py`, `templates.py`, `crossrefs.py`
- **Structure**: `navigation.py`, `taxonomies.py`, `listings.py`, `pagination.py`
- **Output**: `search.py`, `feeds.py`, `sitemap.py`, `seo.py`, `llm.py`, `assets.py`, `icons.py`, `output.py`
- **Agent surface**: `agent_surface.py`, `schema_introspection.py`, `skills.py`, `export.py`, `linting.py`
- **Theme**: `theme_loader.py`, `theme_compile.py`, and the bundled themes under `themes/` (`base`, `material`, `scrivener`)
- **Plugin system**: `plugins.py`
- **Orchestration**: `build.py`
- **Surfaces**: `cli.py`, `server.py`

See [`spec.md`](spec.md) for the full specification.

## License

MIT. See [`LICENSE`](LICENSE) for the full text.
Bundled code and design inspiration are credited in [`ACKNOWLEDGMENTS.md`](ACKNOWLEDGMENTS.md).
