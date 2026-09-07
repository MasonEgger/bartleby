# Session Summary: Audit Playbook for Handoff Agent

**Date**: 2026-06-03
**Duration**: ~10 minutes
**Model**: Claude Opus 4.7 (1M context)

## Key Actions

Mason wants to hand the 37-item audit tracker to another agent to
fix every open item, then run audit pass 2 on the result. Enriched
audit.md so the receiving agent can start cold.

Added a "Fix-it playbook for the next agent" section (9
subsections, ~325 lines) right after the tracker:

0. **Snapshot at handoff** — branch `v1` at `853ab2c`, 282 tests
   green, 4 uncommitted files (Deferral 8 — to review not blindly
   commit), 37 open punch list items.
1. **Project orientation** — tech stack table, directory layout,
   spec/plan/doc inventory.
2. **Conventions** — code style (ABOUTME, mypy strict, ruff,
   TDD), `just check` as the verification gate, BPE-loop commit
   workflow (`/bpe:session-summary` → `/bpe:commit-message` →
   `git commit -S -F commit-msg.md` → `git push`), 8-step
   per-fix recipe.
3. **Items the agent must NOT decide alone** — Meta 1
   (license), Spec 1 (ship-vs-reword Phase 5), Deferral 8 (which
   diffs to commit), TestGap 5 (CI provider). Conservative
   defaults documented if Mason isn't reachable.
4. **Item dependencies** — 6 pairs of items that should land
   together to avoid rework.
5. **Recommended fix order** — Path B first (one afternoon, 5
   items closed, no architectural risk), then Path A (4 items,
   genuinely shippable after), then the long tail in tracker
   order.
6. **How to verify findings are still real** — per-category
   shell one-liners. Critical because findings were written
   2026-06-02 and another agent may have touched them already.
7. **How to know you're done** — concrete completion criteria.
8. **Out of scope** — don't merge to main, don't skip the
   pre-commit hook, don't touch later.md, don't pivot to Phase 5
   without approval, don't delete session summaries, don't bump
   the version.
9. **When in doubt** — escalation reading order plus
   `<CLAUDE_HELP>` block convention for surfacing questions.

Also added a pointer at the very top of audit.md so the playbook
is the obvious next stop after the tracker.

## Verification

- audit.md grew from ~1330 lines to 1691 lines.
- Section headers: Tracker → **Playbook** → Tests 1–6 → Next
  session paths. Reading order is clean.
- `just check` green (282/282 tests pass; ruff + mypy clean).
- Working tree still has the 4 Deferral 8 files uncommitted as
  expected; not staging those.
- No code changes.

## Out of scope for this session

- Did not fix any of the 37 tracker items (that's the handoff
  agent's job).
- Did not change `later.md` (out of band).
- Did not touch the working-tree Deferral 8 diffs.

## Suggested Skills for Next Session

- For the handoff agent: `python:python` for almost everything.
- For audit pass 2 (after the handoff): no special skill needed,
  just `bash`/`grep` over the tracker to verify each fixed item.
