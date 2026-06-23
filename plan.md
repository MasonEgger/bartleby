# Bartleby v0.1.0 Hardening Plan

## Current Status

**0 of 18 steps complete.** This is a delta plan, not a greenfield one.

The 27-step initial build is done: 282 tests pass, `ruff` and `mypy --strict`
are clean, and `new site -> new post -> build -> validate` works end to end.
What remains is the gap between that implementation and the revised `spec.md`
bar of "works as advertised 0.1.0": no stub assets, no inert config keys, no
advertised-but-absent behavior.

This plan turns the audit's open findings (see `audit.md`) and the 2026-06-21
re-spec additions into right-sized TDD steps. It does not re-plan the 27 done
steps. Each step below is scoped to take the existing codebase one verifiable
move closer to a shippable 0.1.0.

Source of truth for behavior is `spec.md`. Source of truth for the remaining
defects is the `audit.md` tracker; each step names the findings it closes.

### Scope at a glance

| Phase | Steps | Closes |
|---|---|---|
| 1. Foundations | 1-3 | Design 3, 4, 5, 14, 15; the JSON output contract |
| 2. Theme reality | 4-7 | Deferral 1, 2, 3; Spec 2, 3 |
| 3. Plugins | 8-9 | Deferral 7; Design 6; the public plugin API |
| 4. Dev server | 10 | Deferral 6; Design 13 |
| 5. Agent surface and CLI | 11-15 | Spec 1 (Phase 5); the static agent surface |
| 6. Feeds | 16 | Site-wide aggregate feed |
| 7. Release readiness | 17-18 | TestGap 1-5; Meta 1, 2; Design 1, 2, 7-12, 16, 17 |

## Implementation Guidelines

- TDD: RED (failing tests) then GREEN (minimal code) then REFACTOR.
- Each step ends with `just check` passing (lint, typecheck, tests).
- Strict type hints everywhere (mypy strict, no `Any` escape hatches).
- Every `.py` file starts with a 2-line `ABOUTME: ` comment.
- Test your application logic, not library behavior.
- Build on prior steps; wire each change into the system, leave no orphan code.
- Follow the YAML-backed module skeleton in `CLAUDE.md` for new typed modules.
- Re-read the relevant `spec.md` section named in each step before writing tests.

## Module map (target state)

New modules this plan adds: `output.py`, `schema_introspection.py`,
`content_query.py`, `linting.py`, `export.py`, `skills.py`. Modules it
substantially changes: `build.py`, `templates.py`, `plugins.py`, `server.py`,
`cli.py`, `feeds.py`, `icons.py`, `theme/`. The full intended layout is in the
prior plan's Architecture Overview and in `spec.md`.

---

## Phase 1 — Foundations

These three steps unblock the rest. The template-context change prevents the
class of bug the audit caught twice; the build-failure and output-contract
changes are depended on by every later command.

### Step 1: Pass the Page dataclass into template context

**NOTE**: Closes Design 3 and Design 4. Today `build_page_context` flattens
`Page` into a hand-built dict, which is why author bylines and listing pages
shipped empty (Bugs 1 and 2). Passing the dataclass through removes the closed
schema. Also move the `on_pages` hook to fire after the draft filter so plugins
never see pages that will be discarded.

```text
1. RED: Write template-context tests in tests/test_templates.py:
   - Test that build_page_context exposes the Page object as `page` with its
     real attributes reachable (page.title, page.date, page.authors as resolved
     Author objects, page.taxonomies, page.custom_metadata fields).
   - Test that a newly added Page field is reachable in context without editing
     build_page_context (add a throwaway field in the test's Page instance and
     assert it renders).
   - Test that author bylines resolve to Author objects, not raw keys.

2. RED: Write a draft-filter ordering test in tests/test_build.py:
   - Test that the on_pages hook receives only published pages (register a hook
     that records the pages it sees; assert a draft page is absent).

3. GREEN: Change build_page_context in src/bartleby/templates.py to put the
   Page dataclass on the context directly; keep any genuinely computed extras
   (excerpt, readtime, seo) as additional keys. Update theme templates in
   src/bartleby/theme/templates/ to read page.<attr>.

4. GREEN: In src/bartleby/build.py move the on_pages dispatch to after the
   draft filter.

5. REFACTOR: Remove now-dead dict-adapter code; ensure no template references a
   key that no longer exists.

6. Update spec cross-reference: confirm the Template Context section of spec.md
   matches the new contract; note any drift.

7. Verify meaningful coverage of the context contract and run `just check`.
```

