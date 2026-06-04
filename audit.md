# Bartleby Audit

Running record of findings from the post-implementation evaluation framework
in [`review.md`](review.md). Each section corresponds to one numbered test.

> **Reading this cold?** Start with the **"Fix-it playbook for the next agent"**
> section right after the tracker. It has project orientation, conventions,
> verification recipes, dependencies between items, and a recommended item
> order. Each tracker row links to the deeper test section that explains the
> finding in full.

## Outstanding work — tracker

All issues across this audit at a glance. Detailed notes in each test
section below.

| ID | Severity | Area | Title | Status |
|---|---|---|---|---|
| Bug 1 | HIGH | Templates | Author bylines empty on every blog post | ✅ FIXED 2026-06-02 |
| Bug 2 | HIGH | Templates | Listing + taxonomy term pages render empty | ✅ FIXED 2026-06-02 |
| Bug 3 | MEDIUM | Scaffolding | New-site config doesn't opt blog into tags | ✅ FIXED 2026-06-02 |
| Bug 4 | LOW | Output | Sitemap omits listing + taxonomy URLs | ✅ FIXED 2026-06-02 |
| Deferral 1 | HIGH | Theme JS | Alpine/HTMX/lunr bundles are 200-byte stubs — theme interactivity is dead | 🔴 OPEN |
| Deferral 6 | HIGH | Dev server | `bartleby serve` has no watchdog + no WebSocket — no live reload | 🔴 OPEN |
| Deferral 2 | MEDIUM | Theme CSS | "Tailwind" is hand-written CSS; docs/spec misrepresent the styling stack | 🟡 OPEN |
| Deferral 3 | MEDIUM | Icons | Only 4 sample SVGs ship; `get_icon_path` returns None for everything else | 🟡 OPEN |
| Deferral 5 | MEDIUM | Crossrefs | `--strict` flag was parsed and ignored | ✅ FIXED 2026-06-02 |
| Deferral 7 | MEDIUM | Plugin hooks | 12 of 17 declared events never fire — user handlers silently no-op | 🟡 OPEN |
| Deferral 4 | LOW | Async build | `async_build` is `asyncio.to_thread(build)` — no real CPU parallelism | 🟢 OPEN |
| Deferral 8 | LOW | Working tree | Pre-existing uncommitted spec/plan + test-only diffs | 🟢 OPEN |
| Hook config | — | Tooling | Session-scoped Stop hook re-fires on met goals and over-claims process gaps | 📝 [later.md](later.md) |
| Design 1 | LOW | Content | `parse_front_matter` matches `---` without requiring newline after; misparse possible on docs starting `---foo` | 🟢 OPEN |
| Design 2 | LOW | Content | `parse_front_matter` swallows non-dict YAML silently (no error surfaced) | 🟢 OPEN |
| Design 3 | MEDIUM | Templates | `build_page_context` flattens `Page` into a hand-built dict — closed schema is why Bugs 1+2 happened. Pass the dataclass directly | 🟡 OPEN |
| Design 4 | MEDIUM | Build | `on_pages` hook fires BEFORE draft filter — plugins operate on pages that will be discarded | 🟡 OPEN |
| Design 5 | MEDIUM | Build | No per-page error isolation — one bad page aborts the whole build with a stack trace | 🟡 OPEN |
| Design 6 | LOW | Plugins | `KNOWN_EVENTS` has 17 names; `BasePlugin` has 16 methods. `on_pages` is missing from BasePlugin | 🟢 OPEN |
| Design 7 | LOW | Build | Magic strings (`"listing_kind"`, `"taxonomy_kind"`, `"term"`, `"index"`) should be StrEnum or constants | 🟢 OPEN |
| Design 8 | LOW | Templates | `resolve_template_name` docstring says "6-level cascade"; implementation has 7 (adds unconditional `page.html` fallback) | 🟢 OPEN |
| Design 9 | LOW | Templates | `resolve_template_name` silent fall-through (`return candidates[-1]`) — Jinja2 raises `TemplateNotFound` but the error could name the candidate list | 🟢 OPEN |
| Design 10 | LOW | Build | Output path hardcoded to `project_dir / "site"` — no config knob for users who want a different location | 🟢 OPEN |
| Design 11 | LOW | Build | `from bartleby.theme import get_theme_templates_dir as _theme_dir` lives inside `build()` instead of module-top — cosmetic | 🟢 OPEN |
| Design 12 | LOW | Plugins | Hook files can't import sibling modules from `hooks/` (directory not on `sys.path`). User workaround: install helpers as a package | 🟢 OPEN |
| Design 13 | MEDIUM | Plugins | No hook-reload story. When Deferral 6 lands the watchdog, changing a hook file won't re-register handlers; stale references could leak in `PluginCollection` | 🟡 OPEN |
| TestGap 1 | MEDIUM | Tests | `test_listings.py` verifies the virtual Page dataclass shape but never renders the list template — Bug 2 shipped despite a "passing" test suite | 🟡 OPEN |
| TestGap 2 | LOW | Tests | `test_theme.py` and `test_theme_full.py` string-match against raw CSS file contents (`".admonition" in css`) instead of rendering + inspecting HTML | 🟢 OPEN |
| TestGap 3 | LOW | Tests | `test_server.py` never exercises `DevServer.run()` (the only method end users hit via `bartleby serve`). Honest given Deferral 6 means there's nothing real to test | 🟢 OPEN |
| TestGap 4 | LOW | Tests | `test_async_build.py` is tautological given `async_build = asyncio.to_thread(build)` — would pass identically if async_build were replaced with a sync function | 🟢 OPEN |
| TestGap 5 | LOW | Tests | No CI smoke test mimicking manual Test 1 (`new site && new post && build && grep rendered output`). ~20 lines; would catch every Test 1 bug class | 🟢 OPEN |
| Spec 1 | HIGH | Spec parity | Spec promises Phase 5 Agent Integration as v1: 9 CLI commands (render/lint/content/schema/generate-skill/export), 5 modules, `ai.skills` + `ai.agent_context` config blocks, and pipeline step 25. None implemented | 🔴 OPEN |
| Spec 2 | MEDIUM | Theme | `theme.features` config is parsed but never consulted by any template — listing or omitting an entry has no effect on rendered HTML | 🟡 OPEN |
| Spec 3 | LOW | Theme | `theme/templates/404.html` exists but no build step renders a standalone `/404.html` in the output — only the web server's 404 fallback | 🟢 OPEN |
| Spec 4 | LOW | Spec parity | Spec's "Deferred Features (v2+)" lists "Data files — load YAML/JSON/CSV as template context" but they were implemented in Step 8 as a customization seam. Stale spec text | 🟢 OPEN |
| Design 14 | MEDIUM | CLI error handling | `_cmd_build` has no exception handler — any error from `build()` (metadata validation, strict-mode crossref failure, missing extension import, etc.) surfaces as a raw Python traceback. `_cmd_validate` only catches `ConfigError`. Need a top-level wrap that prints clean error + exits 1 | 🟡 OPEN |
| Design 15 | LOW | Observability | No `logging.getLogger()` anywhere in `src/`. Every output goes through `print()` (15 call sites). Hard to silence non-essential output or route to log files | 🟢 OPEN |
| Design 16 | LOW | Build readability | `build()` is a 120-line function with no marked phase boundaries (noted in Test 4 Step 10 prose). Split into named helpers (`_load_inputs`, `_filter_and_validate`, `_render_all_pages`, `_emit_outputs`) | 🟢 OPEN |
| Design 17 | LOW | Validate scope | `bartleby validate` only checks config + metadata + author keys. Missing: URL generation dry-run (catches bad `url_format`), template-existence check (catches dangling `template:` front-matter overrides), crossref check (catches broken `.md` links). Run these the way `--strict` does in build | 🟢 OPEN |
| Meta 1 | LOW | Packaging | `README.md` says "License: TBD" and `pyproject.toml` has no `license` field. Blocks PyPI publication and ambiguates downstream use | 🟢 OPEN |
| Meta 2 | LOW | Packaging | No `CHANGELOG.md`. With 27 step commits + ongoing fixes there's already enough history to warrant one | 🟢 OPEN |

**Recommended ship-0.1.0 punch list (priority order):**

1. Deferral 1 — vendor real Alpine/HTMX/lunr bundles. Without them
   every advertised theme interaction is a no-op.
2. Deferral 6 — wire `watchdog.Observer` + `websockets` into
   `DevServer.run()`. The README implies live reload works; it
   doesn't.
3. Deferral 8 — commit the safe test/fixture diffs; review the
   spec/plan diffs and either commit them or drop the local changes.
4. Deferral 2 — either compile real Tailwind output (standalone
   CLI, no Node required) or reword the docs/spec to drop the
   Tailwind framing.

**0.2.0+ material:** Deferrals 3, 4, 7 + Design 3 (drop the
`build_page_context` dict adapter) + Design 4 (move `on_pages` past
the draft filter) + Design 5 (per-page error isolation) + Design 13
(hook-reload story alongside Deferral 6) + TestGap 1 (render
listings/taxonomy templates in their unit tests). Design 1, 2, 6, 7,
8-12 + TestGap 2-5 are nice-to-have polish.

**Totals as of 2026-06-02:**
- **5 fixed** (Bugs 1–4 + Deferral 5)
- **37 open** (Deferrals 1–4, 6–8 + Hook config + Design 1–17 + TestGap 1–5 + Spec 1–4 + Meta 1–2)
- **Release-blocking subset (3):** Deferral 1, Deferral 6, Spec 1
  (decide: ship Phase 5 or reword spec.md to mark it as future work).
- **Ship blockers for PyPI specifically:** Meta 1 (no license) +
  Deferral 1 + Deferral 6.

---

