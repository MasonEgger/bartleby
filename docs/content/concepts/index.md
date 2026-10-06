---
title: "Concepts"
description: "How Bartleby thinks about content, URLs, templates, and plugins."
---

These pages explain the model Bartleby uses internally. Read them in order if you're new; jump straight to the one you need otherwise.

## Pages in this section

- [Content organization](content-organization.md) — how `content/`, content types, and co-located assets fit together
- [Front matter](front-matter.md) — standard fields, taxonomy values, and custom metadata
- [URL generation](urls.md) — path-based defaults, `url_format` placeholders, and per-page overrides
- [Markdown pipeline](markdown-pipeline.md) — the extensions Bartleby loads and the ordering that makes markwright + pymdownx coexist
- [Templates and the lookup cascade](templates.md) — the six-level template search Jinja2 walks for every page
- [Customization seams](customization-seams.md) — `overrides/`, `partials/`, `data/`, `shortcodes/`, and `hooks/`
- [Taxonomies](taxonomies.md) — collecting terms and generating taxonomy pages
- [Plugins and hooks](plugins-and-hooks.md) — file-based hook discovery and event dispatch
- [Agent integration](agents-and-llms.md) — why every page ships as Markdown and JSON-LD alongside HTML