### Step 2: Build failure semantics and clean error reporting

**NOTE**: Closes Design 5, 14, 15 and the spec's "Build Failure Semantics"
section. Collect all page-level errors in one pass, write `site/` only on full
success, and never surface a raw traceback.

```text
1. RED: Write build-failure tests in tests/test_build.py:
   - Test that two pages with errors (bad front matter, bad shortcode) produce
     a single BuildError carrying both, not a stop on the first.
   - Test that a failed build leaves a pre-existing site/ directory untouched
     (seed site/ with a sentinel file, force a failure, assert sentinel still
     present and no partial output written).
   - Test that on success, output is swapped in atomically (build into a temp
     location, then move).
   - Test that pre-render errors (invalid config) fail immediately without a
     render pass.

2. RED: Write error-reporting tests in tests/test_cli.py:
   - Test that a build error prints a clean message with file path and a stable
     error code to stderr and exits 1 (no "Traceback" substring in output).
   - Test that setting BARTLEBY_DEBUG=1 re-enables the traceback.

3. GREEN: In src/bartleby/build.py, accumulate per-page errors during the
   render pass into a list; raise one BuildError with the collected list at the
   end; render into a temp dir and swap on success.

4. GREEN: Add a top-level CLI error boundary in src/bartleby/cli.py that
   catches BuildError/ConfigError/AuthorError, prints clean output, honors
   BARTLEBY_DEBUG, and exits 1.

5. GREEN: Introduce logging.getLogger usage in src/bartleby/ for non-essential
   output; keep results on stdout.

6. RED: Add a test that on_build_error fires once with the collected error list.

7. REFACTOR: Centralize error formatting so text and JSON modes share it.

8. Verify coverage and run `just check`.
```

### Step 3: Structured output layer (--output json)

**NOTE**: Establishes the stable JSON CLI contract every Phase 5 command
depends on. Closes the output half of Spec 1's CLI requirements.

```text
1. RED: Write output-formatter tests in tests/test_output.py:
   - Test that a result dataclass renders to deterministic JSON with the
     documented keys for build (status, pages, static_files, duration_ms,
     errors, warnings, output_dir).
   - Test that an error renders as a JSON object with an "error" key plus code
     and file fields.
   - Test that text mode renders the same data human-readably.
   - Test exit codes: 0 success, 1 error, 2 usage error.

2. Document: confirm the CLI "Error contract" and global-flags section of
   spec.md; the JSON schemas here ARE the stable contract.

3. GREEN: Create src/bartleby/output.py with result dataclasses and a formatter
   that serializes to text or json.

4. GREEN: Add global flags (--output, --config, --quiet, --verbose) in
   src/bartleby/cli.py; route existing commands (build, validate, new site,
   new post) through the formatter. In json mode, never prompt; missing
   required params exit 2.

5. RED: Add tests that `bartleby build --output json` and
   `bartleby validate --output json` emit valid parseable JSON.

6. REFACTOR: Ensure one code path produces both formats.

7. Verify coverage and run `just check`.
```

---

## Phase 2 — Theme reality

Replace the stubbed and hand-rolled theme assets with the real thing so the
advertised interactivity and styling work.

### Step 4: Vendor real Alpine, HTMX, and lunr bundles

**NOTE**: Closes Deferral 1. The current files are ~200-byte stubs, so search,
dark mode, back-to-top, and TOC scroll-spy are all dead.

```text
1. RED: Write asset tests in tests/test_theme.py:
   - Test that each vendored JS file exceeds a sane minimum size and contains a
     known signature string from the real library.
   - Test that THIRD-PARTY-NOTICES lists Alpine (MIT), HTMX (BSD-2), lunr (MIT)
     with pinned versions.
   - Test that build copies the real bundles into site/js/.

2. GREEN: Vendor pinned minified Alpine.js, HTMX, lunr.js into
   src/bartleby/theme/static/js/; record exact versions and licenses in
   THIRD-PARTY-NOTICES.

3. RED: Add a rendered-output test that base.html references the bundles and
   the search/dark-mode markup is wired to them (assert the Alpine directives
   and search container exist in built HTML).

4. GREEN: Ensure base.html and partials reference the real bundles.

5. REFACTOR: Remove the stub placeholder comments.

6. Verify coverage and run `just check`.
```

