# Session Summary: Depend on markwright from PyPI

**Date**: 2026-09-15
**Duration**: short
**Conversation Turns**: 1 (follow-up after the v1 remediation cycle)
**Estimated Cost**: low
**Model**: Opus 4.8

## Key Actions

- Confirmed `markwright` 0.1.0 is published on PyPI (requires-python >=3.11, compatible with bartleby's 3.14 floor).
- Removed the `[tool.uv.sources]` editable override (`markwright = { path = "../do-markdown", editable = true }`) from `pyproject.toml`, leaving the plain `markwright>=0.1.0` dependency to resolve from PyPI.
- Regenerated `uv.lock`: markwright now records `source = { registry = "https://pypi.org/simple" }` with sdist + wheel hashes; no `do-markdown` path remains in the lock or pyproject.
- Verified `just check` green (566 tests, ruff, mypy strict, smoke).

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| Use markwright from PyPI rather than vendor | Dropped editable uv source, relocked, verified | markwright resolves from PyPI; just check green |

## Observations

- Bartleby is now installable by anyone via the published markwright wheel; it no longer needs the sibling `../do-markdown` checkout on disk. This removes the build-environment coupling that broke `just check` earlier in the cycle.
- Supersedes the [[bartleby-toolchain-notes]] point about depending on the sibling checkout.

## Suggested Skills for Next Session

- `python:python`: any further packaging or dependency work.
