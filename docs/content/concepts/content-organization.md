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
Relative `.md` links in that intro resolve against the `content/{type}/` directory, the same way links in a page body do.

Each row in the list shows the page's title, its date when it has one, and its excerpt when the content type sets `excerpt_separator`.
A page without a date gets a row without a date column.
The excerpt is the part of the page above the separator, or the first paragraph when the page has no separator.
The listing renders it as HTML, so inline code and links work.
Feeds and `llms.txt` carry the same excerpt as plain text.

## Navigation for a Content Type

A content type is a listing, so `nav` treats a content-type directory such as `guides/` as one link.
That keeps a blog with hundreds of posts out of the sidebar.
When you want a section tree for a finite set of pages, such as a reference, list the pages yourself under the section:

```yaml
nav:
  - Reference:
      - All Reference Pages: reference/
      - CLI Commands: reference/pages/cli.md
      - Themes: reference/pages/themes.md
```

Every page in that section, and the listing page itself, then shows the section as a sidebar.
Both bundled themes do this for posts, listings, and pages alike.

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
