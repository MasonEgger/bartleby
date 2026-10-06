# Bartleby v1 Remediation Plan

> **Read `handoff.md` first.**
> It carries the current state (v1 baseline `2a4dd91`, 20 confirmed defects, 0/100 started), the settled review decisions (R8 = loud build error; fountain-py integration deferred to a v2 cycle), the known risks, and the exact next action.
> This plan assumes that context.

## Current Status

**0 of 19 steps complete.**

This is a defect-remediation plan, not a feature plan.
The v1 build and the 0.1.0 hardening cycle are done (see git history through `2a4dd91`).
A verified code review found 20 confirmed defects; `spec.md` (the remediation spec) defines the required behavior for each as requirements R1 through R17.
The v1 product spec, cited throughout, is preserved at `git show 2a4dd91:spec.md`.

Every step below names the requirement(s) it closes.
Re-read that requirement section in `spec.md` before writing the step's tests; the acceptance criteria there are the test list.

### Scope at a Glance

| Phase | Steps | Closes |
|---|---|---|
| 1. Unblock the Suite | 1-2 | R1, R2 (critical) |
| 2. Error Contract | 3-4 | R3, R16 |
| 3. Build Pipeline Correctness | 5-8 | R7, R8, R10, R17 |
| 4. Rendering Correctness | 9-11 | R11, R9, R12 |
| 5. Dev Server | 12-14 | R4, R5 |
| 6. CLI and Agent Surface | 15-18 | R6, R13, R14, R15 |
| 7. Cycle Verification | 19 | spec.md Verification section |

### Ordering Constraints (from spec.md Component Boundaries)

- Step 1 (R1) gates everything: the CLI does not import until it lands.
- R3 (step 3) lands before R8 (step 6) and R16 (step 4), which raise or route through `BuildError`.
- R7's asset half (step 5) lands before R8 (step 6); both touch `copy_colocated_assets`.
- R4 (step 12) lands before R5 (steps 13-14): live reload serves the directory the watcher rebuilds into.

## Implementation Guidelines

