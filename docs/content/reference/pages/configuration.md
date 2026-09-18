---
title: "bartleby.yml configuration"
description: "Every top-level config section and its fields."
tags:
  - configuration
---

The `bartleby.yml` at the project root is the single source of truth for site behaviour. Bartleby loads it once at the start of every build.

## site (required)

Global metadata. `title` and `url` are required; everything else is optional.

```yaml
site:
  title: "My Site"
  url: "https://example.com"
  description: "Site-wide description, used as a fallback for page descriptions"
  author: "Mason Egger"
  default_image: "/img/og-default.png"
  twitter: "@masonegger"
```

## nav (optional)

Explicit navigation. When omitted, Bartleby auto-generates a flat nav from top-level pages and directories.

```yaml
nav:
  - Home: index.md
  - Blog: blog/
  - About: about.md
  - Docs:
      - Intro: docs/intro.md
      - Guide: docs/guide.md
```

## content_types

Named groups of pages with shared behaviour. `path` is the only required field per type.

```yaml
content_types:
  blog:
    path: blog/posts
    url_base: blog
    url_format: "{date:%Y/%m/%d}/{slug}"
    readtime: true
    excerpt_separator: "<!-- more -->"
    taxonomies:
      - tags
      - categories
    feeds:
      - rss
      - atom
    pagination:
      enabled: true
      per_page: 10
      url_format: "page/{page}"
    metadata:
      difficulty:
        type: string
        required: true
        choices:
          - beginner
          - intermediate
          - advanced
```

## taxonomies

Site-level taxonomies. Content types opt in via their `taxonomies` list.

```yaml
taxonomies:
  tags:
    slug_format: "{slug}"
  categories:
    slug_format: "{slug}"
```

## theme

Theme appearance and feature toggles.

```yaml
theme:
  palette:
    primary: "indigo"
    accent: "pink"
  color_mode:
    toggle: true
    default: "light"
  features:
    - search
    - navigation.tabs
    - navigation.top
  icon_packs:
    material: true
    fontawesome: true
    octicons: true
    simple: true
  logo: "img/logo.svg"
  favicon: "img/favicon.ico"
  font:
    text: "Inter"
    code: "JetBrains Mono"
```

## authors_file

Path to the authors file. Defaults to `.authors.yml` at the project root.

```yaml
authors_file: ".authors.yml"
```

## exclude_patterns

Gitignore-style patterns. Defaults: `_drafts/**`, `_*.md`, `.git/**`.

```yaml
exclude_patterns:
  - "_drafts/**"
  - "_*.md"
  - ".git/**"
  - "internal/**"
```

## markdown_extensions

Per-extension config overrides. See [Markdown pipeline](../../concepts/markdown-pipeline.md) for the bundled default set.

```yaml
markdown_extensions:
  - name: pymdownx.snippets
    config:
      base_path: ["includes"]
```

## plugins

Reserved for future use. Currently ignored — hook discovery is file-based via `hooks/*.py`.

## extra_css / extra_js

Asset paths injected into every page.

```yaml
extra_css:
  - css/site.css
extra_js:
  - js/analytics.js
```

## ai

Agent integration toggles.

```yaml
ai:
  llms_txt: true
  llms_full_txt: true
  markdown_variants: true
  robots:
    allow:
      - GPTBot
    disallow:
      - BadBot
```

## dev_server

Development server bind settings.

```yaml
dev_server:
  host: "127.0.0.1"
  port: 8000
```
