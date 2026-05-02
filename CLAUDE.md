# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Bartleby is a batteries-included Python static site generator. The full specification is in `spec.md`. No code has been written yet — the project is in the implementation phase.

## Architecture

Bartleby has 27 independently testable components (see spec.md "Component Boundaries"). The key architectural decisions:

- **Frontend stack**: Tailwind CSS + Alpine.js + HTMX + lunr.js (reimplemented, NOT ported from mkdocs-material)
- **Async build**: asyncio orchestrator with `ProcessPoolExecutor` for CPU-bound markdown rendering. All plugin hooks run in the main process — only `markdown.convert()` is dispatched to workers.
- **Co-located assets**: Non-markdown files in `content/` follow the page's output URL, not the source path (Hugo-style page bundles)
- **Extension ordering**: do_markdown.fence preprocessor (priority 40) runs BEFORE pymdownx.superfences (priority 25). The fence postprocessor then injects results AFTER superfences generates HTML.

## Tech Stack

- Python 3.14+, uv for package management
- Python-Markdown + pymdownx + do-markdown for rendering
- Jinja2 for templates, argparse for CLI
- pytest for testing, ruff for linting, mypy (strict) for type checking
- Tailwind CSS standalone CLI for theme compilation (no Node dependency for users)

## Build & Development Commands

```bash
uv sync                    # Install dependencies
uv run pytest              # Run all tests
uv run pytest tests/test_config.py  # Run single test file
uv run pytest -k "test_name"        # Run single test by name
uv run ruff check .        # Lint
uv run ruff format .       # Format
uv run mypy src/           # Type check (strict mode)
```

## Code Style

- All files start with a 2-line comment: first line prefixed with `ABOUTME: ` (grep-friendly)
- Strict type hints everywhere — mypy strict mode, no `Any` escape hatches
- Test-driven development: write tests first, then minimal code to pass
- Single responsibility per function/module
- Validate at system boundaries only — trust internal code
- Never name things "improved", "new", or "enhanced" — names must be evergreen
- Preserve existing code comments unless actively false
- Do not add error handling for impossible scenarios

## Key Specs to Reference

- `spec.md` — Complete project specification (canonical source of truth)
- Build pipeline: 30 steps (spec.md "Build Pipeline > Order of Operations")
- Plugin hooks: 16 hooks (spec.md "Plugin System > Plugin API Hooks")
- Template lookup: 5-level cascade (spec.md "Template System > Template Lookup Order")
- Agent integration: structured CLI, schema introspection, skill generation (spec.md "AI & Agent Integration")
