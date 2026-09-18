---
title: "Taxonomies"
description: "Collecting terms across pages and generating taxonomy listing pages."
---

A taxonomy is a named axis along which you categorise content — `tags`, `categories`, `authors`, anything you declare. Bartleby collects term-to-page mappings across the build and generates listing pages at both global and per-content-type scopes.

## Declaring taxonomies

Define the axis at site level, then opt content types in:

```yaml
taxonomies:
  tags:
    slug_format: "{slug}"
  categories:
    slug_format: "{slug}"

content_types:
  blog:
    path: blog/posts
    taxonomies:
      - tags
      - categories
  tutorials:
    path: tutorials/posts
    taxonomies:
      - tags
```

A content type that doesn't opt into `tags` won't contribute its `tags` front matter values to the global tag index.

## Tagging a page

Use the taxonomy name as a front matter key:

```yaml
---
title: "Deploy with Temporal"
tags:
  - python
  - temporal
categories:
  - devops
---
```

## Generated pages

At build time Bartleby generates two scopes of pages per taxonomy:

**Global**
- `/tags/` — index page listing every tag across the site
- `/tags/python/` — every page tagged `python`

**Per content type**
- `/blog/tags/` — index for blog tags
- `/blog/tags/python/` — every blog post tagged `python`

The same applies for any taxonomy a content type opts into.

## Slug formats

Each taxonomy's `slug_format` is a template applied to the slugified term. The default `"{slug}"` just uses the slug as-is. A format like `"tag:{slug}"` produces URLs like `/tags/tag:temporal-workflows/` — useful for namespacing.

## Sorting

Pages within a term are sorted newest-first by `page.date`. Pages without dates appear after dated pages.

## Templates

Taxonomy pages use a dedicated template type. The lookup order is:

1. `templates/{content_type}/taxonomy/{name}.html`
2. `templates/{content_type}/taxonomy.html`
3. `templates/defaults/taxonomy.html`
4. The bundled theme's `taxonomy.html` / `taxonomy_index.html`

Each page's context includes `page.custom_metadata.taxonomy_name`, `taxonomy_kind` (`"index"` or `"term"`), and (for term pages) `taxonomy_term`.
