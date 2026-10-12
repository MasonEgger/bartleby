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

The help output lists the top-level subcommands: `new`, `build`, `validate`, `serve`, `schema`, `content`, `render`, `lint`, `export`, `generate-skill`, `theme`, `config`, `enable`, and `disable`.

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

## Your First Run

A scaffold builds with no extra setup and renders on the `scrivener` theme:

```bash
bartleby new site mysite
cd mysite
bartleby build
```

Bartleby prints a list of what it created and `Next: cd mysite && bartleby serve`, then `Built 2 pages (12 static files) into site/`.
Run `bartleby serve` to see the welcome page and the feature tour.
To see the Material look instead, set `theme.name: material` in `bartleby.yml`.

## Next Step

With Bartleby installed, follow the [Quickstart](quickstart.md) to go through that first run step by step.
