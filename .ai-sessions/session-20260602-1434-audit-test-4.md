# Session Summary: Audit Test 4 — Commit History Walk

**Date**: 2026-06-02
**Duration**: ~15 minutes
**Model**: Claude Opus 4.7 (1M context)

## Key Actions

- Walked the full 34-commit v1 branch history.
- Deep-dove the four commits flagged in review.md as architecturally
  load-bearing: Step 4 (parse_front_matter, had a bug-fix loop),
  Step 8 (template cascade, the architectural backbone), Step 10
  (MVP build pipeline orchestrator), Step 21 (plugin system).
- Wrote Test 4 to audit.md with per-step findings + 3 cross-cutting
  patterns.
- Added 7 new "Design 1-7" rows to the top-of-file outstanding-work
  tracker so the findings are queued alongside the existing
  deferrals.
- Updated the ship-0.1.0 punch list to call out Designs 3, 4, 5 as
  real 0.2.0 architectural cleanup targets (Design 3 is the root
  cause of Bugs 1 + 2 from Test 1).

Docs-only commit. No code changes.

## Headline findings

- **Design 3 — `build_page_context` flattens Page into a dict.** The
  hand-built `page_namespace` dict in templates.py is a closed schema
  that doesn't expose new Page fields automatically. This is why
  Bug 1 (`authors` exposed as raw key strings) and Bug 2
  (`custom_metadata` not exposed at all) survived to release. The
  d212d95 commit patches the symptoms; the real fix is to pass the
  Page dataclass directly to templates.
- **Design 4 — `on_pages` fires before draft filter.** Plugins
  operate on pages that won't ship.
- **Design 5 — No per-page error isolation.** Build aborts on the
  first bad page.
- **Design 6 — `KNOWN_EVENTS` has 17 entries; BasePlugin has 16
  methods.** `on_pages` slipped through.
- **Design 1 + 2 — `parse_front_matter` paper cuts.** Too-loose
  start detection + silent non-dict YAML swallow.
- **Design 7 — Magic strings everywhere.** `"taxonomy_kind"`,
  `"listing_kind"`, etc. should be enums.

## Verification

- `audit.md` Test 4 section is complete with per-step findings and
  cross-step patterns.
- Tracker table at top of audit.md now has 7 new Design rows.
- No code changes; nothing to test.

## Suggested Skills for Next Session

- None for the audit itself. Tests 5 and 6 remain on the review.md
  list (spec-vs-implementation lint; /ultrareview).
