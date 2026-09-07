# Bartleby v1 Remediation Specification

## Overview

Bartleby's v1 implementation cycle is complete (all 108 todo.md items closed, packaged as 0.1.0 at commit `2a4dd91`).
A multi-agent code review of the `v1` branch on 2026-07-01 surfaced 34 candidate defects.
20 survived adversarial verification in the review, and all 20 were independently re-confirmed against this working tree with exact file and line references before this spec was written.
This spec defines the required behavior for fixing every confirmed defect, stated as TDD-ready requirements: each has a failing-test description, the correct behavior with a citation into the v1 product spec, and acceptance criteria a pytest test can assert.

**Re-verification (2026-09-06).** All 20 defects were re-checked against the working tree on the project's own pinned interpreter (Python 3.14.3). R2 through R17 all still reproduce, with citations accurate (only R3's `content.py:231-232` collapsed to a single line 232). R1 does not reproduce on Python 3.14 and is dispositioned as not-a-defect: see its section below. The original review that produced this spec was run against a pre-3.14 interpreter, which is why R1's premise did not survive; no other item depended on interpreter version.

The v1 product spec remains the canonical description of product behavior.
It is preserved in git and readable with `git show 2a4dd91:spec.md`.
Citations below in the form "v1 spec, Section Name (line N)" refer to that file.

## Scope

In scope: the 20 confirmed defects, their tests, and updates to existing tests that currently codify buggy behavior.
Out of scope: new features, refactors beyond what a fix requires, and the 14 review findings that were refuted during verification.

Severity triage used for ordering:

- Critical (R1, R2): the tool does not run, or a core command always fails on first use.
- High (R3 through R11): a documented feature is broken or produces wrong output.
- Medium (R12 through R17): correctness and hygiene defects with narrower blast radius.

## Available Tooling

Tools the `bpe:validator` agent should consult when reviewing diffs in `/bpe:goal` runs.
`/bpe:plan` propagates these to per-section declarations in plan.md.

**MCPs:**
- (none apply)

**Skills:**
- python:python

**Notes:** Validator should hold every diff to the CLI error contract (R3), the draft-exclusion invariant (R7), and mypy strict typing.
No domain MCPs apply; this is a pure-Python remediation cycle.

## Global Requirements

These apply to every requirement below.

1. **Error contract.** Failures never surface as raw Python tracebacks.
   Every error prints a clean message (file path and line where known, cause, stable error code) to stderr in text mode, or a structured error object to stdout in JSON mode, then exits 1 (usage errors exit 2, per the v1 contract).
   `BARTLEBY_DEBUG=1` re-enables full tracebacks.
   (v1 spec, Error contract, lines 2135 and 2522.)
2. **Draft-exclusion invariant.** Drafts are excluded at build time, so the built output is the publication boundary: nothing unpublished can leak, by construction.
   (v1 spec, Static Agent Surface, line 1717.)
3. **TDD.** Each fix starts with a failing test that reproduces the defect.
   Where an existing test codifies the buggy behavior (noted per requirement), updating that test is part of the RED step, not an afterthought.
4. **Gates.** `uv run pytest`, `uv run ruff check .`, and `uv run mypy src/` (strict) pass after every requirement.
   `just check` runs these plus `ruff format --check` and the e2e smoke gate (`check: lint typecheck test smoke` in the Justfile).
5. **No behavior drift.** Fixes change only the defective behavior.
   Docstrings that document the buggy contract (for example the `:raises ValueError:` lines in `build.py`) are updated to match the fixed contract.

## Requirements

### R1: Restore CLI Importability (Critical)

**Defect.** `src/bartleby/linting.py:205` uses Python 2 exception syntax: `except URLError, ValueError, OSError:`.
This is a `SyntaxError` in Python 3 (verified with `py_compile`).
`src/bartleby/cli.py:38` imports `linting` at module level, so every `bartleby` command dies at startup.

**Root cause.** Missing parentheses around the exception tuple; the module was never import-tested on its own.

**Required behavior.** `check_external_url` catches `(URLError, ValueError, OSError)` and returns `False` on any of them, per its own docstring (linting.py:192-198).

**Acceptance criteria.**
- `import bartleby.linting` succeeds.
- `bartleby --help` (or invoking `main([])`) runs without a `SyntaxError`.
- `check_external_url` returns `False` when the probe raises `URLError`, `ValueError`, or `OSError`.

