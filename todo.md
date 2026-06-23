# Bartleby v0.1.0 Hardening — Progress

Delta plan over the 27-step initial build. See `plan.md` for the full TDD
prompts and `audit.md` for the findings each step closes. 4 of 18 steps done.

## Phase 1 — Foundations

- [x] **Step 1: Pass the Page dataclass into template context** (Design 3, 4)
  - [x] 1.1: RED — template-context tests (Page reachable, new field renders, bylines resolve)
  - [x] 1.2: RED — draft-filter ordering test (on_pages sees only published)
  - [x] 1.3: GREEN — build_page_context passes Page; templates read page.<attr>
  - [x] 1.4: GREEN — move on_pages after the draft filter
  - [x] 1.5: REFACTOR — remove dict-adapter dead code
  - [x] 1.6: Confirm spec Template Context section; run `just check`

- [x] **Step 2: Build failure semantics and clean error reporting** (Design 5, 14, 15)
  - [x] 2.1: RED — collect-all errors, untouched site/ on failure, atomic swap, fail-fast on config
  - [x] 2.2: RED — clean error (no traceback) + BARTLEBY_DEBUG re-enables it
  - [x] 2.3: GREEN — accumulate per-page errors; temp-dir build + swap
  - [x] 2.4: GREEN — top-level CLI error boundary
  - [x] 2.5: GREEN — logging.getLogger for non-essential output
  - [x] 2.6: RED — on_build_error fires once with the collected list
  - [x] 2.7: REFACTOR — shared error formatting; run `just check`

- [x] **Step 3: Structured output layer (--output json)**
  - [x] 3.1: RED — formatter tests (build/error/text shapes, exit codes)
  - [x] 3.2: GREEN — output.py result dataclasses + formatter
  - [x] 3.3: GREEN — global flags; route build/validate/new through it
  - [x] 3.4: RED — build/validate json is valid and parseable
  - [x] 3.5: REFACTOR — one path, both formats; run `just check`

## Phase 2 — Theme reality

- [x] **Step 4: Vendor real Alpine, HTMX, lunr bundles** (Deferral 1)
  - [x] 4.1: RED — size/signature tests + THIRD-PARTY-NOTICES + build copies them
  - [x] 4.2: GREEN — vendor pinned minified bundles; record versions/licenses
  - [x] 4.3: RED — rendered output wires markup to the bundles
  - [x] 4.4: GREEN — base.html/partials reference real bundles
  - [x] 4.5: REFACTOR — remove stub comments; run `just check`

- [ ] **Step 5: Hybrid Tailwind pipeline and `bartleby theme compile`** (Deferral 2)
  - [ ] 5.1: RED — resolver order, checksum-abort, compiled-CSS preference
  - [ ] 5.2: GREEN — package-build CSS from templates + safelist
  - [ ] 5.3: GREEN — theme compile command (PATH/cache/download, SHA-256, --refresh)
  - [ ] 5.4: GREEN — build prefers .bartleby/theme.css
  - [ ] 5.5: RED — theme compile --output json shape
  - [ ] 5.6: REFACTOR — no implicit download in build; run `just check`

- [ ] **Step 6: Feature toggle enforcement** (Spec 2)
  - [ ] 6.1: RED — unknown feature name is a validation error
  - [ ] 6.2: RED — enabling/disabling adds/removes markup entirely
  - [ ] 6.3: GREEN — feature() helper + template gating
  - [ ] 6.4: GREEN — known-feature validation in config.py
  - [ ] 6.5: REFACTOR — one known-feature list; run `just check`

- [ ] **Step 7: Full icon packs and standalone 404** (Deferral 3, Spec 3)
  - [ ] 7.1: RED — resolve icons across all four packs; tree-shake; unused pack = 0 files
  - [ ] 7.2: RED — build renders site/404.html
  - [ ] 7.3: GREEN — vendor complete packs; get_icon_path resolves full set
  - [ ] 7.4: GREEN — 404 render in pipeline
  - [ ] 7.5: REFACTOR — tree-shake scans HTML + templates; run `just check`

## Phase 3 — Plugins

- [ ] **Step 8: All hook events fire; BasePlugin parity** (Deferral 7, Design 6)
  - [ ] 8.1: RED — each of the 16 events dispatched once with correct args; return-value semantics; BasePlugin parity
  - [ ] 8.2: GREEN — add missing dispatch call sites in build.py/server.py
  - [ ] 8.3: GREEN — reconcile KNOWN_EVENTS and BasePlugin
  - [ ] 8.4: REFACTOR — priority-then-registration for every event; run `just check`

