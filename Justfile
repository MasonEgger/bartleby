# Bartleby development commands

default: check

check: lint typecheck test

lint:
    uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/

typecheck:
    uv run mypy src/

test:
    uv run pytest

format:
    uv run ruff format src/ tests/

# Package-build step: compile the shipped theme CSS from the bundled templates
# plus the curated safelist using the real Tailwind standalone CLI. The wheel
# ships the resulting static/css/main.css; end users never run this. Requires a
# `tailwindcss` binary on PATH (the same pinned version bartleby downloads on
# demand for `bartleby theme compile`).
theme-css:
    tailwindcss \
      --content 'src/bartleby/theme/templates/**/*.html' \
      --content 'src/bartleby/theme/safelist.txt' \
      --output src/bartleby/theme/static/css/main.css \
      --minify
