# Session Summary: Promote Unaddressed Findings to Audit Tracker

**Date**: 2026-06-02
**Duration**: ~5 minutes
**Model**: Claude Opus 4.7 (1M context)

## Key Actions

Swept audit.md for findings I'd documented in prose (Tests 3 and 4)
but never elevated to the top-of-file tracker. Added 11 new rows so
the tracker is the complete punch list:

- **Design 8–13** (6 design observations from Test 4 that lived in
  per-step prose):
  - Design 8: `resolve_template_name` claims "6-level cascade" but
    has 7 (unconditional `page.html` fallback)
  - Design 9: silent fall-through return — error could name the
    candidate list
  - Design 10: hardcoded output path `project_dir / "site"`
  - Design 11: import-inside-function in `build()` (cosmetic)
  - Design 12: hook files can't import siblings from `hooks/`
  - Design 13: no hook-reload story (matters once Deferral 6 lands
    the watchdog)
- **TestGap 1–5** (5 test-suite gaps from Test 3 not addressed by
  the d212d95 content-assertion batch):
  - TestGap 1: `test_listings.py` never renders the list template
    (the gap that let Bug 2 ship)
  - TestGap 2: theme tests string-match raw CSS file contents
  - TestGap 3: `test_server.py` never exercises `DevServer.run()`
  - TestGap 4: `test_async_build.py` is tautological
  - TestGap 5: no CI smoke test mimicking manual Test 1

Refreshed the punch list with the new findings. Added a totals
line: **5 fixed, 26 open, 2 release-blocking**.

Docs-only commit. No code changes.

## Verification

- Top-of-file tracker now has 31 rows (5 bugs + 8 deferrals + 1 hook
  config + 13 designs + 5 testgaps + 4 design rows that already
  existed).
- Wait — let me actually recount. The tracker rows are:
  - Bug 1, 2, 3, 4 (4 rows)
  - Deferral 1, 2, 3, 4, 5, 6, 7, 8 (8 rows)
  - Hook config (1 row)
  - Design 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13 (13 rows)
  - TestGap 1, 2, 3, 4, 5 (5 rows)
  - = 31 total rows
- Status counts: 5 fixed (Bugs 1-4 + Deferral 5), 26 open (everything
  else except the hook config note which lives in later.md), 2
  release-blocking (Deferral 1 + Deferral 6).

## Suggested Skills for Next Session

- None for the audit itself. Tests 5 and 6 remain on the review.md
  list. Or move to addressing the queued deferrals.