### Step 5: Hybrid Tailwind pipeline and `bartleby theme compile`

**NOTE**: Closes Deferral 2. Implements the spec's "Theme Asset Pipeline
(Hybrid Tailwind)": real CLI-compiled CSS ships in the wheel; a new command
recompiles including project overrides via an on-demand binary.

```text
1. RED: Write binary-resolver tests in tests/test_theme_compile.py:
   - Test resolution order: a tailwindcss on PATH wins; else a cached binary;
     else an explicit download.
   - Test that a checksum mismatch on download aborts cleanly (no partial
     binary left behind).
   - Test that compiled CSS at <project>/.bartleby/theme.css is preferred over
     the shipped CSS when present and newer than the template tree.

2. Document: confirm the Theme Asset Pipeline section of spec.md.

3. GREEN: Add the package-build step that compiles the shipped theme.css from
   theme templates plus a curated safelist (document the invocation; the wheel
   ships the output).

4. GREEN: Implement `bartleby theme compile` in src/bartleby/cli.py backed by a
   resolver module: PATH -> cache (~/.cache/bartleby/) -> download with SHA-256
   verification; --refresh forces re-download; scans overrides/, partials/,
   shortcodes/; writes .bartleby/theme.css.

5. GREEN: Make build prefer .bartleby/theme.css when present.

6. RED: Test that `theme compile --output json` emits the documented shape
   (status, css_path, binary, duration_ms, classes_scanned).

7. REFACTOR: Ensure the download never runs implicitly during build.

8. Verify coverage and run `just check`.
```

### Step 6: Feature toggle enforcement

**NOTE**: Closes Spec 2. Today `theme.features` is parsed and ignored. Make
every toggle a real conditional and reject unknown names.

```text
1. RED: Write config-validation tests in tests/test_config.py:
   - Test that an unknown theme.features entry is a validation error naming the
     bad entry.
   - Test that the known feature set is accepted.

2. RED: Write rendering tests in tests/test_theme.py:
   - Test that enabling `search` puts the search markup in built HTML and
     disabling it removes the markup entirely (not merely hides it).
   - Test the same for content.code.copy and navigation.top.

3. GREEN: Add a feature(name) template helper backed by the resolved config;
   gate the relevant template blocks on it.

4. GREEN: Add known-feature-name validation in src/bartleby/config.py.

5. REFACTOR: Centralize the known-feature list so config and the helper share
   one source.

6. Verify coverage and run `just check`.
```

### Step 7: Full icon packs and standalone 404

**NOTE**: Closes Deferral 3 and Spec 3. Vendor all four packs complete; render
a real /404.html.

```text
1. RED: Write icon tests in tests/test_icons.py:
   - Test that get_icon_path resolves an icon from each of the four packs
     (material, fontawesome, octicons, simple).
   - Test that tree-shaking copies only referenced icons into site/.
   - Test that an unreferenced pack contributes zero files to output.

2. RED: Write a 404 test in tests/test_build.py:
   - Test that build renders a standalone site/404.html from the 404 template.

3. GREEN: Vendor the four complete icon packs into src/bartleby/theme/icons/;
   ensure get_icon_path resolves against the full set.

4. GREEN: Add the 404 render to the build pipeline (the static-templates step).

5. REFACTOR: Confirm tree-shaking scans both rendered HTML and templates.

6. Verify coverage and run `just check`.
```

---

## Phase 3 — Plugins

Make the declared hook surface real and open the two delivery forms the spec's
public plugin API requires.

### Step 8: All hook events fire; BasePlugin parity

**NOTE**: Closes Deferral 7 and Design 6. Twelve of the declared events never
dispatch today; user handlers silently no-op.

```text
1. RED: Write hook-dispatch tests in tests/test_plugins.py:
   - For each declared event (on_startup, on_config, on_pre_build, on_files,
     on_nav, on_env, on_pre_page, on_page_read_source, on_page_markdown,
     on_page_content, on_page_context, on_post_page, on_post_build,
     on_build_error, on_serve, on_shutdown), register a handler and assert it
     is called once at the right point with the documented arguments.
   - Test that a handler returning a value replaces the value downstream and
     returning None preserves it.
   - Test that BasePlugin defines a method for every event (no missing on_pages
     vs KNOWN_EVENTS mismatch).

2. GREEN: Add the missing dispatch call sites in src/bartleby/build.py and
   src/bartleby/server.py at the pipeline positions named in spec.md.

3. GREEN: Reconcile KNOWN_EVENTS and BasePlugin so the sets match.

4. REFACTOR: Ensure priority-then-registration ordering holds for every event.

5. Verify coverage and run `just check`.
```

