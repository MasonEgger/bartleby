---
title: "URL generation"
description: "Path-based defaults, url_format placeholders, and per-page overrides."
---

Bartleby gives every page an `output_url` exactly once during the build. Cross-references, sitemap, feeds, and the search index all read from that field.

## Default: path-based

Without any URL config, output URLs mirror the source path under `content/`:

| Source | Output URL |
|--------|------------|
| `content/index.md` | `/` |
| `content/about.md` | `/about/` |
| `content/blog/index.md` | `/blog/` |
| `content/blog/posts/my-post.md` | `/blog/posts/my-post/` |

URLs always end with a trailing `/`; each non-index page lives in its own directory with an `index.html`.

## url_format placeholders

A content type's `url_format` is a template string with placeholders:

```yaml
content_types:
  blog:
    path: blog/posts
    url_base: blog
    url_format: "{date:%Y/%m/%d}/{slug}"
```

A post dated 2026-03-01 named `my-post.md` lands at `/blog/2026/03/01/my-post/`.

Supported placeholders:

- `{slug}` — the filename stem (or front matter `slug` override) slugified
- `{date:FORMAT}` — strftime format applied to `page.date`
- `{title}` — slugified page title
- `{categories}` — the first category, slugified

If `url_format` references `{date}` but the page has no date, the build fails with a clear error.

## url_base

`url_base` controls the prefix. When set without `url_format`, URLs become `/{url_base}/{slug}/`. When set with `url_format`, the formatted template is appended after the base:

| Config | Source | Output URL |
|--------|--------|------------|
| `url_base: blog` | `blog/posts/my-post.md` | `/blog/my-post/` |
| `url_base: blog`, `url_format: "{date:%Y/%m/%d}/{slug}"` | `blog/posts/my-post.md` (2026-03-01) | `/blog/2026/03/01/my-post/` |

## Per-page overrides

Front matter can override URL behaviour:

- `url: custom/path` — replaces the generated URL entirely
- `url_base: articles` — replaces just the base prefix; `url_format` still applies
- `slug: custom-slug` — overrides the filename-derived slug

## Slug rules

Slugs are produced by `python-slugify` with one Bartleby-specific tweak: `&` becomes `and`. This matches Hugo and Jekyll conventions, where "Tools & Tips" should slugify to `tools-and-tips` rather than `tools-tips`.
