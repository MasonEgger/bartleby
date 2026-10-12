# Bartleby Goal 8 Plan: First-Run Experience and Docs Layout

Turn a working-but-unwelcoming first five minutes into one as simple as Hugo's, with a docs layout as good as Zensical's (spec.md Goal 8).
The theme system and the showcase shipped in v0.1.1-stabilization (.ai-sessions/v0.1.1-stabilization/).
This cycle builds the first-run feature set on top of it: a single config schema that feeds `--full-config`, the `config` command, and the docs; CLI configuration without one flag per option; content types that turn on and off with one command; full markwright integration through its public config API; a three-column docs layout; an async dev server; a docs-shaped scaffold with a feature tour; and the correctness, acknowledgments, and license work that lets Mason send it to people.

## Starting point (verified against the tree, 2026-10-12)

1. **Config is hand-parsed, with no schema object.** `config.py` has typed dataclasses (`BartlebyConfig` and friends) and per-section `_parse_*` helpers, and `_reject_unknown_top_level_keys` gates the top level. Nothing enumerates every key with its type, default, allowed values, and description. `--full-config`, `config schema`, and the config reference docs all need that one source.
2. **No comment-preserving YAML writer.** `ruamel.yaml` is not a dependency. `config set`, `enable`, and `--full-config` all need to write YAML that keeps comments.
3. **No CLI config surface beyond a few flags.** `build` has `--strict`, `--include-drafts`, `--dry-run`; `serve` has `--host`, `--port`, `--events`. There is no `--base-url`, no `--set`, and no `config` command.
4. **Content types are static.** `ContentTypeConfig` has no `enabled` field; there is no `enable`/`disable` command. Feeds themselves are built: `feeds.py` emits per-type feeds and the site-wide aggregate from the existing per-type `feeds` key and `site.feed`.
5. **markwright runs on name-only extension loading.** `markdown_pipeline.py` lists the eight markwright extensions plus pymdownx in `_DEFAULT_EXTENSIONS` and feeds `extension_configs` from the `markdown_extensions` config. There is no `markwright:` config section, no use of markwright 0.3.0's public config API (`config_from_mapping`, `selected_extensions`, `extension_configs`), and no click-to-load host script or styling.
6. **The dev server is `http.server`-based with a separate reload port.** `server.py` runs `ThreadingHTTPServer` and a WebSocket hub on its own port (`reload_snippet(ws_port)` points the page at it). Goal 8 moves this to Starlette and uvicorn with reload on the same port.
7. **The scaffold is blog-shaped and not minimal.** `src/bartleby/scaffold/` ships a `blog` content type, a sample post, and a `bartleby.yml` that lists every theme feature. Goal 8 wants a docs-shaped scaffold with a minimal config, a home page that says what to do next, and one feature tour page.

## Design decisions carried from the spec (Goal 8)