### Step 9: Entry-point plugin discovery

**NOTE**: Implements the public plugin API's second delivery form: pip-
installed packages via the `bartleby.plugins` entry-point group. Same events
as `hooks/*.py`.

```text
1. RED: Write discovery tests in tests/test_plugins.py:
   - Test that a module registered under the bartleby.plugins entry-point group
     has its on_<event> functions registered (use a fake entry point in the
     test).
   - Test registration order: internal handlers, then installed plugins
     (alphabetical), then project hooks; assert project hooks run last at equal
     priority.
   - Test that `plugins: {name: false}` in config disables a named plugin.

2. Document: confirm the Handler Sources section of spec.md.

3. GREEN: Add entry-point discovery in src/bartleby/plugins.py; merge with the
   existing hooks/*.py discovery; honor the plugins config disable list.

4. GREEN: Wire discovery into the build pipeline's hook-discovery step.

5. REFACTOR: One registration path for all three sources.

6. Verify coverage and run `just check`.
```

---

## Phase 4 — Dev server

### Step 10: Live reload with last-good-build and hook reload

**NOTE**: Closes Deferral 6 and Design 13. The README implies live reload
works; today there is no watcher and no socket.

```text
1. RED: Write watcher tests in tests/test_server.py:
   - Test that a change under any watched path (content/, templates/,
     overrides/, static/, hooks/, data/, shortcodes/, partials/, .authors.yml,
     bartleby.yml) triggers a rebuild (use a fake/triggered observer; assert
     the rebuild callback fires).
   - Test that a bartleby.yml or hooks/*.py change re-registers handlers
     (change a hook, assert the new handler runs on the next rebuild).
   - Test that a failed rebuild keeps the last good output served and surfaces
     the collected errors (assert the previous build is still reachable).
   - Test that the reload snippet is injected only in serve mode, never in
     `bartleby build` output.

2. Document: confirm the Development Server section of spec.md.

3. GREEN: Implement DevServer.run() in src/bartleby/server.py with a
   watchdog observer, a websockets reload channel, full-rebuild-on-change,
   last-good-build retention, pipeline restart on config/hook changes, and the
   serve-only reload snippet.

4. GREEN: Auto-trigger `theme compile` when overrides need it and the binary is
   already cached; otherwise print a one-line hint.

5. RED: Test the --events JSON stream emits one object per line for rebuild and
   error events with the documented fields.

6. REFACTOR: Ensure no reload code leaks into production builds.

7. Verify coverage and run `just check`.
```

---

## Phase 5 — Agent surface and CLI (Spec 1, Phase 5)

Build the agent-facing surface. Schema introspection comes first because the
static manifest and skill generation both read it.

### Step 11: Schema introspection

**NOTE**: Closes part of Spec 1. `bartleby schema` for agent self-discovery.

```text
1. RED: Write tests in tests/test_schema_introspection.py:
   - Test that schema for a content type emits its required/optional fields,
     types, and choices derived from config.
   - Test that schema authors emits public author data only (no private
     fields).
   - Test that schema taxonomies emits taxonomy names and the in-use terms.

2. GREEN: Create src/bartleby/schema_introspection.py and wire
   `bartleby schema <type|authors|taxonomies>` through the output formatter.

3. RED: Test the json output matches the documented manifest field shape (it is
   the same data schema.json will reuse in Step 13).

4. REFACTOR: Factor the schema derivation so Step 13 can reuse it.

5. Verify coverage and run `just check`.
```

### Step 12: Content query

**NOTE**: Closes part of Spec 1. `bartleby content list/get`.

```text
1. RED: Write tests in tests/test_content_query.py:
   - Test that content list returns published pages with curated fields and
     supports filtering by content type and sorting by date.
   - Test that content get <path> returns one page's metadata and body.
   - Test that drafts are excluded from list output by default.

2. GREEN: Create src/bartleby/content_query.py; wire the commands through the
   output formatter.

3. REFACTOR: Share the published-page selection with the build pipeline so
   "published" means the same thing everywhere.

4. Verify coverage and run `just check`.
```