- [ ] **Step 9: Entry-point plugin discovery**
  - [ ] 9.1: RED — bartleby.plugins discovery; ordering internal/plugins/hooks; config disable
  - [ ] 9.2: GREEN — entry-point discovery merged with hooks/*.py; honor disable list
  - [ ] 9.3: GREEN — wire into hook-discovery pipeline step
  - [ ] 9.4: REFACTOR — single registration path; run `just check`

## Phase 4 — Dev server

- [ ] **Step 10: Live reload with last-good-build and hook reload** (Deferral 6, Design 13)
  - [ ] 10.1: RED — watcher fires on all watched paths; hook/config reload; last-good-build on failure; reload snippet serve-only
  - [ ] 10.2: GREEN — DevServer.run() with watchdog + websockets + full rebuild + retention + restart
  - [ ] 10.3: GREEN — auto theme-recompile when cached, else hint
  - [ ] 10.4: RED — --events JSON stream shape
  - [ ] 10.5: REFACTOR — no reload code in production builds; run `just check`

## Phase 5 — Agent surface and CLI (Spec 1)

- [ ] **Step 11: Schema introspection**
  - [ ] 11.1: RED — schema for type/authors/taxonomies; public author fields only
  - [ ] 11.2: GREEN — schema_introspection.py + `bartleby schema` command
  - [ ] 11.3: RED — json matches the manifest field shape
  - [ ] 11.4: REFACTOR — reusable schema derivation; run `just check`

- [ ] **Step 12: Content query**
  - [ ] 12.1: RED — content list (filter/sort), content get, drafts excluded
  - [ ] 12.2: GREEN — content_query.py + commands
  - [ ] 12.3: REFACTOR — share published-page selection with build; run `just check`

- [ ] **Step 13: Static agent surface (schema.json + content-index.json)**
  - [ ] 13.1: RED — both artifacts; field curation rule; llms.txt discovery section; per-page alternate links; collision error; agent_surface toggle
  - [ ] 13.2: GREEN — emit artifacts (pipeline step 24a); reuse schema derivation; alternate-link injection
  - [ ] 13.3: GREEN — ai.agent_surface config + collision detection
  - [ ] 13.4: REFACTOR — one curation function; run `just check`

- [ ] **Step 14: render and lint commands**
  - [ ] 14.1: RED — render single page to HTML + json
  - [ ] 14.2: RED — lint broken links/missing desc/orphans; --check-external opt-in
  - [ ] 14.3: GREEN — render in cli.py reusing pipeline
  - [ ] 14.4: GREEN — linting.py + lint command
  - [ ] 14.5: REFACTOR — share link resolution with crossrefs; run `just check`

- [ ] **Step 15: export, generate-skill, build --dry-run**
  - [ ] 15.1: RED — JSONL/JSON/CSV export
  - [ ] 15.2: RED — three deterministic skills; agent_context verbatim; analyze_content reserved error
  - [ ] 15.3: RED — build --dry-run reports without writing
  - [ ] 15.4: GREEN — export.py, skills.py, dry-run
  - [ ] 15.5: REFACTOR — reuse schema derivation + content selection; run `just check`

## Phase 6 — Feeds

- [ ] **Step 16: Site-wide aggregate feed** (site.feed)
  - [ ] 16.1: RED — include scope rule (empty=all, list restricts, no-feed type = error); merge/sort/limit; category per item; root paths
  - [ ] 16.2: RED — contextual auto-discovery (homepage = aggregate; section = type first, aggregate second)
  - [ ] 16.3: GREEN — site.feed config parse + validation
  - [ ] 16.4: GREEN — aggregate builder + contextual link selection
  - [ ] 16.5: GREEN — wire into feed pipeline step
  - [ ] 16.6: REFACTOR — share item construction; run `just check`

## Phase 7 — Release readiness

- [ ] **Step 17: Smoke test and test-quality hardening** (TestGap 1-5)
  - [ ] 17.1: RED — e2e smoke (scaffold/post/build, grep title + byline + listing)
  - [ ] 17.2: RED — render list + taxonomy templates and assert posts appear
  - [ ] 17.3: RED — theme tests render-and-inspect HTML, not raw CSS strings
  - [ ] 17.4: RED — DevServer.run() integration test
  - [ ] 17.5: GREEN — fix underlying code, not the tests
  - [ ] 17.6: Add smoke test to CI; run `just check`

- [ ] **Step 18: Packaging and polish** (Meta 1-2, Design 1, 2, 7-12, 16, 17)
  - [ ] 18.1: RED — front-matter newline (Design 1) + non-dict YAML error (Design 2) + configurable output dir (Design 10) + expanded validate (Design 17)
  - [ ] 18.2: GREEN — implement those behavior changes
  - [ ] 18.3: REFACTOR — magic-string enum (7), docstring/fall-through (8, 9), import to top (11), hooks sys.path (12), split build() (16)
  - [ ] 18.4: Packaging — LICENSE (MIT), pyproject license, README, CHANGELOG (Meta 1, 2)
  - [ ] 18.5: Run `just check`
