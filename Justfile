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
# Tailwind standalone CLI. bartleby.theme_compile owns the content globs (the
# same ones a user site compiles with), so templates never need a hand-kept
# safelist; each src/bartleby/themes/<name>/ with a tailwind.css is compiled
# into its own static/css/main.css. The wheel ships the resulting files; end
# users never run this. Needs a `tailwindcss` binary on PATH or in the bartleby
# cache (pass `--binary PATH` through `just theme-css --binary PATH`).
theme-css *args:
    uv run python -m bartleby.theme_compile {{args}}
