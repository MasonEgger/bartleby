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
