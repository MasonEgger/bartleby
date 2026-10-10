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

### `jsonld`

The page's JSON-LD block as a serialized string.
The `partials/jsonld.html` partial in the `base` theme prints it inside a `<script type="application/ld+json">` tag.

## Global Functions

### `feature(name)`

Returns `True` when `name` is in the site's `theme.features` list.
Themes use it to switch markup on and off:

```jinja2
{% if feature('search') %}
  {% include "partials/search_trigger.html" %}
{% endif %}
```
