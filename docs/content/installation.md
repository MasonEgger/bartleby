---
title: "Installation"
description: "Install Bartleby with uv or pip and verify it works."
---

Bartleby requires Python 3.14 or newer.
Bartleby needs no Node.js, because the bundled themes ship pre-built assets.

## Install with `uv`

`uv` is the recommended installer:

```bash
uv pip install bartleby-ssg
```

To add Bartleby to an existing project instead, run:

```bash
uv add bartleby-ssg
```

## Install with pip

```bash
pip install bartleby-ssg
```

## Verify the Install

```bash
bartleby --help
```

The help output lists the top-level subcommands: `new`, `build`, `validate`, `serve`, `schema`, `content`, `render`, `lint`, `export`, `generate-skill`, and `theme`.

## Install from Source

Clone the repository to work on Bartleby itself:

```bash
git clone https://github.com/MasonEgger/bartleby.git
cd bartleby
uv sync
uv run bartleby --help
```

`uv sync` installs the dev dependencies (`ruff`, `mypy`, `pytest`).
The `just check` target runs the linter, the strict type check, the test suite, and an end-to-end smoke test.

## Next Step

With Bartleby installed, follow the [Quickstart](quickstart.md) to scaffold and build your first site.
