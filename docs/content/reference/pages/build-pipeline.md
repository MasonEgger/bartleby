---
title: "Build pipeline"
description: "The order of operations from config load to robots.txt write."
tags:
  - build
  - pipeline
---

Bartleby's build pipeline is a single function, `bartleby.build.build`, that runs in deterministic order. `async_build` wraps it in `asyncio.to_thread` so the CLI's `bartleby build` command can be called from async contexts (e.g. the dev server).

## Phases

1. **Load config** — parse `bartleby.yml`, apply defaults, validate cross-references
2. **Discover hooks** — glob `hooks/*.py`, register `on_<event>` functions
3. **Dispatch `on_config`** — let hooks modify the config
4. **Load authors** — parse `.authors.yml`
5. **Discover content** — walk `content/`, parse front matter, classify by content type
6. **Dispatch `on_pages`** — let hooks filter or augment the page list
7. **Filter drafts** — unless `--include-drafts`, drop pages with `draft: true`
8. **Validate metadata** — required fields, type checks, choice constraints, author references; fail fast on errors
9. **Generate URLs** — populate `page.output_url` for every page
10. **Build taxonomies** — collect term-to-page mappings
11. **Generate taxonomy pages** — virtual pages for each taxonomy index and term URL
12. **Generate listing pages** — per-content-type listings with optional pagination and intro content
13. **Build navigation** — explicit or auto-generated, plus prev/next linking
14. **Create markdown renderer** — Python-Markdown with default extensions and user overrides
15. **Create Jinja2 environment** — with the six-level template search path
16. **Dispatch `on_env`** — let hooks register filters/globals
17. **Load data files** — every YAML/TOML under `data/`
18. **Clean the output directory** — `site/` is removed and recreated
19. **Per-page render loop**:
    - Process shortcodes
    - Dispatch `on_page_markdown`
    - Render markdown to HTML
    - Calculate readtime and excerpt (if configured)
20. **Resolve cross-references** — rewrite `.md` links to output URLs
21. **Per-page template render loop**:
    - Resolve template name via the six-level cascade
    - Build template context
    - Render template
    - Dispatch `on_post_page`
    - Write HTML to `site/<url>/index.html`
22. **Copy theme static** — bundled CSS/JS to `site/`
23. **Copy user static** — `static/` over the theme assets (so users can override)
24. **Copy co-located assets** — follow each page's output URL
25. **Tree-shake icons** — scan rendered HTML, copy only referenced SVGs
26. **Write search index** — `site/search/search_index.json`
27. **Generate feeds** — RSS + Atom per content type that opts in
28. **Write Markdown variants** — `<url>/index.md` for every published page (if `ai.markdown_variants`)
29. **Write llms.txt** — structured site overview (if `ai.llms_txt`)
30. **Write llms-full.txt** — full body of every page (if `ai.llms_full_txt`)
31. **Write sitemap** — `sitemap.xml` and `sitemap.xml.gz`
32. **Write robots.txt** — unless `static/robots.txt` provides an override

## BuildResult

Returns a `BuildResult` dataclass:

```python
BuildResult(
    page_count=int,
    duration_seconds=float,
)
```

The CLI prints `Built N pages in T.TTs` on success.

## Plugin hook locations

The hook events that currently fire during a build:

- `on_config` — phase 3
- `on_pages` — phase 6
- `on_env` — phase 16
- `on_page_markdown` — phase 19 (per page)
- `on_post_page` — phase 21 (per page)

Other events are recognised by `discover_hooks` but their pipeline call sites are reserved for future steps.
