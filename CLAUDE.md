# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Bartleby is an agents-first, batteries-included Python static site generator. The full specification is in `spec.md`.

**Positioning (confirmed 2026-08-08):** Bartleby leads as an *agents-first* SSG. Its differentiator is treating AI crawlers and coding agents as a first-class audience alongside humans: per-page Markdown variants, `llms.txt`/`llms-full.txt`, `schema.json`, `content-index.json`, JSON-LD, and deterministic skill generation. This is a deliberate choice not to compete with Zensical (the Material for MkDocs team's Rust-core, docs-focused rewrite) on build performance or docs-team ergonomics. Solid docs/blog output is table stakes; the agent surface is where the work goes. Bartleby stays MIT and free (see the strategic-direction note in memory).

## Architecture

Bartleby is 32 single-responsibility modules under `src/bartleby/`, grouped by build-pipeline phase (see spec.md "Component boundaries"). The key architectural decisions:

- **Frontend stack**: Tailwind CSS + Alpine.js + HTMX + lunr.js (reimplemented, NOT ported from mkdocs-material)
- **Synchronous build**: `build()` in `build.py` runs the whole pipeline in-process. `async_build()` is only an `asyncio.to_thread` wrapper used by the dev server. Parallel and incremental builds are explicit non-goals (spec.md).
- **Co-located assets**: Non-markdown files in `content/` follow the page's output URL, not the source path (Hugo-style page bundles)
- **Theme system (plan.md Section 1 landed; scrivener sources landed in Step 11, templates follow in Steps 12-14)**: the old hardwired `theme/` package is gone. Resolution goes through `theme_loader.py` plus bundled themes under `themes/` (`base`, `material`, `scrivener`). The default theme (`DEFAULT_THEME_NAME`) is `scrivener`; until Step 12 it has no templates of its own and no compiled `main.css`, so a site with no theme config renders base's unstyled fallbacks. Tests that need material must name it through `tests/theme_helpers.py::material_theme()`. `base` owns the search engine: `themes/base/static/js/search.js` exposes the Alpine component `bartlebySearch` (refs `trigger` and `input`; the highlight flag arrives as `data-highlight` with `tojson` on the script tag), loaded from `base.html` when `search` is on. Theme search partials are markup only. A theme is a directory with a `theme.yml` manifest, selected by `theme.name`, `theme.path`, or `theme.package`, composable with `extends`, and exposed whole by `bartleby theme eject` and `theme inspect`. The theme vocabulary is Bartleby-native; do not add mkdocs-material alias keys. Each theme's `tailwind.config.js` owns its safelist (it reads the sibling `safelist.txt`), because the compile passes `--content`, which overrides config content; a component class in `tailwind.css` that no template references must be listed there or Tailwind purges it. Nav directory targets (`dir/`) and auto-nav sections expand into sections in `navigation.py` (pages as children sorted by title, subdirectories nested, `index.md` supplies `url`/`index_url` and stays the first child), except directories that are or contain a content-type path, which stay plain listing links. `build.py` sets `page.toc` from the renderer's `toc_tokens` for every theme.
- **Color mode**: `themes/base/templates/base.html` owns the inline pre-paint script that sets `data-theme` (stored choice in localStorage `bartleby-color-mode`, then `theme.color_mode.default`, then `prefers-color-scheme`). Themes with a toggle write that same key; do not duplicate the script per theme.
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
just check                 # The gate: ruff lint + format check, mypy strict, pytest, e2e smoke
just lint | typecheck | test | smoke | format   # Individual targets
just theme-css             # Recompile the shipped theme CSS (needs tailwindcss on PATH; package-build only)
uv run pytest tests/test_config.py  # Run single test file
uv run pytest -k "test_name"        # Run single test by name
(cd docs && uv run bartleby build)  # Build the docs site (itself a Bartleby site; output in docs/site/, gitignored)
```

Hold every diff to `just check`; `uv run pytest` alone skips ruff, mypy, and the smoke test.

## Code Style

- All files start with a 2-line comment: first line prefixed with `ABOUTME: ` (grep-friendly)
- Strict type hints everywhere: mypy strict mode, no `Any` escape hatches
- Test-driven development: write tests first, then minimal code to pass
- Single responsibility per function/module
- Validate at system boundaries only (trust internal code)
- Never name things "improved", "new", or "enhanced": names must be evergreen
- Preserve existing code comments unless actively false
- Do not add error handling for impossible scenarios

## Module style (YAML-backed modules)

Bartleby has several modules that parse YAML config or content into typed dataclasses. They all share the same skeleton; reuse it when adding new ones:

- `from __future__ import annotations` at the top so type hints are strings
- `if TYPE_CHECKING:` block for runtime-unused imports (`Path`, sibling-module types) to keep them out of the runtime import graph and silence ruff `TC003`
- Type the YAML boundary as `Any` (because `yaml.safe_load` returns `Any`), then narrow with `isinstance` checks inside per-section parse helpers; keeps mypy strict happy without casting churn
- Use `@dataclass(slots=True)` for the typed result objects; `field(default_factory=...)` for mutable defaults
- Custom exception type per module (`ConfigError`, `AuthorError`, `ShortcodeError`, …) with a structured field where helpful (e.g. `ConfigError(message, key_path)`)

Look at `src/bartleby/config.py` and `src/bartleby/authors.py` for the canonical patterns.

## Where Things Are Defined

- `spec.md` is the living product spec (canonical). Its sections: Starting context, Project overview, Available tooling, External tool candidates, Goals, Non-goals, Roadmap / phase log (with the Deferred list), Component boundaries, Success criteria. Nothing may implement a Non-goal or a Deferred item without a spec change first.
- `plan.md` and `todo.md` are the current BPE plan (26 steps, 8 sections) and its checkbox mirror. `.ai-sessions/` is tracked: session summaries and `lessons.md` are committed; only `implementation-notes.md` and `handoffs/` stay local. The BPE goal loop requires a new session summary in every commit.
- Plugin hooks: the 16 `on_*` methods on the base class in `plugins.py` are the public hook API.
- Template lookup: `template_search_bases()` in `templates.py` is the single source of truth for the cascade (project `overrides/`, `templates/`, project root, then the theme); `resolve_template_name()` picks the per-page candidate.
- Agent surface: `llm.py` (Markdown variants, `llms.txt`, JSON-LD), `agent_surface.py` (`schema.json`, `content-index.json`), `schema_introspection.py`, `skills.py` (deterministic skill generation). This is the differentiator; keep it the most consistent part of the tool.
