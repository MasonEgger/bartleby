---
title: "Agent Surface"
description: "The machine-readable files Bartleby publishes and the CLI commands that return the same data."
tags:
  - ai
  - cli
---

This page lists the files and commands that make a Bartleby site readable by agents.
For why they exist, read [Agent integration](../../concepts/agents-and-llms.md).
For the flags of each command, read the [CLI reference](cli.md).

## Files

Bartleby writes these files to the site root on every build.
`ai.llms_txt`, `ai.llms_full_txt`, `ai.markdown_variants`, and `ai.agent_surface` switch them on or off, and all four default to `true`.

| File | Toggle | Contents |
|------|--------|----------|
| `<url>/index.md` | `ai.markdown_variants` | The page's Markdown body, without front matter, next to its HTML |
| `llms.txt` | `ai.llms_txt` | Site overview with one link per Markdown variant, grouped by content type |
| `llms-full.txt` | `ai.llms_full_txt` | The Markdown body of every page, each under a `---` separator with its title, URL, and date |
| `schema.json` | `ai.agent_surface` | Site manifest, described below |
| `content-index.json` | `ai.agent_surface` | One entry per published page, described below |
| `robots.txt` | none | Crawler directives from `ai.robots`, unless `static/robots.txt` exists |

A published page may not use `schema.json` or `content-index.json` as its output path.
The build stops with an `AgentSurfaceError` that names the page.

### `schema.json`

`schema.json` has these top-level keys:

| Key | Contents |
|-----|----------|
| `site` | `title`, `description`, `url`, and `language` (always `en`) |
| `content_types` | One object per content type, in the shape of `bartleby schema <type>` |
| `taxonomies` | Each taxonomy with its `name`, `slug_format`, and the `terms` in use with their `count` |
| `authors` | The public author list, in the shape of `bartleby schema authors` |
| `resources` | Absolute URLs for `sitemap`, `llms_txt`, `content_index`, and a `feeds` list |

Each entry in `resources.feeds` has `content_type` (`null` for the site-wide feed), `format` (`rss` or `atom`), and `url`.
The file uses sorted keys and two-space indentation, so its output is stable between builds.

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
| `bartleby-ops.md` | The commands for building, validating, serving, querying, introspecting, and exporting |

The write and review skills also include a voice and constraints section when `ai.agent_context` sets any value, and the contents of the file named by `ai.skills.style_guide`.
The same inputs always produce the same files.
See the [`ai` configuration](configuration.md#ai) for the keys that control generation.
