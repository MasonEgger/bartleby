---
title: "CLI Commands"
description: "Every bartleby subcommand and its flags."
tags:
  - cli
---

Bartleby ships a single `bartleby` executable built on argparse.
Run `bartleby --help` for the top-level usage, or `bartleby <command> --help` for one command.

## Global Flags

Every command that does work accepts these flags, before or after the subcommand name:

| Flag | Default | Purpose |
|------|---------|---------|
| `--output {text,json}` | `text` | Output format. `json` is machine-readable and is the stable contract for agents. |
| `--config CONFIG` | `./bartleby.yml` | Path to `bartleby.yml`. |
| `--quiet` | off | Hide warnings and the text confirmation of `new`, `build`, and `generate-skill`. Errors, JSON output, and commands that return data still print. |
| `--verbose` | off | Log detailed progress to stderr, such as how many pages were found and where the build wrote them. |

`--quiet` and `--verbose` exclude each other.
Commands run from the directory that holds `bartleby.yml`, or take `--config` with a path to it.
Commands do not take a site directory as an argument.
To act on the docs site from the repository root, run `bartleby build --config docs/bartleby.yml`.

## `bartleby new`

### `bartleby new site`

Scaffold a new project directory.

```
bartleby new site NAME
```

Creates `NAME/` containing `bartleby.yml`, `.authors.yml`, `content/index.md`, and a first post at `content/blog/posts/welcome.md`.
It also creates empty `templates/`, `static/`, and `hooks/` directories.
The generated config selects the `scrivener` theme and defines one `blog` content type that stores posts in `blog/posts` and opts in to the `tags` taxonomy.
Fails if `NAME` already exists.

### `bartleby new post`

Create a new content file under a content type.

```
bartleby new post TITLE [--type TYPE]
```

`--type` defaults to `blog`.
The command slugifies the title to name the file, and writes it to the content type's `path` under `content/`.
The front matter stub holds `title`, `date` (today, in ISO format), and `draft: true`.
Fails if the content type is not declared in `bartleby.yml`, or if the file already exists.

## `bartleby build`

Render the site.

```
bartleby build [--include-drafts] [--strict] [--dry-run]
```

- `--include-drafts` includes pages with `draft: true`.
- `--strict` fails the build on any unresolved cross-reference.
- `--dry-run` renders into a temporary directory, compares the result with the existing `site/`, and reports what would change.
  It writes nothing.

Output goes to `site/` next to `bartleby.yml`, or to the directory named by `output_dir`.
The new output replaces the old one only when the whole build succeeds.
On success, the command prints a summary line such as `Built 62 pages (5 static files) into site/`.
A dry run prints `dry run: A added, M modified, U unchanged, D deleted`, followed by one line per changed path.

## `bartleby validate`

Check the config and content without rendering the site.

```
bartleby validate
```

The command checks metadata against each content type's schema, author references, URL generation, `template:` overrides in front matter, and cross-references.
On success, it prints `validation passed (N files checked)`.
On failure, it prints `validation failed`, then one line per error in the form `<file>:<line> [<code>] <field>: <message>`.

## `bartleby lint`

Check content quality.

```
bartleby lint [--check-external]
```

| Rule | Severity | Meaning |
|------|----------|---------|
| `broken-crossref` | error | A `.md` link resolves to no page. |
| `missing-description` | warning | A page has no `description` in its front matter. |
| `orphaned-page` | warning | A page is not in the navigation and no other page links to it. |
| `broken-external` | error | An external link is unreachable. Only checked with `--check-external`. |

`--check-external` probes each external URL with a HEAD request.
The check is off by default, so a plain `lint` never touches the network.
When there are no findings, the command prints `lint: no issues`.
The command exits 1 only when it finds errors.

## `bartleby serve`

Run the development server.

```
bartleby serve [--host HOST] [--port PORT] [--events]
```

- `--host` defaults to `dev_server.host` from the config, which defaults to `127.0.0.1`.
- `--port` defaults to `dev_server.port`, which defaults to `8000`.
- `--events` prints one JSON object per line on stdout for each change and rebuild.
  The `type` key is `change`, `rebuild`, or `error`.

