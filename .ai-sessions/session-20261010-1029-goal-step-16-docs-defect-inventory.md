# Session Summary: Catalog Every Docs Rendering Defect

**Date**: 2026-10-10
**Duration**: about 45 minutes
**Conversation Turns**: implement, validator x1, finalize
**Estimated Cost**: not tracked
**Model**: claude-sonnet-5-5

## Goal Context

- **Condition**: Plan Step 16 of the 0.1.x theme system plan, driven by /bpe:goal
- **Mode**: full
- **Outcome**: converged (validator clean at iteration 1; step committed and pushed)
- **Steps completed**: Step 16 of the plan; opens Section 5

## Key Actions

- Step 16 is a task step. The only repo change is the todo.md checkoffs. The deliverable is a scratchpad inventory (`step16/docs-defects.md`), not committed by plan design, so its essentials are recorded here.
- Built `docs/` on scrivener and on material from temp copies. Both builds exit 0 with 62 pages and no warnings. `bartleby lint` reports zero issues. Every defect below is invisible to those gates, so Step 17 needs its own checks: the mechanical sweep script (hrefs, raw shortcode syntax, titles, body length) plus Vale (`vale docs/content`).
- Walked pages in headless Chromium at 1280x1000 and classified each page by Diataxis type. The section split is clean at the directory level; the mismatches are drift inside pages, so nothing moves between sections.

### Inventory Counts (149 entries)

| Category | Entries |
|---|---|
| link | 4 |
| render | 4 |
| stub | 0 |
| stale-config | 11 |
| stale-fact | 35 |
| diataxis | 18 |
| dash | 24 files (146 lines, 104 Vale hits) |
| visual | 6 |
| style | 32 |
| gap | 7 |
| engine | 8 |

Notes: 27 content files. Dash entries are one per file. Vale reported 438 alerts; false positives to suppress, not fix: "content type" to "media type" (18), "CLI" (7), "highlighting" (2), Headings on code identifiers. Real fixes: Latin e.g./etc., ThereIs, BadWords, Weasel, Adverbs, Passive, Modals, OxfordComma. One-sentence-per-line fires 93 times in 26 files. Spelling mixes British forms ("behaviour", "organised") into 13 files; normalize to American. The metadata schema block, the `@event_priority` block, and the hook tables are duplicated across concepts, guides, and reference.

### Step 17 Work List (24 items, in order)

1. docs/bartleby.yml: theme.name scrivener, eight-feature list, keep color_mode toggle
2. guides/index.md: fix or delete the broken `posts/*.md` links
3. reference/index.md: fix or delete the broken `pages/*.md` links
4. reference/pages/configuration.md: rewrite the theme section to the native vocabulary
5. reference/pages/plugin-hooks.md: drop "(reserved)" labels and the Reserved hooks section
6. reference/pages/build-pipeline.md: hook locations, summary line, async_build, theme resolution, agent outputs
7. reference/pages/cli.md: add missing subcommands, fix flags, exit codes
8. quickstart.md: scaffold tree, draft handling, output tree
9. index.md: replace "Material-style theme" bullet, CLI bullet, agent-surface copy
10. installation.md: subcommand list, "There are no" wording, source install
11. guides/posts/override-theme-template.md: rewrite for theme system and `theme eject`
12. guides/posts/validate-metadata.md: paste real validate output
13. guides/posts/ai-crawler-directives.md: move "Why This Matters" to the agents concept page
14. inject-content-with-hook, add-jinja-filter, write-a-shortcode: excerpt backticks, audience, long `allow=` line
15. concepts/agents-and-llms.md: add schema.json, content-index.json, generate-skill; cut repeats
16. concepts/templates.md: fix the reversed override order sentence (line 50)
17. concepts/plugins-and-hooks.md: reconcile the "no public plugin API" claim
18. concepts/front-matter.md: resolve `title` required vs default; trim tables
19. markdown-pipeline, content-organization, customization-seams, taxonomies, urls: trim reference drift; add theme seam
20. reference front-matter-fields, shortcodes, template-context: title default, shortcode search path, theme context
21. All 24 dash files: replace em dashes (includes front matter descriptions)
22. All files: Title Case headings, one sentence per line, American spelling, real Vale fixes
23. Record engine bugs E1-E8 for later sections; fix the docs path form in Step 17's Verify command
24. Verify: build and lint from `docs/`, rerun the sweep, Vale has no error-level hits, rescreenshot guides, reference, quickstart on scrivener

### Engine Bug Routing (E1-E8)

- E1: listing intros skip cross-reference rewriting (listings.py renders the intro via render_markdown and bypasses resolve_all_crossrefs). This causes the .md 404 links in guides/index.md and reference/index.md. Route to Step 17, fixed TDD in the engine.
- E2: listing excerpts show literal backticks. Route to Step 17.
- E3: duplicate tag pages at /tags/, /guides/tags/, /reference/tags/. Step 17 investigates config versus engine.
- E4: the base head emits a text/markdown alternate link for 404 and tag pages that have no .md variant. Route to Step 22 (Markdown variants).
- E5: guides/ and reference/ have no sidebar or TOC on scrivener. Route to Step 19.
- E6: reference listing rows have a blank date column. Route to Step 19.
- E7: two switches for the color-mode toggle, the `color-mode.toggle` feature versus `theme.color_mode.toggle`. Route to Step 20 (DX). Step 17 keeps both set in docs/bartleby.yml.
- E8: plan and todo Verify lines use the invalid `bartleby build docs/` and `bartleby lint docs/` forms. Executors are told the working form: `(cd docs && uv run bartleby build)` or `--config docs/bartleby.yml`.

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| Mode: implement, Step 16 | Built, linted, walked, classified, wrote scratchpad inventory | Dirty tree (todo.md only) |
| Validator, iter 1 | Checked entries have path plus defect | Clean; one info finding |
| Mode: finalize, Step 16 | just check, summary, lessons, commit, push | Single signed commit on v0.1.1 |

## Deviations from Plan

- Plan said: `bartleby build docs/` and `bartleby lint docs/`.
- Deviated: those forms exit 2; ran from inside `docs/` with no path argument.
- Impact: recorded as E8 for Step 17.

## Process Notes

- Info finding carried: the inventory's fired-hooks list for plugins-and-hooks.md omits `on_config` (build.py:249) and `on_page_markdown` (build.py:370). Step 17 should derive the fired set from build.py directly.
- The scratchpad inventory is not durable; this summary is the record.
- lessons.md: one lesson added; Recent kept at 10.

## Suggested Skills for Next Session

- content-design:diataxis
- content-design:style-linting
- python:python