### Step 13: Static agent surface (schema.json + content-index.json)

**NOTE**: Implements the spec's static agent surface. Replaces any need for an
MCP server.

```text
1. RED: Write tests in tests/test_agent_surface.py:
   - Test that schema.json is emitted at the site root with site identity,
     content-type schemas, taxonomy terms, public authors, and feed/sitemap/
     llms.txt/content-index locations.
   - Test that content-index.json lists only published pages with URL, .md
     variant URL, and curated fields.
   - Test the field curation rule: semantic fields included (title,
     description, date, updated, type, taxonomy terms, authors, custom schema
     fields); mechanical fields excluded (template, draft, url overrides, toc/
     render toggles).
   - Test that llms.txt opens with a machine-readable section linking
     schema.json and content-index.json by absolute URL.
   - Test that every rendered page head carries a rel="alternate"
     type="text/markdown" link to its .md variant.
   - Test that user content colliding with a generated artifact path is a build
     error with a clear message.
   - Test that ai.agent_surface: false suppresses both artifacts.

2. Document: confirm the Static Agent Surface section of spec.md.

3. GREEN: Generate both artifacts in the build pipeline (the new step 24a);
   reuse the Step 11 schema derivation; add the llms.txt discovery section and
   the per-page alternate link injection.

4. GREEN: Add ai.agent_surface config (default true) and collision detection.

5. REFACTOR: One curation function decides semantic vs mechanical fields.

6. Verify coverage and run `just check`.
```

### Step 14: render and lint commands

**NOTE**: Closes part of Spec 1. Single-page render for fast feedback; content
quality checks.

```text
1. RED: Write render tests in tests/test_cli.py:
   - Test that `bartleby render <path>` renders one content file to HTML
     without a full build and emits json with the rendered output and metadata.

2. RED: Write lint tests in tests/test_linting.py:
   - Test detection of broken internal links, missing descriptions, and orphan
     pages, each as a structured finding with file and a code.
   - Test that --check-external is opt-in and off by default.

3. GREEN: Implement render in src/bartleby/cli.py reusing the markdown pipeline
   and template system.

4. GREEN: Create src/bartleby/linting.py and wire `bartleby lint` through the
   output formatter.

5. REFACTOR: Share link-resolution logic with the crossref resolver.

6. Verify coverage and run `just check`.
```

### Step 15: export, generate-skill, and build --dry-run

**NOTE**: Closes the rest of Spec 1. Deterministic skill generation (no content
analysis; that is deferred and reserved).

```text
1. RED: Write export tests in tests/test_export.py:
   - Test JSONL, JSON, and CSV export of published content with curated fields.

2. RED: Write skill-generation tests in tests/test_skills.py:
   - Test that generate-skill produces the three skills (bartleby-write,
     bartleby-review, bartleby-ops) filled with the site's actual content
     types, schemas, taxonomy terms, authors, and shortcodes.
   - Test determinism: identical config/schema inputs produce byte-identical
     skill files.
   - Test that ai.agent_context (voice/audience/constraints) is included
     verbatim when set.
   - Test that setting ai.skills.analyze_content is a "not yet supported"
     validation error.

3. RED: Write a dry-run test in tests/test_build.py:
   - Test that build --dry-run reports added/modified/deleted without writing
     to disk.

4. GREEN: Create src/bartleby/export.py and src/bartleby/skills.py; wire the
   commands through the output formatter; implement --dry-run in build.

5. REFACTOR: Reuse the Step 11 schema derivation and Step 12 content selection.

6. Verify coverage and run `just check`.
```

---

## Phase 6 — Feeds

### Step 16: Site-wide aggregate feed

**NOTE**: Implements `site.feed` (the homepage firehose) alongside the existing
per-content-type feeds, with contextual auto-discovery.