The server always includes drafts.
Every change triggers a full rebuild, because Bartleby has no incremental build.
A failed rebuild keeps serving the last good output.

## `bartleby render`

Render one content file without a full build, for fast feedback.

```
bartleby render PATH [--format {html,markdown,metadata}]
```

`PATH` is the page's source path relative to `content/`, as `content list` shows it.
`--format` defaults to `html`.
`markdown` prints the source after shortcodes run, and `metadata` prints the title and path.
With `--output json`, every format also returns the URL, word count, and reading time.
The command never touches `site/`.

## `bartleby schema`

Print a schema for agents.

```
bartleby schema TARGET
```

`TARGET` is a content type name, `authors`, or `taxonomies`.
See [Agent output formats](agent-surface.md#bartleby-schema) for the output shapes.

## `bartleby content`

Query the site's published content.

```
bartleby content list [--type TYPE] [--sort {date,title,path}] [--limit N]
bartleby content get PATH
```

`list` returns the path, title, date, content type, URL, and draft flag of each published page.
`--sort` defaults to `date`, newest first.
`get` returns one page's metadata, raw Markdown body, and word count.
`PATH` is the source path, as `list` shows it.

## `bartleby export`

Export published content for other tools.

```
bartleby export [--format {jsonl,json,csv}] [--type TYPE]
                [--include-content] [--include-html] [--file FILE]
```

- `--format` defaults to `jsonl`.
- `--type` limits the export to one content type.
- `--include-content` adds each page's Markdown body.
- `--include-html` adds an `html` field with each page's rendered body.
  The export runs the build's own render phase to get it, so the field holds the same HTML the built page embeds.
  It writes no `site/` output.
  Plugin hooks run too: see [hooks during export](plugin-hooks.md#hooks-during-export).
- `--file` writes to a file and prints `wrote FILE`. Without it, the export goes to stdout.

## `bartleby generate-skill`

Generate agent skills from the site's content types, authors, and taxonomy terms.

```
bartleby generate-skill [--force]
```

The command writes `bartleby-write.md`, `bartleby-review.md`, and `bartleby-ops.md` to `ai.skills.output_dir`, which defaults to `.claude/skills`.
The output is deterministic, so `--force` changes nothing.
See [Agent output formats](agent-surface.md#generated-skills) for what each skill contains.

## `bartleby theme`

Work with the active theme.

### `bartleby theme compile`

```
bartleby theme compile [--refresh]
```

Recompile the theme's CSS with the Tailwind standalone tool.
The result includes your design tokens and project templates.
`--refresh` downloads the Tailwind binary again.
The build uses the compiled style sheet at `.bartleby/theme.css` when the file is current.

### `bartleby theme eject`

```
bartleby theme eject [--to DIR] [--force]
```

Copy the active theme chain, flattened, into one directory you can edit.
`--to` defaults to `themes/<theme-name>` in the project.
`--force` overwrites files in an existing destination.
The command prints the `theme:` block to add to `bartleby.yml`.

### `bartleby theme inspect`

```
bartleby theme inspect
```

List every theme file with the layer that provides it.
The first line names the theme and its chain, such as `Theme scrivener (chain: scrivener -> base)`.
A file that your `overrides/` directory replaces gets a `[shadowed by overrides/...]` note.
With `--output json`, the command returns `status`, `theme`, `chain`, and `files`.
See [Themes](themes.md#bartleby-theme-inspect) for the fields of each file.

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | The command succeeded. |
| `1` | The command ran and found a problem: a build, config, author, theme, or content error, a failed `validate`, or a `lint` error. |
| `2` | Usage error: no `bartleby.yml` at the resolved path, an unknown content type, a missing page, an existing target directory, or an invalid argument. |

## Error Output

With `--output text`, errors go to stderr in the form `error [code] message`.
With `--output json`, an error is a JSON object on stdout with `error` and `code` keys, and a `file` key when one applies.
The codes are `usage_error`, `build_error`, `config_error`, `author_error`, `content_error`, `theme_error`, `theme_compile_error`, and `agent_surface_error`.
Each message follows one shape, described in [Error messages](errors.md).
