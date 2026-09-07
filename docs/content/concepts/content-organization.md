---
title: "Content organization"
description: "How Bartleby discovers, classifies, and ships your content."
---

Every Bartleby site has a `content/` directory at its root. Bartleby walks that tree and turns every Markdown file into a page; every non-Markdown file becomes a co-located asset that travels with its associated page.

## Directory layout

```
mysite/
├── bartleby.yml
├── .authors.yml
├── content/
│   ├── index.md            # The site root (/)
│   ├── about.md            # Static page (/about/)
│   ├── blog/
│   │   ├── index.md        # Optional intro for the /blog/ listing
│   │   └── posts/
│   │       ├── first-post.md
│   │       └── diagram.png # Co-located asset
│   └── tutorials/
│       ├── index.md
│       └── posts/
│           └── deploy.md
├── templates/              # Optional template overrides
├── static/                 # Site-wide static files copied to /
└── hooks/                  # Optional Python hook modules
```

## Content types

A content type is a named group of pages with shared behaviour. You declare one in `bartleby.yml`:

```yaml
content_types:
  blog:
    path: blog/posts
    readtime: true
    excerpt_separator: "<!-- more -->"
    taxonomies:
      - tags
```

Any Markdown file under `content/blog/posts/` becomes a `blog` page. The `path` field is the only required setting. Other options:

- `readtime: true` — calculate estimated reading time and expose it as `page.readtime` in templates
- `excerpt_separator: "<!-- more -->"` — split posts at this marker for listing excerpts
- `taxonomies: [tags]` — opt this content type in to the listed site taxonomies
- `feeds: [rss, atom]` — emit per-type syndication feeds
- `pagination: { enabled: true, per_page: 10 }` — paginate the listing page
- `metadata: { ... }` — validate per-type front matter (see [front matter](front-matter.md))

Pages outside any declared content type are treated as static pages. They get URLs but no listing page, no feed, and no readtime calculation.

## Listing pages

Each content type automatically gets a listing page at its base URL (`/blog/`). If `content/{type}/index.md` exists, its rendered body appears above the post list as introductory content.

## Co-located assets

Files placed alongside content (`content/blog/posts/diagram.png`) follow the page's output URL, not the source path. This matters when `url_format` relocates a post: the diagram lands in the same directory as the page so `![](diagram.png)` keeps working.

See [URL generation](urls.md) for the relocation details.

## File exclusion

Files matching `exclude_patterns` are skipped during discovery. The defaults exclude `_drafts/**`, `_*.md`, and `.git/**`. Add your own patterns in `bartleby.yml`.

## Drafts

Front matter `draft: true` is honoured: drafts are excluded from the production build (`bartleby build`) but appear in the development server (`bartleby serve`). Pass `--include-drafts` to `bartleby build` to override.