- TDD: RED (failing tests that reproduce the defect) then GREEN (minimal fix) then REFACTOR.
- Where an existing test codifies the buggy behavior, updating it is part of the RED step (each step's NOTE names these).
- Each step ends with `just check` passing (pytest, ruff, mypy strict).
- Strict type hints everywhere; no `Any` escape hatches.
- Every new `.py` file starts with a 2-line `ABOUTME: ` comment.
- Test your application logic, not library behavior.
- Fixes change only the defective behavior; update docstrings that document the buggy contract.
- Build on prior steps; leave no orphan code.

---

## Phase 1: Unblock the Suite

**Validator consults:**
- MCPs: none
- Skills: python:python

### Step 1: Fix the linting.py SyntaxError and Add an Import Health Gate (R1)

**NOTE**: `src/bartleby/linting.py:205` has Python 2 `except` syntax, a hard `SyntaxError`.
`cli.py:38` imports linting at module level, so every CLI command is dead.
Nothing else can be verified until this lands.
Also investigate why the v1 e2e smoke test passed with an unimportable CLI.

**DISPOSITION (2026-09-06): done, not as originally planned.**
R1 does not reproduce on Python 3.14 (PEP 758 legalizes the syntax); see spec.md's R1 Disposition.
Sub-step 2 (parenthesize) is intentionally NOT applied: `ruff format` reverts it and `just check` would fail.
`linting.py` stays unchanged. The kept deliverable is the import-health gate `tests/test_import_health.py`.
Sub-step 3's smoke gap does not exist: `tests/test_smoke.py` already drives `cli.main()`.
`just check` is green after the prerequisite markdown-dependency migration (do-markdown -> markwright).

```text
1. RED: Write import-health tests first:
   - Create tests/test_import_health.py:
     - Test that every module under src/bartleby/ imports cleanly: walk the
       bartleby package with pkgutil.walk_packages and
       importlib.import_module each module; assert no exception. This fails
       today with SyntaxError from linting.py.
     - Test that check_external_url returns False when the probe raises
       URLError, when it raises ValueError, and when it raises OSError
       (monkeypatch urllib.request.urlopen to raise each in turn).

2. GREEN: Fix src/bartleby/linting.py:205 to
   `except (URLError, ValueError, OSError):` (parenthesized tuple). No other
   code change.

3. Investigate the smoke-test gap: read tests/test_smoke.py and determine how
   it exercised "the CLI" without importing cli.py (for example by calling
   build() directly). If it bypasses the console entry point, extend it to
   invoke bartleby.cli.main() in-process for at least one command so an
   import-time regression in any CLI dependency fails the suite.

4. Verify meaningful coverage of the import gate and run `just check`. This is
   the first time the full suite can run; fix nothing else that surfaces, but
   record any unexpected failures in the session notes for later steps.
```

### Step 2: Populate the Tailwind Release Checksum Map (R2)

**NOTE**: `_RELEASE_SHA256` in `src/bartleby/theme_compile.py:28` shipped empty, so first-run `bartleby theme compile` always fails before fetching.
The real digests come from the Tailwind CSS GitHub release for `PINNED_TAILWIND_VERSION`; fetching them is implementation work, not test work.

```text
1. RED: Write checksum-map tests first:
   - Extend tests/test_theme_compile.py:
     - Test that _RELEASE_SHA256's key set equals exactly the six asset names
       tailwind_asset_name() can produce: tailwindcss-linux-x64,
       tailwindcss-linux-arm64, tailwindcss-macos-x64, tailwindcss-macos-arm64,
       tailwindcss-windows-x64.exe, tailwindcss-windows-arm64.exe.
     - Test that every value matches ^[0-9a-f]{64}$.
     - Test the map path: monkeypatch _RELEASE_SHA256 with an entry whose value
       is the SHA-256 of known stub bytes, call
       _download_binary(cache_dir=tmp, expected_sha256=None, fetch=stub) for
       that asset, and assert the binary installs (no "no recorded SHA-256"
       error).

2. GREEN: Populate _RELEASE_SHA256 in src/bartleby/theme_compile.py with the
   official SHA-256 digests for PINNED_TAILWIND_VERSION, one entry per asset
   name above. Fetch the digests from the tailwindcss GitHub release for that
   exact version (the release publishes per-asset checksums); verify each
   downloaded digest string is 64 hex chars before committing it. Keep the
   header comment's promise that the map is bumped together with
   PINNED_TAILWIND_VERSION accurate.

3. RED: Confirm the regression guard: the existing checksum-mismatch test
   (tests/test_theme_compile.py:96) still passes unchanged.

4. Verify coverage and run `just check`.
```

> **Fable checkpoint (optional).**
> Phase 1 done: R1 and R2, both critical.
> The full suite runs for the first time and `just check` is green.
> Natural commit and review boundary before Phase 2.

---

## Phase 2: Error Contract

**Validator consults:**
- MCPs: none
- Skills: python:python

### Step 3: Route ContentError and Build Validation Failures Through the Error Contract (R3)

**NOTE**: Two escapes from the clean-error contract: `ContentError` is not caught by the CLI boundary at `cli.py:109`, and `build.py` raises raw `ValueError` for metadata (line 259) and strict-crossref (line 350) failures.
`tests/test_build.py:306` (`test_build_strict_fails_on_broken_crossref`) asserts `pytest.raises(ValueError)` and codifies the bug; updating it is part of RED.

```text
1. RED: Write build-exception tests first:
   - Modify tests/test_build.py:
     - Change test_build_strict_fails_on_broken_crossref (line 306) to expect
       BuildError, carrying one PageError per broken crossref with its
       file_path.
     - Add a test that a build whose pages fail metadata validation raises
       BuildError carrying one PageError per validation failure with its
       file_path (no build-level test covers this path today).

2. RED: Write CLI error-contract tests for ContentError:
   - Extend tests/test_cli.py, mirroring the existing clean-error tests at
     lines 251, 279, 298, 348:
     - Test that a content-discovering command (use `lint`) run against a site
       with malformed front matter exits 1 and prints no "Traceback" substring
       to stderr.
     - Test that the same scenario with --output json emits a structured
       ErrorOutput on stdout with code "content_error" and the offending file
       path (from ContentError.source_path).
     - Test that BARTLEBY_DEBUG=1 re-raises so the full traceback prints.

3. GREEN: In src/bartleby/build.py, replace the raw ValueError raises at the
   metadata-validation site (line 259) and the strict-crossref site (line 350)
   with BuildError carrying PageError entries. Update the build.py docstrings
   that document `:raises ValueError:` to the new contract.

4. GREEN: In src/bartleby/cli.py, import ContentError, add it to the except
   tuple at line 109, and add a "content_error" entry to _ERROR_CODES so
   _report_error formats it with the source path.

5. REFACTOR: Confirm every command that calls discover_content (lint, export,
   generate-skill, render, content list/get, schema) is covered by the same
   boundary; there should be exactly one catch site.

6. Verify coverage and run `just check`.
```

### Step 4: Guarantee Temp Build Directory Cleanup on Every Failure Path (R16)

**NOTE**: Cleanup of the `.bartleby-build-*` temp dir is attached to specific helpers (`_fail_build`, dry-run, success swap) instead of the temp dir's lifetime.
Failures that bypass those paths (strict-crossref, exceptions in `_emit_outputs`) leak it.
Depends on step 3: strict failures now raise `BuildError`.

```text
1. RED: Write temp-dir lifecycle tests first:
   - Extend tests/test_build.py:
     - Test that after a strict-mode build failure (broken crossref,
       strict=True), no directory matching .bartleby-build-* remains under the
       project dir.
     - Test that after an exception injected into _emit_outputs (monkeypatch
       one of its emit calls to raise), no temp dir remains and the previous
       site/ output is untouched.
     - Confirm the existing success-path guard
       (tests/test_build.py:378, test_successful_build_swaps_output_atomically)
       still passes.

2. GREEN: In src/bartleby/build.py, wrap the pipeline from temp-dir creation
   (line 284) through the success swap in try/finally (or a context manager
   owning state.output_dir) so the temp dir is removed on every exit path that
   did not swap it into place. _fail_build keeps its existing behavior; the
   finally is the backstop, so a double-remove must be tolerated
   (ignore_errors or existence check).

3. REFACTOR: If _fail_build's rmtree is now redundant with the backstop,
   simplify to one removal site; keep the docstring contracts at build.py
   282-283 and 717-724 accurate.

4. Verify coverage and run `just check`.
```

> **Fable checkpoint (optional).**
> Phase 2 done: R3 and R16.
> The CLI error contract now catches every failure class and no build path leaks a temp dir.
> Commit and review boundary before Phase 3.

---

## Phase 3: Build Pipeline Correctness

**Validator consults:**
- MCPs: none
- Skills: python:python

### Step 5: Enforce Draft Exclusion for Co-Located Assets and the Taxonomy Schema (R7)

**NOTE**: Drafts are filtered from pages but not from `state.assets` (`build.py:251` vs `:415`), so a draft's co-located asset leaks to output via the orphan fallback in `assets.py:61-70`.
Separately, `derive_taxonomies_schema` (`schema_introspection.py:177`) never filters drafts and the CLI caller passes raw discovered pages.

```text
1. RED: Write draft-asset exclusion tests first:
   - Extend tests/test_build.py (alongside test_build_excludes_drafts at
     line 188):
     - Test that a production build (include_drafts=False) of a draft page
       with a co-located asset writes neither the page nor the asset to the
       output tree.
     - Test that include_drafts=True writes both the draft page and its asset.
     - Test that a published page's co-located asset still copies (regression
       guard).

2. RED: Write taxonomy-schema draft tests:
   - Extend tests/test_schema_introspection.py (fixture at line 142 has no
     draft; add one):
     - Test that derive_taxonomies_schema over a published page and a
       draft-only page omits terms contributed solely by the draft, and that
       term counts reflect published pages only.
   - Extend tests/test_cli.py:
     - Test that `bartleby schema taxonomies --output json` on a site with a
       draft-only term does not list that term.

3. GREEN: In src/bartleby/build.py, filter state.assets to assets whose
   directory belongs to a surviving page when drafts are excluded (drop assets
   co-located with filtered-out drafts before copy_colocated_assets runs).

4. GREEN: Apply select_published inside derive_taxonomies_schema in
   src/bartleby/schema_introspection.py so the filter is enforced at the
   boundary, not per-caller. Confirm the agent_surface.py:79 caller (which
   already pre-filters) still produces identical output.

5. REFACTOR: If the asset filter and the page filter now share "is this page
   published" logic, extract one helper so published means the same thing in
   both places.

6. Verify coverage and run `just check`.
```

### Step 6: Detect Co-Located Asset Collisions in Shared Directories (R8)

**NOTE**: `assets.py:47` keys `page_by_dir` on source directory with silent last-writer-wins.
Spec decision: two pages sharing a directory that contains assets is a loud `BuildError` (through the step 3 contract), not a guessed association.
Two pages in one directory with no assets stay legal.

```text
1. RED: Write collision tests first:
   - Extend tests/test_assets.py:
     - Test that two published pages in one source directory with at least one
       co-located asset raise a clear error naming the directory and both
       pages.
     - Test that two pages in one directory with no assets build fine.
     - Confirm the single-page bundle tests (lines 34 and 58) still pass
       unchanged (regression guard).
   - Extend tests/test_build.py:
     - Test that the collision surfaces from a full build as BuildError (clean
       CLI error, not a traceback).

2. GREEN: In src/bartleby/assets.py, build the directory index as
   dict[str, list[Page]] and, when copying an asset whose directory maps to
   more than one page, raise the collision error naming the directory and the
   pages. Route it through BuildError in src/bartleby/build.py so the step 3
   contract formats it.

3. REFACTOR: Keep the no-asset case cheap: the collision check should only
   fire when an asset actually resolves to a multi-page directory, not on
   discovery of the directory itself.

4. Verify coverage and run `just check`.
```

### Step 7: Merge Icon Pack Defaults Instead of Replacing Them (R10)

**NOTE**: `build.py:416-421` uses `{user config} or {all-true defaults}`, so naming any pack drops every unnamed pack, and `icons.py:31` treats missing keys as disabled.
`icon_packs: {simple: false}` currently disables all four packs.

```text
1. RED: Write pack-resolution tests first:
   - Extend tests/test_build.py (near the icon tree-shaking test at line 103):
     - Test that a build with icon_packs {simple: false} resolves material,
       fontawesome, and octicons to True and simple to False (an icon from an
       enabled pack still lands in output; a simple-pack icon does not).
     - Test that empty or unset icon_packs resolves all four packs True.
     - Test that {fontawesome: false, simple: false} disables exactly those
       two. Base fixtures on tests/fixtures/configs/full.yml:35.

2. GREEN: In src/bartleby/build.py, start from the all-four-True default dict
   and overlay the explicit config entries
   ({**defaults, **{k: bool(v) for k, v in config.theme.icon_packs.items()}}).

3. REFACTOR: If the default pack list now exists in more than one place,
   centralize it as one constant shared with icons.py.

4. Verify coverage and run `just check`.
```

### Step 8: Count Only Copied Files in static_file_count (R17)

**NOTE**: `build.py:477-481` globs every non-HTML file in the final tree, so feeds, sitemap, search index, llms.txt, agent-surface JSON, markdown variants, robots.txt, and icon SVGs all inflate the count.
The docstring at `build.py:100` promises "non-HTML asset files copied into the output tree".

```text
1. RED: Write count-accuracy tests first:
   - Extend tests/test_build.py:
     - Test that a build with N files under static/ and M co-located assets
       reports static_file_count == N + M even though the output tree also
       contains generated artifacts (feeds, sitemap, search index, robots.txt,
       and llms.txt at minimum; assert those files exist in the tree so the
       test proves they are excluded).
     - Test that toggling a generated artifact (ai.llms_txt on vs off) does
       not change static_file_count.

2. GREEN: Return copy counts from copy_static_files and copy_colocated_assets
   (or count their copied paths at the call sites in src/bartleby/build.py)
   and sum those for BuildResult.static_file_count instead of re-globbing the
   output tree.

3. REFACTOR: Keep the BuildResult docstring (build.py:100, 106) accurate; it
   already describes the fixed behavior.

4. Verify coverage and run `just check`.
```

> **Fable checkpoint (optional).**
> Phase 3 done: R7, R8, R10, R17.
> Draft exclusion holds at the boundary, shared-directory asset collisions fail loudly, icon packs merge, and the static file count is honest.
> Commit and review boundary before Phase 4.

---

## Phase 4: Rendering Correctness

**Validator consults:**
- MCPs: none
- Skills: python:python

### Step 9: Render Listing Intro Content as HTML (R11)

**NOTE**: `_read_intro_content` (`listings.py:103-109`) returns raw markdown and `defaults/list.html:8` emits it with `| safe`, so users see literal `## Heading`.
`tests/test_listings.py:120` asserts a plain substring that passes either way; strengthening it is part of RED.

```text
1. RED: Strengthen listing-intro tests first:
   - Modify tests/test_listings.py:
     - Change test_listing_includes_index_md_content (line 120) so the
       index.md body contains markdown (## Welcome and **bold**) and the test
       asserts the listing intro contains <h2>Welcome</h2> and
       <strong>bold</strong>, not the literal markdown.

2. GREEN: In src/bartleby/listings.py, run the index.md body through the
   markdown renderer (the same create_markdown_renderer/render_markdown
   pipeline pages use) before storing intro_content, so the template's
   existing `| safe` receives HTML.

3. REFACTOR: If listings.py now needs a renderer instance, accept it from the
   build pipeline rather than constructing a second one; one renderer per
   build.

4. Verify coverage and run `just check`.
```

### Step 10: Emit Valid JSON-LD from One Generator (R9)

**NOTE**: `partials/jsonld.html` hand-builds JSON with raw interpolation; HTML autoescaping corrupts quotes into `&#34;` and JSON escapes never happen.
A correct generator already exists (`generate_jsonld`, `llm.py:77-89`).
Spec prefers deleting the duplication: render the block from the Python generator.

```text
1. RED: Write special-character JSON-LD tests first:
   - Extend tests/test_templates.py (near the presence assertion at line 414):
     - Test that rendering a full page whose title and description contain a
       double quote, a backslash, and a < character produces an ld+json script
       block whose contents pass json.loads.
     - Test that the parsed headline and description round-trip the original
       strings exactly (no &#34; entities, no lost characters).
     - Test that the parsed object equals
       json.loads(generate_jsonld(page, site)) for the same page.

2. GREEN: Make the template context carry the generate_jsonld output (a
   context key produced in build_page_context or a template global), and
   reduce src/bartleby/theme/templates/partials/jsonld.html to emitting that
   pre-serialized JSON inside the script tag with `| safe`. Delete the
   hand-built key/value lines.

3. REFACTOR: Confirm generate_jsonld covers the fields the partial used to
   emit (headline, description, url, datePublished, @type Article vs WebPage);
   extend the generator, not the template, if anything is missing. Extend
   tests/test_llm.py with the special-character inputs so the generator path
   is covered directly too.

4. Verify coverage and run `just check`.
```

### Step 11: Protect Multi-Backtick Inline Code from Shortcode Expansion (R12)

**NOTE**: `_INLINE_CODE_RE` (`shortcodes.py:23`) only matches single-backtick spans, so shortcodes inside CommonMark multi-backtick spans get expanded.

```text
1. RED: Write multi-backtick protection tests first:
   - Extend tests/test_shortcodes.py (alongside the protection tests at lines
     69-89):
     - Test that a shortcode inside a double-backtick span is emitted
       literally.
     - Test that a shortcode inside a double-backtick span that itself
       contains a single backtick is emitted literally.
     - Confirm test_shortcode_inside_inline_code_is_literal (line 76) still
       passes (regression guard).

2. GREEN: In src/bartleby/shortcodes.py, replace _INLINE_CODE_RE with logic
   implementing CommonMark's rule: a span opened by a run of N backticks
   closes at the next run of exactly N (a backreference regex like
   (`+)...(?<!`)\1(?!`) or a small scanner; pick the simplest form that passes
   mypy strict and reads clearly). Keep _collect_protected_spans as the single
   integration point.