**Test notes.** No existing test imports `linting.py` (which is how this shipped).
Add an import-level smoke assertion so a future syntax error in any module fails the suite; the e2e smoke test from v1 step 17 should already do this once the CLI is importable, so verify why it did not catch this.

**Disposition (2026-09-06): not a defect on Python 3.14.**
The project pins `requires-python = ">=3.14"`, and Python 3.14 shipped PEP 758, which legalizes unparenthesized multiple exception types in `except` clauses.
On 3.14.3, `import bartleby.linting` succeeds and `check_external_url` already catches `URLError`, `ValueError`, and `OSError` with the file unchanged; the `SyntaxError` reproduces only on pre-3.14 interpreters (confirmed on system 3.12.3), which is what the original review used.
Applying the parenthesized "fix" would break `just check`: `ruff format` (target `py314`) canonicalizes the tuple back to the unparenthesized PEP 758 form, so `ruff format --check` would fail.
`linting.py` is therefore left unchanged.
The durable deliverable of this requirement is the import-health gate `tests/test_import_health.py`, which walks every `bartleby` module and imports it (catching any real future module-level syntax/import error) and asserts `check_external_url`'s three-exception contract directly.
The v1 smoke-test gap (R1's original test note) does not exist: `tests/test_smoke.py` already drives `bartleby.cli.main()`, so collecting it exercises the full module-level import chain.

### R2: Populate Tailwind Release Checksums (Critical)

**Defect.** `src/bartleby/theme_compile.py:28` ships `_RELEASE_SHA256: dict[str, str] = {}`.
The download path (`theme_compile.py:164-166`) raises `ThemeCompileError("no recorded SHA-256 for asset ...")` when the map has no entry and no `expected_sha256` was injected.
Production callers (`compile_theme_css`, lines 232-236) never inject one, so a first-run `bartleby theme compile` on a machine with no PATH or cached binary always fails before fetching anything.

**Root cause.** The digest map the header comment (lines 24-27) promises for `PINNED_TAILWIND_VERSION` was never populated; only tests inject checksums, so the empty map went unnoticed.

**Required behavior.** The customizer path downloads the platform-appropriate Tailwind standalone binary on demand, pinned version, SHA-256 verified, cached.
(v1 spec, Theme Asset Pipeline, lines 1420 and 1427; CLI, line 2246.)
`_RELEASE_SHA256` holds the official GitHub release digests for every platform asset of the pinned version, and the map is bumped together with `PINNED_TAILWIND_VERSION`.

**Acceptance criteria.**
- `_RELEASE_SHA256` contains a digest matching `^[0-9a-f]{64}$` for every asset name `tailwind_asset_name()` can return (`tailwindcss-linux-x64`, `tailwindcss-linux-arm64`, `tailwindcss-macos-x64`, `tailwindcss-macos-arm64`, `tailwindcss-windows-x64.exe`, `tailwindcss-windows-arm64.exe`), and the key set equals exactly that set.
- `_download_binary(cache_dir=..., expected_sha256=None, fetch=stub)` for the current platform uses the map digest instead of raising "no recorded SHA-256", and installs the binary when the stubbed bytes hash to the map value.
- Checksum mismatch still aborts cleanly (existing behavior, regression guard).

**Test notes.** Existing tests (`tests/test_theme_compile.py:73`, `:96`, `:120`) all inject `expected_sha256` explicitly; add coverage that exercises the map path.
Fetching the real digests from the Tailwind GitHub release for the pinned version is part of the implementation, not the test.

### R3: Route All CLI Failures Through the Error Contract (High)

**Defect.** Two exception classes escape the CLI error boundary as raw tracebacks:
- `ContentError` (raised by `content.py:151` and `content.py:231-232` on malformed front matter) is not in the `except` tuple at `cli.py:109`, not in `_ERROR_CODES` (`cli.py:75-80`), and never imported by cli.py.
  Every content-discovering command hits this: `lint` (cli.py:657), `export` (cli.py:688), `generate-skill` (cli.py:716), and the render and content-query paths.
- The build pipeline raises raw `ValueError` for metadata validation failures (`build.py:259-262`) and strict-mode crossref failures (`build.py:350-351`) instead of `BuildError`, which the CLI does catch.

**Root cause.** `ContentError` was never wired into the CLI error contract, and two build failure sites predate the `BuildError` type (`build.py:138-151`) and were never migrated.

**Required behavior.** Global requirement 1 (v1 spec, lines 2135 and 2522).
Page-level errors, including broken cross-references in strict mode, are collected so the build fails once with the complete list (v1 spec, line 2520).

**Acceptance criteria.**
- Metadata validation failure raises `BuildError` carrying one `PageError` per failure with its `file_path`.
- `build(..., strict=True)` with unresolved cross-references raises `BuildError` with one `PageError` per broken crossref.
- Any content-discovering command run against a site with malformed front matter exits 1, prints no `Traceback` to stderr, and in `--output json` mode emits a structured `ErrorOutput` with a stable code (`content_error`) and the offending file path from `ContentError.source_path`.
- With `BARTLEBY_DEBUG=1`, both cases re-raise so the full traceback prints (parity with `_report_error`, cli.py:169-170).

**Test notes.** `tests/test_build.py:306` (`test_build_strict_fails_on_broken_crossref`) currently asserts `pytest.raises(ValueError)` and codifies the bug; update it in the RED step.
Mirror the existing clean-error CLI tests (`tests/test_cli.py:251`, `:279`, `:298`, `:348`) for `ContentError`.
Update `build.py` docstrings that document `:raises ValueError:`.

### R4: Serve the Configured Output Directory (High)

**Defect.** `DevServer.run()` hardcodes the serve directory: `site_dir = self.config_path.parent / "site"` (`server.py:259`).
The build writes to `config.output_dir` (`build.py:281`, config field at `config.py:218`, added in commit `5f4f503`), so with `output_dir` set to anything else, `run()` builds into the configured dir and serves a stale or missing `site/`.

**Root cause.** `run()` never consults the loaded config for the output directory.

**Required behavior.** The dev server serves whatever the build produced (v1 spec, bartleby serve, line 2219; Development Server, line 2603).

**Acceptance criteria.**
- With `output_dir: public` in bartleby.yml, `DevServer.run()` serves the built index from `<project>/public/` (GET `/` returns 200 with the built body, no 404, no fallback to `site/`).
- With `output_dir` unset, serving from `<project>/site/` still works (regression guard).

**Test notes.** The only `run()` test (`tests/test_server.py:245`) uses a fixture with no `output_dir` key; parametrize or add a second fixture with a custom dir.

### R5: Wire Live Reload into the Dev Server (High)

**Defect.** `DevServer.run()` (`server.py:250-267`) does build-once, bind, serve-forever.
The change-detection and reload primitives all exist and are unit-tested (`WATCHED_PATHS` :30, `RELOAD_SNIPPET` :46, `is_watched` :54, `classify_change` :70, `inject_reload_snippet` :94, `rebuild` :134, `dispatch_change` :188, `rebuild_with_events` :227) but nothing in `run()` calls any of them.
No watchdog observer and no WebSocket server are imported or started anywhere in server.py, despite the module docstring claiming watchdog change detection and the v1 spec listing `watchdog` and `websockets` as dependencies (lines 2706-2707).

**Root cause.** The primitives were built and tested in isolation (v1 plan steps) but the composition step into `run()` never happened.

**Required behavior.** v1 spec, Development Server, Live Reload (line 2605): a watchdog file watcher monitors the watched roots; every change triggers a full rebuild; a WebSocket connection pushes the reload signal; the reload snippet is injected into served pages only in serve mode; failed rebuilds keep serving the last good build; drafts are included in serve mode.

**Acceptance criteria.**
- With `run()` active, modifying a watched file (for example `content/<page>.md`) triggers a rebuild whose output is visible over HTTP within a bounded wait.
- A change to an unwatched path (for example inside the output dir, or `README.md`) does not trigger a rebuild.
- HTML served by `run()` contains `RELOAD_SNIPPET`, a WebSocket client connected to `/__bartleby_reload` receives a signal after a rebuild, and `bartleby build` output contains no snippet.

**Test notes.** Existing primitive tests (`tests/test_server.py:114`, `:140`, `:146`, `:155`, `:181`, `:200`, `:215`, `:227`) stay; add integration coverage through `run()`.
This is the largest requirement in the cycle; expect it to decompose into watcher wiring, WebSocket serving, and snippet injection sub-steps at plan time.

### R6: Resolve Crossrefs Before the Lint Orphan Pass (High)

**Defect.** `_cmd_lint` (`cli.py:665-672`) renders markdown into `page.rendered_content` but never rewrites `.md` hrefs to output URLs.
`_lint_orphans` (`linting.py:129-148`) and its href collector `_inbound_urls` (`linting.py:151-165`) compare inbound hrefs against `page.output_url`, so `.md` targets never match output URLs and every page is reported orphaned.
The build pipeline does the missing step at `build.py:341` (`resolve_all_crossrefs`).
Note `_lint_crossrefs` (`linting.py:94-110`) calls `resolve_page_crossrefs` but discards the rewritten HTML.

**Root cause.** The lint command omits the crossref-resolution step the orphan check depends on.

**Required behavior.** v1 spec, bartleby lint (line 2320): orphaned means not in nav and not linked from any other page.
A page linked from another page must not be reported orphaned.

**Acceptance criteria.**
- On a scaffolded site where page A links to page B via a relative `.md` path, `bartleby lint --output json` produces no `orphaned-page` finding for B.
- A page present in navigation is never reported orphaned.
- After the lint pre-pass, `page.rendered_content` (or the orphan pass input) contains output URLs, not `.md` targets.

**Test notes.** `tests/test_linting.py:90` (`test_linked_page_is_not_orphan`) hand-crafts already-resolved hrefs, masking the integration defect; keep it, and add a CLI-level test through `_cmd_lint`.
`tests/test_cli.py:602` only asserts on `broken-crossref`; extend it to assert no spurious orphans.

### R7: Enforce the Draft-Exclusion Invariant Everywhere (High)

**Defect.** Two paths leak draft content in violation of global requirement 2:
- Co-located assets: drafts are filtered from `pages` (`build.py:251-252`) but `state.assets` never is.
  `copy_colocated_assets` (`build.py:415`) then finds no associated page for a draft's asset and the orphan fallback (`assets.py:61-70`) copies it to the output at its source path.
- Taxonomy schema: `derive_taxonomies_schema` (`schema_introspection.py:177`) passes pages straight to `build_taxonomies` with no draft filter, and the CLI caller (`cli.py:541-542`) passes raw discovered pages, so `bartleby schema taxonomies` reports draft-only terms.
  (The `agent_surface.py:79` caller pre-filters with `select_published`, which masked this.)

**Root cause.** Draft exclusion is applied per-caller instead of at the boundary; two callers forgot.

**Required behavior.** v1 spec, line 1717 (publication boundary), line 342 (drafts excluded from production builds), line 350 (assets follow their page), line 1723 (schema lists terms in use, which means published use).

**Acceptance criteria.**
- A production build of a draft page with a co-located asset writes neither the page nor the asset; `include_drafts=True` writes both; a published page's asset still copies (regression guard).
- `derive_taxonomies_schema` over a published page and a draft-only page omits terms contributed solely by the draft, and counts reflect published pages only.
- `bartleby schema taxonomies` lists no draft-only terms.

**Test notes.** `tests/test_build.py:188` checks the draft page dir only; extend to the asset.
`tests/test_schema_introspection.py:142` has no draft in its fixture; add one.

### R8: Define Co-Located Asset Behavior for Shared Directories (High)

**Defect.** `assets.py:47` builds `page_by_dir` keyed on source directory with last-writer-wins, so when two pages share a source directory, every asset in that directory is routed to the last page's output URL, silently cross-routing the other page's assets.

**Root cause.** The directory-to-page index is a plain dict that discards all but one page per directory, and nothing detects the collision.

**Required behavior.** v1 spec, Static Files and Co-Located Assets (lines 346-369): assets follow their page's output URL.
The v1 spec assumes a single page per bundle directory (Hugo leaf-bundle model) and leaves the shared-directory case undefined.
**Decision for this cycle:** treat a shared directory containing assets as a build error, loudly, rather than guessing an association.
Two pages in one directory with no co-located assets remain legal (nothing to mis-route).
Raise `BuildError` (through the R3 contract) naming the directory and both pages, so the user restructures into one-bundle-per-directory.

**Acceptance criteria.**
- Two published pages in one source directory with at least one co-located asset produce a clean build error naming the directory and the pages.
- Two pages in one directory with no assets build fine.
- Single-page bundles are unaffected (regression guard on `tests/test_assets.py:34` and `:58`).

**Test notes.** No existing test covers two pages in one directory.
If Mason prefers per-page asset association over an error, this section is the one to edit at review time; the error keeps v1 semantics honest without inventing an association rule the spec never defined.

### R9: Emit Valid JSON-LD (High)

**Defect.** `src/bartleby/theme/templates/partials/jsonld.html` builds JSON by hand with raw `{{ }}` interpolation inside hand-written quotes for `headline`, `description`, `url`, and `datePublished`.
Jinja HTML autoescaping (`templates.py:75-77`) turns a `"` in a title into `&#34;` inside a JSON string, and JSON-required escapes (backslash, control chars) are never applied.
A title like `The "Best" Way` yields invalid or corrupted JSON-LD on every page (the partial is included from `base.html:18`).
A correct generator already exists: `generate_jsonld` in `src/bartleby/llm.py:77-89` builds a dict and returns `json.dumps(...)`.

**Root cause.** The partial duplicates the Python generator's logic by string concatenation instead of using JSON serialization.

**Required behavior.** v1 spec, JSON-LD Structured Data (lines 1733-1767 and 2005-2012): produces valid Schema.org markup for Article and WebPage types (line 1944).
Fix by serializing, not by escaping harder: either interpolate each value with `| tojson` (emitting the full quoted token, no hand-written surrounding quotes), or render the whole block from `generate_jsonld(...)` so the template and Python paths cannot diverge.
Prefer the single-generator approach; it deletes the duplication.
It also resolves a second divergence the two paths carry today: the partial picks Article by `page.date` (jsonld.html:2) while the generator picks by `page.content_type_name` (llm.py:79), and acceptance criterion 3 needs one rule.

**Acceptance criteria.**
- Rendering a page whose title and description contain `"`, `\`, and `<` produces an `ld+json` block whose contents pass `json.loads`.
- The parsed `headline` and `description` round-trip the original strings exactly (no HTML entities, no lost characters).
- The rendered block equals `json.loads(generate_jsonld(page, site))` output semantically (same parsed object).

**Test notes.** `tests/test_templates.py:414` only asserts the block is present; `tests/test_llm.py:119-152` only tests the Python path with tame input.
Add a special-characters rendering test through the template.

### R10: Merge Icon Pack Defaults Instead of Replacing Them (High)

**Defect.** `build.py:416-421` applies the all-enabled default dict only when the config dict is empty (`{...} or {defaults}`).
Naming any pack skips the defaults entirely, and `icons.py:31` treats missing keys as disabled (`icon_packs.get(pack_key, False)`).
So `icon_packs: {simple: false}` disables all four packs.

**Root cause.** Defaults are an either/or fallback instead of a base the config overrides.

**Required behavior.** v1 spec, lines 76, 1385, and 2739: all four packs enabled by default; set a pack to `false` to exclude it.
Resolution starts from all four packs `True` and applies the explicit config entries on top.

**Acceptance criteria.**
- `icon_packs: {simple: false}` resolves to material, fontawesome, octicons `True` and simple `False`.
- Empty or unset `icon_packs` resolves to all four `True`.
- `icon_packs: {fontawesome: false, simple: false}` disables exactly those two, and icons from the enabled packs still land in the output.

**Test notes.** No existing test sets a single pack to `false` through a build; `tests/fixtures/configs/full.yml:35` already has an `icon_packs` block usable as a fixture base.

### R11: Render Listing Intro Content as HTML (High)

**Defect.** `_read_intro_content` (`listings.py:103-109`) returns the raw markdown body of `content/{type}/index.md`, and `defaults/list.html:8` emits it with `| safe`.
Users see literal `## Heading` and `**bold**` on listing pages.

**Root cause.** No markdown render step between reading index.md and displaying it.

**Required behavior.** v1 spec, Content Type Listings (line 296): the file's rendered content is displayed above the listing (also pipeline steps at lines 2478 and 2770, acceptance at 2553).

**Acceptance criteria.**
- An index.md body of `## Welcome` produces `<h2>Welcome</h2>` in the listing intro region, not the literal string.
- Inline markdown (bold, links) in the intro renders to HTML.

**Test notes.** `tests/test_listings.py:120` asserts a plain substring that passes either way; strengthen it to assert rendered HTML.

### R12: Cover Multi-Backtick Inline Code in Shortcode Protection (Medium)

**Defect.** `_INLINE_CODE_RE` (`shortcodes.py:23`) is `` r"`[^`\n]+`" ``, which only matches single-backtick spans.
CommonMark multi-backtick spans (used precisely to embed literal backticks) are mis-parsed, so a shortcode inside a double-backtick span can be expanded instead of left literal.

**Root cause.** The regex does not implement CommonMark's rule that a span opened by a run of N backticks closes at the next run of exactly N.

**Required behavior.** Inline code spans are left untouched regardless of backtick-run length (function docstring, shortcodes.py:32-35; v1 spec shortcodes, lines 1268-1305).

**Acceptance criteria.**
- A shortcode inside a double-backtick span is emitted literally.
- A shortcode inside a span that itself contains a single backtick is emitted literally.
- The existing single-backtick test still passes.

**Test notes.** Extend `tests/test_shortcodes.py` alongside the existing protection tests at lines 69-89.

### R13: Discover Shortcodes Across All Three Lookup Locations (Medium)

**Defect.** `_discover_shortcode_names` (`cli.py:739-744`) scans only `templates/shortcodes/`.
The Jinja loader (`templates.py:68-74`) resolves `shortcodes/{name}.html` from the project root (the v1 spec's preferred location), `templates/`, and the built-in theme, so shortcodes that render fine are missing from generated skills.

**Root cause.** Discovery hard-codes the alternative location and does not mirror the loader's cascade.

**Required behavior.** v1 spec, line 1277: shortcode templates live at `shortcodes/{name}.html` at the project root (preferred), `templates/shortcodes/{name}.html` (alternative), or in the built-in theme.
`generate-skill` reports available shortcodes as part of the site's actual shape (line 1790).

**Acceptance criteria.**
- A shortcode at `<project>/shortcodes/foo.html` appears in generated skill output.
- A shortcode at `<project>/templates/shortcodes/bar.html` is still discovered.
- Built-in theme shortcodes (`get_theme_templates_dir()/shortcodes/*.html`) are included, and names are de-duplicated across locations.

**Test notes.** `tests/test_cli.py:707` uses a bare site; `tests/test_skills.py:128` bypasses discovery.
Add direct tests for `_discover_shortcode_names`.

### R14: Advertise the Aggregate Feed in schema.json (Medium)

**Defect.** `_resource_locations` (`agent_surface.py:149-174`) enumerates only per-type feeds and never adds the site-wide `/feed.xml` and `/atom.xml` that `generate_feeds` (`feeds.py:130-140`) writes when `config.site.feed.enabled` (added in commit `eade87c`).

**Root cause.** The resource enumeration was not updated when the aggregate feed landed.

**Required behavior.** v1 spec, line 1725: schema.json describes feed locations, per-type and the site-wide aggregate.

**Acceptance criteria.**
- With `site.feed.enabled` and `rss` in formats, `schema["resources"]["feeds"]` includes the aggregate `<site.url>/feed.xml`.
- With `atom` in formats, the aggregate `<site.url>/atom.xml` entry is present.
- With `site.feed.enabled: false`, no aggregate entry is emitted.

**Test notes.** Extend `tests/test_agent_surface.py:167`.

### R15: Scope the Hooks sys.path Insertion (Medium)

**Defect.** `discover_hooks` (`plugins.py:155-164`) inserts `hooks/` at the front of `sys.path` and never removes it, so the project's hooks directory shadows imports for the process lifetime.
The insertion exists so hooks can import underscore-prefixed siblings (commit `2e16cc0`).

**Root cause.** A load-phase need was implemented as a permanent global mutation.

**Required behavior.** Hooks can import sibling modules during discovery, and `sys.path` is restored afterward (v1 spec, Customization and Extensibility, the hooks seam at line 23; the spec never authorizes a process-lifetime path mutation).

**Acceptance criteria.**
- After `discover_hooks` returns, `sys.path` equals its pre-call value.
- A hook importing an underscore-prefixed sibling still loads (regression guard on `tests/test_plugins.py:150`).
- Calling `discover_hooks` twice does not grow `sys.path`.

**Test notes.** Add a sys.path equality assertion; a try/finally around the load loop is the expected shape.
The double-call criterion already passes today via the `not in sys.path` guard (plugins.py:156); it stays as a regression guard against a fix that removes only the first insertion, so the RED step must fail on the equality assertion, not on it.
Watch dev-server rebuilds (R5): hooks are re-discovered per rebuild, so the cleanup must hold across repeated calls.

### R16: Guarantee Temp Build Directory Cleanup (Medium)

**Defect.** The temp dir from `tempfile.mkdtemp` (`build.py:284`) is removed only by `_fail_build` (line 523), the dry-run path (line 468), and the success swap (line 730).
Failures after creation that bypass `_fail_build` leak it: the strict-crossref raise at line 351 today, and any exception out of `_emit_outputs` or the 404 write (line 395).
There is no try/finally around the pipeline.

**Root cause.** Cleanup is attached to specific known-failure helpers instead of the temp dir's lifetime.

**Required behavior.** A failed build never touches the previous good output and never leaves build output behind (build.py's own contracts at lines 282-283, 516, 717-724; v1 spec, lines 2611 and 2619).

**Acceptance criteria.**
- After a strict-mode failure, no `.bartleby-build-*` directory remains under the project dir.
- After an exception injected into `_emit_outputs`, no temp dir remains.
- Successful and dry-run builds still leave no temp dir (regression guard on `tests/test_build.py:378`).

**Test notes.** Note the interaction with R3: once strict failures raise `BuildError`, route them through cleanup too.
A try/finally (or context manager) owning `state.output_dir` covers all paths at once.

### R17: Count Only Copied Files in static_file_count (Medium)

**Defect.** `build.py:477-481` computes `static_file_count` by globbing every non-HTML file in the final tree, so generated artifacts (search index, feeds, markdown variants, llms.txt files, sitemap, agent-surface JSON, robots.txt, tree-shaken icon SVGs, all emitted in `build.py:400-447`) inflate the count.
The field's own docstring (build.py:100, 106) says "non-HTML asset files copied into the output tree".

**Root cause.** Counting by output-tree glob instead of counting what the copy steps copied.

**Required behavior.** `static_files` in build stats reports copied static files and co-located assets, distinct from generated artifacts (v1 spec, build stats at lines 2260-2270; the field docstring).

**Acceptance criteria.**
- `static_file_count` equals files copied from `static/` plus co-located assets, excluding every generated artifact class listed above.
- A build with N static files and M co-located assets reports N + M regardless of generated artifacts.
- Toggling a generated artifact (for example `ai.llms_txt`) does not change the count.

**Test notes.** `tests/test_output.py` round-trips the field but never validates it against a real tree; add a build-level assertion.
The natural fix is returning counts from `copy_static_files` and `copy_colocated_assets` instead of re-globbing.

## Component Boundaries

Each requirement above is independently implementable and testable, with three ordering constraints:

- R3 (error contract) before R8 and R16, which raise or route through `BuildError`.
- R4 before R5: live reload serves the same directory the watcher rebuilds into.
- R7's asset half and R8 both touch `copy_colocated_assets`; implement in that order to avoid churn.

Everything else can proceed in any order after R1, which gates the whole suite (the CLI does not import until it lands).

## Verification

The cycle is done when:

1. All acceptance criteria above have passing tests that were observed failing first.
2. `just check` passes (pytest, ruff, mypy strict).
3. The e2e smoke test exercises a build and serve cycle on a site with a custom `output_dir`, a draft with a co-located asset, and a title containing a double quote, and the output is correct for all three.

## Open Questions

For `/bpe:brainstorm` (decision D3); none of these block this remediation cycle.

1. fountain-py integration (screenplay content in bartleby sites) is the next goal after remediation.
   Should it run as a v2 spec cycle that starts only after this remediation ships?
   Recommendation: yes.
   It is feature work with its own brainstorm, spec, and plan, and this cycle is scoped to the 20 confirmed defects under the no-behavior-drift rule, so nothing about fountain-py belongs here.
2. R8 resolves the shared-directory asset bundle as a loud build error rather than a per-page association rule.
   Confirm that choice before plan time; R8's test notes mark the section to edit if the answer is association instead.
