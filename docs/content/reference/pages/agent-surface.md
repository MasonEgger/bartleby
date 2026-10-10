---
title: "Agent Output Formats"
description: "Every machine-readable file Bartleby publishes, its fields, and the CLI commands that return the same data."
tags:
  - ai
  - cli
---

This page is the reference for every agent output format: the per-page Markdown variants, `llms.txt`, `llms-full.txt`, `schema.json`, `content-index.json`, the JSON-LD blocks, and the generated skills.
It also covers the CLI commands that return the same data.
For why they exist, read [Agent integration](../../concepts/agents-and-llms.md).
For the flags of each command, read the [CLI reference](cli.md).

## Files

Bartleby writes these files to the site root on every build.
`ai.llms_txt`, `ai.llms_full_txt`, `ai.markdown_variants`, and `ai.agent_surface` switch them on or off, and all four default to `true`.

| File | Toggle | Contents |
|------|--------|----------|
| `<url>/index.md` | `ai.markdown_variants` | The page's Markdown body, without front matter, next to its HTML |
| `llms.txt` | `ai.llms_txt` | Site overview with one link per Markdown variant, grouped by content type, described below |
| `llms-full.txt` | `ai.llms_full_txt` | The Markdown body of every published page, each under a `---` separator with its title, absolute URL, and date |
| `schema.json` | `ai.agent_surface` | Site manifest, described below |
| `content-index.json` | `ai.agent_surface` | One entry per published page, described below |
| `robots.txt` | none | Crawler directives from `ai.robots`, unless `static/robots.txt` exists |

### Per-Page Guarantee

