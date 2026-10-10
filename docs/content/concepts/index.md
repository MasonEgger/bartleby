---
title: "Concepts"
description: "How Bartleby thinks about content, URLs, templates, and plugins."
---

These pages explain the model Bartleby uses internally.
Read them in order if you're new.
Otherwise, jump straight to the one you need.

## Pages in This Section

- [Content organization](content-organization.md): how `content/`, content types, and co-located assets fit together
- [Front matter](front-matter.md): how Bartleby reads and validates the block at the top of a page
- [URL generation](urls.md): path-based defaults, `url_format`, and per-page overrides
- [Markdown pipeline](markdown-pipeline.md): the extensions Bartleby loads and the ordering that makes markwright and pymdownx coexist
- [Templates and the lookup cascade](templates.md): the template search Jinja2 walks for every page
- [Customization seams](customization-seams.md): the places where a project changes Bartleby without forking it
- [Taxonomies](taxonomies.md): collecting terms and generating taxonomy pages
- [Plugins and hooks](plugins-and-hooks.md): hook discovery and event dispatch
- [Agent integration](agents-and-llms.md): why every page ships as Markdown and JSON-LD alongside HTML, and what else agents get
