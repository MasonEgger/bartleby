---
title: "URL Generation"
description: "Path-based defaults, url_format placeholders, and per-page overrides."
---

Bartleby assigns every page an `output_url` once, early in the build.
Cross-references, the sitemap, feeds, and the search index all read from that field.

## Default: Path-Based

Without any URL config, output URLs mirror the source path under `content/`:

| Source | Output URL |
|--------|------------|
| `content/index.md` | `/` |
| `content/about.md` | `/about/` |
| `content/blog/index.md` | `/blog/` |
| `content/blog/posts/my-post.md` | `/blog/posts/my-post/` |

URLs always end with a `/`.
Each non-index page lives in its own directory with an `index.html`.

## The `url_format` Option

A content type's `url_format` is a template string with placeholders:

```yaml
content_types:
  blog:
    path: blog/posts
    url_base: blog
    url_format: "{date:%Y/%m/%d}/{slug}"
```

A post dated 2026-03-01 in `my-post.md` lands at `/blog/2026/03/01/my-post/`.
The placeholders are `{slug}`, `{date:FORMAT}`, `{title}`, and `{categories}`.
If `url_format` references `{date}` but a page has no date, the build fails with a clear error.

## The `url_base` Option

`url_base` sets the URL prefix.
Without `url_format`, URLs become `/{url_base}/{slug}/`.
With `url_format`, the formatted template follows the base:

| Config | Source | Output URL |
|--------|--------|------------|
| `url_base: blog` | `blog/posts/my-post.md` | `/blog/my-post/` |
| `url_base: blog`, `url_format: "{date:%Y/%m/%d}/{slug}"` | `blog/posts/my-post.md` (2026-03-01) | `/blog/2026/03/01/my-post/` |

## Per-Page Overrides

Front matter can override URL behavior for a single page.
The `url`, `url_base`, and `slug` fields each change a different part of the result.
The [front matter fields reference](../reference/pages/front-matter-fields.md) describes them.

## Slug Rules

`python-slugify` produces slugs, with one Bartleby-specific change: `&` becomes `and`.
This matches Hugo and Jekyll, where "Tools & Tips" slugifies to `tools-and-tips` and not `tools-tips`.