Every published page from `content/` has a Markdown variant at `<url>/index.md` when `ai.markdown_variants` is on.
Every HTML page, including `404.html`, carries exactly one JSON-LD block.
The block parses as JSON and has `@context`, `@type`, `name`, `headline`, and `url`.
The [JSON-LD](#json-ld) section lists the types and keys.
Drafts and pages matched by `exclude_patterns` are never rendered, so they get neither.
Listing pages, taxonomy pages, and `404.html` have no Markdown source and no variant.
Their HTML omits the `text/markdown` alternate link, which the theme emits only when the variant exists.

A published page may not use `schema.json` or `content-index.json` as its output path.
The build stops with an `AgentSurfaceError` that names the page.

### `llms.txt` and `llms-full.txt`

`llms.txt` opens with the site title and description.
When `ai.agent_surface` is on, a `Machine-readable` section follows with absolute links to `schema.json` and `content-index.json`.
Then comes one section per content type that has published pages, in the order `content_types` lists them, and a `Pages` section for pages that have no content type.
Each entry is one line: `- [Title](absolute-md-url): summary`.
The summary is the page description, else its excerpt, else its title, with whitespace runs collapsed to single spaces.

`llms-full.txt` has the same header, then one block per published page.
A block is `---`, `# Title`, `URL: <absolute page URL>`, a `Date:` line when the page has a date, a blank line, and the raw Markdown body.

Both files list published pages only, in source-path order.

### `schema.json`

`schema.json` has these top-level keys:

| Key | Contents |
|-----|----------|
| `site` | `title`, `description`, `url`, and `language` (always `en`) |
| `content_types` | One object per content type, in the shape of `bartleby schema <type>` |
| `taxonomies` | Each taxonomy with its `name`, `slug_format`, and the `terms` in use with their `count` |
| `authors` | The public author list, in the shape of `bartleby schema authors` |
| `theme` | The active theme, described below |
| `resources` | Absolute URLs for `sitemap`, `llms_txt`, `content_index`, and a `feeds` list |

Each entry in `resources.feeds` has `content_type` (`null` for the site-wide feed), `format` (`rss` or `atom`), and `url`.
The file uses sorted keys and two-space indentation, so its output is stable between builds.

The `theme` block has three keys:

| Key | Contents |
|-----|----------|
| `name` | The name of the theme the site selects |
| `chain` | The resolved theme names, selected theme first and the root ancestor (`base`) last |
| `features` | Three sorted lists, described below |

`features` carries all three lists because each answers a different question:

| List | Contents |
|------|----------|
| `enabled` | The names `theme.features` in `bartleby.yml` asks for |
| `implemented` | The union of `features` across the manifests in the chain |
| `active` | The names in both lists, which is what the built site can do |

An agent should read `active` to know what the site supports.
A name that appears in `enabled` but not in `implemented` is a feature the build warned about and did not render.
For the docs site, `active` equals `enabled`, because `scrivener` implements all eight features.

### JSON-LD

Each page's block is a `schema.org` object.
The type depends on what the page is:

| Type | Used for |
|------|----------|
| `Article` | A page that belongs to a content type |
| `CollectionPage` | A listing or taxonomy page that the build generates |
| `WebPage` | Any other page, including `404.html` |

The block has these keys:

| Key | Present when |
|-----|--------------|
| `@context` | Always. The value is `https://schema.org`. |
| `@type` | Always |
| `name`, `headline` | Always. Both hold the page title. |
| `description` | Always. The page description, else `site.description`, else an empty string. |
| `url` | Always. The absolute page URL. |
| `datePublished` | The page is an `Article` and has a date, in ISO format |

The `partials/jsonld.html` partial in the `base` theme prints the block.
The characters `<`, `>`, and `&` appear as `\u003c`, `\u003e`, and `\u0026`, so a value can never close the surrounding `<script>` tag.

### Determinism

Every file above is a pure function of the site's content, config, and theme.
The build date shows in the HTML footer, but none of these files carry it or any other timestamp.
Pages appear in source-path order, JSON keys are sorted, and two builds of the same input produce byte-identical files.

### `content-index.json`

`content-index.json` has a `count` and a `content` list.
Each entry in `content` carries only fields that describe the page:

| Key | Present when |
|-----|--------------|
| `title` | Always |
| `type` | Always. The content type name, or `null` for a static page. |
| `url`, `md_url` | Always. Both are absolute. |
| `description` | The page sets one |
| `date` | The page has a date, in ISO format |
| `authors` | The page lists author keys |
| One key per taxonomy | The page has terms, such as `tags` |
| One key per custom metadata field | The page sets it |

The index leaves out fields that configure the build, such as `template`, `draft`, and URL overrides.

## `bartleby schema`

Print a schema from the config, authors file, and content.

```
bartleby schema TARGET
```

`TARGET` is one of:

- A content type name, such as `blog`.
- `authors`.
- `taxonomies`.

In text mode, a content type prints its path and its required and optional fields.
Use `--output json` for the full shape.

For a content type, the JSON has these keys:

| Key | Contents |
|-----|----------|
| `content_type`, `path` | The type's name and content path |
| `url_base`, `url_format` | The URL settings, or `null` |
| `required_fields`, `optional_fields` | Lists of `{name, type, choices?}` objects built from the type's `metadata` schema |
| `features` | `pagination`, `per_page`, `feeds`, `readtime`, and `excerpt_separator` when set |

For `authors`, the JSON is `{"authors": [...]}`.
Each author has `id` and `name`, plus `url`, `image`, and `bio` when set.

For `taxonomies`, the JSON is `{"taxonomies": [...]}`.
Each taxonomy has `name`, `slug_format`, and `terms`, a list of `{term, count}` objects that counts published pages only.

An unknown content type is a usage error and exits 2.

## `bartleby content`

`bartleby content list --output json` returns `{"count": N, "content": [...]}`.
Each entry has `path`, `title`, `date`, `type`, `url`, and `draft`.
Only published pages appear.

`bartleby content get PATH --output json` returns one object with `path`, `url`, `content_type`, `metadata`, `content` (the raw Markdown body), and `word_count`.
`metadata` holds the title, date, description, authors, taxonomy terms, and draft flag.

## `bartleby export`

`bartleby export` writes one record per published page.
Each record has `path`, `url`, `type`, `title`, `date`, and `word_count`.
It adds `description`, `authors`, and one key per taxonomy when the page has them.
`--include-content` adds a `content` key.
`--include-html` adds an `html` key holding the rendered body, produced by the build's own render phase.

| Format | Shape |
|--------|-------|
| `jsonl` | One JSON object per line. This is the default. |
| `json` | One JSON array |
| `csv` | A header row, then one row per page, with the columns `path`, `url`, `type`, `title`, `date`, `authors`, `tags`, and `word_count`. The columns join list values with commas. |

## Generated Skills

`bartleby generate-skill` writes three files to `ai.skills.output_dir`:

| File | Contents |
|------|----------|
| `bartleby-write.md` | Each content type with its required and optional fields, the authors, the taxonomy terms in use, the available shortcodes, and the `bartleby new post` command |
| `bartleby-review.md` | Each content type's metadata schema, the existing taxonomy terms, and the `bartleby validate` command |
| `bartleby-ops.md` | The commands for building, validating, serving, querying, introspecting, and exporting, the active theme with its active features, and the `theme inspect`, `eject`, and `compile` commands |

The write and review skills also include a voice and constraints section when `ai.agent_context` sets any value, and the contents of the file named by `ai.skills.style_guide`.

### Generated-Skill Contract

The generated skills describe the site as it is.

- The same site always produces byte-identical files.
  Lists are sorted, nothing reads the clock or the network, and discovery order does not matter.
- Content types, fields, choices, authors, and taxonomy terms come from the same derivation as `schema.json`, so the two always agree.
- The theme name, its chain, and its active features come from the `theme` object in `schema.json`.
- Only published pages count.
  A draft adds no term and no example path.
- Every `bartleby` command in a skill parses against the CLI.
  Commands use a real content type and a real page path from the site.
- The output has no placeholder text.
  A section with nothing to say says `none`.

The write and review skills describe the schema, not the prose.
No content analysis runs.

See the [`ai` configuration](configuration.md#ai) for the keys that control generation.
