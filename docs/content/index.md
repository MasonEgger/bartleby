---
title: "Bartleby"
description: "A batteries-included Python static site generator built for humans and agents."
---

Bartleby is a Python static site generator.
It turns Markdown content into a fast, search-indexed, agent-readable website.
Bartleby has no plugin ecosystem to chase and no JavaScript build chain to maintain.
Feeds, sitemap, search, taxonomies, admonitions, JSON-LD, Open Graph tags, and `llms.txt` all ship in the core.

## Why Bartleby

Most static site generators treat AI agents as an afterthought.
Bartleby treats them as a first-class audience alongside human readers.
Bartleby publishes every page as HTML for browsers, Markdown for LLM crawlers, and JSON-LD for structured-data consumers.
The site root carries `llms.txt`, `llms-full.txt`, `schema.json`, and `content-index.json`, so an agent can learn the shape of the site without crawling it page by page.
A set of CLI commands gives coding agents the same view from the terminal, and `generate-skill` writes agent skills from your site's real schema.

For human authors, the surface area is small.
Write Markdown with YAML front matter, configure `bartleby.yml`, and run `bartleby build`.
Bartleby wires up the Markdown extensions, the theme, the feeds, and the search index by default.

## What's in the Box

- **Markdown rendering** with markwright, pymdownx, and the standard Python-Markdown extensions
- **Themes** selected by name, path, or package, with three bundled (`base`, `material`, and `scrivener`, the default), design tokens, `extends`, and `bartleby theme eject`
- **Search** through a JSON index that lunr.js reads client-side
- **Feeds** in RSS 2.0 and Atom 1.0, per content type and site-wide
- **Sitemap** (plain and gzipped) and `robots.txt` with AI crawler directives
- **SEO meta tags** for Open Graph, Twitter Card, and canonical URLs
- **Agent surface** with Markdown variants, `llms.txt`, `llms-full.txt`, JSON-LD, `schema.json`, and `content-index.json`
- **Taxonomies** with global and per-content-type listings
- **Pagination** for listing pages
- **Cross-references** that rewrite relative `.md` links to output URLs
- **Shortcodes** that use `[% ... %]` syntax for reusable Jinja2 fragments
- **Plugin hooks** from `hooks/*.py` or from installed packages
- **CLI** with `new`, `build`, `validate`, `lint`, `serve`, `render`, `schema`, `content`, `export`, `generate-skill`, and `theme`
- **Dev server** with change-driven rebuilds

## Where to Go Next

- [Installation](installation.md): install Bartleby with `uv` or `pip`
- [Quickstart](quickstart.md): build your first site in five minutes
- [Concepts](concepts/index.md): how Bartleby thinks about content, URLs, templates, and plugins
- [Guides](guides/index.md): task-oriented walkthroughs for common customizations
- [Reference](reference/index.md): lookup pages for config, CLI, and hook APIs
