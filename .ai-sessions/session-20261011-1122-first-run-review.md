# Session Summary: First-Run Review and Serve Fixes

**Date**: 2026-10-11
**Duration**: about 6 hours across two context windows
**Conversation Turns**: about 12 user turns
**Estimated Cost**: high (five comparison subagents with screenshots, plus two context windows)
**Model**: Claude Opus 5.5 (claude-opus-5-5), Sonnet 5.5 at the end

## Key Actions

- Scaffolded a site with `bartleby new site` in a temp directory and served it on the tailnet for a first-use review.
- Restyled `scrivener` against the unslop-ui rules: system sans, neutral palette, one accent, no double rules, margin bar, or italics.
- Replaced the color-mode text button with an icon switch shared from `base` (`partials/color_mode_toggle.html`).
- Moved the starter site into package data (`src/bartleby/scaffold/`) with a README, and made `new site` print the next command.
- Found and fixed three dev-server bugs test-first: a single-threaded server stalled behind an idle iOS preconnect, the reload script targeted the HTTP port, and the watcher rebuilt forever on its own open and close events.
- Ran five comparison subagents (MkDocs, Material, Sphinx with furo, Hugo, Zensical) under one protocol and published a private comparison artifact with a scorecard and proposed default experience.
- Collected Mason's product decisions for the next plan through AskUserQuestion: solo author first, Starlette plus uvicorn dev server, `bartleby enable <content-type> <name>` with a matching disable, per-type plus combined feeds, three-column layout with opt-in merge, home plus a feature tour as starter content, stay on 0.1.x.

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| Serve a fresh `new site` on the tailnet | Scaffolded in a temp dir, served on 8765 | Mason saw the first-use page |
| "That looks very AI", unslop-ui, README, icon toggle | Read the unslop-ui SKILL.md (Reddit was blocked), restyled scrivener, added scaffold README and switch | Restyle and toggle landed, tests added |
| Next step, serve output, blog default, tailnet, compare five tools | Fixed next-step and serve flushing, fixed three server bugs, dispatched five evaluators, built the comparison artifact | Artifact published; tailnet works |
| Decisions on Hugo-style output, docs default, async server, layout, markwright, licenses, skills | Asked three AskUserQuestion batches, saved memories, edited the global CLAUDE.md | Decisions recorded for the next plan |

## Efficiency Insights

**What went well:**
- A shared PROTOCOL.md let five evaluators produce comparable reports.
- Writing the idle-socket test first proved the stall came from `HTTPServer`, not Tailscale.

**What could improve:**
- Four evaluator subagents had Write denied for their reports; the protocol should have said where reports may go, or used the scratchpad.
- One evaluator ran `uv init` in another evaluator's directory; give each agent a hard path check.
- Questions went out as prose at first; Mason prefers AskUserQuestion.

**Course corrections:**
- Corrected a false claim that Hugo falls back to a free port after checking its real output.
- Killed a runaway serve process (94% CPU) and fixed the watcher loop that caused it.

## Process Improvements

- When a fix is "it doesn't load on another device", test concurrency (idle sockets, parallel requests) before blaming the network.
- Check a claim about another tool against a run of that tool before publishing it.

## Observations

- Bartleby leads on error messages, JSON output, and the agent surface, and trails on the first five minutes.
- The starter home page advertised feeds and highlighting that were broken; claims in a scaffold need their own tests.

## Suggested Skills for Next Session

- `bpe:plan`: the next step is a new plan built from the comparison and Mason's decisions.
- `python:python`: the plan is Python application work (dev server, enable command, feeds).