- **One schema is the single source** for `--full-config`, `config schema`, and the configuration reference docs. A drift test fails if the validator accepts a key the schema omits, or the reverse.
- **CLI config is a few dedicated flags plus `--set`**, not one flag per option. `--set key.path=value` is repeatable on `build`, `serve`, and `validate`, parses values as YAML, runs through the same validator, and labels its errors as coming from `--set`. Environment-variable config is Deferred (spec.md), so no step reads env vars.
- **`enable`/`disable` toggle content types** through an `enabled` flag, never by deleting config, and are safe to run twice. `enable blog tutorials` adds a blog-shaped type named `tutorials`. Each enabled type gets its own RSS and Atom feeds plus the one combined site feed.
- **markwright is a released dependency, consumed, not changed.** Bartleby validates and passes the `markwright:` section through markwright's public config API and follows its Click-to-Load docs for the host script. Markup lives in markwright; the swap script and the CSS live in Bartleby's themes. Embeds load eagerly by default (markwright's default); click-to-load is opt-in.
- **The docs layout is Bartleby's own markup and CSS**, three columns, following the Zensical and Material shape without copying it, with feature flags to fold the table of contents into the nav and to move top-level sections into header tabs.

## Spec fences honored

- **No `## Invariants` section** exists in spec.md, so that fence does not apply.
- **Non-goals (spec.md):** no step touches build speed, parallel or incremental builds, dynamic/CMS features, hosting, or a plugin/theme marketplace. The async dev server is about serving, not build speed.
- **Deferred (spec.md Roadmap):** no step implements `migrate mkdocs`, a fourth bundled theme, fountain-py, multi-site linking, environment-variable config, or the skill-generation rework. `--set` is the only config-override layer this cycle.
- **Version:** Bartleby stays on 0.1.x; no step bumps to 0.2.0.

## Current Status

Legend: [ ] not started, [~] in progress, [x] complete.

- [ ] Section 1: The config schema and the annotated writer (Steps 1-2)
- [ ] Section 2: CLI configuration surface (Steps 3-6)
- [ ] Section 3: Content types on demand (Steps 7-8)
- [ ] Section 4: markwright integration (Steps 9-11)
- [ ] Section 5: The async dev server (Step 12)
- [ ] Section 6: Three-column docs layout (Step 13)
- [ ] Section 7: Scaffold and first-run output (Steps 14-15)
- [ ] Section 8: Docs, acknowledgments, correctness, and the final gate (Steps 16-19)

---

## Section 1: The config schema and the annotated writer

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: uv run ruff check --output-format=json src/ tests/, uv run mypy src/

The keystone. Everything in Section 2 and the config reference docs read from the schema built here, and the writer built here is shared by `config set`, `enable`, and `--full-config`.

### Step 1: The config schema object and its drift test

**NOTE**: New module `src/bartleby/config_schema.py`. Describe every `bartleby.yml` key the validator in `config.py` accepts: its dotted path, type, default, allowed values (when a closed set), whether it repeats (content types, taxonomies), and a one-line description. Follow the YAML-backed-module skeleton in CLAUDE.md (`from __future__ import annotations`, `TYPE_CHECKING` block, `@dataclass(slots=True)`). The schema is data about config, so it reads defaults from the `config.py` dataclasses where it can rather than copying literals. Do not change `config.py`'s parsing here; the drift test ties the two together.

```text
1. RED: Write schema and drift tests first:
   - Create tests/test_config_schema.py:
     - Test that `config_schema.CONFIG_SCHEMA` is a flat, ordered collection of field entries, each with path, type name, default, choices (or None), repeatable flag, and a non-empty one-line description.
     - Test that every top-level key named in `config.py`'s `_reject_unknown_top_level_keys` has a schema entry at that top-level path.
     - Test that each closed-set field carries its real allowed values (e.g. a theme feature field lists exactly `theme_loader.THEME_FEATURES`; a feed-formats field lists `rss` and `atom`).
     - Test that every schema default equals the corresponding `config.py` dataclass default for the fields that have one (parametrize over a mapping of schema path to dataclass attribute), so a default cannot drift between the two.
     - Test that `schema_field(path)` returns one entry by dotted path and raises KeyError for an unknown path.

2. Document:
   - Module docstring for config_schema.py: the schema is the single source for `--full-config`, `config schema`, and the configuration reference docs; it mirrors `config.py`'s accepted keys and a drift test enforces the match.

3. GREEN: Write MINIMAL code to make tests pass:
   - Create src/bartleby/config_schema.py with a `ConfigField` dataclass and a module-level `CONFIG_SCHEMA` sequence covering every accepted key, plus `schema_field(path)`.
   - Reference `config.py` dataclass defaults and `theme_loader.THEME_FEATURES` directly rather than re-typing their values.

4. RED: Add drift-direction test:
   - Add a test that fails if `config.py` grows a new accepted top-level key with no schema entry (walk `_reject_unknown_top_level_keys`'s known-key set and assert each is covered). Mutation-check it by temporarily adding a fake key to the known set in the test and confirming the assertion fires.

5. GREEN: Close any gaps the drift test surfaces.

6. REFACTOR: Keep field construction in small per-section helpers mirroring `config.py`'s `_parse_*` grouping so the two files stay legible side by side.

7. Update documentation: none beyond the docstring (Step 16 writes the reference page from this schema).

8. Verify meaningful coverage of the schema and both drift directions, and run `just check`.
```

### Step 2: The comment-preserving YAML writer and the full-config renderer

**NOTE**: New module `src/bartleby/config_edit.py`, backed by `ruamel.yaml` (add `ruamel.yaml` to `pyproject.toml` dependencies and `uv lock`). Two jobs that `config set`, `enable`, and `--full-config` all call: set one dotted key in an existing `bartleby.yml` while keeping its comments and key order, and render a complete annotated config from `CONFIG_SCHEMA` with every option at its default and a one-line comment. Values round-trip through `ruamel.yaml`'s round-trip loader so existing comments survive.

```text
1. RED: Write writer tests first:
   - Create tests/test_config_edit.py:
     - Test that `set_key(text, "site.title", "New")` on a YAML string with a comment above `site:` returns text with the comment intact and the value changed.
     - Test that setting a dotted path that does not exist yet creates the intermediate mappings.
     - Test that setting a key leaves sibling keys and their inline comments untouched.
     - Test that `render_full_config(CONFIG_SCHEMA)` emits valid YAML where every schema field appears at its default with its one-line description as a trailing or leading comment, and that re-parsing it through `config.load_config` succeeds with no error.
     - Test that a scalar value passed as a Python str/int/bool is emitted with the right YAML type (no quoting of a bool).

2. Document:
   - config_edit.py module docstring: the two entry points, the ruamel round-trip guarantee, and that it is the one writer shared by `config set`, `enable`, and `--full-config`.

3. GREEN: Write MINIMAL code to make tests pass:
   - Add `ruamel.yaml` to pyproject.toml; `uv lock`.
   - Create src/bartleby/config_edit.py with `set_key(text, dotted_path, value) -> str` and `render_full_config(schema) -> str` using a single shared `ruamel.yaml.YAML(typ="rt")` instance.

4. RED: Add integration test:
   - Round-trip: start from the scaffold `bartleby.yml`, `set_key` a nested value, assert the file still parses through `config.load_config` and the one value changed.

5. GREEN: Wire minimally.

6. REFACTOR: Factor the dotted-path walk used by both `set_key` and (later) `config get` into one helper in config_edit.py.

7. Update documentation: CHANGELOG.md Unreleased: new `ruamel.yaml` dependency and why (comment-preserving config writes).

8. Verify meaningful coverage of comment preservation and full-config round-trip, and run `just check`.
```

---

## Section 2: CLI configuration surface

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: uv run ruff check --output-format=json src/ tests/, uv run mypy src/

Everything here is logic a bug can hide in (override parsing, provenance, YAML value coercion), so every step is TDD. No step reads environment variables; that layer is Deferred.

### Step 3: The `--set key.path=value` override layer

**NOTE**: New overrides applied to the raw parsed mapping before `config._parse_config` runs, so they go through the same validator. `--set` is repeatable and lands on `build`, `serve`, and `validate`. Values parse as YAML (`42` is an int, `true` a bool, `[a, b]` a list), and any resulting validation error is labeled as coming from `--set`, not from the file. Put the override logic in `config.py` next to `load_config` so the file and the overrides share one validation path.

```text
1. RED: Write override tests first:
   - In tests/test_config.py:
     - Test that `apply_overrides(raw, ["site.title=Hi", "dev_server.port=9000"])` sets a string and an int (YAML-typed), returning the mutated mapping.
     - Test that an override with no `=` raises ConfigError naming `--set` and the bad token.
     - Test that `site.url=` with an empty value, or a value that fails the real validator (e.g. `dev_server.port=notaport`), raises ConfigError whose source is labeled `--set`.
     - Test that a dotted path creates intermediate mappings and that a repeated `--set` on the same key keeps the last.
     - Test that `load_config(path, overrides=[...])` applies overrides and then validates, so an override that violates a rule fails exactly as a file value would.

2. Document:
   - Docstring on `apply_overrides` and the `overrides` parameter of `load_config`: YAML value parsing, dotted paths, and the `--set` error source label.

3. GREEN: Write MINIMAL code to make tests pass:
   - config.py: `apply_overrides(raw, sets)` parsing each value with `yaml.safe_load`; thread an `overrides: list[str] | None` param through `load_config` applied before `_parse_config`.

4. RED: Add CLI integration tests:
   - In tests/test_cli.py: add `--set` (action append) to `build`, `serve`, and `validate`; assert `build --set site.title=Z` builds with the overridden title and that a bad `--set` exits non-zero with the `--set`-labeled message.

5. GREEN: Wire `--set` into the three subparsers and pass `args.set` into `load_config`.

6. REFACTOR: Share the dotted-path walk with config_edit.py's helper from Step 2.

7. Update documentation: none here (Step 16 documents `--set`).

8. Verify meaningful coverage of value typing and error labeling, and run `just check`.
```

### Step 4: `--base-url` and resolved-config provenance

**NOTE**: `--base-url` is the one new dedicated flag (overrides `site.url` for one run); `--port`, `--host`, `--include-drafts`, and `--strict` already exist on their commands and are not re-added. Provenance is needed by `config show` in Step 5: for each resolved value, where it came from (default, file, or `--set`). Track provenance as the config is assembled rather than reconstructing it afterward.

```text
1. RED: Write provenance and flag tests first:
   - In tests/test_config.py:
     - Test that `resolve_with_sources(path, overrides)` returns, for a set of representative keys, the value and its source: a key absent from the file reads `default`, a key in the file reads `file`, and a key given via `--set` reads `set`.
     - Test that `--base-url` maps to a `site.url` override and that provenance for `site.url` then reads `set`.
   - In tests/test_cli.py:
     - Test that `build --base-url https://x.test` renders canonical URLs against that base (assert on one absolute URL in output), and that `--base-url` is accepted on build, serve, and validate.

2. Document:
   - Docstring on `resolve_with_sources`: the three sources and how `--set` and `--base-url` map onto them.

3. GREEN: Write MINIMAL code to make tests pass:
   - config.py: `resolve_with_sources(...)` returning a mapping of dotted path to (value, source); implement by tagging the raw file keys, the override keys, and filling the rest from schema defaults.
   - cli.py: add `--base-url` to build/serve/validate, translated into a `site.url` entry in the overrides list.

4. RED: Add integration test:
   - Assert `resolve_with_sources` agrees with `load_config` on the final values for a fixture config with one file key, one default, and one `--set`.

5. GREEN: Wire minimally.

6. REFACTOR: Keep provenance tagging beside `apply_overrides` so the two stay consistent.

7. Update documentation: none here.

8. Verify meaningful coverage of all three sources and the `--base-url` mapping, and run `just check`.
```

### Step 5: The `config` command group

**NOTE**: New `config` subcommand in cli.py with four actions. `config show` prints the resolved config with each value's source (Step 4), `config get <key>` prints one value, `config set <key> <value>` validates the value then writes it into `bartleby.yml` through config_edit.py (Step 2) keeping comments, and `config schema --output json` lists every key from `CONFIG_SCHEMA` with type, default, allowed values, and description. Results go through the existing `output.py` text/JSON formatter so `--output json` is stable.

```text
1. RED: Write command tests first:
   - In tests/test_cli.py (or tests/test_config_commands.py):
     - Test that `config show` lists resolved values each tagged with its source, and `--output json` yields a stable sorted structure.
     - Test that `config get site.title` prints exactly the resolved value and that an unknown key exits non-zero with a message naming the key.
     - Test that `config set site.title "X"` writes the value into a tmp_path `bartleby.yml`, preserves a comment placed above `site:`, and that re-running it is idempotent.
     - Test that `config set` rejects a value that fails validation (e.g. `dev_server.port notaport`) without writing the file.
     - Test that `config schema --output json` contains one object per `CONFIG_SCHEMA` field with path, type, default, choices, and description.

2. Document:
   - Handler docstrings and one-sentence argparse help for each of show/get/set/schema.

3. GREEN: Write MINIMAL code to make tests pass:
   - cli.py: `config` parser with `show`, `get`, `set`, `schema` subparsers and handlers; `set` validates by loading the candidate config in memory before writing via config_edit.set_key.
   - output.py: result dataclasses for show/get/schema with `to_dict`/`to_text` like the theme command results.

4. RED: Add integration test:
   - `config set` then `config get` on the same tmp_path config returns the value just written, and `config show` marks it as `file`.

5. GREEN: Wire minimally.

6. REFACTOR: Reuse the Step 4 provenance and the Step 1 schema; do not re-derive either.

7. Update documentation: none here (Step 16).

8. Verify meaningful coverage of each action and the write-safety of `config set`, and run `just check`.
```

### Step 6: `bartleby new site --full-config`

**NOTE**: `new site` keeps writing the minimal scaffold config by default (Step 14 sets that content). `--full-config` instead writes the complete annotated config from `render_full_config(CONFIG_SCHEMA)` (Step 2). The test that every accepted option appears is the spec's explicit requirement.

```text
1. RED: Write full-config tests first:
   - In tests/test_cli.py:
     - Test that `new site <dir> --full-config` writes a `bartleby.yml` whose parsed key set covers every path in `CONFIG_SCHEMA` (assert no schema path is missing from the file).
     - Test that the generated full config parses cleanly through `config.load_config` with no error and no warning.
     - Test that each option in the generated file carries its one-line description as a comment.
     - Test that `new site <dir>` without the flag writes the minimal config and that the minimal config is a strict subset of the full one's keys.

2. Document:
   - Update `new site` argparse help to describe `--full-config` in one sentence.

3. GREEN: Write MINIMAL code to make tests pass:
   - cli.py `_cmd_new_site`: when `--full-config`, write `render_full_config(CONFIG_SCHEMA)` as `bartleby.yml` instead of the scaffold template.

4. RED: Add integration test:
   - Scaffold with `--full-config`, build the site, assert the build succeeds (the full config is valid and complete).

5. GREEN: Wire minimally.

6. REFACTOR: none expected.

7. Update documentation: none here (Step 14 covers the scaffold README; Step 16 the reference).

8. Verify the every-key test is meaningful (mutation-check by removing one schema field and confirming the test fails), and run `just check`.
```

---

## Section 3: Content types on demand

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: uv run ruff check --output-format=json src/ tests/, uv run mypy src/

Feeds already exist in `feeds.py`; this section adds the `enabled` flag, the `enable`/`disable` commands, and the correctness that an enabled type's feeds carry entries.

### Step 7: `enable` and `disable` content types

**NOTE**: Add `enabled: bool = True` to `ContentTypeConfig` and have the build skip a disabled type (no listing, no pages, no feeds). `bartleby enable <content-type> <name>` merges a blog-shaped content-type block into `bartleby.yml` through config_edit.py if it is absent, defaulting the new type's `feeds` to `[rss, atom]`, and is safe to run twice. `bartleby disable <content-type> <name>` sets `enabled: false` on that type rather than deleting it. The first argument is the shape (`blog`), the second the instance name (`tutorials`); a site may enable the same shape more than once.

```text
1. RED: Write enable/disable and skip tests first:
   - In tests/test_config.py: test that a content type with `enabled: false` parses with `enabled` False and defaults True when absent.
   - In tests/test_build.py: test that a disabled content type produces no listing page, no content pages, and no feed files, while an enabled one still does.
   - In tests/test_cli.py (or tests/test_enable.py):
     - Test that `enable blog tutorials` on a tmp_path config adds a `tutorials` content type with a blog shape and `feeds: [rss, atom]`, and that running it again changes nothing (idempotent).
     - Test that `enable blog tutorials` then `disable blog tutorials` leaves the `tutorials` block present with `enabled: false`.
     - Test that `enable` preserves existing comments in `bartleby.yml` (shared writer).

2. Document:
   - `ContentTypeConfig.enabled` docstring; handler docstrings and argparse help for `enable`/`disable`.

3. GREEN: Write MINIMAL code to make tests pass:
   - config.py: add `enabled` to `ContentTypeConfig` and parse it; build.py: skip disabled types in listing, page, and feed generation.
   - cli.py: `enable`/`disable` handlers building the content-type block and writing it via config_edit.set_key.

4. RED: Add integration test:
   - `enable blog tutorials`, add one post under the new path, build, and assert the `tutorials` listing and its feed files exist; then `disable` and assert a rebuild drops them.

5. GREEN: Wire minimally.

6. REFACTOR: Keep the blog-shaped block definition in one place reused by `enable` and by the scaffold's `--blog` (Step 14).

7. Update documentation: none here (Step 16).

8. Verify meaningful coverage of the skip path and idempotency, and run `just check`.
```

### Step 8: An enabled type's feeds carry entries, plus the combined feed

**NOTE**: The spec requires that `enable blog <name>` yields feeds that actually carry entries and that one combined site feed aggregates across enabled types, with the per-type `feeds` key as the opt-out and `site.feed` controlling the combined feed. `feeds.py` already builds both; this step proves the end-to-end result and fixes any gap (for example a disabled type leaking into the aggregate, or an enabled type with posts emitting an empty feed).

```text
1. RED: Write feed-content tests first:
   - In tests/test_feeds.py:
     - Test that for an enabled content type with two published posts, the generated RSS and Atom each contain exactly those two items with their titles and links.
     - Test that the combined site feed contains items from every enabled type with its own feeds on, and excludes a type whose `feeds` is empty (opt-out) and a disabled type.
     - Test that `site.feed.enabled: false` suppresses the combined feed while per-type feeds remain.

2. Document:
   - Note the per-type-plus-combined guarantee in feeds.py's module docstring if not already precise.

3. GREEN: Write MINIMAL code to make tests pass:
   - feeds.py / build.py: fix any gap the tests expose (disabled-type exclusion in `compute_aggregate_types`, empty-feed suppression).

4. RED: Add integration test:
   - Build a fixture site with two enabled blog-shaped types and one disabled; assert each enabled type's feed files carry its entries and the combined feed merges both enabled types only.

5. GREEN: Wire minimally.

6. REFACTOR: Reuse the published-page selection already shared across sitemap/feeds; do not add a parallel one.

7. Update documentation: none here (Step 16).

8. Verify the feeds carry real entries (assert on item count and titles, not just file presence), and run `just check`.
```

---

## Section 4: markwright integration

**Tools:**
- Skills: python:python, frontend-design:frontend-design
- MCPs: none
- Linters: uv run ruff check --output-format=json src/ tests/, uv run mypy src/

markwright 0.3.0 is a released dependency. Bartleby consumes its public config API and follows its Click-to-Load docs; no step changes markwright. Step 9 is Python (Feature); Steps 10 and 11 are theme markup and CSS (Task), with the linters above applying only where Python is touched.

### Step 9: The `markwright:` config section through markwright's public API

**NOTE**: A `markwright:` section in `bartleby.yml` has the same shape as `markwright.toml` (`enable`, `disable`, `warn`, and one option table per extension). Validate and resolve it through markwright 0.3.0's public API: `config_from_mapping(table, source)`, `selected_extensions(config)`, and `extension_configs(config, names)`. `markdown_pipeline.py` then loads the selected markwright extensions with those configs instead of the hardcoded name list. If a `markwright.toml` or a `[tool.markwright]` table in `pyproject.toml` is also present, the build warns that it was ignored and only `bartleby.yml` counts. Bartleby uses markwright's own option defaults; it does not set any.

```text
1. RED: Write markwright-config tests first:
   - In tests/test_config.py: test that a `markwright:` section parses into a raw mapping carried on the config (store the mapping; markwright owns its schema).
   - In tests/test_markdown_pipeline.py:
     - Test that with no `markwright:` section, the pipeline loads markwright's default selected extensions (assert the eight markwright extension names resolve through `selected_extensions` on an empty config).
     - Test that `markwright: {disable: [youtube]}` drops the youtube extension from the loaded set.
     - Test that an invalid markwright option raises through markwright's own `ConfigError`/`OptionError`, surfaced as a Bartleby ConfigError whose source names `bartleby.yml` and the `markwright:` key.
     - Test that `config_from_mapping` is called with the `markwright:` mapping and that `extension_configs` output is passed to Python-Markdown.
   - In tests/test_build.py: test that a `markwright.toml` next to `bartleby.yml`, or a `[tool.markwright]` table in a sibling `pyproject.toml`, emits exactly one warning naming the ignored file and does not change rendering.

2. Document:
   - markdown_pipeline.py docstring: markwright extensions and configs now come from markwright's public config API driven by the `markwright:` section; Bartleby never reimplements markwright's schema.

3. GREEN: Write MINIMAL code to make tests pass:
   - config.py: parse and carry the raw `markwright` mapping.
   - markdown_pipeline.py: build the markwright config via `config_from_mapping`, resolve names via `selected_extensions`, and pass `extension_configs` into the Markdown instance; translate markwright's config exceptions into a Bartleby ConfigError with the right source.
   - build.py: detect a present-but-ignored `markwright.toml`/`[tool.markwright]` and warn once.

4. RED: Add integration test:
   - Build a fixture with `markwright: {disable: [twitter]}`; assert a page using a twitter embed renders the raw fence (extension off) and the warning for a stray `markwright.toml` appears.

5. GREEN: Wire into build.py minimally.

6. REFACTOR: Keep the markwright-config construction in one helper in markdown_pipeline.py.

7. Update documentation: none here (Step 16).

8. Verify coverage of enable/disable, option validation via markwright, and the ignored-file warning, and run `just check`.
```

### Step 10: Click-to-load host script and styles in both themes (task)

**NOTE**: markwright 0.3.0 emits the click-to-load markup (a versioned preview with the live markup in a `<template>`) when an embed sets `load: click`; it ships no JS or CSS. Bartleby's themes ship the one script that swaps the preview for the live embed on click and the styles for the preview, following markwright's Click-to-Load docs page for the host script and provider processor calls. Script and styles live in `base` (behavior is theme-neutral) so both visual themes inherit them; per-theme CSS only skins the preview. Embeds stay eager by default; this step only adds the opt-in path.

```text
1. Scope:
   - Artifact(s): src/bartleby/themes/base/static/js/ (new click-to-load script), base template wiring to include it only when a click embed is on the page, and preview styles in base plus skinning hooks in material and scrivener.
   - Desired end state: a page with a `load: click` embed renders the preview, and clicking it swaps in the live embed using the provider calls markwright documents; a page with only eager embeds loads no extra script.

2. Tooling:
   - Skills: frontend-design:frontend-design (preview styling in both color modes)
   - MCPs: none
   - External: markwright's Click-to-Load docs page (the host-script contract); `uv run bartleby build` on a scratch site with one click embed.

3. Do the work:
   - Read markwright's Click-to-Load docs for the exact template markup and provider processor calls; write the base swap script to that contract with an ABOUTME header.
   - Include the script from base only when the page carries a click-to-load preview; style the preview in base and add material/scrivener skins.

4. Verify:
   - Build a scratch site with one eager and one click embed; grep the eager page's HTML for the live embed and the absence of the swap script, and the click page's HTML for the `<template>` preview and the swap script; exit 0, no UndefinedError.

5. Document:
   - none here (Step 14's scaffold README quickstart shows the opt-in; Step 16 documents it in reference).
```

### Step 11: Both themes style every markwright class hook (task)

**NOTE**: markwright emits class hooks for the host to style and ships no CSS by design. `material` and `scrivener` must style every hook each markwright extension emits (highlight, youtube, codepen, twitter, instagram, slideshow, image_compare, and fence output) so the feature tour renders polished in both themes and both color modes. CSS lives in the theme Tailwind sources; recompile per the theme-css workflow.

```text
1. Scope:
   - Artifact(s): src/bartleby/themes/material/tailwind.css + safelist.txt and src/bartleby/themes/scrivener/tailwind.css + safelist.txt (component classes for every markwright hook), then regenerated static/css/main.css for both.
   - Desired end state: each markwright extension's output is styled in both themes, light and dark, with no unstyled raw blocks.

2. Tooling:
   - Skills: frontend-design:frontend-design
   - MCPs: none
   - External: the enumerated markwright class hooks (read them from markwright's rendered output on a sample page); `just theme-css`; `uv run bartleby build` + browser.

3. Do the work:
   - Enumerate every class markwright emits by rendering a page that exercises all eight extensions; add component classes for each to both themes' Tailwind sources and safelists; run `just theme-css`.

4. Verify:
   - Build a sample page using all eight extensions on each theme; confirm in a browser (desktop and mobile, light and dark) that every embed and highlight block is styled; screenshots surfaced to Mason.

5. Document:
   - CHANGELOG.md: markwright class hooks styled in both bundled themes.
```

---

## Section 5: The async dev server

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: uv run ruff check --output-format=json src/ tests/, uv run mypy src/

### Step 12: Rewrite the dev server on Starlette and uvicorn with same-port reload

**NOTE**: Replace the `http.server.ThreadingHTTPServer` plus separate-WebSocket-port design in `server.py` with Starlette and uvicorn serving both the static files and the reload WebSocket on one port (after sphinx-autobuild's design). Add `starlette` and `uvicorn` to dependencies and `uv lock`. Keep the behavior the current tests pin: `is_watched`/`classify_change` event filtering stays, a full rebuild runs on every watched change, and the robustness property (an idle or preconnected socket must not stall a real request) still holds. `reload_snippet` connects to the same port now, on `RELOAD_WS_PATH`.

```text
1. RED: Write server tests first (extend tests/test_server.py):
   - Test that `reload_snippet()` now points the page at `location.host` and `RELOAD_WS_PATH` on the serving port (no separate port in the URL).
   - Test that the Starlette app serves a built file at its URL and the reload WebSocket route is mounted on the same app.
   - Test the robustness property against the Starlette/uvicorn server: an idle TCP connection held open does not block a parallel request (the same shape as the existing idle-socket test, retargeted).
   - Keep and re-run the existing `is_watched`/`classify_change` event-filter tests unchanged.

2. Document:
   - server.py module docstring and CLAUDE.md "Dev server" bullet: Starlette + uvicorn, one port for files and reload, watchdog event filter unchanged.

3. GREEN: Write MINIMAL code to make tests pass:
   - Add `starlette` and `uvicorn` to pyproject.toml; `uv lock`.
   - Rewrite server.py: a Starlette app with a static-files route and a WebSocket reload route on the same app, run by uvicorn; a watchdog observer calling the existing change classifier and broadcasting a reload; `reload_snippet` targeting the same port.
   - Remove the old `ThreadingHTTPServer` and separate-port hub code once nothing references them.

4. RED: Add integration test:
   - Start the server on an ephemeral port in a thread, fetch a built page over HTTP and open the reload WebSocket on the same port, write a content file, and assert a reload message arrives.

5. GREEN: Wire into `_cmd_serve` minimally, preserving `--host`/`--port`/`--events`/`--set`/`--base-url`.

6. REFACTOR: Keep the change classifier (`is_watched`, `classify_change`) exactly as is; only the transport changes.

7. Update documentation: CHANGELOG.md: dev server moved to Starlette and uvicorn with same-port live reload.

8. Verify the robustness property and the reload round-trip on the new server, and run `just check`.
```

---

## Section 6: Three-column docs layout

**Tools:**
- Skills: frontend-design:frontend-design, python:python
- MCPs: none
- Linters: uv run ruff check --output-format=json src/ tests/, uv run mypy src/

### Step 13: Three-column layout with fold-TOC and tabs feature flags (task)

**NOTE**: Both themes already have a sidebar, content, and TOC from the theme-system cycle. This step makes the default docs layout a true three-column shell (navigation, content, page table of contents) in Bartleby's own markup and CSS, following the Zensical and Material shape without copying it, and adds two `theme.features` flags: one folds the TOC into the left navigation (two-column), and one moves top-level sections into header tabs. Add the two new feature names to `theme_loader.THEME_FEATURES` (that part is Python, covered by the section's python tools) with a test, and gate the layout on them in both themes.

```text
1. Scope:
   - Artifact(s): theme_loader.py + tests/test_theme_loader.py (two new feature names); base layout blocks and material/scrivener `doc_layout.html` and the nav/toc partials for the three-column shell and the two flags; both themes' Tailwind sources + safelists; regenerated main.css.
   - Desired end state: a docs page shows three columns by default; enabling the fold flag collapses the TOC into the nav; enabling the tabs flag renders top-level sections as header tabs; both themes implement both flags; no shared files between material and scrivener.

2. Tooling:
   - Skills: frontend-design:frontend-design (layout and responsive behavior), python:python (the THEME_FEATURES addition)
   - MCPs: none
   - External: `/home/mmegger/Code/MasonEgger/mkdocs-material` and the Zensical reference for shape only (do not copy CSS); `just theme-css`; `uv run bartleby build docs/` + browser.

3. Do the work:
   - Add the two feature names and a test; implement the three-column shell and the two flags in both themes' templates and CSS; recompile.

4. Verify:
   - Build the docs with the default (three columns), then with each flag on, in both themes; confirm in a browser (desktop and mobile, both color modes) the columns, the fold, and the tabs behave; no feature warnings; no UndefinedError; screenshots surfaced to Mason.

5. Document:
   - CHANGELOG.md: three-column docs layout and the fold-TOC and tabs feature flags.
```

---

## Section 7: Scaffold and first-run output

**Tools:**
- Skills: python:python, frontend-design:frontend-design, content-design:tutorial-writing, content-design:style-linting
- MCPs: none
- Linters: uv run ruff check --output-format=json src/ tests/, uv run mypy src/

### Step 14: The docs-shaped scaffold and the feature tour (task)

**NOTE**: Edit `src/bartleby/scaffold/`. The default `new site` writes a docs-shaped site: a minimal `bartleby.yml` (only what the site needs to build), a home page that says what to do next, and one feature tour page showing each markwright and pymdownx feature with its source beside the result. The scaffold writes no `markwright:` section (embeds eager by default). `new site --blog` adds the blog-shaped content type using the shared block from Step 7. The README quickstart shows how to opt into click-to-load (`load: click`). Honor the writing hard rules in all scaffold prose.

```text
1. Scope:
   - Artifact(s): src/bartleby/scaffold/bartleby.yml (minimal, docs-shaped, no blog, no markwright section), src/bartleby/scaffold/content/index.md (home that says what to do next), src/bartleby/scaffold/content/<feature-tour>.md (each markwright + pymdownx feature with source beside result), src/bartleby/scaffold/README.md (quickstart including the click-to-load opt-in); cli.py `_cmd_new_site` for `--blog`.
   - Desired end state: `new site` builds a docs-shaped site with a working feature tour from a small config; `new site --blog` adds the blog type; `new site --full-config` (Step 6) still writes the complete config.

2. Tooling:
   - Skills: frontend-design:frontend-design (the tour page reads well), content-design:tutorial-writing + style-linting (home and tour prose), python:python (the `--blog` handler)
   - MCPs: none
   - External: `uv run bartleby new site`, `build`, `serve`.

3. Do the work:
   - Rewrite the scaffold files for the docs shape; author the feature tour showing each extension's source and rendered result; add `--blog` to `_cmd_new_site` reusing the Step 7 block; write the README quickstart with the click-to-load opt-in.

4. Verify:
   - `new site` then `build` exits 0 with no warnings and renders the home and tour pages; the tour page shows every markwright and pymdownx feature; `new site --blog` adds the blog type and builds; `lint` is clean.

5. Document:
   - The scaffold README is the quickstart; add any new scaffold pages to the scaffold nav.
```

### Step 15: Hugo-style first-run output for `new site` and `serve`

**NOTE**: `new site` and `serve` should print what Hugo prints: `new site` reports what was created and the next command; `serve` prints the build summary, the URL, and how to stop. The message assembly is testable logic (what files, which URL, which next command), so this is a Feature step; keep the strings going through `output.py` so `--output json` stays consistent.

```text
1. RED: Write output tests first:
   - In tests/test_cli.py:
     - Test that `new site <dir>`'s result lists the created top-level entries and names the next command (`cd <dir> && bartleby serve`), and that `--output json` carries the same as structured fields.
     - Test that the serve startup summary includes the page count, the bound URL (host and port), and the stop hint, assembled from the build result and the resolved host/port (unit-test the formatter, not a live server).

2. Document:
   - Docstrings on the new/updated output dataclasses.

3. GREEN: Write MINIMAL code to make tests pass:
   - output.py: extend `NewSiteOutput` and add a serve-startup result with `to_text`/`to_dict` carrying created entries, next command, URL, page count, and stop hint.
   - cli.py: populate them in `_cmd_new_site` and the serve startup path.

4. RED: Add integration test:
   - `new site` prints the created entries and the exact next command; assert on the text.

5. GREEN: Wire minimally.

6. REFACTOR: Reuse the resolved host/port from Step 4 rather than re-reading config.

7. Update documentation: none here (Step 16).

8. Verify the summaries carry real values (page count and URL from the build, not placeholders), and run `just check`.
```

---

## Section 8: Docs, acknowledgments, correctness, and the final gate

**Tools:**
- Skills: python:python, content-design:diataxis, content-design:tutorial-writing, content-design:style-linting
- MCPs: none
- Linters: uv run ruff check --output-format=json src/ tests/, uv run mypy src/

### Step 16: Document the config, enable, markwright, and layout surface from the schema (task)

**NOTE**: New and updated pages under `docs/content/`. The configuration reference comes from `CONFIG_SCHEMA` (the spec's one-schema rule), cross-checked by a test. Document `--set`, `--base-url`, the `config` command, `enable`/`disable`, the `markwright:` section with click-to-load, and the three-column layout with its feature flags. Honor the writing hard rules.

```text
1. Scope:
   - Artifact(s): docs/content/reference/pages/configuration.md (generated-from-schema reference), a how-to for enabling content types, a how-to for configuring markwright and click-to-load, updates to the CLI reference for `--set`/`--base-url`/`config`/`enable`/`disable`, and the three-column layout in the theme docs; docs/bartleby.yml nav; a test under tests/ that the configuration reference lists exactly the `CONFIG_SCHEMA` keys.
   - Desired end state: a newcomer can configure from the CLI, enable a blog, configure markwright and click-to-load, and pick the layout, from the docs alone; the config reference cannot drift from the schema.

2. Tooling:
   - Skills: content-design:diataxis (type per page), content-design:tutorial-writing (the how-tos), content-design:style-linting; python:python (the schema-to-docs drift test)
   - MCPs: none
   - External: `bartleby config schema --output json` as the reference source; `bartleby build docs/`, `bartleby lint docs/`.

3. Do the work:
   - Generate or hand-write the configuration reference from the schema and add a drift test tying it to `CONFIG_SCHEMA`; write the how-tos against the real commands; update the CLI reference; honor the writing hard rules.

4. Verify:
   - Build and lint docs clean; the schema-to-docs drift test passes; every flag/command/section named in the docs exists in code and vice versa (spot-check both ways).

5. Document:
   - This step is the documentation; add new pages to docs nav.
```

### Step 17: Acknowledgments and the license compatibility check (task)

**NOTE**: Create an acknowledgments file crediting anything borrowed in inspiration or code (the Zensical and Material layout shape, sphinx-autobuild's dev-server design, Hugo's first-run output shape, any icon such as the color-mode sun) and check each source's license for MIT compatibility before it stays. Confirm Zensical's license specifically and the origin of the color-mode toggle icon. Record findings; if any source is incompatible, replace the borrowed asset rather than ship it.

```text
1. Scope:
   - Artifact(s): ACKNOWLEDGMENTS.md at the repo root (and linked from README and the docs), listing each borrowed source, what was taken (inspiration vs. code vs. asset), and its license with an MIT-compatibility note.
   - Desired end state: every external inspiration or asset used in this cycle is credited and its license confirmed compatible with Bartleby's MIT license; the color-mode icon's provenance is resolved (kept with credit if compatible, replaced if not).

2. Tooling:
   - Skills: content-design:style-linting (the file's prose)
   - MCPs: none
   - External: the upstream license files for MkDocs, Material for MkDocs, Hugo, sphinx-autobuild, furo, Zensical, and the icon source; a web check for Zensical's current license and the sun icon's license.

3. Do the work:
   - Enumerate every borrowing in this cycle and the theme-system cycle's visual inspirations; record each with its license and a compatibility verdict; resolve the sun icon (credit or replace).

4. Verify:
   - Every entry names a specific source and a specific license with a compatibility verdict; no asset with an unconfirmed or incompatible license remains in the tree (grep the themes for the icon in question and confirm its status).

5. Document:
   - ACKNOWLEDGMENTS.md is the deliverable; link it from README.md and the docs.
```

### Step 18: Correctness sweep for first-run claims

**NOTE**: The spec's rule that anything the scaffold or docs claim works, works. Prove the load-bearing claims with tests: the scaffold and docs feeds carry entries, highlighted code has the CSS that styles it, and the feature tour's every feature renders. This is the honesty gate before the final gate; it is Feature because the checks are real assertions a regression can break.

```text
1. RED: Write claim tests first:
   - In tests/test_scaffold.py (or the scaffold test module):
     - Test that building `new site --blog` with the sample post yields a blog feed whose RSS and Atom each carry the sample post as an item.
     - Test that the built feature tour page contains the rendered output class for every markwright and pymdownx feature it claims to show (enumerate the features and assert each hook class is present in the HTML).
     - Test that highlighted code in the built output references the highlight CSS (the Pygments/pymdownx highlight classes appear in both the HTML and the compiled theme CSS).
   - In the docs test module: test that the docs build's feeds carry entries for each enabled type.

2. Document:
   - none beyond the tests.

3. GREEN: Fix any claim the tests expose as false (a missing feed entry, an unstyled highlight, a tour feature that does not render).

4. RED: Add integration test:
   - A single end-to-end test that scaffolds, builds, and asserts the home links resolve, the tour renders every feature, and the feeds carry entries.

5. GREEN: Wire minimally.

6. REFACTOR: Reuse the feed-content assertions from Step 8 rather than duplicating them.

7. Update documentation: none.

8. Verify every first-run claim has a test that would fail if the claim broke, and run `just check`.
```

### Step 19: Final gate for Goal 8 (task)

**NOTE**: The acceptance gate for Goal 8. Bartleby stays on 0.1.x (no version bump). Prove the Goal 8 success criteria from a clean environment.

```text
1. Scope:
   - Artifact(s): CHANGELOG.md (finalize the Unreleased entry for the whole cycle), README.md (first-run section if it drifted); no version bump.
   - Desired end state: every Goal 8 success criterion in spec.md holds and is demonstrated from a clean install.

2. Tooling:
   - Skills: python:python
   - MCPs: none
   - External: `just check`; a clean-venv install of the built wheel; `bartleby new site`, `build`, `serve` in the scratchpad; browser for the layout and tour.

3. Do the work:
   - `just check` green.
   - Build the wheel, install into a fresh venv, run `new site` then `serve`, and confirm a three-column docs site with a working feature tour from a small `bartleby.yml`; confirm `--full-config` lists every accepted option; confirm `enable blog <name>` adds a blog whose RSS and Atom feeds carry entries; confirm the wheel bundles the scaffold and both themes' assets.
   - Walk every Goal 8 success criterion in spec.md with evidence per line.

4. Verify:
   - `just check` green AND the clean-env install reproduces the three-column site, the tour, `--full-config`, and working `enable` feeds. Produce the success-criteria checklist with evidence for Mason, who holds the governing bar.

5. Document:
   - Finalize CHANGELOG.md and README.md.
```

---

## Implementation Guidelines

- **TDD for Feature steps** (1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 15, 18): failing test first, minimal code, refactor; test Bartleby's logic, never the framework or markwright's own schema.
- **Task steps** (10, 11, 13, 14, 16, 17, 19) carry literal Scope/Tooling/Do/Verify/Document instructions; markup and docs steps verify by building a site and grepping output, since no HTML linter is in the gate.
- **One schema, no drift.** `CONFIG_SCHEMA` is the single source for `--full-config`, `config schema`, and the config reference docs; each consumer has a drift test tying it back to the schema.
- **markwright is consumed, not changed.** Use only its public API (`config_from_mapping`, `selected_extensions`, `extension_configs`) and its documented click-to-load contract. No step edits markwright.
- **The comment-preserving writer is shared.** `config set`, `enable`, and `--full-config` all go through config_edit.py; do not add a second YAML writer.
- **No environment-variable config.** `--set` is the only override layer this cycle (spec.md Deferred).
- **The gate is `just check`.** Hold every diff to it; `uv run pytest` alone skips ruff, mypy, and the smoke test.
- **Code style (CLAUDE.md):** ABOUTME headers, strict typing (`Any` only at the YAML boundary), single responsibility, validate at boundaries only, no impossible-scenario handling, evergreen names, preserve comments. Load the `python` skill before writing Python.
- **Writing hard rules** apply to docs, comments, commit messages, CHANGELOG, and the acknowledgments file: no em or en dashes, no banned words, straight quotes, one sentence per line in committed Markdown, Title Case headings.
- **Scope discipline.** No migrate command, no fourth theme, no fountain, no multi-site, no env-var config, no skill-gen rework, no 0.2.0 work. Record anything beyond this plan in spec.md's Deferred list.
- **Git workflow (CLAUDE.md):** never commit to main; work on `v0.1.1`. Commit only when Mason asks: session-summary, then commit-message, then `git commit -S -F commit-msg.md`, then `/init`. `commit-msg.md` stays gitignored, never staged.

## Success Metrics

The plan is done when all Goal 8 success criteria in spec.md hold:

1. `bartleby new site` then `bartleby serve` gives a three-column docs site with a working feature tour from a small `bartleby.yml` (Steps 13, 14, 15).
2. `bartleby new site --full-config` lists every accepted option, enforced by a test (Steps 1, 2, 6).
3. Config is reachable from the CLI without one flag per option: `--set`, `--base-url`, and `config show|get|set|schema`, all from the one schema (Steps 3, 4, 5).
4. `bartleby enable blog <name>` adds a blog whose RSS and Atom feeds carry entries, and `disable` turns it off through an `enabled` flag; same shape can be enabled more than once (Steps 7, 8).
5. markwright is fully integrated: the `markwright:` section validates through markwright's public API, a stray `markwright.toml` warns, both themes style every class hook, embeds are eager by default, and click-to-load is an opt-in that works (Steps 9, 10, 11).
6. The dev server is async on Starlette and uvicorn with same-port live reload, and an idle socket does not stall a request (Step 12).
7. Anything the scaffold or docs claim works, works, each with a test; borrowed inspiration and assets are credited and license-checked (Steps 16, 17, 18).
8. `just check` is green and `bartleby-ssg` reproduces the first-run experience from a clean install; Bartleby stays on 0.1.x (Step 19). Mason is willing to send it to people. Governing bar.
