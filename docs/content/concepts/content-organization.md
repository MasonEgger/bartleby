---
title: "Content Organization"
description: "How Bartleby discovers, classifies, and ships your content."
---

Every Bartleby site has a `content/` directory at its root.
Bartleby walks that tree and turns every Markdown file into a page.
Every non-Markdown file becomes a co-located asset that travels with its associated page.

## Directory Layout

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
├── overrides/              # Optional replacements for theme templates
├── templates/              # Optional content-type templates
├── partials/               # Optional Jinja2 fragments
├── shortcodes/             # Optional shortcode templates
├── data/                   # Optional YAML and TOML data files
├── static/                 # Site-wide static files copied to /
└── hooks/                  # Optional Python hook modules
```

Bartleby requires only `bartleby.yml` and `content/`.
The [customization seams](customization-seams.md) page explains each optional directory.

## Content Types

A content type is a named group of pages that share behavior.
You declare one in `bartleby.yml`:

```yaml
content_types:
  blog:
    path: blog/posts
    readtime: true
    excerpt_separator: "<!-- more -->"
    taxonomies:
      - tags
```

Any Markdown file under `content/blog/posts/` becomes a `blog` page.
The `path` field is the only required setting.
The other options turn on reading time, excerpts, taxonomies, feeds, pagination, and metadata validation.
The [configuration reference](../reference/pages/configuration.md#content_types) lists each one.

Pages outside any declared content type are static pages.
They get URLs, but no listing page, no feed, and no reading time.

## Listing Pages

Each content type automatically gets a listing page at its base URL, such as `/blog/`.
If `content/{type}/index.md` exists, its rendered body appears above the post list as introductory content.

## Co-Located Assets

Files placed alongside content, such as `content/blog/posts/diagram.png`, follow the page's output URL and not the source path.
This matters when `url_format` relocates a post.
The diagram lands in the same directory as the page, so `![](diagram.png)` keeps working.
See [URL generation](urls.md) for the relocation details.

## File Exclusion

Files that match `exclude_patterns` are skipped during discovery.
The defaults exclude `_drafts/**`, `_*.md`, and `.git/**`.
Add your own patterns in `bartleby.yml`.

## Drafts

A page with `draft: true` in its front matter is excluded from `bartleby build`.
Drafts do appear in the development server (`bartleby serve`).
Pass `--include-drafts` to `bartleby build` to include them.
