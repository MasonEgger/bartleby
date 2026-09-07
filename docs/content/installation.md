---
title: "Installation"
description: "Install Bartleby with uv or pip and verify it works."
---

Bartleby requires Python 3.14 or newer. There are no Node.js prerequisites — the bundled theme ships with pre-vendored assets.

## Install with uv

`uv` is the recommended installer:

```bash
uv pip install bartleby
```

For a project-local install you'd usually add it to a project:

```bash
uv add bartleby
```

## Install with pip

```bash
pip install bartleby
```

## Verify the install

```bash
bartleby --help
```

You should see the top-level subcommands: `new`, `build`, `validate`, `serve`.

## Install from source

Clone the repository and install in editable mode for development:

```bash
git clone https://github.com/MasonEgger/bartleby.git
cd bartleby
uv sync
uv run bartleby --help
```

The dev dependencies (`ruff`, `mypy`, `pytest`) install automatically with `uv sync`. The `just check` target runs lint, type-checking, and the full test suite.

## Next step

With Bartleby installed, follow the [Quickstart](quickstart.md) to scaffold and build your first site.
