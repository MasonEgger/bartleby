---
title: "Template context"
description: "Every variable available inside a Jinja2 template."
tags:
  - templates
---

The context dict returned by `build_page_context` is unpacked into every template render. Variables below are always present.

## Top-level keys

### site

The site config, exposed as a dict for template-friendly attribute access.

```jinja2
{{ site.title }}
{{ site.url }}
{{ site.description }}
{{ site.author }}
{{ site.default_image }}
{{ site.twitter }}
```

### page

The current page being rendered. Always a dict (not the underlying `Page` dataclass) so `page.title` works in Jinja2.

| Field | Type | Notes |
|-------|------|-------|
| `title` | string | Required for every page |
| `description` | string \| null | |
| `date` | date \| null | |
| `content` | string | Rendered HTML body |
| `url` | string | The output URL (with trailing `/`) |
| `readtime` | int \| null | Set when content type has `readtime: true` |
| `excerpt` | string | Rendered excerpt, empty when not configured |
| `authors` | list[string] | Author keys (resolve via `data` or your own lookup) |
| `taxonomies` | dict[string, list[string]] | E.g. `{"tags": ["python"]}` |
| `toc` | list | Table of contents entries from the markdown render |
| `previous` | Page \| null | Previous page in nav order |
| `next` | Page \| null | Next page in nav order |

### nav

The resolved navigation as a list of `NavItem` objects. Each item has `title`, `url`, `children`, `page`, `is_section`.

```jinja2
{% for item in nav %}
  {% if item.url %}<a href="{{ item.url }}">{{ item.title }}</a>
  {% else %}<span>{{ item.title }}</span>{% endif %}
{% endfor %}
```

### pages

All pages in the build (real + generated taxonomy/listing pages).

### taxonomies

Mapping with two scopes:

```python
{
  "global": {"tags": TaxonomyData, "categories": TaxonomyData, ...},
  "by_content_type": {"blog": {"tags": TaxonomyData}, ...},
}
```

Each `TaxonomyData` has `name`, `terms` (dict keyed by term name), and `content_type` (None for global).

### config

The full parsed `BartlebyConfig` dataclass. Use this for accessing theme settings, AI toggles, etc.

### build

```python
{
  "date": datetime.date,        # build timestamp
  "bartleby_version": str,      # the running Bartleby version
}
```

### data

Files from `data/`, keyed by stem. See [Customization seams](../../concepts/customization-seams.md).

### extra_css / extra_js

Lists of paths from `config.extra_css` / `config.extra_js`. Templates render `<link>` and `<script>` tags from these:

```jinja2
{% for css in extra_css %}
<link rel="stylesheet" href="/{{ css.lstrip('/') }}">
{% endfor %}
```

### seo

Pre-built SEO payload:

```python
{
  "og": {"og:title": ..., "og:description": ..., "og:type": ..., ...},
  "twitter": {"twitter:card": ..., "twitter:title": ..., ...},
  "canonical": "https://example.com/page-url/",
}
```

The bundled `partials/seo_meta.html` iterates these to emit the right `<meta>` tags.
