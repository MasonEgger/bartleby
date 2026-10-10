---
title: "Taxonomies"
description: "How Bartleby collects terms across pages and generates taxonomy listing pages."
---

A taxonomy is a named axis along which you categorize content.
`tags` and `categories` are the usual ones, but you can declare any name.
Bartleby collects term-to-page mappings across the build and generates listing pages at a global scope and at a per-content-type scope.

## Declaring Taxonomies

Define the axis at the site level, then opt content types in:

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

A content type that does not opt in to `tags` contributes no `tags` values to any tag index.

## Tagging a Page

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

## Generated Pages

For every taxonomy, Bartleby generates pages at two scopes.

**Global**

- `/tags/` lists every tag across the site.
- `/tags/python/` lists every page tagged `python`.

**Per content type**

- `/blog/tags/` lists the tags used by blog pages.
- `/blog/tags/python/` lists every blog page tagged `python`.

The same applies to every taxonomy a content type opts in to.
Both scopes come from the same opt-in, so a content type that uses `tags` always gets its own tag pages as well as a share of the global ones.

The scoped pages carry the content type in their titles, so they read as different pages.
The global index is "Tags" and the blog's is "Tags in Blog".
A term page is "Tags: python" globally and "Tags in Blog: python" for the blog.
The back link on a scoped term page reads "All tags in blog".

## Slug Formats

Each taxonomy's `slug_format` is a template applied to the slugified term.
The default, `"{slug}"`, uses the slug as is.
A format like `"tag:{slug}"` produces URLs such as `/tags/tag:temporal-workflows/`, which is useful for namespacing.

## Sorting

Pages within a term sort newest-first by `page.date`.
Pages without dates come after dated pages.

## Templates

Term pages and index pages use their own template types, `taxonomy` and `taxonomy_index`.
For a term page that belongs to a content type, the lookup tries these names in order:

1. `{content_type}/taxonomy/{name}.html`
2. `{content_type}/taxonomy.html`
3. `{content_type}/base.html`
4. `defaults/taxonomy.html`
5. `taxonomy.html`, then `page.html`

An index page skips the first name, and uses `taxonomy_index` in place of `taxonomy` in the rest.
Global pages have no content type, so they start at `defaults/`.
Each name is looked up in your `overrides/` and `templates/` directories first, then in the theme chain.

The page's `custom_metadata` carries `taxonomy_name`, `taxonomy_kind` (`"index"` or `"term"`), and, for term pages, `taxonomy_term`.