```text
1. RED: Write aggregate-feed tests in tests/test_feeds.py:
   - Test that an empty include list aggregates every content type that has its
     own feeds enabled.
   - Test that a non-empty include list restricts the aggregate to those types.
   - Test that naming a type with no feed of its own is a config validation
     error.
   - Test that items are merged across types, sorted date-descending, and
     truncated to limit.
   - Test that each item carries a category naming its source content type.
   - Test that /feed.xml and /atom.xml are written at the root per formats.

2. RED: Write auto-discovery tests in tests/test_feeds.py or test_theme.py:
   - Test that the homepage advertises the aggregate feed in its head.
   - Test that a content-type page advertises that type's feed first and the
     aggregate second.

3. Document: confirm the Feed Generation section of spec.md.

4. GREEN: Add site.feed config parsing and validation in src/bartleby/config.py.

5. GREEN: Implement the aggregate builder in src/bartleby/feeds.py and the
   contextual rel="alternate" link selection in the template layer.

6. GREEN: Wire the aggregate into the build pipeline's feed step.

7. REFACTOR: Share item construction between per-type and aggregate feeds.

8. Verify coverage and run `just check`.
```

---

## Phase 7 — Release readiness

### Step 17: Smoke test and test-quality hardening

**NOTE**: Closes TestGap 1-5. The audit shipped two HIGH bugs through a green
suite because listings were never rendered in tests and there was no e2e smoke.

```text
1. RED: Add an end-to-end smoke test in tests/test_smoke.py:
   - Scaffold a site, create a published post, build, and assert rendered HTML
     contains the post title, a non-empty author byline, and the post appearing
     in the listing page (grep the actual output, not just file existence).

2. RED: Strengthen tests/test_listings.py and tests/test_taxonomies.py:
   - Render the list and taxonomy templates and assert the posts appear in the
     HTML, not just that the virtual Page dataclass has the right shape.

3. RED: Strengthen tests/test_theme.py:
   - Render and inspect HTML rather than string-matching raw CSS file contents.

4. RED: Add a DevServer.run() integration test now that Step 10 made it real.

5. GREEN: Make any failing assertions pass by fixing the underlying code, not
   by weakening the tests.

6. Add the smoke test to the CI invocation.

7. Verify coverage and run `just check`.
```

### Step 18: Packaging and polish

**NOTE**: Closes Meta 1, 2 and the low-severity Design items (1, 2, 7, 8, 9,
10, 11, 12, 16, 17). Group cohesively; each is small.

```text
1. RED: Write tests where behavior changes:
   - tests/test_content.py: front matter requires a newline after the opening
     --- (Design 1); non-dict YAML front matter raises a clear error rather
     than being swallowed (Design 2).
   - tests/test_build.py: the output directory is configurable, not hardcoded
     to site/ (Design 10).
   - tests/test_cli.py: `bartleby validate` also dry-runs URL generation,
     checks template existence for template: overrides, and checks crossrefs
     (Design 17).

2. GREEN: Implement the above behavior changes.

3. REFACTOR (no behavior change, keep tests green):
   - Replace magic strings with a StrEnum or constants (Design 7).
   - Fix the resolve_template_name docstring/count and make the fall-through
     error name the candidate list (Design 8, 9).
   - Move the in-function theme import to module top (Design 11).
   - Put hooks/ on sys.path so hook files can import siblings (Design 12).
   - Split build() into named phase helpers (Design 16).

4. Packaging: add a LICENSE file (MIT), set the license field in
   pyproject.toml, update README to state the license, and create CHANGELOG.md
   covering the path to 0.1.0 (Meta 1, 2).

5. Verify coverage and run `just check`.
```

---

## Success Metrics

- Every audit tracker item targeted above is closed; the remaining open items
  are only the explicitly deferred ones (Deferral 4 parallel build, the
  voice/tone content analysis, the public theme API and extra themes).
- A fresh `new site -> new post -> build -> serve` produces a styled site with
  working search, dark mode, and live reload, plus schema.json,
  content-index.json, per-type and aggregate feeds, and generated skills.
- `bartleby <command> --output json` is valid JSON for every command.
- `ruff`, `mypy --strict`, and the full test suite (including the e2e smoke
  test) pass.
- No stub assets, no inert config keys, no advertised-but-absent behavior:
  the 0.1.0 "works as advertised" bar from spec.md is met.

## Out of scope (deferred, by decision)

- Parallel build architecture (asyncio + ProcessPoolExecutor); the build stays
  synchronous and is documented as such.
- Incremental rebuilds (--dirty).
- Voice/tone content analysis for skill generation (sponsorware candidate).
- Public theme API and additional themes (ReadTheDocs-style, minimal).
- Migration tool (`bartleby migrate`); first candidate to graduate later.