3. REFACTOR: Keep the function docstring (shortcodes.py:32-35) accurate about
   what is protected.

4. Verify coverage and run `just check`.
```

> **Fable checkpoint (optional).**
> Phase 4 done: R11, R9, R12.
> Listing intros render, JSON-LD is valid from one generator, and multi-backtick inline code is protected from shortcode expansion.
> Commit and review boundary before Phase 5.

---

## Phase 5: Dev Server

**Validator consults:**
- MCPs: none
- Skills: python:python

### Step 12: Serve the Configured Output Directory (R4)

**NOTE**: `DevServer.run()` hardcodes `site/` at `server.py:259` while the build writes to `config.output_dir`.
The only `run()` test uses a fixture that leaves `output_dir` unset, which is why this shipped.

```text
1. RED: Write output-dir serving tests first:
   - Extend tests/test_server.py (parametrize or clone
     test_run_builds_and_serves_pages_over_http at line 245):
     - Test that with output_dir: public in bartleby.yml, run() serves the
       built index from <project>/public/ (GET / returns 200 with the built
       body).
     - Test that with output_dir unset, serving from <project>/site/ still
       works (regression guard).

2. GREEN: In src/bartleby/server.py, resolve the serve directory from the
   loaded config's output_dir instead of the "site" literal. run() already
   builds via build_once, so load the config once and share it between the
   build and the handler rather than re-parsing.

