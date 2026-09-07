# Bartleby v1 Remediation: Progress

Read `handoff.md` first, then `plan.md` for the full TDD prompts and `spec.md` (R1-R17) for required behavior and acceptance criteria. 0 of 19 steps done.
Each phase ends at an optional Fable checkpoint (safe commit and review boundary); the markers live in `plan.md`.

## Phase 1: Unblock the Suite

- [x] **Step 1: Fix the linting.py SyntaxError and add an import health gate** (R1)
  - [x] 1.1: RED: tests/test_import_health.py: all bartleby modules import; check_external_url returns False on URLError/ValueError/OSError
  - [x] 1.2: GREEN: parenthesize the except tuple at linting.py:205 — investigated, not applied; see session notes, no source change was needed under Python 3.14
  - [x] 1.3: Investigate the smoke-test gap; make smoke invoke cli.main() if it bypasses the entry point — already does; no gap found
  - [x] 1.4: Run `just check` (first full-suite run); record unexpected failures — do-markdown/markwright rename fixed by prerequisite migration (commit 24fdace); `just check` now green, 511 passed

- [x] **Step 2: Populate the Tailwind release checksum map** (R2)
  - [x] 2.1: RED: map key set equals the six asset names; values match ^[0-9a-f]{64}$; map path installs via _download_binary
  - [x] 2.2: GREEN: populate _RELEASE_SHA256 with official digests for PINNED_TAILWIND_VERSION
  - [x] 2.3: RED: checksum-mismatch abort regression guard still passes
  - [x] 2.4: Run `just check`

- [x] **Fable checkpoint (optional): Phase 1 done (R1, R2, critical); suite runs, `just check` green**

## Phase 2: Error Contract

- [x] **Step 3: Route ContentError and build validation failures through the error contract** (R3)
  - [x] 3.1: RED: strict-crossref test expects BuildError (update test_build.py:306); metadata failure raises BuildError with PageErrors
  - [x] 3.2: RED: ContentError via lint: exit 1, no traceback; json ErrorOutput with content_error + source path; BARTLEBY_DEBUG re-raises
  - [x] 3.3: GREEN: build.py raises BuildError at both sites; docstrings updated
  - [x] 3.4: GREEN: cli.py catches ContentError; _ERROR_CODES gets content_error
  - [x] 3.5: REFACTOR: one catch site covers all content-discovering commands
  - [x] 3.6: Run `just check`

- [x] **Step 4: Guarantee temp build directory cleanup on every failure path** (R16)
  - [x] 4.1: RED: no .bartleby-build-* remains after strict failure or _emit_outputs exception; success guard still passes
  - [x] 4.2: GREEN: try/finally (or context manager) owns the temp dir lifetime
  - [x] 4.3: REFACTOR: single removal site; docstring contracts stay accurate
  - [x] 4.4: Run `just check`

- [x] **Fable checkpoint (optional): Phase 2 done (R3, R16); error contract catches every failure, no temp-dir leaks**

## Phase 3: Build Pipeline Correctness

- [x] **Step 5: Enforce draft exclusion for co-located assets and the taxonomy schema** (R7)
  - [x] 5.1: RED: draft page + asset both absent from production build; include_drafts writes both; published asset regression guard
  - [x] 5.2: RED: derive_taxonomies_schema omits draft-only terms; CLI schema taxonomies omits them
  - [x] 5.3: GREEN: filter state.assets against surviving pages before copy
  - [x] 5.4: GREEN: select_published inside derive_taxonomies_schema; agent_surface output unchanged
  - [x] 5.5: REFACTOR: one shared published-page helper
  - [x] 5.6: Run `just check`

- [x] **Step 6: Detect co-located asset collisions in shared directories** (R8)
  - [x] 6.1: RED: two pages + asset in one dir raises error naming dir and pages; no-asset case builds; single-bundle regression guards
  - [x] 6.2: GREEN: dict[str, list[Page]] index; collision raises through BuildError
  - [x] 6.3: REFACTOR: check fires only when an asset hits a multi-page dir
  - [x] 6.4: Run `just check`

- [x] **Step 7: Merge icon pack defaults instead of replacing them** (R10)
  - [x] 7.1: RED: {simple: false} leaves other three enabled; empty config = all four; two-false case exact
  - [x] 7.2: GREEN: overlay config entries on the all-True default dict
  - [x] 7.3: REFACTOR: one canonical pack-list constant
  - [x] 7.4: Run `just check`

- [ ] **Step 8: Count only copied files in static_file_count** (R17)
  - [ ] 8.1: RED: count equals N static + M assets despite generated artifacts present; ai.llms_txt toggle does not change count
  - [ ] 8.2: GREEN: sum copy counts from copy_static_files/copy_colocated_assets, no re-glob
  - [ ] 8.3: REFACTOR: BuildResult docstring accurate
  - [ ] 8.4: Run `just check`

- [ ] **Fable checkpoint (optional): Phase 3 done (R7, R8, R10, R17); draft exclusion, loud asset-collision error, icon-pack merge, honest static count**

## Phase 4: Rendering Correctness

- [ ] **Step 9: Render listing intro content as HTML** (R11)
  - [ ] 9.1: RED: strengthen test_listings.py:120 to assert <h2>/<strong>, not literal markdown
  - [ ] 9.2: GREEN: render index.md body through the markdown pipeline before storing intro_content
  - [ ] 9.3: REFACTOR: accept the build's renderer instance; one renderer per build
  - [ ] 9.4: Run `just check`

