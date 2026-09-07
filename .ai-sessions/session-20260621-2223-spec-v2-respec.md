# Session Summary: Spec v2 re-spec (strategy, plugins, agent surface, feeds)

**Date**: 2026-06-21
**Duration**: multi-day thread (2026-06-12 through 2026-06-21)
**Conversation Turns**: ~14 user prompts
**Estimated Cost**: high (multiple parallel analyst subagents, large spec edits, two browser-review cycles)
**Model**: Opus 4.8 (1M context) for later turns; Fable 5 earlier

## Key Actions

- Ran a full project assessment (3 parallel Explore agents over spec/plan/audit + empirical test/lint/typecheck/smoke runs) and served an HTML dossier on the tailnet.
- Worked the venture question with `indie:idea` + `indie:venture-routing`: decided Bartleby is free MIT infrastructure, not a direct venture; sponsorware is the eventual funding path; adjacent products are the MicroSaaS plays. Captured to vault `raw/` and to project memory.
- Amended the `indie:idea` skill with the flagship-job carve-out (G1 exception + F6 flag) at the marketplace source, synced to cache.
- Re-specced spec.md (v2): Phase 5 agent integration into v1, hybrid Tailwind pipeline (`bartleby theme compile`), static agent surface (schema.json + content-index.json, llms.txt as discovery root), no MCP, build failure semantics (collect-all then fail, atomic site/ write), synchronous execution model (honest async), real vendored JS, full icon packs, feature-toggle enforcement, MIT + funding + 0.1.0 versioning policy.
- Ran `/bpe:review` on spec.md (55 decision units). Server kept dying to the background-task timeout and shell teardown; fixed by launching with `setsid`. Applied feedback via `/bpe:apply-review`: public plugin API (hooks/ AND entry-point packages) moved into v1; rejects on skill generation overridden after verifying intent (kept v1 generic deterministic skill).
- Added the site-wide aggregate feed under `site.feed` (empty `include: []` = all feed-enabled types; non-empty restricts; listing a type with no feed is a validation error) plus contextual auto-discovery `<link>` tags.

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| Assess project viability, serve HTML report | 3 parallel analysts + empirical runs, served dossier on tailnet | Delivered; B+ quality, viable-niche verdict |
| Questions about the future / monetization | indie skills, rubric pass | Decided: free MIT infra, sponsorware later |
| Update indie:idea with carve-out, start brainstorm | Skill edit + `/bpe:brainstorm` | Carve-out added; spec v2 decisions captured |
| `/bpe:review spec.md` | Generated 55-unit review page, served (setsid) | Reviewed and saved |
| `/bpe:apply-review` | Applied plugin-API change; overrode skill rejects after verify | spec.md updated |
| RSS design question | Analysis + design, then folded `site.feed` into spec | Aggregate feed specced |
| commit then `/bpe:plan` | This commit sequence | In progress |

## Efficiency Insights

**What went well:**
- Parallel Explore agents for the assessment kept the main context clean and returned only conclusions.
- Empirically running the smoke test (new site -> build) refuted a reviewer claim (front-matter leak) before it reached the report.

**What could improve:**
- The `/bpe:review` server died twice (background-task timeout, then nohup reaped on shell teardown) before `setsid` fixed it. Wasted two restarts.

**Course corrections:**
- Plugin strategy flipped twice: brainstorm said "both in v1," spec drafted as "staged/deferred," apply-review review comment flagged the conflict, resolved back to "both in v1." The spec now matches the brainstorm.

## Process Improvements

- Launch long-lived local review/preview servers with `setsid ... < /dev/null &` from the start so they survive shell teardown and the background-task timeout.
- When a brainstorm decision and the drafted spec diverge, the review's job is to catch it; the apply-review step did exactly that here.

## Observations

- The working tree accumulated spec changes across several turns (plugins, then feeds) without a commit. This commit clears that backlog before `/bpe:plan`.
- spec.md grew from ~2663 to ~2790 lines across the re-spec.

## Suggested Skills for Next Session

- `python:python` — `/bpe:plan` produces a TDD roadmap and the next execute-plan steps are Python/uv/pytest work.
