---
title: "Concepts"
description: "How Bartleby thinks about content, URLs, templates, and plugins."
---

These pages explain the model Bartleby uses internally.
Read them in order if you're new.
Otherwise, jump straight to the one you need.

## Pages in This Section

- [Content organization](content-organization.md) covers how `content/`, content types, and co-located assets fit together.
- [Front matter](front-matter.md) covers how Bartleby reads and validates the block at the top of a page.
- [URL generation](urls.md) covers the path-based defaults, `url_format`, and per-page overrides.
- [Markdown pipeline](markdown-pipeline.md) lists the extensions Bartleby loads and the ordering that lets markwright and pymdownx coexist.
- [Templates and the lookup cascade](templates.md) walks the template search Jinja2 runs for every page.
- [Customization seams](customization-seams.md) names the places where a project changes Bartleby without forking it.
- [Taxonomies](taxonomies.md) explains how terms are collected and taxonomy pages generated.
- [Plugins and hooks](plugins-and-hooks.md) explains hook discovery and event dispatch.
- [Agent integration](agents-and-llms.md) explains why every page ships as Markdown and JSON-LD alongside HTML, and what else agents get.
