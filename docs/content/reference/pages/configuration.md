---
title: "bartleby.yml Configuration"
description: "Every top-level config section and its fields."
tags:
  - configuration
---

The `bartleby.yml` file at the project root is the single source of truth for site behavior.
Bartleby loads it once at the start of every build.
The `site` section is the only required one.

## `site`

Global site metadata.
The section requires `title` and `url`.

```yaml
site:
  title: "My Site"
  url: "https://example.com"
  description: "Site-wide description, used as a fallback for page descriptions"
  author: "Mason Egger"
  default_image: "/img/og-default.png"
  twitter: "@masonegger"
  feed:
    enabled: true
    formats: [rss, atom]
    limit: 50
```

| Key | Default | Purpose |
|-----|---------|---------|
| `title` | required | Site title |
| `url` | required | Absolute base URL, used for canonical links, feeds, and the sitemap |
| `description` | `""` | Site description and fallback page description |
| `author` | `""` | Default author name |
| `default_image` | none | Fallback Open Graph image |
| `twitter` | none | Twitter handle for card metadata |
| `feed` | see below | Site-wide aggregate feed |

The `site.feed` block controls the aggregate feed that merges items across content types:

| Key | Default | Purpose |
|-----|---------|---------|
| `enabled` | `true` | Generate the aggregate feed |
| `formats` | `[rss, atom]` | Formats to write at the site root |
| `include` | `[]` | Content types to merge. Empty means every type that has its own `feeds`. A listed type must define `feeds`. |
| `limit` | `50` | Maximum items in the merged feed |
| `title` | `site.title` | Channel title |

## `nav`

Explicit navigation.
When you omit it, Bartleby generates the navigation from the content tree.

```yaml
nav:
  - Home: index.md
  - Blog: blog/
  - About: about.md
  - Docs:
      - Intro: docs/intro.md
      - Guide: docs/guide.md
```

## `content_types`

Named groups of pages that share behavior.
`path` is the only required field.

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

| Key | Default | Purpose |
|-----|---------|---------|
| `path` | required | Directory under `content/` that holds the type's pages |
| `url_base` | none | URL prefix for the type's pages |
| `url_format` | none | URL template. Placeholders: `{slug}`, `{date:FORMAT}` (strftime), `{title}`, `{categories}` |
| `readtime` | `false` | Compute `page.readtime` |
| `excerpt_separator` | none | Marker that ends the excerpt |
| `taxonomies` | `[]` | Site taxonomies this type uses. Each must be declared under `taxonomies`. |
| `feeds` | `[]` | Per-type feed formats: `rss`, `atom` |
| `pagination.enabled` | `false` | Paginate the listing page |
| `pagination.per_page` | `10` | Pages per listing page |
| `pagination.url_format` | `page/{page}` | URL template for pages after the first |
| `metadata` | none | Schema for custom front matter fields, one entry per field |
| `metadata.<field>.type` | required | The field's type |
| `metadata.<field>.required` | `false` | Whether every page of the type must set the field |
| `metadata.<field>.choices` | none | The values the field accepts |