3. REFACTOR: If DevServer now holds the loaded config, remove any other
   hardcoded "site" references in server.py against it.

4. Verify coverage and run `just check`.
```

### Step 13: Wire the File Watcher into DevServer.run() (R5, part 1)

**NOTE**: All change-detection primitives exist and are unit-tested (`WATCHED_PATHS`, `is_watched`, `dispatch_change`, `rebuild`, `rebuild_with_events`, last-good-build retention) but `run()` never starts a watcher.
No watchdog Observer exists anywhere in server.py despite the module docstring and the v1 spec dependency list.
This step is rebuild-on-change through `run()`; the browser-facing reload channel is step 14.

```text
1. RED: Write watcher integration tests first:
   - Extend tests/test_server.py:
     - Test that with run() active, modifying a watched file (a content/*.md
       page) triggers a rebuild whose output is visible over HTTP within a
       bounded wait (poll GET until the changed content appears or a timeout
       fails the test).
     - Test that a change to an unwatched path (a file inside the output dir,
       or README.md at the project root) does not trigger a rebuild (assert
       the rebuild callback count stays flat over a short window; structure
       run() so the test can inject or observe the rebuild hook rather than
       sleeping blind).

2. GREEN: In src/bartleby/server.py, start a watchdog Observer inside run()
   over the project's watched roots, routing events through is_watched /
   dispatch_change into rebuild (or rebuild_with_events), and stop it cleanly
   on server shutdown. Import watchdog at module level; it is a declared
   dependency (confirm it is in pyproject.toml; add it if the v1 packaging
   step missed it).

3. GREEN: Confirm the existing last-good-build retention test
   (tests/test_server.py:181) holds when the failure occurs via a real
   watcher-triggered rebuild; add that integration case if it does not.

4. REFACTOR: run() should compose existing primitives, not duplicate their
   logic; keep classify_change / should_trigger_full_rebuild as the single
   decision points. Keep the module docstring accurate.

5. Verify coverage and run `just check`.
```

### Step 14: Serve the Reload Snippet and WebSocket Channel (R5, part 2)

**NOTE**: `RELOAD_SNIPPET` and `inject_reload_snippet` exist and are unit-tested, but served HTML never contains the snippet and no WebSocket endpoint exists.
Spec contract: snippet in serve-mode pages only, reload signal pushed at `/__bartleby_reload` after each successful rebuild, `bartleby build` output snippet-free.

```text
1. RED: Write reload-channel tests first:
   - Extend tests/test_server.py:
     - Test that HTML served by run() contains RELOAD_SNIPPET.
     - Test that a WebSocket client connected to /__bartleby_reload receives a
       message after a rebuild completes (drive a watched-file change or call
       the rebuild path directly, then assert the client receives the signal
       within a bounded wait).
     - Test that `bartleby build` output HTML contains no RELOAD_SNIPPET
       (regression guard; a test near this exists at tests/test_server.py:200
       for inject_reload_snippet in isolation, so this one goes through the
       real build).

2. GREEN: In src/bartleby/server.py, inject RELOAD_SNIPPET into HTML responses
   in serve mode (at the request handler, or as a serve-only post-build pass
   over the temp output; the handler approach keeps build output clean by
   construction). Serve the WebSocket endpoint at /__bartleby_reload using the
   websockets library (confirm the dependency in pyproject.toml; add it if
   missing) and broadcast one message to connected clients after each
   successful rebuild.

3. REFACTOR: Reload code must not leak into production builds: assert the
   injection lives only on the serve path, and keep the snippet's URL and the
   endpoint route defined once.

4. Verify coverage and run `just check`.
```

> **Fable checkpoint (optional).**
> Phase 5 done: R4 and R5 (the largest requirement).
> The dev server serves the configured output dir, rebuilds on watched changes, and live-reloads the browser.
> Commit and review boundary before Phase 6.

---

## Phase 6: CLI and Agent Surface

**Validator consults:**
- MCPs: none
- Skills: python:python

### Step 15: Resolve Crossrefs Before the Lint Orphan Pass (R6)

**NOTE**: `_cmd_lint` never rewrites `.md` hrefs to output URLs, so `_lint_orphans` compares mismatched URL spaces and reports every page orphaned.
The build pipeline already does the missing step (`resolve_all_crossrefs`, `build.py:341`).

```text
1. RED: Write lint-orphan integration tests first:
   - Extend tests/test_cli.py (near the lint JSON test at line 602):
     - Test that on a scaffolded site where page A links to page B via a
       relative .md path, `bartleby lint --output json` produces no
       orphaned-page finding for B.
     - Test that a page present in navigation is never reported orphaned.
     - Extend the existing lint JSON test to assert no spurious orphan
       findings appear for the fixture site.

2. GREEN: In src/bartleby/cli.py's _cmd_lint, call resolve_all_crossrefs over
   the rendered pages (mirroring build.py:341) after rendering and before
   lint_site, so page.rendered_content carries output URLs when the orphan
   pass reads it.

3. REFACTOR: _lint_crossrefs (linting.py:94-110) calls resolve_page_crossrefs
   and discards the rewritten HTML; now that the CLI resolves up front,
   confirm lint's crossref findings still report correctly and remove the
   redundant re-resolution if it is now dead weight. Keep
   tests/test_linting.py:76-101 passing unchanged.

4. Verify coverage and run `just check`.
```

### Step 16: Discover Shortcodes Across All Three Lookup Locations (R13)

**NOTE**: `_discover_shortcode_names` (`cli.py:739-744`) scans only `templates/shortcodes/`, but the Jinja loader resolves from the project root (preferred), `templates/`, and the built-in theme.
Generated skills under-report available shortcodes.

```text
1. RED: Write discovery tests first:
   - Extend tests/test_cli.py with direct tests for _discover_shortcode_names:
     - Test that a shortcode at <project>/shortcodes/foo.html is discovered.
     - Test that <project>/templates/shortcodes/bar.html is still discovered.
     - Test that built-in theme shortcodes
       (get_theme_templates_dir()/shortcodes/*.html) are included.
     - Test that a name defined in multiple locations appears once (sorted,
       de-duplicated).
   - Extend tests/test_cli.py's generate-skill test (line 707) with a
     project-root shortcode and assert it appears in the generated skill
     output.

2. GREEN: In src/bartleby/cli.py, make _discover_shortcode_names scan the
   same cascade the Jinja loader resolves: <project>/shortcodes/,
   <project>/templates/shortcodes/, and get_theme_templates_dir()/shortcodes/;
   merge stems into a sorted, de-duplicated list.

3. REFACTOR: The cascade order is defined in templates.py:68-74; reference one
   shared source for the search roots if that can be done without contortion,
   so the loader and discovery cannot drift again.

4. Verify coverage and run `just check`.
```

### Step 17: Advertise the Aggregate Feed in schema.json (R14)

**NOTE**: `_resource_locations` (`agent_surface.py:149-174`) enumerates per-type feeds only; the site-wide `/feed.xml` and `/atom.xml` written by `generate_feeds` never appear in the advertised resources.

```text
1. RED: Write aggregate-feed resource tests first:
   - Extend tests/test_agent_surface.py (near the per-type assertion at line
     167):
     - Test that with site.feed.enabled and rss in formats,
       schema["resources"]["feeds"] includes the aggregate <site.url>/feed.xml.
     - Test that with atom in formats, the aggregate <site.url>/atom.xml entry
       is present.
     - Test that with site.feed.enabled false, no aggregate entry is emitted.

2. GREEN: In src/bartleby/agent_surface.py's _resource_locations, read
   config.site.feed and append the aggregate feed URLs per enabled format,
   alongside the existing per-type loop.

3. REFACTOR: Feed URL construction now exists in feeds.py and agent_surface.py;
   share one helper if the duplication is textual, so the advertised URLs
   cannot drift from the written files.

4. Verify coverage and run `just check`.
```

### Step 18: Scope the Hooks sys.path Insertion (R15)

**NOTE**: `discover_hooks` (`plugins.py:155-164`) inserts `hooks/` at the front of `sys.path` permanently.
The insertion exists so hooks can import underscore-prefixed siblings; that behavior must survive.
Dev-server rebuilds re-discover hooks, so cleanup must hold across repeated calls.

```text
1. RED: Write sys.path hygiene tests first:
   - Extend tests/test_plugins.py:
     - Test that after discover_hooks returns, sys.path equals its pre-call
       value.
     - Test that calling discover_hooks twice does not grow sys.path.
     - Confirm test_hook_can_import_sibling_module (line 150) still passes
       (regression guard: sibling imports work during discovery).

2. GREEN: In src/bartleby/plugins.py, scope the insertion with try/finally:
   insert hooks_path before the load loop, remove it after (only if this call
   added it), so the path is present exactly while hook modules are being
   imported.

3. REFACTOR: Note in the discover_hooks docstring that sibling imports resolve
   only at discovery time; a hook that defers a sibling import to call time
   would break, and that is intended (imports at module top, per house style).

4. Verify coverage and run `just check`.
```

> **Fable checkpoint (optional).**
> Phase 6 done: R6, R13, R14, R15.
> Lint resolves crossrefs before the orphan pass, shortcode discovery spans all three lookup locations, the aggregate feed is advertised, and the hooks `sys.path` insertion is scoped.
> Commit and review boundary before Phase 7.

---

## Phase 7: Cycle Verification

**Validator consults:**
- MCPs: none
- Skills: python:python

### Step 19: Extend the E2E Smoke Test and Close the Cycle

**NOTE**: spec.md's Verification section requires the smoke test to exercise a build and serve cycle on a site with a custom `output_dir`, a draft with a co-located asset, and a title containing a double quote.
This step proves the fixes compose; it should require no production-code changes.
If it does surface one, fix it under the step 3 error contract and record it.

```text
1. RED: Extend the e2e smoke test:
   - Modify tests/test_smoke.py:
     - Scaffold a site with output_dir set to a non-default value, one
       published post whose title contains a double quote, one draft post
       with a co-located asset, and a page-to-page .md crossref link.
     - Build and assert: the output lands in the configured dir; the draft
       page and its asset are absent; the published page's ld+json block
       json.loads cleanly and round-trips the quoted title; the crossref
       resolves to an output URL in the rendered HTML.
     - Serve (DevServer.run) and assert: GET / returns the built index from
       the configured dir and the served HTML contains RELOAD_SNIPPET.

2. GREEN: Only if the smoke test surfaces a composition defect, fix it
   minimally under the established contracts; otherwise no production change.

3. Final gate: run `just check` and confirm the full suite, ruff, and mypy
   strict pass. Review todo.md: every step checked, every spec.md requirement
   R1-R17 closed.

4. Update CHANGELOG.md with a remediation entry summarizing the 20 fixed
   defects for the next release.
```

> **Fable checkpoint (optional).**
> Phase 7 done: the cycle is verified.
> The e2e smoke test exercises custom `output_dir`, a draft with a co-located asset, and a quoted title through build and serve; `just check` is green and all of R1-R17 are closed.
> Final commit boundary; bartleby is ready to ship.

---

## Success Metrics

- All 20 confirmed review findings (spec.md R1 through R17) are closed with tests that were observed failing first.
- `bartleby` imports and every CLI command starts; `bartleby theme compile` works on a clean machine.
- No known path surfaces a raw Python traceback; drafts and their assets cannot reach production output; served and built HTML carry valid JSON-LD.
- `bartleby serve` rebuilds on watched changes and live-reloads the browser, serving the configured output directory.
- `just check` passes: full test suite (including the extended e2e smoke test), ruff, and mypy strict.

## Out of Scope (Unchanged from v1)

- Parallel build architecture, incremental rebuilds, voice/tone content analysis, public theme API, migration tool.
- The 14 refuted review findings; do not "fix" behavior the verification pass confirmed correct.
