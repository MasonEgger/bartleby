---
title: "Build Pipeline"
description: "The order of operations from config load to robots.txt write."
tags:
  - build
  - pipeline
---

Bartleby's build pipeline is a single function, `bartleby.build.build`, that runs in a fixed order.
`async_build` runs the same function on a worker thread through `asyncio.to_thread`.
The CLI's `bartleby build` command calls `async_build`, and the dev server calls `build` directly.

The build renders into a temporary directory next to your project and swaps it into place only if every phase succeeds.
A failed build leaves the previous `site/` untouched.

## Phases

The numbered steps below group into five stages.

### Load Inputs

1. **Load config.** Parse `bartleby.yml`, apply defaults, and validate cross-references.
2. **Discover plugins and hooks.** Load installed plugins from the `bartleby.plugins` entry point group, then glob `hooks/*.py`.
3. **Dispatch startup events.** Fire `on_startup`, `on_config`, and `on_pre_build`.
4. **Load authors.** Parse `.authors.yml`.
5. **Resolve the theme.** Select the theme by `name`, `path`, or `package`, follow `extends` to build the chain, and warn about any enabled feature that no manifest in the chain declares.
6. **Discover content.** Walk `content/`, parse front matter, and classify pages by content type.

### Prepare Pages

7. **Filter drafts.** With `--include-drafts`, keep every page.
    Otherwise, drop pages with `draft: true` and the assets that belong only to them.
8. **Dispatch `on_files`.** Hooks can filter or augment the page list.
9. **Validate metadata.** Check required fields, types, choices, and author references.
    Any error fails the build.
10. **Generate URLs.** Set `page.output_url` for every page.
11. **Build taxonomies.** Collect term-to-page mappings.
12. **Generate taxonomy pages.** Create a virtual page for each taxonomy index and term at both scopes.
13. **Create the Markdown renderer.** Load the default extensions and your overrides.
14. **Generate listing pages.** Create one listing per content type, with its pagination pages, and add the intro content.
15. **Build navigation.** Use the explicit `nav` or generate one, link previous and next pages, then dispatch `on_nav`.
16. **Create the Jinja2 environment.** Put `overrides/`, `templates/`, the project root, and the theme chain on the search path, then dispatch `on_env`.
17. **Load data files.** Read every YAML and TOML file under `data/`.

### Render

18. **Render Markdown for each page.**
    - Dispatch `on_pre_page` and `on_page_read_source`.
    - Process shortcodes.
    - Dispatch `on_page_markdown`.
    - Render Markdown to HTML.
    - Dispatch `on_page_content`.
    - Compute reading time and the excerpt (plain text and HTML), if the content type enables them.
19. **Resolve cross-references.** Rewrite `.md` links to output URLs in page bodies, excerpts, and listing intros.
    With `--strict`, an unresolved link fails the build.
20. **Render templates for each page.**
    - Pick the template through the cascade.
    - Build the template context and dispatch `on_page_context`.
    - Render the template and dispatch `on_post_page`.
    - Write the HTML to `<url>/index.html`.
21. **Render `404.html`.** Use the theme's `404.html` template.

### Write Outputs

22. **Copy theme static files.** Take them from every layer of the theme chain.
23. **Copy project static files.** `static/` overwrites theme files of the same name.
24. **Apply compiled theme CSS.** Use `.bartleby/theme.css` when `bartleby theme compile` produced it and the file is current.
25. **Copy co-located assets.** Each asset follows its page's output URL.
26. **Tree-shake icons.** Scan the rendered HTML and templates, and copy only the SVGs they reference.
27. **Write the search index** to `search/search_index.json`.
28. **Generate feeds.** Write RSS and Atom files for content types that enable them, plus the site-wide feed.
29. **Write Markdown variants** to `<url>/index.md` for every published page, if `ai.markdown_variants` is on.
30. **Write `llms.txt`,** if `ai.llms_txt` is on.
31. **Write `llms-full.txt`,** if `ai.llms_full_txt` is on.
32. **Write the sitemap** as `sitemap.xml` and `sitemap.xml.gz`.
33. **Write `schema.json` and `content-index.json`,** if `ai.agent_surface` is on.
34. **Write `robots.txt`,** unless `static/robots.txt` exists.

### Finish

35. **Swap the output into place.** The temporary directory replaces `site/`. With `--dry-run`, Bartleby diffs it against the current `site/` and discards it.
36. **Dispatch `on_post_build` and `on_shutdown`.**

## BuildResult

`build` returns a `BuildResult` dataclass:

```python
BuildResult(
    page_count=int,
    duration_seconds=float,
    static_file_count=int,
    output_dir=str,
)
```

`static_file_count` counts theme static files, project static files, and co-located assets.
It leaves out generated files such as the search index, feeds, and sitemap.

On success, the CLI prints `Built N pages (S static files) into site/`.
With `--output json`, it prints a JSON object with `status`, `pages`, `static_files`, `duration_ms`, `warnings`, `errors`, and `output_dir`.

## Plugin Hook Locations

Fifteen of the 16 hook events fire during a build.
The sixteenth, `on_serve`, fires when the dev server starts.

| Event | Step |
|-------|------|
| `on_startup` | 3 |
| `on_config` | 3 |
| `on_pre_build` | 3 |
| `on_files` | 8 |
| `on_nav` | 15 |
| `on_env` | 16 |
| `on_pre_page` | 18 (per page) |
| `on_page_read_source` | 18 (per page) |
| `on_page_markdown` | 18 (per page) |
| `on_page_content` | 18 (per page) |
| `on_page_context` | 20 (per page) |
| `on_post_page` | 20 (per page) |
| `on_post_build` | 36 |
| `on_shutdown` | 36 |
| `on_build_error` | 18 or 20, when a page fails |

The [plugin hook reference](plugin-hooks.md) gives the signature of each event.