- [ ] **Step 10: Emit valid JSON-LD from one generator** (R9)
  - [ ] 10.1: RED: quoted/backslash/< title renders an ld+json block that json.loads and round-trips; equals generate_jsonld output
  - [ ] 10.2: GREEN: context carries generate_jsonld output; partial emits it; hand-built lines deleted
  - [ ] 10.3: REFACTOR: generator covers all fields the partial emitted; special-char tests on the generator too
  - [ ] 10.4: Run `just check`

- [ ] **Step 11: Protect multi-backtick inline code from shortcode expansion** (R12)
  - [ ] 11.1: RED: shortcode literal inside double-backtick span; inside span containing a single backtick; single-backtick regression guard
  - [ ] 11.2: GREEN: CommonMark N-backtick span matching replaces _INLINE_CODE_RE
  - [ ] 11.3: REFACTOR: docstring accurate
  - [ ] 11.4: Run `just check`

- [ ] **Fable checkpoint (optional): Phase 4 done (R11, R9, R12); listing intros render, valid JSON-LD, multi-backtick code protected**

## Phase 5: Dev Server

- [ ] **Step 12: Serve the configured output directory** (R4)
  - [ ] 12.1: RED: output_dir: public served correctly; default site/ regression guard
  - [ ] 12.2: GREEN: resolve serve dir from loaded config; share config between build and handler
  - [ ] 12.3: REFACTOR: no other hardcoded "site" in server.py
  - [ ] 12.4: Run `just check`

- [ ] **Step 13: Wire the file watcher into DevServer.run()** (R5, part 1)
  - [ ] 13.1: RED: watched change rebuilds (visible over HTTP, bounded wait); unwatched change does not
  - [ ] 13.2: GREEN: watchdog Observer in run() routing through existing primitives; clean shutdown; dependency confirmed in pyproject.toml
  - [ ] 13.3: GREEN: last-good-build retention holds via a real watcher-triggered failure
  - [ ] 13.4: REFACTOR: compose primitives, no duplicated decision logic; module docstring accurate
  - [ ] 13.5: Run `just check`

- [ ] **Step 14: Serve the reload snippet and WebSocket channel** (R5, part 2)
  - [ ] 14.1: RED: served HTML contains RELOAD_SNIPPET; WS client at /__bartleby_reload gets signal after rebuild; build output snippet-free
  - [ ] 14.2: GREEN: serve-path snippet injection + websockets endpoint broadcasting on successful rebuild; dependency confirmed
  - [ ] 14.3: REFACTOR: reload code lives only on the serve path; route/URL defined once
  - [ ] 14.4: Run `just check`

- [ ] **Fable checkpoint (optional): Phase 5 done (R4, R5); serves configured output dir, rebuilds on change, live-reloads**

## Phase 6: CLI and Agent Surface

- [ ] **Step 15: Resolve crossrefs before the lint orphan pass** (R6)
  - [ ] 15.1: RED: .md-linked page not orphaned via CLI lint; nav page never orphaned; existing lint JSON test asserts no spurious orphans
  - [ ] 15.2: GREEN: _cmd_lint calls resolve_all_crossrefs before lint_site
  - [ ] 15.3: REFACTOR: remove redundant re-resolution in _lint_crossrefs if dead; unit tests unchanged
  - [ ] 15.4: Run `just check`

- [ ] **Step 16: Discover shortcodes across all three lookup locations** (R13)
  - [ ] 16.1: RED: project-root, templates/, and theme shortcodes all discovered; de-duplicated; generate-skill includes project-root shortcode
  - [ ] 16.2: GREEN: _discover_shortcode_names scans the loader's cascade
  - [ ] 16.3: REFACTOR: one shared source for the search roots where feasible
  - [ ] 16.4: Run `just check`

- [ ] **Step 17: Advertise the aggregate feed in schema.json** (R14)
  - [ ] 17.1: RED: aggregate feed.xml/atom.xml present per formats; absent when site.feed disabled
  - [ ] 17.2: GREEN: _resource_locations reads config.site.feed and appends aggregate URLs
  - [ ] 17.3: REFACTOR: shared feed-URL helper so advertised and written URLs cannot drift
  - [ ] 17.4: Run `just check`

- [ ] **Step 18: Scope the hooks sys.path insertion** (R15)
  - [ ] 18.1: RED: sys.path restored after discover_hooks; double call does not grow it; sibling-import regression guard
  - [ ] 18.2: GREEN: try/finally scopes the insertion to the load loop
  - [ ] 18.3: REFACTOR: docstring notes discovery-time-only sibling resolution
  - [ ] 18.4: Run `just check`

- [ ] **Fable checkpoint (optional): Phase 6 done (R6, R13, R14, R15); lint orphans fixed, shortcode discovery, aggregate feed, scoped sys.path**

## Phase 7: Cycle Verification

- [ ] **Step 19: Extend the e2e smoke test and close the cycle**
  - [ ] 19.1: RED: smoke covers custom output_dir + quoted title + draft-with-asset + .md crossref, through build and serve
  - [ ] 19.2: GREEN: fix composition defects only if surfaced; otherwise no production change
  - [ ] 19.3: Final gate: `just check`; all todo steps checked; R1-R17 closed
  - [ ] 19.4: CHANGELOG.md remediation entry

- [ ] **Fable checkpoint (optional): Phase 7 done; cycle verified, R1-R17 closed, `just check` green, ready to ship**
