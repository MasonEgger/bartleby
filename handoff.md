# Bartleby v1 Remediation: Handoff

This is the entry point for the remediation cycle.
Read it, then `plan.md` for the step-by-step TDD prompts and `spec.md` for the per-requirement required behavior and acceptance criteria.
An implementation model should be able to start from this file alone.

## Current State

The branch is `v1`, a feature branch (not `main`), so committing here is fine.
The v1 build and the 0.1.0 hardening cycle are done and tagged in history at baseline commit `2a4dd91` ("Add packaging metadata for the 0.1.0 release").
A multi-agent code review of the `v1` branch on 2026-07-01 surfaced 34 candidate defects; 20 survived adversarial verification and were re-confirmed against this working tree with exact file and line references.
Those 20 defects are the whole scope of this cycle, written up as requirements R1 through R17 in `spec.md` (some requirements cover more than one defect).
Progress is 0 of 100: none of the 19 plan steps have started.

The v1 product spec (the canonical description of product behavior) is preserved in git and readable with `git show 2a4dd91:spec.md`.
Citations in `spec.md` of the form "v1 spec, Section Name (line N)" refer to that file, not to the current `spec.md`.

Working tree note: `spec.md`, `plan.md`, and `todo.md` are uncommitted remediation-cycle docs.
`plan.md` and `todo.md` are committed as part of this handoff; `spec.md` is left for Mason to commit himself.

## What To Build

Fix all 20 confirmed defects under strict TDD, in the order `plan.md` lays out.
The plan is organized into 7 phases; critical defects (R1, R2) come first, then the phases follow the dependency constraints in the spec's Component Boundaries section.

- R1, R2 are critical: the CLI does not import at all (a Python 2 `except` syntax error), and `bartleby theme compile` always fails on a clean machine (empty checksum map).
- R3 through R11 are high severity: a documented feature is broken or produces wrong output.
- R12 through R17 are medium: correctness and hygiene defects with a narrower blast radius.

Each step names the requirement(s) it closes.
Re-read that requirement in `spec.md` before writing the step's tests; the acceptance criteria there are the test list.
Every step ends with `just check` passing (pytest, ruff, mypy strict, `ruff format --check`, and the e2e smoke gate).

## Decisions The Review Settled

Two open questions were resolved before plan time.

1. **R8 (shared-directory asset bundle): loud build error, confirmed.**
   When two pages share a source directory that contains co-located assets, the build fails loudly with a `BuildError` naming the directory and both pages, routed through the R3 error contract.
   It does not guess a per-page association.
   Why: the v1 product spec assumes one page per bundle directory (the Hugo leaf-bundle model) and never defined the shared-directory case, so inventing an association rule would be new product behavior, which this no-behavior-drift cycle is not scoped for.
   The loud error keeps v1 semantics honest and pushes the user to restructure into one bundle per directory.
   Two pages in one directory with no co-located assets stay legal (nothing to mis-route).
   R8's required-behavior and test notes in `spec.md` already encode this; do not rewrite them.

2. **fountain-py integration: deferred to a v2 cycle.**
   Screenplay content support (fountain-py) is the next goal after this remediation, but it is feature work with its own brainstorm, spec, and plan.
   It does not belong in this cycle, which is scoped to the 20 confirmed defects under the no-behavior-drift rule.
   It is out of scope here and should not influence any remediation step.

## Shipping Context

Mason wants bartleby released soon.
This remediation cycle is the gate: once R1-R17 are closed and `just check` (including the extended e2e smoke test) passes, bartleby is ready to ship.
fountain-py integration is the likely next cycle (a v2 spec), started only after this remediation ships.

## Known Risks

- **R5 (live reload) is the largest requirement.** The change-detection primitives exist and are unit-tested, but nothing in `DevServer.run()` composes them, and no watchdog Observer or WebSocket server is started anywhere. The plan splits it into steps 13 (watcher wiring) and 14 (reload snippet plus WebSocket channel). Confirm `watchdog` and `websockets` are in `pyproject.toml`; add them if the v1 packaging step missed them.
- **Ordering dependencies are load-bearing, not cosmetic.** R3 (step 3) must land before R8 (step 6) and R16 (step 4), which both route through `BuildError`. R7's asset half (step 5) must land before R8 (step 6); both touch `copy_colocated_assets`. R4 (step 12) must land before R5 (steps 13-14); live reload serves the directory the watcher rebuilds into. Do not reorder across these.
- **The v1 e2e smoke test passed with an unimportable CLI.** Step 1 must investigate why (likely it called `build()` directly and never invoked the console entry point) and close that gap, or the same class of import regression ships again.
- **Two existing tests codify the bugs** and must be updated as part of the RED step, not treated as passing baselines: `tests/test_build.py:306` (asserts `pytest.raises(ValueError)` for the strict-crossref path) and `tests/test_listings.py:120` (asserts a substring that passes whether or not the intro renders).

## Next Action

Start Step 1 in `plan.md`: write the import-health tests in `tests/test_import_health.py` (RED), then fix the Python 2 `except` syntax at `src/bartleby/linting.py:205` to `except (URLError, ValueError, OSError):` (GREEN), which unblocks CLI import and lets the full suite run for the first time.