`<field>` stands for a field name that you choose.
The supported types are listed in [Front matter fields](front-matter-fields.md#custom-metadata).

## `taxonomies`

Site-level taxonomies.
Content types opt in through their `taxonomies` list.

```yaml
taxonomies:
  tags:
    slug_format: "{slug}"
  categories:
    slug_format: "{slug}"
```

| Key | Default | Purpose |
|-----|---------|---------|
| `slug_format` | `{slug}` | Template that builds a term's slug. The placeholder `{slug}` is the slugified term. |

## `theme`

Theme selection, features, and appearance.

```yaml
theme:
  name: scrivener
  features:
    - search
    - search.highlight
    - nav.tabs
    - nav.sidebar
    - nav.section-index
    - nav.back-to-top
    - content.code.copy
    - color-mode.toggle
  color_mode:
    default: light
  tokens:
    color.primary: "#2a4b7c"
    font.text: "Charter, Georgia, serif"
    radius: "2px"
  icon_packs:
    material: true
    fontawesome: true
    octicons: true
    simple: true
  logo: "img/logo.svg"
  favicon: "img/favicon.ico"
```

| Key | Default | Purpose |
|-----|---------|---------|
| `name` | `scrivener` | A bundled theme: `base`, `material`, or `scrivener` |
| `path` | none | A theme directory, relative to the project or absolute |
| `package` | none | The name of an entry point in the `bartleby.themes` group |
| `features` | `[]` | Features to switch on, from the list below |
| `color_mode.default` | none | Starting mode: `light` or `dark`. Without it, the toggle follows the reader's system setting. |
| `tokens` | `{}` | Design tokens, a flat map of dotted names to CSS values |
| `icon_packs` | all `true` | Enable or disable a bundled icon pack: `material`, `fontawesome`, `octicons`, `simple` |
| `logo`, `favicon` | none | The site logo and favicon, as a path relative to `static/` or a full URL. `img/logo.svg` is the file `static/img/logo.svg`. The bundled themes show the logo before the site title in the header and link the favicon from the `<head>`. Templates read them as `config.theme.logo` and `config.theme.favicon`, both root-relative URLs such as `/img/logo.svg`. |

Set at most one of `name`, `path`, and `package`.
Setting more than one is a config error.

A theme extends another theme with `extends` in its own `theme.yml` manifest, not in `bartleby.yml`.
For example, the manifest of `scrivener` contains `extends: base`.
Bartleby resolves the chain leaf-first, so a theme's files override its parent's.

### Features

`features` accepts only these names.
Any other name is a config error, and the error message lists the valid ones.
A feature that the active theme chain does not declare in a manifest produces a build warning.

| Feature | Effect |
|---------|--------|
| `search` | The search box and the client-side search index |
| `search.highlight` | Highlight the search terms on the page a result opens |
| `nav.tabs` | Top-level sections render as tabs in the header |
| `nav.sidebar` | The section tree renders as a sidebar |
| `nav.section-index` | A section's index page is the section's own nav entry |
| `nav.back-to-top` | A back-to-top button appears after scrolling |
| `content.code.copy` | Code blocks get a copy button |
| `color-mode.toggle` | The header shows a light and dark toggle |

The `color-mode.toggle` feature is the only switch for the toggle.
It also controls the small script in `<head>` that applies the saved or system color mode before the page paints.
`color_mode.default` works with or without the feature.
The old `color_mode.toggle` key is a config error that points at this feature.

### Tokens

A token name becomes a CSS custom property: `color.primary` becomes `--bb-color-primary`.
Tokens reach the page when you run `bartleby theme compile`, which writes them into the compiled stylesheet.
The bundled themes read these tokens:

| Token | Controls |
|-------|----------|
| `color.primary` | Primary color |
| `color.accent` | Secondary accent color |
| `color.bg`, `color.text` | Background and text colors in light mode |
| `color.bg-dark`, `color.text-dark` | Background and text colors in dark mode |
| `font.text`, `font.ui`, `font.code` | Body, interface, and code fonts |
| `radius` | Corner radius |
| `logo.height` | Height of the image from `theme.logo` |

Token values must be strings.
The old mkdocs-style `palette` and `font` keys are config errors, and the message points to `theme.tokens`.

## `authors_file`

Path to the authors file.
Defaults to `.authors.yml` at the project root.

```yaml
authors_file: ".authors.yml"
```

## `output_dir`

Directory for the built site, relative to the project root.
Defaults to `site`.

## `exclude_patterns`

Gitignore-style patterns to skip during content discovery.
Defaults: `_drafts/**`, `_*.md`, `.git/**`.
Setting the key replaces the defaults, so repeat any default you want to keep.

```yaml
exclude_patterns:
  - "_drafts/**"
  - "_*.md"
  - ".git/**"
  - "internal/**"
```

## `markdown_extensions`

Per-extension config overrides.
See [Markdown extensions](markdown-extensions.md) for the default set and [Markdown pipeline](../../concepts/markdown-pipeline.md) for how overrides merge.

```yaml
markdown_extensions:
  - name: pymdownx.snippets
    config:
      base_path: ["includes"]
```

## `plugins`

Controls installed plugins.
Hook discovery from `hooks/*.py` does not depend on this key.
Map an installed plugin's entry point name to `false` to disable it without uninstalling it:

```yaml
plugins:
  some-plugin: false
```

A list form is accepted, and it has no effect on discovery.

## `extra_css` and `extra_js`

Asset paths that Bartleby injects into every page.

```yaml
extra_css:
  - css/site.css
extra_js:
  - js/analytics.js
```

## `ai`

Agent integration settings.

```yaml
ai:
  llms_txt: true
  llms_full_txt: true
  markdown_variants: true
  agent_surface: true
  robots:
    allow:
      - GPTBot
    disallow:
      - BadBot
  skills:
    output_dir: .claude/skills
    style_guide: docs/style-guide.md
  agent_context:
    voice: "Plain, direct, second person"
    audience: "Developers who run static sites"
    constraints:
      - "Never use marketing language"
```

| Key | Default | Purpose |
|-----|---------|---------|
| `llms_txt` | `true` | Write `llms.txt` |
| `llms_full_txt` | `true` | Write `llms-full.txt` |
| `markdown_variants` | `true` | Write an `index.md` next to each page's HTML |
| `agent_surface` | `true` | Write `schema.json` and `content-index.json` |
| `robots.allow` | `[]` | Crawler names that get an explicit `Allow: /` group |
| `robots.disallow` | `[]` | Crawler names that get a `Disallow: /` group |
| `skills.output_dir` | `.claude/skills` | Where `generate-skill` writes |
| `skills.style_guide` | none | A Markdown file whose text goes into the generated skills. A missing file is a usage error. |
| `skills.regenerate_on_build` | `false` | Rewrite the skills after every `bartleby build`, as `generate-skill` does. A dry run and the dev server do not. |
| `agent_context.voice` | none | Voice description, copied into the write and review skills |
| `agent_context.audience` | none | Audience description, copied the same way |
| `agent_context.constraints` | `[]` | List of rules, copied the same way |

See [Agent output formats](agent-surface.md) for what each output contains.

## `dev_server`

Development server bind settings.

```yaml
dev_server:
  host: "127.0.0.1"
  port: 8000
```

| Key | Default | Purpose |
|-----|---------|---------|
| `host` | `127.0.0.1` | Address the server binds to. `--host` overrides it. |
| `port` | `8000` | Port the server binds to. `--port` overrides it. |
