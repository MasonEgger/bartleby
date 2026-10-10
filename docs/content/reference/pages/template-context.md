---
title: "Template Context"
description: "Every variable available inside a Jinja2 template."
tags:
  - templates
---

Bartleby builds one context for each page and unpacks it into the template render.
The keys below are always present.

## Top-Level Keys

### `site`

The site config, as a dict.

```jinja2
{{ site.title }}
{{ site.url }}
{{ site.description }}
{{ site.author }}
{{ site.default_image }}
{{ site.twitter }}
```

### `page`

The page being rendered.
It is the `Page` object itself, so every attribute is reachable in a template.

| Attribute | Type | Notes |
|-----------|------|-------|
| `title` | string | The page title |
| `description` | string or null | |
| `date` | date or null | |
| `content` | string | Rendered HTML body |
| `url` | string | The output URL, with a trailing `/` |
| `readtime` | int or null | Set when the content type has `readtime: true` |
| `excerpt` | string | The excerpt as plain text, with the Markdown syntax removed. Feeds and `llms.txt` use it. Empty when the content type has no `excerpt_separator`. |
| `excerpt_html` | string | The same excerpt rendered to HTML. Listing templates use it. |
| `authors` | list | `Author` objects with `key`, `name`, `description`, `avatar`, and `url`. An unknown key stays a plain string. |
| `taxonomies` | dict of lists | For example `{"tags": ["python"]}` |
| `taxonomy_links` | dict of lists | The same terms as links. Each entry has `term` and `url`, for example `{"tags": [{"term": "python", "url": "/blog/tags/python/"}]}`. A post in a content type links to that type's term page, which lists its siblings. A page outside any content type links to the global term page. `url` is null when the term has no page, so check it before building an anchor. |
| `custom_metadata` | dict | Front matter fields that are neither standard nor taxonomy names |
| `toc` | list | Table of contents entries from the Markdown render |
| `previous`, `next` | Page or null | Neighbors in navigation order |
| `content_type_name` | string or null | The page's content type |
| `draft` | bool | The draft flag |
| `source_path` | path | The source file, relative to `content/`. Generated pages use a path that starts with `__generated__`. |
| `abs_source_path` | path | The source file's absolute path |
| `generated` | bool | `true` for a listing or taxonomy page that the build created, `false` for a page read from `content/` |
| `raw_content` | string | The Markdown body after the front matter, before shortcodes run |
| `rendered_content` | string | Rendered HTML body. `content` is the same value. |
| `output_url` | string | The output URL. `url` is the same value. |
| `author_keys` | list of strings | The `authors` front matter keys, before Bartleby resolves them into `authors` |
| `taxonomy_values` | dict of lists | The taxonomy terms from front matter. `taxonomies` is the same value. |
| `template_override` | string or null | The `template` front matter value |
| `url_override` | string or null | The `url` front matter value |
| `url_base_override` | string or null | The `url_base` front matter value |
| `slug_override` | string or null | The `slug` front matter value |

To read a custom field:

```jinja2
{% if page.custom_metadata.difficulty %}
<span class="difficulty difficulty-{{ page.custom_metadata.difficulty }}">
  {{ page.custom_metadata.difficulty }}
</span>
{% endif %}
```

### `nav`

The resolved navigation, a list of `NavItem` objects.
Each item has `title`, `url`, `children`, `page`, `is_section`, and `index_url`.

```jinja2
{% for item in nav %}
  {% if item.url %}<a href="{{ item.url }}">{{ item.title }}</a>
  {% else %}<span>{{ item.title }}</span>{% endif %}
{% endfor %}
```

### `pages`

Every page in the build, including generated taxonomy and listing pages.

### `taxonomies`

A mapping with two scopes:

```python
{
  "global": {"tags": TaxonomyData, "categories": TaxonomyData, ...},
  "by_content_type": {"blog": {"tags": TaxonomyData}, ...},
}
```