## Fix-it playbook for the next agent

This section gives a fresh agent everything it needs to work through
the tracker. Read it once, then use the tracker as your work queue.

### 0 — Snapshot at handoff (2026-06-02)

When this playbook was written:

- **Branch**: `v1`, pushed to `origin/v1`. Do not merge to `main`
  — that's Mason's call.
- **Last commit**: `853ab2c` ("Add 'Next session — paths' closeout
  to audit.md").
- **Tests**: 282/282 pass. `ruff check`, `ruff format --check`,
  and `mypy --strict` are all clean.
- **Working tree has 4 uncommitted files** (this is Deferral 8):
  `plan.md`, `spec.md`, `tests/fixtures/configs/full.yml`,
  `tests/test_config.py`. They predate the post-implementation
  audit work and are real refinements — review their diffs and
  decide whether to commit them. Do NOT just blindly add them to
  a fix commit; they deserve their own commit with a clear message.
- **Open punch list**: 37 items in the tracker above (Deferrals,
  Designs, TestGaps, Specs, Metas). Each links to a Test section
  with full detail.

### 1 — Project orientation (10-minute read)

**What Bartleby is**: a batteries-included Python static site
generator. The full architecture is in `spec.md`; the 27-step
implementation roadmap that produced this codebase is in `plan.md`.
A working sample build is in `tests/fixtures/site/`.

**Tech stack**:

| Layer | Tool |
|---|---|
| Language | Python 3.14+ |
| Package manager | uv (`uv sync`, `uv run`) |
| Lint + format | ruff (configured in `pyproject.toml`) |
| Type check | mypy in strict mode (`uv run mypy src/`) |
| Tests | pytest (`uv run pytest`) |
| Task runner | just (`Justfile` has `check`, `lint`, `typecheck`, `test`, `format`) |
| Templates | Jinja2 |
| Markdown | Python-Markdown + pymdownx + do-markdown |

**Where things live**:

```
src/bartleby/
├── *.py                   # 24 source modules (spec promises 27; 5 missing — Spec 1)
└── theme/
    ├── templates/         # Bundled Jinja2 theme (base.html, partials/, defaults/)
    ├── static/{css,js}/   # Theme assets (Deferral 1: js/ are stubs)
    └── icons/             # Icon SVGs (Deferral 3: only 4 sample files)

tests/
├── test_*.py              # 27 test files, 282 tests
├── conftest.py            # Shared fixtures (`sample_site_path`, `sample_config`)
└── fixtures/
    ├── site/              # Sample Bartleby project (used by integration tests)
    ├── configs/           # Config YAML fixtures
    ├── authors/           # .authors.yml fixtures
    ├── templates/         # Custom template fixtures
    └── hooks_site/        # Hook discovery fixtures

docs/                      # The Bartleby docs ARE a Bartleby site
                           # `cd docs && uv run bartleby build` produces docs/site/
```

**Specs and supporting docs**:

- `spec.md` — canonical product spec (some sections describe
  unbuilt features; see Spec 1 in tracker).
- `plan.md` — 27-step TDD implementation roadmap (all checked off).
- `todo.md` — original implementation checklist (all checked off).
- `CLAUDE.md` — project-specific Claude Code instructions
  including a **"Module style (YAML-backed modules)"** section
  that's load-bearing for any new YAML-parsing module.
- `README.md` — project README. Note: "License: TBD" (Meta 1).
- `later.md` — out-of-band note about the session-scoped Stop hook
  misbehaviour. Not in scope for the next agent.
- `review.md` — the original 6-test audit framework.
- `.ai-sessions/` — durable session summaries + `lessons.md` +
  `lessons-pruned.md`. New sessions should add their own summary
  via `/bpe:session-summary`.

### 2 — Conventions you must follow

**Code style** (also in `CLAUDE.md`):

- Every `.py` file starts with a two-line comment, first line
  prefixed `ABOUTME:` (grep-friendly).
- mypy strict, no `Any` escape hatches except at YAML boundaries
  (then narrow with `isinstance`).
- ruff for lint + format. ~99 char line length.
- Test-driven development: RED → GREEN → REFACTOR. Write the
  failing test first.
- Single responsibility per function/module.
- Names must be evergreen — never `improved_X`, `new_X`,
  `enhanced_X`. Just name the thing.
- Preserve existing code comments unless actively false.
- Do not add error handling for impossible scenarios. Validate at
  boundaries, trust internal code.
- **Module style for YAML-backed modules** is documented in
  `CLAUDE.md`. Reuse the skeleton from `src/bartleby/config.py`
  and `src/bartleby/authors.py` when adding new ones.

**Verification command** — run after every code change:

```bash
just check    # ruff lint + format-check + mypy strict + pytest
```

This must be green before you commit. If any step fails, fix
before moving on.

**Commit hygiene**:

- Stay on branch `v1`. Do NOT merge to `main` (Mason's job).
- Sign every commit (`-S`). The pre-commit hook will enforce this.
- The pre-commit hook also requires a new `.ai-sessions/session-*`
  summary file each commit. Use `/bpe:session-summary` or write
  one by hand following the pattern in existing summaries.
- Title is imperative, ~70 chars max. Body explains the *why*.
- Footer states `All checks pass: ruff lint + format, mypy strict,
  N/N tests green.`
- Use the BPE workflow per `~/.claude/rules/git-workflow.md`:
  `/bpe:session-summary` → `/bpe:commit-message` → commit using
  `git commit -S -F commit-msg.md` → `git push`.
- `commit-msg.md` is gitignored — never stage it.

**Per-fix workflow**:

1. Read the tracker row + its Test section.
2. Re-verify the finding is still open (audit was written
   2026-06-02; another agent may have fixed it).
3. Add a failing test (RED).
4. Implement the fix.
5. Run `just check` — must be green.
6. Mark the row as `✅ FIXED YYYY-MM-DD` in the tracker.
7. Commit + push (see "Commit hygiene").
8. Move to the next item.

### 3 — Items the agent must NOT decide alone

A handful of items require a human choice. Surface them to Mason
rather than picking arbitrarily:

| Item | Decision needed |
|---|---|
| **Meta 1** | Which license? (MIT, Apache-2.0, BSD-3-Clause are the defaults for an SSG.) |
| **Spec 1** | Ship Phase 5 wholesale (~weeks of work) OR reword `spec.md` to mark Phase 5 as Roadmap. The cheap fix is the rewording. |
| **Deferral 8** | Some of the working-tree spec/plan diffs may be stale relative to fixes the next agent introduces. Review diff per file before committing. |
| **TestGap 5** | What CI provider? GitHub Actions is the safe default since the repo is on github.com/MasonEgger. |

If Mason isn't reachable, default to the conservative option
(reword for Spec 1; MIT for Meta 1; GitHub Actions for TestGap 5;
commit the diffs verbatim for Deferral 8 if `just check` still
passes).

### 4 — Item dependencies

Some items are linked. Address them together to avoid rework:

- **Deferral 6** (dev server live reload) ⇄ **Design 13** (hook
  reload story). The watchdog wiring needs to know how to refresh
  the `PluginCollection` when a `hooks/*.py` file changes.
- **Deferral 1** (vendor real Alpine/HTMX/lunr) ⇄ **Spec 2**
  (`theme.features` is dead config). Wiring real JS without
  consulting `theme.features` means every site emits the same
  interactivity regardless of config. Either fix both together
  or wire `theme.features` first so the JS additions can honor it.
- **Bug 2 fix already shipped** ⇄ **TestGap 1** (`test_listings.py`
  never renders the list template). The integration tests I
  added in `test_build.py` catch the bug end-to-end, but the
  unit-level gap remains. Worth closing alongside any Page →
  template architecture work.
- **Design 3** (drop `build_page_context` dict adapter) ⇄ **Bug 1
  fix already shipped** ⇄ **Bug 2 fix already shipped**. The
  patched-symptom fixes papered over the root cause. The
  *architectural* fix (pass `Page` dataclass directly) closes
  Design 3 and prevents future bugs of the same family. Worth
  doing instead of leaving the patches in.
- **Design 14** (CLI error handling) ⇄ **Design 17** (validate
  scope). Both touch `cli.py::_cmd_build` and `_cmd_validate`.
  Do them in one commit.
- **Spec 1** ⇄ all of Phase 5 (Components 23–27). The decision
  to ship vs. reword unblocks the rest.

### 5 — Recommended fix order

Path B → Path A → re-audit (per the closeout below). Within
those paths, this order minimizes rework:

**Path B — quick wins (one afternoon)**:

1. **Deferral 8** — review diffs, commit working-tree changes (or
   revert). Closes 1 tracker item; unblocks Spec 4.
2. **Meta 1** — pick a license, add `LICENSE` file, update
   `README.md` and `pyproject.toml`. Closes 1 item.
3. **Meta 2** — write `CHANGELOG.md` seeded from existing
   commits. Closes 1 item.
4. **Design 14 + Design 17 together** — wrap `_cmd_build` and
   extend `_cmd_validate`. ~50 lines + tests. Closes 2 items.

That's 4 commits, 5 items closed, no architectural risk.

**Path A — release-blockers**:

5. **Spec 1 (lightweight)** — reword `spec.md` to mark Phase 5
   sections as Roadmap (unless Mason wants to ship Phase 5).
   Updates also clear Spec 4 (data files spec drift). 1 commit.
6. **Deferral 1** — vendor real Alpine, HTMX, lunr bundles into
   `src/bartleby/theme/static/js/`. Total ~40 KB gzipped. Include
   license headers. 1 commit.
7. **Spec 2** — wire `theme.features` config into the templates.
   Adds `{% if "search" in config.theme.features %}` guards around
   the search modal, dark-mode toggle, back-to-top, etc. Best done
   right after Deferral 1 so the gating matches what actually
   works. 1 commit.
8. **Deferral 6 + Design 13 together** — add `watchdog.Observer`
   and `websockets` to `DevServer`. Re-glob `hooks/*.py` on
   change. Inject a small WebSocket-reload `<script>` into served
   HTML. ~150 lines + tests. 1 commit, possibly 2 (watchdog
   first, then WebSocket).

After Path A, the source is genuinely shippable as 0.1.0.

**Remaining items** (work through in tracker order):

9. Bug-family architectural fixes: **Design 3** (Page dict
   adapter) + **TestGap 1** (render listings in unit tests). 1
   commit each.
10. **Design 4** — move `on_pages` hook past the draft filter. 1
    small commit + 1 new test.
11. **Design 5** — per-page error isolation in the render loop.
12. **Designs 1, 2, 6, 7, 8–12, 15, 16** — small polish items.
13. **TestGaps 2–5** — render-and-inspect theme tests, exercise
    `DevServer.run()`, smoke test in CI.
14. **Deferral 7** — wire remaining 12 hook events. Big mechanical
    commit.
15. **Deferral 3** — bulk-vendor real icon packs.
16. **Deferral 4** — real `ProcessPoolExecutor`-based async build.
    Decide whether to keep `asyncio.to_thread` or fully replace.

### 6 — How to verify the audit findings are still real

Before fixing any item, **verify it's still open**. The audit was
written 2026-06-02; another agent or a follow-up commit may have
addressed it. Quick checks per category:

**Bug-like (already FIXED but worth re-verifying)**:
```bash
# Bugs 1 + 2 — smoke test
rm -rf /tmp/bartleby-smoke && mkdir -p /tmp/bartleby-smoke
cd /tmp/bartleby-smoke && uv run --project <path-to-repo> bartleby new site demo
cd demo && cat > content/blog/posts/hello.md << 'EOF'
---
title: Hello
date: 2026-06-02
draft: false
authors: [default]
---
Body.
EOF
uv run --project <path-to-repo> bartleby build
grep -q "By" site/blog/posts/hello/index.html && echo "Bug 1 OK"
grep -q 'href="/blog/posts/hello/"' site/blog/index.html && echo "Bug 2 OK"
```

**Deferrals**: each tracker row names the location. Check it
directly:

| Item | One-liner to verify still open |
|---|---|
| Deferral 1 | `cat src/bartleby/theme/static/js/alpine.min.js` — if it's a 200-byte stub, still open |
| Deferral 6 | `grep -q "watchdog\|websockets" src/bartleby/server.py` — if nothing, still open |
| Deferral 7 | `grep -c 'run_event(' src/bartleby/build.py` — if < 12, still open |
| Meta 1 | `grep license pyproject.toml` — if no `license = ` line, still open |
| Meta 2 | `test -f CHANGELOG.md` — if absent, still open |

**Spec items**: read the spec section vs. the implementation.

For the rest, read the tracker row's linked Test section and
re-derive the check.

### 7 — How to know you're done

The agent is done when:

- Every tracker row that wasn't blocked on a human decision is
  marked `✅ FIXED YYYY-MM-DD`.
- The "Totals" line at the top of the tracker is updated.
- `just check` is still green.
- The branch is pushed to `origin/v1`.
- A summary report in a new `.ai-sessions/session-*.md` covers
  what was fixed, what was skipped (with reason), and any
  surprises.

Then Mason will run another audit pass against the result.

### 8 — Things explicitly out of scope

Do NOT:

- Merge to `main`.
- Change `--no-verify` or skip the pre-commit hook.
- Edit the BPE plugin or any file under `~/.claude/`.
- Touch `later.md` — that's an out-of-band note about a separate
  tool issue.
- Pivot to Phase 5 feature work without explicit approval (Spec 1
  requires Mason's decision).
- Delete or move existing session summaries.
- Bump the package version yet — that happens once Mason approves
  shipping.

### 9 — When in doubt

- Read the linked Test section in this file.
- Read `spec.md` for "what was supposed to happen".
- Read the relevant src module for "what actually happens".
- If still stuck, surface the question in your session summary
  with a `<CLAUDE_HELP>...</CLAUDE_HELP>` block so Mason sees it.

---

## Test 1 — End-to-end smoke test

**When**: 2026-06-02
**Method**: Scaffolded a fresh site in `/tmp/bartleby-smoke/demo`, ran
`bartleby new site demo && bartleby new post "Hello" --type blog && bartleby build`,
inspected the rendered HTML, search index, llms.txt, sitemap, and Markdown
variants.

### What works end-to-end

- Scaffold (`new site` creates the correct skeleton — `bartleby.yml`,
  `.authors.yml`, `content/`, `templates/`, `static/`, `hooks/`)
- `new post` slugifies the title (`"Hello"` → `hello.md`) and writes a
  `draft: true` front matter stub
- Build runs in ~130ms producing 3 pages + theme assets + auxiliary files
- HTML5 structure: DOCTYPE, viewport meta, canonical, OG, Twitter Card
- Post body renders with TOC anchor IDs and the excerpt separator preserved
- `og:type=article` + `article:published_time` correctly emitted for blog post
- `og:type=website` for the static index
- Readtime calculated and shown (`1 min read`)
- Excerpt extracted (visible in llms.txt entry)
- Tag rendered in post footer
- Search index includes per-page entries plus per-section anchored entries,
  with `tags` propagated and a lunr-compatible config block
- Markdown variant published next to each HTML file (body only, no front matter)
- llms.txt structured by content type with excerpt-derived descriptions
- Sitemap, gzipped sitemap, and robots.txt all generated

### Bugs surfaced (prioritized)

#### Bug 1 — HIGH — Author objects not resolved into the template context

**Symptom**: A blog post with `authors: [default]` in front matter and a
matching `default` entry in `.authors.yml` renders an empty author line in
the default post template:

```html
<p>By
    
</p>
```

**Root cause**: `src/bartleby/templates.py::build_page_context` exposes
`"authors": list(page.author_keys)` — a list of strings, not resolved
`Author` objects. The default post template iterates and tries
`{{ author.name }}`, which is undefined on a string and renders empty
under Jinja2 autoescape.

**Why tests miss it**: `test_build.py` checks the rendered HTML file
exists. It never asserts on the byline. The Step 3 `resolve_authors`
function exists in `src/bartleby/authors.py` and is unit-tested, but
nothing in the build pipeline calls it.

**Fix sketch**:
- In `build.py`, call `resolve_authors(page.author_keys, authors)` and
  pass the resolved list into `build_page_context`.
- Or pass the `authors` dict into `build_page_context` and resolve there.
- Either way, `page_namespace["authors"]` becomes `list[Author]` so
  `{{ author.name }}`, `{{ author.url }}`, `{{ author.avatar }}` work
  in templates.
- Add an integration test that builds the fixture site and asserts the
  resolved author's name appears in the rendered post HTML.

**Files touched**: `src/bartleby/build.py`, `src/bartleby/templates.py`
(maybe), `tests/test_build.py` (new assertion).

---

#### Bug 2 — HIGH — Blog listing pages render an empty post list

**Symptom**: After building the smoke-test site (1 published blog post),
`site/blog/index.html` contains:

```html
<section>
  <h1>Blog</h1>
  <ul>
    <!-- nothing here -->
  </ul>
</section>
```

**Root cause**: `src/bartleby/listings.py::_build_listing_page` stuffs
the post list into `custom_metadata["posts"]`. The bundled list
template (`src/bartleby/theme/templates/defaults/list.html`) reads:

```jinja
{% set listed = paginator.items if paginator else page.posts %}
```

But `build_page_context` only hoists a fixed set of fields into the
page namespace (`title`, `description`, `date`, `content`, …). It
does *not* expose `custom_metadata` entries as page attributes, so
`page.posts` is undefined and the loop iterates over nothing.

The same is true for `page.intro_content` and `page.paginator`.

**Why tests miss it**: `test_listings.py` asserts that the
`custom_metadata["posts"]` list is correct on the virtual `Page`
object — but it never renders a template. The `test_build.py`
integration test checks that `site/blog/index.html` exists, but
not that it contains any posts.

**Fix sketch** (one or the other):
- **Option A**: In `build_page_context`, copy listing-specific
  `custom_metadata` keys onto the page namespace when the page is a
  listing (`page.custom_metadata.get("listing_kind") == "content_type"`).
  Same for taxonomy pages.
- **Option B**: Update the bundled list template to read
  `page.custom_metadata.posts` directly. (Less ergonomic for end users.)
- Add an integration assertion that the listing HTML contains at least
  one `<a href="...">` to each published post.

**Files touched**: `src/bartleby/templates.py` or
`src/bartleby/theme/templates/defaults/list.html`,
`tests/test_build.py` (new assertion).

---

#### Bug 3 — MEDIUM — Scaffolded `bartleby.yml` doesn't opt the blog type into the tags taxonomy

**Symptom**: After `bartleby new site demo` and writing a post with
`tags: [greeting]`, no `/tags/` or `/tags/greeting/` pages are
generated. A fresh user has no way to discover why.

**Root cause**: `src/bartleby/cli.py::_DEFAULT_CONFIG` declares
`tags` at the site level but does not include `taxonomies: [tags]`
under the `blog` content type. The taxonomy collector requires
explicit opt-in per content type.

**Why tests miss it**: `test_cli.py::test_new_site_valid_config`
verifies the generated config loads — it doesn't run a build against
a post with tags.

**Fix sketch**: Add `taxonomies:\n      - tags` to the `blog` content
type block in `_DEFAULT_CONFIG`. Document the requirement in the
[Taxonomies concept page](docs/content/concepts/taxonomies.md) more
prominently (it's already covered, but worth front-loading).

**Files touched**: `src/bartleby/cli.py`,
`tests/test_cli.py` (new assertion that a post with tags produces tag
listing pages after build).

---

#### Bug 4 — LOW — Sitemap omits listing pages and taxonomy pages

**Symptom**: `sitemap.xml` for the smoke-test site contains only
`/blog/posts/hello/` and `/`. It does NOT contain `/blog/`
(the listing page that exists on disk at `site/blog/index.html`).

**Root cause**: `src/bartleby/build.py` calls
`write_sitemap(pages, config.site, output_dir)` — using `pages` (real
pages only), not `all_pages` (which includes the virtual listing and
taxonomy pages).

**Why tests miss it**: `test_sitemap.py` only tests sitemap generation
in isolation with arbitrary page lists. The build integration tests
don't introspect the sitemap.

**Fix sketch**: Pass `all_pages` to `write_sitemap` instead of `pages`.
Same for `build_search_index` (so search results include landing /
listing pages) and `generate_llms_txt` (so agents can find listings).

Add an integration test asserting the sitemap contains the listing URL.

**Files touched**: `src/bartleby/build.py`, `tests/test_build.py`
(new assertion).

---

### Summary

| # | Severity | Surface | Impact | Status |
|---|----------|---------|--------|--------|
| 1 | HIGH | Templates | Author bylines broken on every blog post for every user | **FIXED 2026-06-02** |
| 2 | HIGH | Templates | Listing pages broken — biggest user-visible failure | **FIXED 2026-06-02** |
| 3 | MEDIUM | Scaffolding | Fresh-user friction; tags appear to do nothing until config is hand-edited | **FIXED 2026-06-02** |
| 4 | LOW | Output | Listing/taxonomy URLs not discoverable via sitemap | **FIXED 2026-06-02** |

**Test quality finding**: the integration suite checks file *existence*
but not file *content*. Bugs 1, 2, and 4 all passed CI because their
respective tests stopped at `(site / "blog" / "index.html").exists()`.
A small batch of "assert this string appears in the rendered HTML"
assertions would have caught all three.

**Fix details:**
- Bug 1: `build_page_context` now accepts an `authors` dict and resolves
  `page.author_keys` into `Author` objects via `_resolve_author_objects`.
  `build()` passes the loaded authors through.
- Bug 2: Listing and taxonomy templates read `page.custom_metadata.*`
  (`posts`, `intro_content`, `paginator`) directly. The list template
  also had a wrong attribute name — `post.url` → `post.output_url`.
  Taxonomy term pages now carry their associated pages in
  `custom_metadata["posts"]` so the term template can iterate the
  actual list rather than ALL site pages.
- Bug 3: `_DEFAULT_CONFIG` in `cli.py` now includes `taxonomies: [tags]`
  under the scaffolded `blog` content type.
- Bug 4: `write_sitemap` now receives `all_pages` (real + virtual)
  instead of `pages` (real only).

**Test quality fix shipped alongside:** added 5 new content-level
assertions to `test_build.py` covering byline rendering, listing post
links, sitemap URL inclusion, and taxonomy term page contents. Added
`test_new_site_blog_opted_into_tags` to `test_cli.py`. The integration
suite now exercises content, not just file existence.

**Verified end-to-end:** a fresh `bartleby new site demo && bartleby new
post Hello --type blog && bartleby build` produces 7 pages (was 3), the
post HTML contains `By Site Author`, the listing has `<a
href="/blog/posts/hello/">Hello</a>` with the excerpt, `/tags/`,
`/tags/greeting/`, `/blog/tags/`, and `/blog/tags/greeting/` exist, and
the sitemap lists all of them.

---

## Test 2 — Audit the deferrals

**When**: 2026-06-02
**Method**: For each deferred item flagged in review.md, verify the current
state on disk, then sweep all session summaries for `defer|stub|placeholder|
TODO|reserved|future|later` to surface anything I'd missed.

### Confirmed deferrals (8)

#### Deferral 1 — Vendored JS bundles are stubs

**Location**: `src/bartleby/theme/static/js/{alpine,htmx,lunr}.min.js`
**State**: Each file is 200 bytes — a comment plus
`console.debug && console.debug("X placeholder");`. Nothing actually
runs client-side.

**Impact**: Every generated site references these scripts in `<head>`
via `<script defer src="/js/alpine.min.js">` etc., but the search
modal, dark-mode toggle, back-to-top button, and TOC scroll spy all
silently do nothing in a browser. The HTML *looks* interactive (the
Alpine `x-data` attributes are emitted) but no JavaScript ever
upgrades the markup.

**Real fix**: Vendor the actual minified bundles. They're tiny —
Alpine.js v3 is ~16KB gzipped, HTMX is ~14KB gzipped, lunr.js is
~9KB gzipped. Total cost: one download, one commit.

**Severity**: HIGH (release-blocking — the theme advertises features
that don't work).

---

#### Deferral 2 — Tailwind CSS is hand-written, not compiled

**Location**: `src/bartleby/theme/static/css/main.css` (116 lines)
**State**: A small handwritten stylesheet with CSS custom properties
for light/dark, base typography, admonition variants, code blocks,
search modal, TOC sidebar, back-to-top button, responsive breakpoint,
grid cards, and an `.md-button` rule. No Tailwind. No PostCSS config.
No `tailwind.config.{js,ts}` anywhere in the repo.

**Impact**: The README, spec.md, and several doc pages talk about
"Tailwind CSS". The reality is hand-written CSS that *looks*
Tailwind-flavoured in places. A user expecting to extend the theme
via Tailwind utility classes will not find any.

**Real fix**: Either
- (a) wire up the standalone Tailwind CLI (no Node.js install
  required), commit a real `tailwind.config.js`, and have the theme
  build script compile `main.css` from sources, OR
- (b) reword the docs/spec to drop the Tailwind framing and describe
  the theme as "hand-written, designed to coexist with user-provided
  Tailwind/styled-components/etc."

**Severity**: MEDIUM (cosmetic misrepresentation; nothing renders
incorrectly).

---

#### Deferral 3 — Icon packs ship one SVG each

**Location**: `src/bartleby/theme/icons/`
**State**:
```
material/account.svg
fontawesome-brands/github.svg
octicons/heart-fill-24.svg
simple/python.svg
```
Four files total. `get_icon_path("material-heart", ...)` returns `None`
because `material/heart.svg` doesn't exist.

**Impact**: The icons module works correctly — tree-shaking, pack
opt-in, slug parsing — but a user trying to render even basic
icons gets a `None` back from the resolver for anything except the
four sample files.

**Real fix**: Vendor the real icon packs as a build-time step (or
even just as a one-off mass copy). Material Design Icons is ~7000
SVGs, FontAwesome Brands ~500, Octicons ~200, Simple Icons ~3000.
Bundling all of them is ~30 MB on disk; tree-shaking ensures only
referenced icons ship per-site. Alternatively, distribute the icon
packs as optional pip extras (`bartleby[icons-material]`).

**Severity**: MEDIUM (advertised feature unusable until real packs
arrive; the infrastructure is correct).

---

#### Deferral 4 — Async build has no real parallelism

**Location**: `src/bartleby/build.py::async_build`
**State**:
```python
async def async_build(config_path, *, include_drafts=False) -> BuildResult:
    return await asyncio.to_thread(build, config_path, include_drafts=include_drafts)
```
A one-line wrapper. No `ProcessPoolExecutor`, no `aiofiles`, no
`asyncio.gather` over the post-render outputs. The sync `build()`
is still the canonical implementation; the async wrapper just pushes
it onto a worker thread.

**Impact**: The CLI's `bartleby build` runs through `asyncio.run(async_build(...))`,
so the entry point looks async, but build time is identical to a
direct synchronous call. The doc claim "real CPU parallelism is
future work" is honest.

**Real fix**: Three pieces:
- Make `markdown.Markdown` instances picklable across processes (or
  reconstruct them per-worker from picklable config).
- Dispatch `markdown.convert()` calls to a `ProcessPoolExecutor`.
- Run post-render outputs (search index, feeds, sitemap, llms.txt) in
  parallel via `asyncio.gather`.
- Audit that plugin hooks never cross the process boundary.

**Severity**: LOW (current build is fast enough for small/medium
sites; revisit if build times bite).

---

#### Deferral 5 — Crossref errors silently dropped

**Location**: `src/bartleby/build.py` — calls
`resolve_all_crossrefs(all_pages, content_dir)` and discards the
returned errors list.

**Impact**: A page that links `[other](nonexistent.md)` will get
the error recorded (Step 13 tests verify this), but the error is
never printed, logged, or made buildgate-fatal. Authors deploy
sites with broken cross-references and never know.

**Real fix**: 
- Print each `CrossRefError` to stderr at build end.
- When the CLI is invoked with `--strict`, fail the build (exit 1).
- The `--strict` flag is already in `cli.py::_build_parser` — it's
  parsed and ignored. Wire it through to a `strict` parameter on
  `build()`/`async_build()`.

**Severity**: MEDIUM (silent data quality failure; affects every
multi-page site with internal links).

**Status**: **FIXED 2026-06-02**. `build()` and `async_build()` now
accept `strict: bool = False`. Crossref errors print to stderr in
both modes; `strict=True` raises `ValueError` after printing. CLI
wires `args.strict` through. Two new tests in `test_build.py` cover
both paths.

---

#### Deferral 6 — Dev server is just a static file server

**Location**: `src/bartleby/server.py`
**State**: `DevServer.run()` spawns a synchronous
`http.server.SimpleHTTPRequestHandler` bound to `site/`. That's it.
There is no `watchdog.Observer` import, no WebSocket server, no
asyncio loop. `DevServer.handle_change()` exists as a method that
tests call directly, but nothing in `run()` ever invokes it because
nothing watches the filesystem.

**Impact**: `bartleby serve` today:
- Runs an initial build (with drafts)
- Serves `site/` over HTTP
- **Never rebuilds on file change** (you have to Ctrl-C and re-run)
- **Never pushes a reload to the browser**

The README/docs imply live reload works. It doesn't. This is the
biggest gap between advertised behaviour and reality.

**Real fix**:
- Add `watchdog.Observer` to watch `content/`, `templates/`,
  `static/`, `hooks/`, `data/`, `bartleby.yml`, `.authors.yml`.
- On change: dispatch to `DevServer.handle_change()` (which already
  classifies the change and triggers a rebuild).
- Add a WebSocket server (the `websockets` library is already a
  declared dependency) that pushes a `reload` message after every
  successful rebuild.
- Inject a `<script>` snippet into served HTML that opens the
  WebSocket and `location.reload()`s on message.

**Severity**: HIGH (advertised core feature doesn't work; users
following the quickstart will be confused).

---

#### Deferral 7 — Most plugin hook events are "reserved"

**Location**: `src/bartleby/build.py` only calls 5 of 17 declared
events: `on_config`, `on_pages`, `on_env`, `on_page_markdown`,
`on_post_page`.

**Reserved-but-not-fired** (12): `on_startup`, `on_shutdown`,
`on_pre_build`, `on_files`, `on_nav`, `on_pre_page`,
`on_page_read_source`, `on_page_content`, `on_page_context`,
`on_post_build`, `on_build_error`, `on_serve`.

**Impact**: Users can register handlers against these events and
get no errors at discovery time, but their handlers never fire.
The plugin hook reference doc page (which I wrote) labels these
"reserved" — but the labeling lives in prose, not in code. A user
following plugin examples from a Bartleby tutorial elsewhere
(MkDocs hooks, e.g.) could easily register an `on_pre_build`
handler expecting it to run.

**Real fix**: For each reserved event, identify the right phase of
the build pipeline and add a `plugins.run_event(...)` call site.
Most are one-line additions. `on_files` and `on_nav` would need a
slightly bigger rework because the current pipeline doesn't have a
single discrete "files" or "nav" object you can hand to a hook.

**Severity**: MEDIUM (silent failures for users who register against
reserved events; consider raising on registration of an unsupported
event instead).

---

#### Deferral 8 — Uncommitted spec/plan/test changes in working tree

**State**: `git status` shows:
- `plan.md` — 186 lines changed (spec/plan refinements made before
  the implementation session began)
- `spec.md` — 156 lines changed (same)
- `tests/fixtures/configs/full.yml` — 7 lines added (extra_css and
  extra_js fixture entries)
- `tests/test_config.py` — 10 lines added (a `test_extra_css_and_js_parsed`
  test plus 2 assertions in `test_default_values_applied`)

The corresponding code changes (extra_css / extra_js fields on
`BartlebyConfig`) **were** committed at some point — `git diff
src/bartleby/config.py` is empty. So the test+fixture additions are
test-only and would land cleanly.

The plan.md and spec.md edits are larger and look like real spec/plan
refinements (template cascade widened from 5 to 6 levels, customization
seams documented, Step 21 redesigned to drop entry_points). Worth
committing as a "spec/plan refinements" commit — they're already
reflected in the implementation.

**Real fix**: Two commits:
1. `Add extra_css/extra_js test coverage` — stage `tests/test_config.py`
   and `tests/fixtures/configs/full.yml`. Safe.
2. `Refine spec.md and plan.md for customization seams and hook system`
   — stage `plan.md` and `spec.md`. Review the diff before committing
   in case any part of the refinement is now stale.

**Severity**: LOW (test-only diffs are pure improvement; spec/plan
diffs are documentation that's already true).

---

### Summary table

| # | Severity | Area | Real impact | Status |
|---|----------|------|-------------|--------|
| 1 | HIGH | Vendor JS | Theme interactivity (search, toggle, TOC, back-to-top) is dead on arrival | **OPEN** |
| 6 | HIGH | Dev server | `bartleby serve` doesn't actually reload — advertised feature missing | **OPEN** |
| 2 | MEDIUM | Tailwind | Docs misrepresent the styling stack | **OPEN** |
| 3 | MEDIUM | Icons | Icon resolver returns `None` for everything except 4 sample SVGs | **OPEN** |
| 5 | MEDIUM | Crossrefs | Broken internal links silently shipped | **FIXED 2026-06-02** |
| 7 | MEDIUM | Hooks | 12 of 17 declared events never fire; user handlers silently no-op | **OPEN** |
| 4 | LOW | Async build | API exists; CPU parallelism doesn't | **OPEN** |
| 8 | LOW | Working tree | Pre-existing uncommitted spec/plan + test-only diffs from before this work | **OPEN** |

## Test 3 — Test quality vs. test count

**When**: 2026-06-02
**Method**: Read every test file (27 files, 3777 lines, 275 tests). For
each, classified the assertion pattern: does the test exercise real
behavior, or does it verify shape/existence/string-matching? Cross-checked
findings against the smoke-test bugs from Test 1.

### Tier 1 — Strong (21 files, ~75% of test surface)

These exercise input → behavior → output cleanly. They drive the unit
under test with real inputs, inspect the resulting object structure or
output content, and would catch regressions on the public contract.

| File | Why it's strong |
|------|-----------------|
| `test_config.py` | Load real YAML fixtures, assert on parsed dataclass fields and validation error messages |
| `test_authors.py` | Load + resolve, assert structure |
| `test_content.py` | Parse front matter, check field mapping + exclusion patterns |
| `test_metadata.py` | Validate against schema, assert on `ValidationError.field` and `.message` |
| `test_urls.py` | Input page + content type → expected URL string. Pure behavior. |
| `test_pagination.py` | Drive `paginate()` with various counts, check the chunked output |
| `test_taxonomies.py` | Term collection + counts + slug formats |
| `test_navigation.py` | Tree structure, prev/next linking, sort order |
| `test_crossrefs.py` | Input HTML → expected rewritten HTML + error list |
| `test_shortcodes.py` | Input markdown → rendered template output |
| `test_search.py` | Input pages → JSON structure (per-page + per-section entries with tags) |
| `test_feeds.py` | Input pages → XML, **parsed with `xml.etree`** to verify structure |
| `test_sitemap.py` | Same — XML parsed and checked, not string-matched |
| `test_seo.py` | Input page → meta tag dict |
| `test_icons.py` | Input icon name → resolved SVG path |
| `test_assets.py` | Input fixtures → file copies (with binary byte-fidelity check) |
| `test_markdown_pipeline.py` | Input markdown → HTML containing expected elements (`<table>`, `<input>` for tasks) |
| `test_templates.py` | Real template render through the 6-level lookup cascade |
| `test_llm.py` | Input pages → llms.txt + JSON-LD structures |
| `test_cli.py` | Real end-to-end `main(["new", "site", "mysite"])` → check file structure → chain `main(["new", "post", ...])` → check |
| `test_init.py` | Trivial smoke (12 lines) — version exists |

The XML feed/sitemap tests are noteworthy: they use `ElementTree.fromstring`
to parse the output and walk the tree, not string-match it. That's the
gold standard for testing structured output.

### Tier 2 — Mixed (4 files)

Exercise the unit but stop short of the integration point where bugs live.

#### `test_build.py` — 13 tests, missed bugs 1, 2, 4 from Test 1

Drives the full build pipeline against the fixture site (real
integration), but every assertion checks **file existence** or **a single
hardcoded string**. Sample:

```python
def test_build_renders_blog_post(project: Path) -> None:
    build(project / "bartleby.yml")
    rendered_dir = project / "site" / "blog" / "posts" / "first-post"
    assert (rendered_dir / "index.html").exists()    # only checks existence
```

```python
def test_build_renders_index_page(project: Path) -> None:
    build(project / "bartleby.yml")
    rendered = (project / "site" / "index.html").read_text(encoding="utf-8")
    assert "Welcome" in rendered                      # single token
```

No test reads `site/blog/index.html` and asserts the post is in the
listing. No test reads `site/blog/posts/first-post/index.html` and
asserts the author name appears. No test inspects `site/sitemap.xml`
to confirm listing URLs are included. **The listing-empty bug, the
empty-byline bug, and the missing-sitemap-URL bug all passed CI here.**

#### `test_theme.py` — 10 tests, string-matching on rendered templates

Renders each template fixture with a stub context, then string-matches
the output:

```python
assert "/css/main.css" in rendered                   # the link exists
assert "/js/alpine.min.js" in rendered               # the script tag exists
assert "theme-toggle" in rendered                    # the toggle markup exists
```

Tells you the template emits the right tags. Tells you **nothing** about
whether the linked CSS/JS does anything useful in a browser. The fact that
`alpine.min.js` is a 200-byte stub (Deferral 1 from Test 2) is invisible
here.

#### `test_theme_full.py` — 8 tests, weakest signal in the suite

Half the tests read the raw CSS file and check for class names:

```python
def test_css_has_admonition_styles() -> None:
    css_path = get_theme_templates_dir().parent / "static" / "css" / "main.css"
    text = css_path.read_text()
    assert ".admonition" in text
```

This tests that the **string** `".admonition"` appears in a file. Doesn't
verify the rule is well-formed, doesn't verify it gets applied, doesn't
even verify the CSS is valid. Could be replaced with `grep -q ".admonition"
src/bartleby/theme/static/css/main.css` in CI and lose nothing.

#### `test_listings.py` — 7 tests, missed bug 2 from Test 1

This is the most insidious. The tests verify the virtual `Page` object's
`custom_metadata["posts"]` field is correctly populated:

```python
posts_in_context = listing.custom_metadata["posts"]
assert isinstance(posts_in_context, list)
assert posts_in_context[0] is newer
```

This passes — the data structure is correct. But **no test renders the
listing template**, so the actual bug — that the template reads
`page.posts` (undefined) and not `page.custom_metadata.posts` — is
invisible. The unit is correct in isolation; the integration is broken.

### Tier 3 — Weak (2 files)

#### `test_server.py` — explicitly skips the real surface

The module docstring is honest:

> Network IO (HTTP + WebSocket) is intentionally not exercised in tests —
> instead we cover the rebuild dispatcher, change classification, and
> config plumbing.

10 tests; 7 are unit tests of pure functions (`classify_change`,
`should_trigger_full_rebuild`); 3 exercise `DevServer.build_once` and
`handle_change`. **No test exercises `DevServer.run()`** — the only
method end users actually invoke via `bartleby serve`. The hooks
listing in Test 2 (Deferral 6) confirms `run()` is just a bare
`http.server.SimpleHTTPRequestHandler`; there's nothing to test
because nothing watches files or pushes WebSocket reload.

#### `test_async_build.py` — tautological concurrency tests

Given `async_build` is literally:

```python
async def async_build(config_path, *, include_drafts=False):
    return await asyncio.to_thread(build, config_path, include_drafts=include_drafts)
```

…the tests verify:

- It produces output (i.e. `build()` still works)
- It produces the **same** output as `sync_build` (also tautological —
  same function, called through a thread wrapper)
- It writes the search index, sitemap (delegated to `build()`)
- It completes within 15 seconds (no hang)

What's **missing**: any test of actual concurrency. No assertion that two
pages render in parallel. No assertion that the event loop isn't blocked.
No assertion that `asyncio.gather` runs the post-render outputs
concurrently. Given the implementation is `to_thread(build)` and provides
no real parallelism (Deferral 4), the tests are honest about what's
there — but the suite would pass identically if `async_build` were
replaced with `def async_build(...): return build(...)` and
`asyncio.run()` removed from `cli.py`.

### Pattern findings

1. **`.exists()` over content inspection.** Integration tests stop at
   file existence. Three of the four high/medium bugs from Test 1
   (empty listing, empty byline, missing sitemap URLs) would have been
   caught by adding two-line assertions like `assert "Hello" in
   (site / "blog" / "index.html").read_text()` to existing tests.

2. **Unit tests stop at the dataclass.** `test_listings.py` and
   `test_taxonomies.py` correctly verify the virtual-page data
   structure, but never render the templates that consume those
   structures. The contract between the listings module and the listing
   template is untested.

3. **Theme tests don't test theme rendering.** They test template
   substrings and CSS file substrings. They would all pass even if every
   linked asset was a 404 or every CSS rule had broken syntax.

4. **The serve/async story is intentionally underspecified.** Both
   `test_server.py` and `test_async_build.py` document up front that
   they're not testing the surface that matters. That's honest — but
   it's also the reason `bartleby serve` doesn't have working live
   reload (Deferral 6) and `async_build` provides no concurrency
   (Deferral 4). No test would have flagged either gap.

### Quantification

- **27 test files, 275 tests, 3777 lines.**
- **Tier 1 (strong): 21 files (~78%)** — real behavior coverage
- **Tier 2 (mixed): 4 files (~15%)** — shape/string-matching where
  behavior testing would surface real bugs
- **Tier 3 (weak): 2 files (~7%)** — explicitly skip the real surface

Test **count** is honest as a coverage-breadth proxy. Test **quality**
is bimodal: the per-module unit tests are strong; the integration and
theme tests are shape-checks dressed up as integration tests.

### What would meaningfully improve the test suite

In rough priority order:

1. **Augment `test_build.py` with content assertions.** For each
   page type, after build, read the rendered HTML and assert on the
   substantive content (post body present, byline rendered with author
   name, listing contains links to every published post, taxonomy page
   contains the term name, sitemap contains every nav URL).
2. **Render the listing/taxonomy templates in their unit tests.**
   `test_listings.py` should assert `posts[0].title in rendered_html`,
   not just `posts[0] is newer_page`.
3. **Replace CSS-file-string-matching in `test_theme_full.py` with
   render-and-inspect.** If you want to verify admonition styling, render
   a page with an admonition and check the `<div class="admonition">`
   appears in the HTML, not that `.admonition` appears in the CSS source.
4. **Add a smoke test in CI that mimics the manual Test 1 above.**
   Scaffold + post + build + grep the rendered output for specific
   strings. ~20 lines; would catch every Test 1 bug.
5. **Once Deferrals 4 and 6 land for real, write actual concurrency
   tests and live-reload tests.** Until then, the existing skeletons
   are honest placeholders.

The smallest delta that buys the most signal: 8–10 new assertions in
`test_build.py` (item 1). That alone would have caught Bugs 1, 2, and 4
from the Test 1 smoke audit.

## Test 4 — Read the commits as a story

**When**: 2026-06-02
**Method**: Walked the full v1 branch history (34 commits), then deep-dove
the four commits flagged in `review.md` as architecturally load-bearing
(Steps 4, 8, 10, 21). Looked for design errors that compound downstream.

### Branch shape

34 commits on `v1`, all linear (no merges, no reverts, no fixup squashes).
The 27 implementation steps are bookended by 3 pre-Step-1 commits (spec
drafts + plan), 1 housekeeping commit between Steps 1 and 2 (gitignore +
pypi name), and 3 post-Step-27 commits (docs, audit fixes, audit
tracker). Every "Step N" commit follows the same shape: imperative title,
narrative body explaining the *why*, bulleted change list, and an
"All checks pass: N/N tests green" footer. Commit hygiene is exceptional.

Pre-existing modifications to `plan.md`, `spec.md`, `tests/fixtures/configs/
full.yml`, and `tests/test_config.py` were never folded in — they persist
as uncommitted diffs in the working tree (Deferral 8 in Test 2).

### Step 4 — `parse_front_matter` (commit 05bc8b0)

The bug-fix loop in the session summary was the obvious tell. The final
implementation is clean — but a real edge case slipped through:

**Issue A: Front matter detection is too loose.**
```python
if not text.startswith(FRONT_MATTER_DELIMITER):
    return {}, text
```
This matches any document starting with `---`, even `---horizontal rule`
or `---foo bar`. The closing-marker search will fail for most such
documents (returning the original text unchanged), so it's silent — but
a document starting with `---` whose body happens to contain `\n---`
somewhere will accidentally have its body chopped and the chopped chunk
fed to `yaml.safe_load`. Should require `text.startswith("---\n")` (or
EOF after `---`).

**Issue B: YAML parse failures are silently dropped.**
```python
parsed: Any = yaml.safe_load(front_matter_block)
if parsed is None:
    return {}, body
if not isinstance(parsed, dict):
    return {}, body
```
If `yaml.safe_load` returns a list, scalar, or anything non-dict, the
function returns empty metadata silently. Metadata validation will then
fire on the empty dict and complain about missing `title`, but the actual
parse error (e.g. tab indentation, malformed YAML) never surfaces. Worth
either logging or re-raising on non-dict YAML.

Neither issue is critical; both are paper cuts.

### Step 8 — Template system + 6-level cascade (commit c6978a1)

**Strong**: `resolve_template_name` iterates *candidates first, then
locations* (overrides → templates → theme). This is the correct ordering
— it means a content-type-specific template in the theme wins over a
generic defaults template in overrides. Inverting the loop order would
break the override semantics. The cascade tests cover this well.

**The architectural mistake that bit later**: `build_page_context`
flattens the `Page` dataclass into a hand-built dict:

```python
page_namespace: dict[str, object] = {
    "title": page.title,
    "description": page.description,
    ...
    "authors": list(page.author_keys),   # this is the Bug 1 location
}
```

The original commit message says this is "so templates can use
mkdocs-style `page.title` access without adapter classes". But Jinja2
reads dataclasses just fine — `page.title` works whether `page` is a
dict or a `Page` dataclass. The hand-built dict has two real costs:

1. **Closed schema.** Anything new on `Page` (like `slug_override` in
   Step 6, `previous`/`next` in Step 9) silently doesn't reach
   templates unless someone remembers to add it here. This is the
   surface that caused Bug 1 (`authors` exposed as raw key strings) and
   Bug 2 (`custom_metadata` not exposed at all, so listing templates
   couldn't see their post lists). Both bugs survived to release.
2. **Two parallel APIs.** Internal code reads `page.author_keys`,
   `page.custom_metadata`, `page.output_url`. Templates read
   `page.authors`, `page.custom_metadata`, `page.url`. The list template
   even had `post.url` instead of `post.output_url` because of this
   inconsistency.

The fix in commit `d212d95` patches the symptoms by exposing
`custom_metadata` and resolving authors. The real fix would be to drop
the dict adapter and pass the `Page` dataclass directly. Worth a
follow-up.

**Other Step 8 notes:**
- The "6-level cascade" is actually 7 levels — the `if template_type
  != "page": candidates.append("page.html")` line adds an unconditional
  bottom fallback to `page.html`. Doesn't break anything, but the
  docstring count is off by one.
- The fall-through return (`return candidates[-1]`) is silent. If
  nothing on disk matches, the function returns the deepest candidate
  name and lets Jinja2 raise `TemplateNotFound`. Honest but the error
  could be friendlier.

### Step 10 — MVP build pipeline (commit 44930e9)

**`build()` is 120 lines with no internal phase boundaries marked.**
Readable, but the logical phases (load, discover, validate, structure,
render, output) are inline rather than extracted. A reader has to parse
the structure mentally. Splitting into named helpers (`_load_inputs`,
`_filter_and_validate`, `_render_all_pages`, `_emit_outputs`) would
make the hook insertion points obvious and keep each phase under a
screen.

**Two real hook-placement issues:**

1. **`on_pages` fires BEFORE draft filtering.** A plugin that wants
   to augment the published page set sees drafts too, then build.py
   filters them out. Order should be: discover → filter drafts →
   on_pages. Right now it's: discover → on_pages → filter. Means
   a plugin like "add canonical URL" runs on drafts that won't ship.

2. **`on_env` fires AFTER `data = load_data_files`** but the env
   doesn't see the data either way; data goes into the template
   context separately. A plugin wanting to inject data via on_env
   has nowhere to attach it. Need either an `on_data` event or a
   way for `on_env` to mutate the data dict.

**Hardcoded output path.** `output_dir = project_dir / "site"` — not
configurable. Spec hardcodes `site/` so this is by design, but it
removes a customization seam users will eventually ask for.

**No per-page error isolation.** A single page rendering throwing
(bad shortcode, unparseable date) aborts the whole build with a
stack trace. Better: catch per-page, dispatch `on_build_error`, and
in non-strict mode continue with the remaining pages. Real
production sites need this.

**`from bartleby.theme import get_theme_templates_dir as _theme_dir`
is inside the function.** Should be a top-of-file import. Cosmetic.

### Step 21 — Plugin system (commit 4aa5b4d)

**Clean overall.** `register()` uses stable sort (registration order
preserved within a priority). `event_priority` decorator works on both
methods and module functions per the test suite. `discover_hooks`
correctly skips `_`-prefixed files. The negative test
(`test_no_entry_point_discovery`) is a great defensive measure — it
locks in the "no public plugin API" design decision so a future refactor
that re-adds entry_points will fail loudly.

**Real issue: BasePlugin has 16 methods; `KNOWN_EVENTS` has 17.**

```python
KNOWN_EVENTS: tuple[str, ...] = (
    "on_startup", "on_shutdown", "on_config", "on_pre_build",
    "on_files", "on_nav", "on_env", "on_pre_page",
    "on_page_read_source", "on_page_markdown", "on_page_content",
    "on_page_context", "on_post_page", "on_post_build",
    "on_build_error", "on_serve",
    "on_pages",                                  # 17th, no BasePlugin method
)
```

`on_pages` was added during Step 10 to support the build pipeline's
page-filter hook, but never made it into BasePlugin's method list. A
real `BasePlugin` subclass can't implement `on_pages` cleanly — they'd
have to add the method themselves. Either remove `on_pages` from
`KNOWN_EVENTS` and rename to something already declared, or add the
matching no-op method to `BasePlugin`.

**Minor: no cross-hook import support.** Each hook file is loaded into
an isolated namespace via `importlib.util.spec_from_file_location`. A
hook that does `import my_helper` where `my_helper` is a sibling in
`hooks/` will fail because the hooks directory isn't on `sys.path`.
Most real-world hook collections will want this. Workaround for users:
put helpers in a package they install separately.

**No reload semantics.** `discover_hooks` is single-shot. When the dev
server lands its watchdog (Deferral 6), changing a hook file won't
re-register its handlers without a server restart. The fixed
`module_name = f"_bartleby_hook_{path.stem}"` would make re-loading
overwrite the spec but might leak stale function references in the
PluginCollection. Worth solving alongside Deferral 6.

### Cross-step patterns

**A: `Page` is the central god-object.** Almost every module touches
the `Page` dataclass: discovery sets the basic fields, URL generation
sets `output_url`, navigation sets `previous`/`next`, markdown rendering
sets `rendered_content` and `excerpt`, taxonomy/listing generation
creates virtual `Page` instances. The dataclass is comprehensible
because it's flat (no nested mutation), but the *order* of who sets
what is implicit. Refactoring `Page` to a frozen builder pattern
(immutable handoffs between phases) would surface that ordering
explicitly. Probably 0.2.0 work.

**B: Virtual pages stuff state into `custom_metadata`.** Listing and
taxonomy modules create virtual `Page` instances with their structured
data buried in `custom_metadata["posts"]`, `custom_metadata["paginator"]`,
etc. This is what caused Bug 2. A real fix would be subclassing
`Page` (or a sibling type `VirtualPage`) with named attributes. The
present approach gets away with it because mypy doesn't complain about
dict accesses on `dict[str, object]` — but the contract between the
generator and the template is untyped.

**C: Magic strings.** `"taxonomy_kind"`, `"taxonomy_term"`,
`"listing_kind"`, `"index"`, `"term"`, `"content_type"` appear in
`listings.py`, `taxonomies.py`, and `build.py::_template_type_for`.
A typo in any of them silently dispatches to the wrong template type.
Should be `enum.StrEnum` or module-level constants.

### Verdict

The history is exceptionally well-structured for an unsupervised
27-step push. Every commit is self-contained, tests pass at every
boundary, and the architectural decisions are documented in the
commit bodies. The four load-bearing commits I called out as
high-risk:

- **Step 4 (`parse_front_matter`)**: two minor edge cases (loose start
  detection, silent YAML failure). Not currently biting.
- **Step 8 (template cascade)**: cascade is correct; the dict-adapter
  pattern in `build_page_context` is the architectural mistake that
  caused Bugs 1 and 2 and will continue to be a pain point.
- **Step 10 (build pipeline)**: hook placement for `on_pages` is wrong
  (fires before draft filter); no per-page error isolation; long
  function with implicit phases. None are bugs *today* but all three
  will hurt as the pipeline accretes work.
- **Step 21 (plugin system)**: clean overall; `on_pages` in
  `KNOWN_EVENTS` but not `BasePlugin` is a small consistency miss;
  no reload story for the future dev server.

Plus three cross-cutting findings:
- **`Page` is a god-object** with implicit phase ordering
- **Virtual pages use untyped `custom_metadata`** (cause of Bug 2)
- **Magic strings** (`"taxonomy_kind"`, `"listing_kind"`, etc.) should
  be enums

None of these block 0.1.0 shipping. All of them are reasonable
0.2.0–0.3.0 cleanup targets — adding them to the audit tracker below
as "Design 1-7" so they're queued alongside the existing deferrals.

## Test 5 — Lint the spec against the implementation

**When**: 2026-06-02
**Method**: Walked `spec.md` section by section against the actual code.
Compared the spec's component list (27 components), CLI command catalogue
(14 commands), build pipeline (30-step order of operations), AI config
schema, and theme features against what's in `src/bartleby/`.

Note: `spec.md` has uncommitted refinements (Deferral 8) so I compared
against the working-tree version since that represents the actual intent.

### Gap Category A — Phase 5 "Agent Integration" never implemented

This is the largest gap by surface area. The spec devotes entire sections
to features that don't exist in the codebase. The 27-step
implementation plan deliberately scoped these out, but the spec still
describes them as v1 deliverables.

**Missing CLI commands (9 of 14):**

| Command | Spec describes | Implementation |
|---|---|---|
| `bartleby render <path>` | Single-page render to stdout | ❌ Not present |
| `bartleby lint` | Content quality checks (broken links, orphans, missing alt text, duplicate titles, unused terms) | ❌ Not present |
| `bartleby content list` | List content with filters/sort/fields | ❌ Not present |
| `bartleby content get <path>` | Fetch one piece of content as structured data | ❌ Not present |
| `bartleby schema <content-type>` | Export content type's metadata schema | ❌ Not present |
| `bartleby schema authors` | Export author definitions | ❌ Not present |
| `bartleby schema taxonomies` | Export taxonomy definitions + current term values | ❌ Not present |
| `bartleby generate-skill` | Generate agent skill files from config + content analysis | ❌ Not present |
| `bartleby export` | Serialize site to JSONL/JSON/CSV | ❌ Not present |

5 of 14 commands are implemented: `new site`, `new post`, `build`,
`validate`, `serve`.

**Missing src modules (5 of 27 components):**

The spec's Component Boundaries section enumerates 27 components. The
codebase has 24 source modules; missing:

- `content_query.py` (Component 23) — for `content list` / `content get`
- `schema_introspection.py` (Component 24) — for `schema` commands
- `linting.py` (Component 25) — for `lint`
- `skills.py` (Component 26) — for `generate-skill`
- `export.py` (Component 27) — for `export`

`output.py` (mentioned in plan.md for structured `--output json`) is
also missing; there is no `--output json` flag wired anywhere.

**Missing config blocks:**

Spec describes a full `ai.skills` configuration block:
```yaml
ai:
  skills:
    output_dir: .claude/skills
    analyze_content: true
    include_examples: 3
    style_guide: null
    regenerate_on_build: false
```

And an `ai.agent_context` block:
```yaml
ai:
  agent_context:
    voice: null
    audience: null
    constraints: []
```

Both are completely absent from `AIConfig` in `src/bartleby/config.py`.
The `AIConfig` dataclass has only `llms_txt`, `llms_full_txt`,
`markdown_variants`, and `robots` — the LLM output toggles. Everything
else `ai.*` describes is unbuilt.

**Missing build pipeline step:**

Spec pipeline step 25 — "Regenerate skills — if `ai.skills.
regenerate_on_build` is enabled, regenerate agent skill files from
current content" — is not in `build()`. There's no skills module to
regenerate from anyway.

### Gap Category B — Build pipeline coverage

Spec promises a 30-step "Order of Operations". The implementation
covers 22 of 30:

| Step | Coverage |
|---|---|
| 1–2 | ⚠️ Spec says "Discover plugins from pip packages and `plugins/` directory" — Step 21 implementation drops both in favour of `hooks/*.py`. Spec text is now stale. |
| 3 (`on_startup`) | ❌ Reserved (Deferral 7) |
| 4 (`on_config`) | ✅ |
| 5 (`on_pre_build`) | ❌ Reserved |
| 6 (discover content) | ✅ |
| 7 (`on_files`) | ❌ Reserved |
| 8 (validate metadata) | ✅ |
| 9 (resolve nav) | ✅ |
| 10 (`on_nav`) | ❌ Reserved |
| 11–14 (taxonomies + listings + link pages) | ✅ |
| 15 (`on_env`) | ✅ |
| 16a (`on_pre_page`) | ❌ Reserved |
| 16b (`on_page_read_source`) | ❌ Reserved |
| 16c (shortcodes) | ✅ |
| 16d (`on_page_markdown`) | ✅ |
| 16e (render markdown) | ✅ |
| 16f (`on_page_content`) | ❌ Reserved |
| 16g (crossrefs) | ✅ (since d212d95 errors print + `--strict` honors them) |
| 16h–j (readtime, template lookup, context build) | ✅ |
| 16k (`on_page_context`) | ❌ Reserved |
| 16l (render template) | ✅ |
| 16m (`on_post_page`) | ✅ |
| 16n (write to site) | ✅ |
| 16o (copy colocated) | ✅ |
| 17 (markdown variants) | ✅ |
| 18 (tree-shake icons) | ✅ |
| 19 (search index) | ✅ |
| 20 (feeds) | ✅ |
| 21 (sitemap) | ✅ |
| 22 (robots.txt) | ✅ |
| 23 (llms.txt) | ✅ |
| 24 (llms-full.txt) | ✅ |
| 25 (regenerate skills) | ❌ Not implemented |
| 26 (render static templates 404.html etc.) | ⚠️ Theme has `404.html` template but build never renders it as a standalone `/404.html` in output |
| 27 (copy static assets) | ✅ |
| 28 (copy theme assets) | ✅ |
| 29 (`on_post_build`) | ❌ Reserved |
| 30 (`on_shutdown`) | ❌ Reserved |

8 reserved hooks + 1 missing skills step + 1 missing 404 emission =
**8 of 30 steps fully missing, 1 partial** beyond what's in the
existing Deferral 7. The 404 gap is the only genuinely new finding
here (the rest are already tracked as Deferral 7 or Gap A).

### Gap Category C — Theme features advertised but dead

Spec's "Theme Feature Toggles" section and `theme.features` config
list claim:

```yaml
theme:
  features:
    - search                    # Search modal with lunr.js
    - navigation.tabs           # Top-level nav as tabs
    - navigation.top            # Back-to-top button
    - navigation.sections       # Sidebar with collapsible sections
    - navigation.expand         # Expand-all default for sections
    - content.code.copy         # Copy button on code blocks
    - content.tabs.link         # Tab clicks update URL
    - toc.follow                # Sidebar TOC follows scroll
    - announce.dismiss          # Dismissible announcement bar
```

The `ThemeConfig` dataclass accepts `features: list[str]`, but the
bundled theme templates do not consult that list. Every "feature" the
template hard-codes (search modal markup, dark-mode toggle, back-to-top
button, TOC sidebar) is always emitted regardless of `theme.features`.
And per Deferral 1, the JS that would activate any of them is a stub.

This is technically two gaps stacked:
1. **`theme.features` is a dead config value** — listing or omitting an
   entry has no effect on the rendered HTML.
2. **Even when markup is emitted, no JS runs** (Deferral 1).

### Gap Category D — Smaller gaps

**Deferred Features (v2+) section is honest.** Spec explicitly defers
archive pages, social card generation, i18n, asset pipeline, page
feedback widget, and migration tool. None of these are claimed as v1.
The `data:` template seam (Step 8) does provide YAML+TOML data files —
which the deferred list says is "deferred to v2", an inconsistency.
The implementation actually has data files (Step 8); the deferred list
is stale.

**Spec mentions a "Future: MCP Server" section.** Explicitly future
work; not a gap.

**Spec doesn't document `extra_css` / `extra_js`** in the
`bartleby.yml` reference but the implementation supports them
(matches the docs/ site I wrote). The spec.md uncommitted-diff
includes this (Deferral 8). When the spec changes are committed
this gap closes.

**Spec calls extension load order "do_markdown.fence preprocessor
(priority 40) BEFORE pymdownx.superfences (priority 25)".** Code
relies on Python-Markdown's natural priority ordering — there's no
explicit re-ordering in `markdown_pipeline.py`. This works only
because the loaded extensions self-declare those priorities. Worth a
defensive comment or test that locks in the assertion. (Step 7 does
have a behavioural test for this — so it is verified, just not
documented in the code.)

### What's in the code but not (yet) in spec

- `extra_css` / `extra_js` config keys (working-tree spec adds these)
- The 6-level template cascade (working-tree spec widens from 5)
- Customization Seams enumerated as a discrete section (working-tree spec)
- Step 21 plugin redesign (drop entry_points + `plugins/` subclass) — working-tree spec
- `--strict` build flag (added 2026-06-02; spec doesn't mention)
- The `--include-drafts` build flag (impl-only)

When the Deferral 8 working-tree spec/plan diff lands, the first four
of these close. The last two should be added to spec.md as a small
follow-up.

### Verdict + tracker additions

The "spec vs. implementation" picture is clearer than I expected:

- **Phase 5 Agent Integration is the giant missing piece.** 9 CLI
  commands, 5 modules, 2 config blocks, 1 pipeline step. This was
  explicitly scoped out of the 27-step plan, but the spec still
  promises it. Anyone reading spec.md as "what Bartleby 0.1 does" is
  going to be confused.
- **Theme feature config is dead** — the `theme.features` list is
  declared and parsed but nothing reads it.
- **The 404 template is shipped but never rendered as a standalone
  output file.**

Most other gaps are already tracked (Deferral 7 reserved hooks,
Deferral 1 dead JS, Deferral 8 working-tree spec diffs).

Adding four new tracker entries — Spec 1 (Phase 5 wholesale missing),
Spec 2 (`theme.features` is dead config), Spec 3 (404.html never
rendered as output), Spec 4 (spec describes data files as "deferred
to v2" but they're implemented).

## Test 6 — Run /ultrareview on the branch

_Pending (user-triggered, billed). Out of scope for the agent;
worth running as an independent cross-check on this audit's
findings before acting on them._

---

## Next session — paths

Tests 1–5 closed; tracker has 37 open items. The four reasonable
ways to spend the next session:

### Path A — Tackle the top of the punch list (release-blockers)

Get the 3 release-blocking items off the tracker:

1. **Deferral 1** — vendor real `alpine.min.js`, `htmx.min.js`,
   `lunr.min.js` bundles into `src/bartleby/theme/static/js/`.
   These are tiny (~40 KB combined gzipped), no build chain
   needed. The CDN-served bundles can be checked in directly with
   their license headers preserved.
2. **Deferral 6** — wire `watchdog.Observer` and `websockets`
   into `DevServer.run()`. The change-classification logic
   (`classify_change`) and rebuild dispatcher (`handle_change`)
   already exist from Step 23; just need the actual file watcher
   and the WebSocket reload broadcast.
3. **Spec 1** — either ship Phase 5 (large) or reword `spec.md`
   to mark the agent-integration sections as Roadmap (cheap).
   The "MCP Server" section already has the right shape to copy.

Effort: 1–3 days for #1 and #3; #2 is the big-ticket item
(~1 week including good live-reload UX). After this Bartleby is
genuinely shippable.

### Path B — Quick wins (small high-leverage fixes)

Pick off the LOW-severity items that have small surface area but
real impact:

- **Design 14** — wrap `_cmd_build` with a clean exception
  handler so users see "metadata validation failed: …" instead
  of a Python traceback. ~15 lines.
- **Design 17** — extend `bartleby validate` to also dry-run
  URL generation, check template existence, and report crossref
  errors. ~30 lines.
- **Meta 1** — pick a license (MIT? Apache-2.0?), add it to
  `pyproject.toml`, drop a `LICENSE` file at the repo root,
  update README.
- **Meta 2** — add a `CHANGELOG.md` seeded from the existing
  Step 1–27 commit messages. The session summaries already
  describe each step.
- **Deferral 8** — review the working-tree spec/plan diffs and
  either commit them (closes Spec 4 + closes the extra_css/js
  drift) or revert.

Effort: one focused afternoon. Closes 5 tracker items with no
architectural risk.

### Path C — Run `/ultrareview` first

Before acting on any of the above, run `/ultrareview` as an
independent cross-check on this audit. Different reviewer model,
different prompt, different blind spots. The audit's findings are
self-consistent but I'm the same agent that built most of this —
worth knowing whether a fresh perspective surfaces things I
papered over. User-triggered and billed; not something the agent
can spawn.

### Path D — Pivot to feature work

The audit found 37 open items but the code in `main..v1` is a
working SSG. If shipping isn't the immediate goal, the next
logical feature step from the original plan was Step 28
(structured `--output json` for every CLI command) — that's the
foundation for everything in Phase 5 Agent Integration.

`spec.md` describes the JSON output shape in the "Structured CLI
for Agents" section. The infrastructure module would be
`output.py` (plan.md mentions it). Each existing CLI command
would gain an `--output {text|json}` flag and a result dataclass
that serialises both ways.

Effort: ~2–3 days. Doesn't close any audit items directly but
unlocks Phase 5 work without committing to all of it.

### Recommendation

If shipping 0.1.0 matters: **Path B first (one afternoon),
then Path A** — quick wins clear the smaller stuff so the bigger
work isn't drag-burdened by accumulated debt. Run `/ultrareview`
(Path C) at any point before merging the Path A work.

If shipping isn't immediate: **Path D** — feature work keeps
momentum and the tracker stays a known backlog rather than a
blocker.
