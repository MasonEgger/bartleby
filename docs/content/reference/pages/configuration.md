---
title: "bartleby.yml Configuration"
description: "Every top-level config section and its fields."
tags:
  - configuration
---

The `bartleby.yml` file at the project root is the single source of truth for site behavior.
Bartleby loads it once at the start of every build.
The `site` section is the only required one.
A key written twice in one mapping is a config error naming the line, because the second value would silently replace the first.

Each section below has a short example and the notes that the tables cannot hold.
The [Option Reference](#option-reference) at the end lists every key with its type, default, allowed values, and whether it is required.
That list is generated from the same schema that `bartleby config schema` prints and `bartleby new site --full-config` writes, and a test fails when the page and the schema disagree.

You can change values without editing the file.
`--set KEY.PATH=VALUE` and `--base-url` override a value for one run, and `bartleby config show`, `get`, and `set` read and write it.
The [CLI reference](cli.md#bartleby-config) has the flags, and [Configure Bartleby from the Command Line](../../guides/posts/configure-from-the-command-line.md) walks through them.

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
  language: "en"
  feed:
    enabled: true
    formats: [rss, atom]
    limit: 50
```

`site.title` and `site.url` are the only required keys in the whole file.
`site.url` is the absolute base for canonical links, feeds, and the sitemap, so it must be an `http` or `https` URL with a host; an empty value or one without a scheme is a config error.
Override it for one run with `--base-url` or `--set site.url=...`.
A string key left null in the file (`description:` with nothing after it) reads as its default.

The `site.feed` block controls the aggregate feed that merges items across content types.
A type listed in `site.feed.include` must define `feeds`.
Leave `include` empty to merge every type that has its own `feeds`.

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

`<field>` stands for a field name that you choose.
The supported types are listed in [Front matter fields](front-matter-fields.md#custom-metadata).
`url_format` accepts the placeholders `{slug}`, `{date:FORMAT}` (strftime), `{title}`, and `{categories}`.
Setting `enabled: false` skips the type's pages, listing, and feeds and keeps the block, as `bartleby disable` does.
See [Enable Content Types](../../guides/posts/enable-content-types.md) for the commands.

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

`slug_format` is a template that builds a term's slug.
Its placeholder `{slug}` is the slugified term.

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

`theme.color_mode.default` is the starting mode, `light` or `dark`.
Without it, the toggle follows the reader's system setting.
`theme.icon_packs` maps a bundled pack to a flag: `material`, `fontawesome`, `octicons`, and `simple`.
Every pack is on until you set it to `false`.
`theme.logo` and `theme.favicon` take a path relative to `static/` or a full URL, so `img/logo.svg` is the file `static/img/logo.svg`.
The bundled themes show the logo before the site title in the header and link the favicon from the `<head>`.
Templates read them as `config.theme.logo` and `config.theme.favicon`, both root-relative URLs such as `/img/logo.svg`.

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
| `nav.toc-fold` | The page's headings move into the sidebar and the right-hand table of contents goes away. The fold applies when the page is in the sidebar tree, and other pages keep the right-hand table of contents. |
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
Token names contain dots, so `config set theme.tokens.color.primary red` and `--set theme.tokens.color.primary=red` address the one key `color.primary`.
The old mkdocs-style `palette` and `font` keys are config errors, and the message points to `theme.tokens`.

## `authors_file`

Path to the authors file.
Defaults to `.authors.yml` at the project root.

```yaml
authors_file: ".authors.yml"
```

## `output_dir`

Directory for the built site, relative to the project root; an absolute path works too.
Defaults to `site`.

The build replaces this directory whole on every run, so it may not be the project directory, a directory above it, or a directory the build reads: `content`, `static`, `templates`, `overrides`, `hooks`, `data`, `shortcodes`, `partials`, or a `theme.path` directory.
Such a value is a `config_error` with a fix hint, from the file and from `--set`.
A symlink is followed: the link stays and its target gets the new build.

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

## `markwright`

Settings for the markwright extensions (embeds, code fences, highlighting).
The section has the shape of a `markwright.toml`: `enable` or `disable` (not both), `warn`, and one table per extension.
markwright validates it when the config loads, so an unknown key or bad value fails `bartleby validate`, `config set`, and the build with markwright's own message under the `markwright` key, labeled with the config file or `--set` as its source.
Only this section counts; a `markwright.toml` or `[tool.markwright]` table next to `bartleby.yml` is ignored, and the build warns about it.
Embeds load eagerly unless you set `load: click` on one.
[Configure markwright and Click-to-Load Embeds](../../guides/posts/configure-markwright.md) shows the shape.

```yaml
markwright:
  disable: [twitter]
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

`ai.robots` takes two lists, `allow` and `disallow`.
Crawlers in `allow` get an explicit `Allow: /` group, and crawlers in `disallow` get a `Disallow: /` group.
`ai.skills.style_guide` names a Markdown file whose text goes into the generated skills, and a missing file is a usage error.
`ai.skills.regenerate_on_build` rewrites the skills after every `bartleby build`, as `generate-skill` does.
A dry run and the dev server do not.
`ai.agent_context.voice`, `audience`, and `constraints` are copied into the write and review skills.

See [Agent output formats](agent-surface.md) for what each output contains.

## `dev_server`

Development server bind settings.

```yaml
dev_server:
  host: "127.0.0.1"
  port: 8000
```

`--host` and `--port` on `bartleby serve` override these two keys.

## Option Reference

Every key `bartleby.yml` accepts, in the order of `CONFIG_SCHEMA`.
A path segment in angle brackets, such as `<name>`, stands for a name that you choose, so `content_types.<name>.path` is `content_types.blog.path` for a content type called `blog`.
`none` in the Default column means the key has no value until you set one.
`any` in the Allowed Values column means the key does not restrict its value to a closed set.

<!-- config-schema:begin -->

### Options for `site`

| Path | Type | Default | Allowed Values | Required | Description |
|---|---|---|---|---|---|
| `site.title` | string | none | any | yes | The site title. |
| `site.url` | string | none | any | yes | The canonical site URL, used for absolute links. |
| `site.description` | string | `""` | any | no | A short site description. |
| `site.author` | string | `""` | any | no | The default author name. |
| `site.default_image` | string | none | any | no | A fallback social image path or URL. |
| `site.twitter` | string | none | any | no | The site Twitter handle for social cards. |
| `site.language` | string | `en` | any | no | The BCP 47 language tag of the site's pages, written to the html lang attribute. |
| `site.feed.enabled` | boolean | `true` | any | no | Generate the site-wide aggregate feed. |
| `site.feed.formats` | list | `["rss", "atom"]` | `rss`, `atom` | no | Feed formats to emit at the site root. |
| `site.feed.include` | list | `[]` | any | no | Content types to aggregate; empty means every type with feeds. |
| `site.feed.limit` | integer | `50` | any | no | Maximum items in the aggregate feed. |
| `site.feed.title` | string | none | any | no | Feed title override; falls back to site.title. |

### Options for `nav`

| Path | Type | Default | Allowed Values | Required | Description |
|---|---|---|---|---|---|
| `nav` | list | none | any | no | Explicit navigation tree; omit to build it from the content directory. |

### Options for `theme`

| Path | Type | Default | Allowed Values | Required | Description |
|---|---|---|---|---|---|
| `theme.name` | string | `scrivener` | any | no | A bundled theme name. Set only one of name, path, or package. |
| `theme.path` | string | none | any | no | A theme directory, relative to the project or absolute. |
| `theme.package` | string | none | any | no | A theme installed as a bartleby.themes entry point. |
| `theme.features` | list | `[]` | `color-mode.toggle`, `content.code.copy`, `nav.back-to-top`, `nav.section-index`, `nav.sidebar`, `nav.tabs`, `nav.toc-fold`, `search`, `search.highlight` | no | Theme features to enable. |
| `theme.tokens` | mapping | `{}` | any | no | Design-token overrides, dotted token name to CSS value. |
| `theme.color_mode.default` | string | none | `light`, `dark` | no | The color mode used before a visitor chooses one. |
| `theme.icon_packs` | mapping | `{}` | any | no | Icon pack name to enabled flag. |
| `theme.logo` | string | none | any | no | The site logo, a path under static/ or a URL. |
| `theme.favicon` | string | none | any | no | The site favicon, a path under static/ or a URL. |

### Options for `authors_file`

| Path | Type | Default | Allowed Values | Required | Description |
|---|---|---|---|---|---|
| `authors_file` | string | `.authors.yml` | any | no | The authors file, relative to the project. |

### Options for `exclude_patterns`

| Path | Type | Default | Allowed Values | Required | Description |
|---|---|---|---|---|---|
| `exclude_patterns` | list | `["_drafts/**", "_*.md", ".git/**"]` | any | no | Glob patterns for content files to skip. |

### Options for `markdown_extensions`

| Path | Type | Default | Allowed Values | Required | Description |
|---|---|---|---|---|---|
| `markdown_extensions` | list | `[]` | any | no | Extra Python-Markdown extensions, by name or name with options. |

### Options for `markwright`

| Path | Type | Default | Allowed Values | Required | Description |
|---|---|---|---|---|---|
| `markwright` | mapping | `{}` | any | no | markwright settings (enable, disable, warn, one table per extension), validated by markwright itself. |

### Options for `plugins`

| Path | Type | Default | Allowed Values | Required | Description |
|---|---|---|---|---|---|
| `plugins` | list | `[]` | any | no | Plugins to enable; a name-to-boolean mapping also disables auto-registered ones. |

### Options for `extra_css`

| Path | Type | Default | Allowed Values | Required | Description |
|---|---|---|---|---|---|
| `extra_css` | list | `[]` | any | no | Extra stylesheet paths or URLs to load on every page. |

### Options for `extra_js`

| Path | Type | Default | Allowed Values | Required | Description |
|---|---|---|---|---|---|
| `extra_js` | list | `[]` | any | no | Extra script paths or URLs to load on every page. |

### Options for `output_dir`

| Path | Type | Default | Allowed Values | Required | Description |
|---|---|---|---|---|---|
| `output_dir` | string | `site` | any | no | Where the built site is written. |

### Options for `content_types`

| Path | Type | Default | Allowed Values | Required | Description |
|---|---|---|---|---|---|
| `content_types.<name>.path` | string | none | any | yes | The directory under content/ that holds this type. |
| `content_types.<name>.enabled` | boolean | `true` | any | no | Build this type's listing, pages, and feeds; false skips them but keeps the block. |
| `content_types.<name>.url_base` | string | none | any | no | The URL prefix for this type. |
| `content_types.<name>.url_format` | string | none | any | no | The URL pattern for pages of this type. |
| `content_types.<name>.taxonomies` | list | `[]` | any | no | Taxonomies this type uses; each must be declared under taxonomies. |
| `content_types.<name>.feeds` | list | `[]` | `rss`, `atom` | no | Feed formats to emit for this type. |
| `content_types.<name>.readtime` | boolean | `false` | any | no | Compute a reading time for each page. |
| `content_types.<name>.excerpt_separator` | string | none | any | no | The marker that ends a page excerpt. |
| `content_types.<name>.pagination.enabled` | boolean | `false` | any | no | Paginate the listing page. |
| `content_types.<name>.pagination.per_page` | integer | `10` | any | no | Items per listing page. |
| `content_types.<name>.pagination.url_format` | string | `page/{page}` | any | no | The URL pattern for pages after the first. |
| `content_types.<name>.metadata.<field>.type` | string | none | `string`, `integer`, `boolean`, `date`, `list` | yes | The front matter field type. |
| `content_types.<name>.metadata.<field>.required` | boolean | `false` | any | no | Whether pages must set this field. |
| `content_types.<name>.metadata.<field>.choices` | list | none | any | no | Allowed values for this field. |

### Options for `taxonomies`

| Path | Type | Default | Allowed Values | Required | Description |
|---|---|---|---|---|---|
| `taxonomies.<name>.slug_format` | string | `{slug}` | any | no | The URL slug pattern for a term. |

### Options for `ai`

| Path | Type | Default | Allowed Values | Required | Description |
|---|---|---|---|---|---|
| `ai.llms_txt` | boolean | `true` | any | no | Write llms.txt. |
| `ai.llms_full_txt` | boolean | `true` | any | no | Write llms-full.txt. |
| `ai.markdown_variants` | boolean | `true` | any | no | Write a Markdown variant of each page. |
| `ai.agent_surface` | boolean | `true` | any | no | Write schema.json and content-index.json. |
| `ai.robots` | mapping | `{}` | any | no | Crawler directives, such as disallow mapped to a list of crawlers. |
| `ai.skills.output_dir` | string | `.claude/skills` | any | no | Where generated agent skills are written. |
| `ai.skills.style_guide` | string | none | any | no | A style guide file included in generated skills. |
| `ai.skills.regenerate_on_build` | boolean | `false` | any | no | Regenerate skills on every build. |
| `ai.agent_context.voice` | string | none | any | no | The writing voice, included in generated skills. |
| `ai.agent_context.audience` | string | none | any | no | The target audience, included in generated skills. |
| `ai.agent_context.constraints` | list | `[]` | any | no | Rules generated skills must follow. |

### Options for `dev_server`

| Path | Type | Default | Allowed Values | Required | Description |
|---|---|---|---|---|---|
| `dev_server.host` | string | `127.0.0.1` | any | no | The host the dev server binds to. |
| `dev_server.port` | integer | `8000` | any | no | The port the dev server listens on. |

<!-- config-schema:end -->
