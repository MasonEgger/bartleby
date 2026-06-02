---
title: "Templates and the lookup cascade"
description: "How Bartleby decides which Jinja2 template renders each page."
---

Every page goes through a six-level template lookup. The first match wins. This lets users override individual theme templates without forking the whole theme.

## The six-level cascade

For a page of "template type" `<kind>` (typically `post`, `list`, `page`, `taxonomy`, or `taxonomy_index`):

1. **Front matter `template` field** — explicit per-page override
2. **`overrides/<name>`** at the project root — for replacing theme templates
3. **`templates/{content_type}/{kind}.html`** — content-type-specific layout
4. **`templates/{content_type}/base.html`** — content-type base
5. **`templates/defaults/{kind}.html`** — site-wide default
6. **Built-in theme fallback** — the templates shipped with Bartleby

The Jinja2 environment searches these roots in order: `overrides/` → `templates/` → the project directory itself → the bundled theme. Including the project directory in the search path is what makes `{% include "partials/banner.html" %}` resolve naturally.

## Template context

Every template receives the same context object:

| Key | Type | Notes |
|-----|------|-------|
| `site` | dict | `title`, `url`, `description`, `author`, `default_image`, `twitter` |
| `page` | dict | Current page — `title`, `content`, `url`, `date`, `description`, `authors`, `readtime`, `toc`, `previous`, `next`, `taxonomies` |
| `nav` | list | `NavItem` tree from the resolved navigation |
| `pages` | list | All pages in the build |
| `taxonomies` | dict | `{"global": ..., "by_content_type": ...}` |
| `config` | BartlebyConfig | The full parsed config |
| `build` | dict | `date`, `bartleby_version` |
| `data` | dict | Contents of every YAML/TOML file under `data/`, keyed by stem |
| `extra_css` | list | Paths from `config.extra_css` for rendering `<link>` tags |
| `extra_js` | list | Paths from `config.extra_js` for rendering `<script>` tags |
| `seo` | dict | `{"og": ..., "twitter": ..., "canonical": ...}` |

## Per-page template override

In front matter:

```yaml
---
title: "Special landing page"
template: campaigns/launch.html
---
```

Bartleby will look for `templates/campaigns/launch.html`, then `overrides/campaigns/launch.html`, then the bundled theme. Use this for one-off page layouts that don't justify a new content type.
