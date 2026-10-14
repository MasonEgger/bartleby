---
title: "Bartleby"
description: "A batteries-included Python static site generator built for humans and agents."
---

Bartleby is a Python static site generator.
It turns Markdown content into a fast, search-indexed, agent-readable website.
Bartleby has no plugin ecosystem to chase and no JavaScript build chain to maintain.
Feeds, sitemap, search, taxonomies, admonitions, JSON-LD, Open Graph tags, and `llms.txt` all ship in the core.

## Why Bartleby

Bartleby publishes every page as HTML for browsers, Markdown for LLM crawlers, and JSON-LD for structured-data consumers.
The site root carries `llms.txt`, `llms-full.txt`, `schema.json`, and `content-index.json`, so an agent can learn the shape of the site without crawling it page by page.
A set of CLI commands gives coding agents the same view from the terminal, and `generate-skill` writes agent skills from your site's real schema.

For human authors, the surface area is small.
Write Markdown with YAML front matter, configure `bartleby.yml`, and run `bartleby build`.
Bartleby wires up the Markdown extensions, the theme, the feeds, and the search index by default.

## What's in the Box

Markdown is rendered with markwright, pymdownx, and the standard Python-Markdown extensions.
Three themes ship in the package: `scrivener` (the default), `material`, and the shared `base` they both extend.
A theme is selected by name, path, or package, carries its design tokens, and can be composed with `extends` or copied whole with `bartleby theme eject`.

Search runs client-side from a JSON index that lunr.js reads.
Feeds come in RSS 2.0 and Atom 1.0, per content type and site-wide.
The build also writes a plain and a gzipped sitemap, a `robots.txt` with AI crawler directives, and Open Graph, Twitter Card, and canonical meta tags on every page.

The agent surface is a Markdown variant of every page, `llms.txt`, `llms-full.txt`, JSON-LD, `schema.json`, and `content-index.json`.

Taxonomies get global and per-content-type listings, and listing pages paginate.
Relative `.md` links are rewritten to their output URLs.
Shortcodes use `[% ... %]` syntax for reusable Jinja2 fragments, and plugin hooks load from `hooks/*.py` or from installed packages.

The CLI covers `new`, `build`, `validate`, `lint`, `serve`, `render`, `schema`, `content`, `export`, `generate-skill`, and `theme`.
The dev server rebuilds when a file changes.

## Where to Go Next

- Install Bartleby with `uv` or `pip` in [Installation](installation.md).
- Build your first site in five minutes with the [Quickstart](quickstart.md).
- Read [Concepts](concepts/index.md) for how Bartleby thinks about content, URLs, templates, and plugins.
- Follow the [Guides](guides/index.md) for task-oriented walkthroughs of common customizations.
- Look things up in the [Reference](reference/index.md) pages for config, CLI, and hook APIs.
