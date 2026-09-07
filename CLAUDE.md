# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Bartleby is an agents-first, batteries-included Python static site generator. The full specification is in `spec.md`.

**Positioning (confirmed 2026-08-08):** Bartleby leads as an *agents-first* SSG. Its differentiator is treating AI crawlers and coding agents as a first-class audience alongside humans: per-page Markdown variants, `llms.txt`/`llms-full.txt`, `schema.json`, `content-index.json`, JSON-LD, and deterministic skill generation. This is a deliberate choice not to compete with Zensical (the Material for MkDocs team's Rust-core, docs-focused rewrite) on build performance or docs-team ergonomics. Solid docs/blog output is table stakes; the agent surface is where the work goes. Bartleby stays MIT and free (see the strategic-direction note in memory).

## Architecture

Bartleby has 27 independently testable components (see spec.md "Component Boundaries"). The key architectural decisions:

- **Frontend stack**: Tailwind CSS + Alpine.js + HTMX + lunr.js (reimplemented, NOT ported from mkdocs-material)
- **Async build**: asyncio orchestrator with `ProcessPoolExecutor` for CPU-bound markdown rendering. All plugin hooks run in the main process — only `markdown.convert()` is dispatched to workers.
- **Co-located assets**: Non-markdown files in `content/` follow the page's output URL, not the source path (Hugo-style page bundles)
- **Extension ordering**: markwright.fence preprocessor (priority 40) runs BEFORE pymdownx.superfences (priority 25). The fence postprocessor then injects results AFTER superfences generates HTML.

## Tech Stack

- Python 3.14+, uv for package management
- Python-Markdown + pymdownx + markwright for rendering
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

## Module style (YAML-backed modules)

Bartleby has several modules that parse YAML config or content into typed dataclasses. They all share the same skeleton — reuse it when adding new ones:

- `from __future__ import annotations` at the top so type hints are strings
- `if TYPE_CHECKING:` block for runtime-unused imports (`Path`, sibling-module types) to keep them out of the runtime import graph and silence ruff `TC003`
- Type the YAML boundary as `Any` (because `yaml.safe_load` returns `Any`), then narrow with `isinstance` checks inside per-section parse helpers — keeps mypy strict happy without casting churn
- Use `@dataclass(slots=True)` for the typed result objects; `field(default_factory=...)` for mutable defaults
- Custom exception type per module (`ConfigError`, `AuthorError`, `ShortcodeError`, …) with a structured field where helpful (e.g. `ConfigError(message, key_path)`)

Look at `src/bartleby/config.py` and `src/bartleby/authors.py` for the canonical patterns.

## Key Specs to Reference

- `spec.md` — Complete project specification (canonical source of truth)
- Build pipeline: 30 steps (spec.md "Build Pipeline > Order of Operations")
- Plugin hooks: 16 hooks (spec.md "Plugin System > Plugin API Hooks")
- Template lookup: 5-level cascade (spec.md "Template System > Template Lookup Order")
- Agent integration: structured CLI, schema introspection, skill generation (spec.md "AI & Agent Integration")
