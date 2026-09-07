---
title: "CLI commands"
description: "Every bartleby subcommand and its flags."
tags:
  - cli
---

Bartleby ships a single `bartleby` executable backed by argparse. Run `bartleby --help` for the top-level usage.

## bartleby new site

Scaffold a new project directory.

```
bartleby new site NAME
```

Creates `NAME/` containing `bartleby.yml`, `.authors.yml`, `content/index.md`, and empty `templates/`, `static/`, and `hooks/` directories. Errors if `NAME` already exists.

## bartleby new post

Create a new content file under the chosen content type.

```
bartleby new post "Post Title" [--type TYPE]
```

`--type` defaults to `blog`. The title is slugified to produce the filename; the front matter stub includes `title`, `date` (today, ISO format), and `draft: true`. Errors if the content type is not declared in `bartleby.yml` or if the target file already exists.

## bartleby build

Render the site.

```
bartleby build [--include-drafts] [--strict]
```

- `--include-drafts` includes pages with `draft: true` in the output. Default is false.
- `--strict` (reserved) — currently parsed but not enforced; will fail the build on cross-reference and validation warnings in a future release.

Output goes to `site/` next to `bartleby.yml`. The directory is cleaned before each build. Prints a summary line on success: `Built N pages in T.TTs`.

## bartleby validate

Run config and metadata validation without rendering.

```
bartleby validate
```

Exits 0 on a clean config; exits 1 with errors listed on stderr otherwise. Useful in CI as a fast pre-build check.

## bartleby serve

Run the development server.

```
bartleby serve [--host HOST] [--port PORT] [--dirty]
```

- `--host` defaults to `dev_server.host` from config (typically `127.0.0.1`)
- `--port` defaults to `dev_server.port` from config (typically `8000`)
- `--dirty` enables incremental rebuilds for content-only changes; config and template changes still trigger a full rebuild

Drafts are always included in dev builds.

## Exit codes

| Command | Success | Failure |
|---------|---------|---------|
| `new site` | 0 | 1 (directory exists) |
| `new post` | 0 | 1 (no config / unknown type / file exists) |
| `build` | 0 | non-zero on metadata validation failure |
| `validate` | 0 | 1 (config or metadata error) |
| `serve` | (long-running) | 1 (no config) |
