# Bartleby development commands

default: check

check: lint typecheck test smoke

lint:
    uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/

typecheck:
    uv run mypy src/

test:
    uv run pytest

# End-to-end smoke gate: scaffold a site, add a post, build, and grep the
# rendered output. Run explicitly in CI so a regression in the full
# scaffold->build path fails the build even if narrower unit tests stay green.
smoke:
    uv run pytest tests/test_smoke.py

format:
    uv run ruff format src/ tests/

# Package-build step: compile each bundled theme's shipped CSS with the real
# Tailwind standalone CLI. Every src/bartleby/themes/<name>/ that has a
# tailwind.css is compiled into its own static/css/main.css, using its own
# tailwind.config.js when it has one; themes without sources are skipped. The
# wheel ships the resulting files; end users never run this. Requires a
# `tailwindcss` binary on PATH (the same pinned version bartleby downloads on
# demand for `bartleby theme compile`).
theme-css:
    #!/usr/bin/env bash
    set -euo pipefail
    for theme_dir in src/bartleby/themes/*/; do
      [ -f "${theme_dir}tailwind.css" ] || continue
      args=(--input "${theme_dir}tailwind.css" --output "${theme_dir}static/css/main.css" --minify)
      if [ -f "${theme_dir}tailwind.config.js" ]; then
        args+=(--config "${theme_dir}tailwind.config.js")
      fi
      tailwindcss "${args[@]}"
    done
