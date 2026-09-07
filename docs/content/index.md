---
title: "Bartleby"
description: "A batteries-included Python static site generator built for humans and agents."
---

Bartleby is a Python static site generator that takes Markdown content and turns it into a fast, search-indexed, agent-readable website — with no plugin ecosystem to chase and no JavaScript build chain to maintain. Every feature most documentation sites want — feeds, sitemap, search, taxonomies, syntax highlighting, admonitions, JSON-LD, Open Graph tags, llms.txt — ships in the core.

## Why Bartleby

Most static site generators treat AI agents as an afterthought. Bartleby treats them as a first-class audience alongside human readers. Every page is published as HTML for browsers, Markdown for LLM crawlers, and JSON-LD for structured-data consumers. The site root carries `llms.txt` and `llms-full.txt` so agents can navigate the corpus without crawling page-by-page.

For human authors, the surface area is small: write Markdown with YAML front matter, configure `bartleby.yml`, and run `bartleby build`. Everything else — the markdown extensions, the theme, the feeds, the search index — is wired up by default.

## What's in the box

- **Markdown rendering** with markwright, pymdownx, and the standard Python-Markdown extensions
- **Built-in Material-style theme** with Tailwind-friendly CSS, Alpine.js interactivity, and dark mode
- **Search** via a JSON index lunr.js consumes client-side
- **Feeds** — RSS 2.0 and Atom 1.0 per content type
- **Sitemap** + gzipped sitemap + robots.txt with AI crawler directives
- **SEO meta tags** — Open Graph, Twitter Card, canonical URLs
- **LLM output** — llms.txt, llms-full.txt, Markdown variants alongside every HTML page
- **Taxonomies** — global and per-content-type listings
- **Pagination** for listing pages
- **Cross-references** — relative `.md` links rewritten to output URLs
- **Shortcodes** — `[% ... %]` syntax for reusable Jinja2 fragments
- **Plugin hooks** via `hooks/*.py` — no entry points, no subclassing
- **CLI** with `new site`, `new post`, `build`, `validate`, `serve`
- **Dev server** with change-driven rebuilds

## Where to go next

- [Installation](installation.md) — install Bartleby with `uv` or `pip`
- [Quickstart](quickstart.md) — build your first site in five minutes
- [Concepts](concepts/index.md) — how Bartleby thinks about content, URLs, templates, and plugins
- [Guides](guides/index.md) — task-oriented walkthroughs for common customizations
- [Reference](reference/index.md) — exhaustive coverage of config, CLI, and hook APIs