Each `TaxonomyData` has `name`, `terms` (a dict keyed by term name), and `content_type` (`None` for the global scope).
Each term is a `TaxonomyTerm` with `name`, `slug`, `pages` (the pages that carry the term), and `count`.

### `config`

The full parsed `BartlebyConfig`.
Templates read theme settings from `config.theme`, which has `name`, `features`, `tokens`, `color_mode`, `icon_packs`, `logo`, and `favicon`.
`color_mode` holds only `default`, and `logo` and `favicon` are root-relative URLs or `None`.
The bundled themes render them, so a custom header can include `partials/logo.html` to show the logo.
They read the AI toggles from `config.ai`.

### `build`

```python
{
  "date": datetime.date,        # build date
  "bartleby_version": str,      # the running Bartleby version
}
```

`date` is the build date, and `bartleby_version` is the version of the running Bartleby.

### `data`

Files from `data/`, keyed by file stem.
See [Customization seams](../../concepts/customization-seams.md).

### `extra_css` and `extra_js`

Lists of the paths from `config.extra_css` and `config.extra_js`.
Templates render `<link>` and `<script>` tags from them:

```jinja2
{% for css in extra_css %}
<link rel="stylesheet" href="/{{ css.lstrip('/') }}">
{% endfor %}
```

### `seo`

A prebuilt SEO payload:

```python
{
  "og": {"og:title": ..., "og:description": ..., "og:type": ..., ...},
  "twitter": {"twitter:card": ..., "twitter:title": ..., ...},
  "canonical": "https://example.com/page-url/",
}
```

The `partials/seo_meta.html` partial in the `base` theme loops over these values to emit the `<meta>` tags.

### `feed_links`

A list of `{type, href, title}` dicts, one for each feed that applies to the page.
The base layout renders them as `<link rel="alternate">` tags.

### `markdown_url`

The root-relative URL of the page's Markdown variant, such as `/blog/posts/first/index.md`, or `None` when the page has no variant.
The `base` layout renders `<link rel="alternate" type="text/markdown">` only when this value is set, so the link and the file always agree.

### `jsonld`

The page's JSON-LD block as a serialized string.
The `partials/jsonld.html` partial in the `base` theme prints it inside a `<script type="application/ld+json">` tag.

## Listing Pages

A listing page is a generated page, one per content type, or one per pagination page when the type enables pagination.
It renders with the `list` template type.
The context is the one above, and the page's `custom_metadata` carries these keys:

| Key | Type | Notes |
|-----|------|-------|
| `listing_kind` | string | Always `content_type` |
| `posts` | list of Page | The content type's published pages, newest first. With pagination, only the pages on this listing page. |
| `intro_content` | string | The HTML of `content/<type>/index.md`, or an empty string. With pagination, only the first listing page has it. |
| `paginator` | PaginatorPage | Present only when the content type enables pagination |

A `PaginatorPage` has `items`, `page_number`, `total_pages`, `has_next`, `has_prev`, `next_url`, `prev_url`, and `page_range`.
`next_url` and `prev_url` are `None` at the ends of the range.

## Taxonomy Pages

A taxonomy page is a generated page for a taxonomy index or for one term, at the global scope and at each content type's scope.
An index renders with the `taxonomy_index` template type and a term page with the `taxonomy` type.
The page's `custom_metadata` carries these keys:

| Key | Type | Notes |
|-----|------|-------|
| `taxonomy_name` | string | The taxonomy, such as `tags` |
| `taxonomy_kind` | string | `index` or `term` |
| `taxonomy_term` | string | The term name. Term pages only. |
| `posts` | list of Page | The pages that carry the term. Term pages only. |

## Global Functions

### `feature(name)`

Returns `True` when `name` is in the site's `theme.features` list.
Themes use it to switch markup on and off:

```jinja2
{% if feature('search') %}
  {% include "partials/search_trigger.html" %}
{% endif %}
```
