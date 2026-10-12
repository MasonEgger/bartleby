# Bartleby Goal 8 TODO: First-Run Experience and Docs Layout

Mirrors plan.md. Check sub-steps as execute-plan completes them; a step is done when all its sub-steps are checked.

## Section 1: The config schema and the annotated writer

### Step 1: The config schema object and its drift test (feature)
- [x] 1. RED: config_schema tests (flat ordered fields with path/type/default/choices/repeatable/description; every top-level key covered; closed sets carry real allowed values; defaults equal config.py dataclass defaults; schema_field lookup + KeyError)
- [x] 2. Document: config_schema.py module docstring (single source for full-config, config schema, reference docs)
- [x] 3. GREEN: config_schema.py with ConfigField + CONFIG_SCHEMA + schema_field, referencing config.py defaults and THEME_FEATURES
- [x] 4. RED: drift-direction test (new accepted top-level key with no schema entry fails; mutation-check it)
- [x] 5. GREEN: close gaps
- [x] 6. REFACTOR: per-section field helpers mirroring config.py grouping
- [x] 7. Document: none beyond docstring
- [x] 8. Verify: coverage of schema + both drift directions + `just check`

### Step 2: The comment-preserving YAML writer and the full-config renderer (feature)
- [x] 1. RED: config_edit tests (set_key keeps comment; creates intermediate maps; siblings untouched; render_full_config emits every field at default with description comment and re-parses; scalar types correct)
- [x] 2. Document: config_edit.py docstring (two entry points, ruamel round-trip, one shared writer)
- [x] 3. GREEN: add ruamel.yaml dep + uv lock; config_edit.py set_key + render_full_config on one YAML(rt) instance
- [x] 4. RED: integration round-trip from scaffold bartleby.yml
- [x] 5. GREEN: wire minimally
- [x] 6. REFACTOR: shared dotted-path walk
- [x] 7. Document: CHANGELOG ruamel.yaml dependency
- [x] 8. Verify: comment preservation + full-config round-trip + `just check`

## Section 2: CLI configuration surface

### Step 3: The `--set key.path=value` override layer (feature)
- [x] 1. RED: apply_overrides tests (string + int YAML-typed; missing `=` error names --set; validator failure labeled --set source; dotted path creates maps, last wins; load_config overrides apply then validate)
- [x] 2. Document: apply_overrides + load_config overrides param docstring
- [x] 3. GREEN: config.py apply_overrides + overrides param threaded through load_config
- [x] 4. RED: CLI integration (--set append on build/serve/validate; overridden build; bad --set non-zero)
- [x] 5. GREEN: wire --set into three subparsers
- [x] 6. REFACTOR: share dotted-path walk with config_edit.py
- [x] 7. Document: none here
- [x] 8. Verify: value typing + error labeling coverage + `just check`

### Step 4: `--base-url` and resolved-config provenance (feature)
- [x] 1. RED: resolve_with_sources tests (default/file/set per key; --base-url maps to site.url override, provenance set); CLI --base-url renders canonical URLs, accepted on build/serve/validate
- [x] 2. Document: resolve_with_sources docstring (three sources, --set/--base-url mapping)
- [x] 3. GREEN: config.py resolve_with_sources; cli.py --base-url -> site.url override
- [x] 4. RED: integration (resolve_with_sources agrees with load_config on final values)
- [x] 5. GREEN: wire minimally
- [x] 6. REFACTOR: provenance tagging beside apply_overrides
- [x] 7. Document: none here
- [x] 8. Verify: all three sources + --base-url mapping coverage + `just check`

### Step 5: The `config` command group (feature)
- [x] 1. RED: command tests (show lists values + sources, json stable; get prints value, unknown key non-zero; set writes keeping comments, idempotent; set rejects invalid without writing; schema json one object per field)
- [x] 2. Document: show/get/set/schema handler docstrings + argparse help
- [x] 3. GREEN: cli.py config parser + handlers (set validates in memory before writing via config_edit.set_key); output.py result dataclasses
- [x] 4. RED: integration (set then get returns written value; show marks it file)
- [x] 5. GREEN: wire minimally
- [x] 6. REFACTOR: reuse Step 4 provenance + Step 1 schema
- [x] 7. Document: none here
- [x] 8. Verify: each action + config set write-safety coverage + `just check`

### Step 6: `bartleby new site --full-config` (feature)
- [x] 1. RED: full-config tests (generated file covers every CONFIG_SCHEMA path; parses with no error/warning; each option carries description comment; minimal config is a subset)
- [x] 2. Document: new site --full-config argparse help
- [x] 3. GREEN: cli.py _cmd_new_site writes render_full_config(CONFIG_SCHEMA) when --full-config
- [x] 4. RED: integration (scaffold --full-config then build succeeds)
- [x] 5. GREEN: wire minimally
- [x] 6. REFACTOR: none expected
- [x] 7. Document: none here
- [x] 8. Verify: every-key test mutation-checked + `just check`

## Section 3: Content types on demand

### Step 7: `enable` and `disable` content types (feature)
- [x] 1. RED: enabled parse (false/absent->True); build skips disabled (no listing/pages/feeds); enable adds blog-shaped type with feeds [rss,atom], idempotent; disable sets enabled false keeping block; enable preserves comments
- [x] 2. Document: ContentTypeConfig.enabled + enable/disable handler docstrings + help
- [x] 3. GREEN: config.py enabled field + parse; build.py skip disabled; cli.py enable/disable via config_edit.set_key
- [x] 4. RED: integration (enable + post + build -> listing + feeds exist; disable -> rebuild drops them)
- [x] 5. GREEN: wire minimally
- [x] 6. REFACTOR: one blog-shaped block reused by enable and scaffold --blog
- [x] 7. Document: none here
- [x] 8. Verify: skip path + idempotency coverage + `just check`

### Step 8: An enabled type's feeds carry entries, plus the combined feed (feature)
- [x] 1. RED: per-type RSS + Atom carry exactly the published items; combined feed merges enabled-with-feeds types, excludes opt-out and disabled; site.feed.enabled false suppresses combined only
- [x] 2. Document: per-type-plus-combined guarantee in feeds.py docstring
- [x] 3. GREEN: feeds.py/build.py fix gaps (disabled exclusion, empty-feed suppression)
- [x] 4. RED: integration (two enabled types + one disabled; per-type feeds carry entries; combined merges enabled only)
- [x] 5. GREEN: wire minimally
- [x] 6. REFACTOR: reuse shared published-page selection
- [x] 7. Document: none here
- [x] 8. Verify: feeds carry real entries (item count + titles) + `just check`

## Section 4: markwright integration

### Step 9: The `markwright:` config section through markwright's public API (feature)
- [x] 1. RED: markwright section parses to raw mapping; no section -> default selected extensions; disable drops one; invalid option -> Bartleby ConfigError sourced to bartleby.yml markwright key; config_from_mapping + extension_configs used; stray markwright.toml/[tool.markwright] warns once
- [x] 2. Document: markdown_pipeline.py docstring (configs via markwright public API, never reimplement schema)
- [x] 3. GREEN: config.py carry markwright mapping; markdown_pipeline.py config_from_mapping + selected_extensions + extension_configs + exception translation; build.py ignored-file warning
- [x] 4. RED: integration (disable twitter -> raw fence; stray markwright.toml warning)
- [x] 5. GREEN: wire into build.py
- [x] 6. REFACTOR: markwright-config construction in one helper
- [x] 7. Document: none here
- [x] 8. Verify: enable/disable + option validation + ignored-file warning coverage + `just check`

### Step 10: Click-to-load host script and styles in both themes (task)
- [x] 1. Scope: base click-to-load swap script + conditional include; preview styles in base + material/scrivener skins
- [x] 2. Tooling: frontend-design; markwright Click-to-Load docs; build scratch site with a click embed
- [x] 3. Do: write base swap script to markwright's contract; include only when a click preview is present; style preview
- [x] 4. Verify: eager page has live embed + no swap script; click page has <template> preview + swap script; exit 0, no UndefinedError
- [x] 5. Document: none here

### Step 11: Both themes style every markwright class hook (task)
- [ ] 1. Scope: material + scrivener tailwind.css + safelist.txt component classes for every markwright hook; regenerated main.css
- [ ] 2. Tooling: frontend-design; enumerated markwright class hooks; just theme-css; build + browser
- [ ] 3. Do: enumerate hooks from rendered output; add classes to both themes; recompile
- [ ] 4. Verify: all eight extensions styled in both themes, both modes, desktop + mobile; screenshots to Mason
- [ ] 5. Document: CHANGELOG (markwright hooks styled in both themes)

## Section 5: The async dev server

### Step 12: Rewrite the dev server on Starlette and uvicorn with same-port reload (feature)
- [ ] 1. RED: reload_snippet points at location.host + RELOAD_WS_PATH on serving port; Starlette app serves a built file + mounts reload WS on same app; robustness (idle socket does not block parallel request) on new server; existing is_watched/classify_change tests kept
- [ ] 2. Document: server.py docstring + CLAUDE.md dev-server bullet (Starlette + uvicorn, one port, event filter unchanged)
- [ ] 3. GREEN: add starlette + uvicorn deps + uv lock; rewrite server.py (static route + WS route on one app via uvicorn; watchdog -> classifier -> broadcast; reload_snippet same port); remove old ThreadingHTTPServer + separate-port hub
- [ ] 4. RED: integration (serve on ephemeral port; fetch page + open WS same port; edit file -> reload message arrives)
- [ ] 5. GREEN: wire into _cmd_serve preserving --host/--port/--events/--set/--base-url
- [ ] 6. REFACTOR: keep change classifier exactly; only transport changes
- [ ] 7. Document: CHANGELOG (dev server -> Starlette + uvicorn, same-port reload)
- [ ] 8. Verify: robustness property + reload round-trip + `just check`

## Section 6: Three-column docs layout

### Step 13: Three-column layout with fold-TOC and tabs feature flags (task)
- [ ] 1. Scope: theme_loader.py two new feature names + test; base + material/scrivener doc_layout + nav/toc partials for three columns and both flags; both themes tailwind + safelist; regenerated main.css
- [ ] 2. Tooling: frontend-design (layout + responsive), python (THEME_FEATURES); mkdocs-material/Zensical for shape only; just theme-css; build docs + browser
- [ ] 3. Do: add two features + test; implement three-column shell + fold + tabs in both themes; recompile
- [ ] 4. Verify: default three columns, fold on, tabs on, both themes, both modes, desktop + mobile; no feature warnings; no UndefinedError; screenshots to Mason
- [ ] 5. Document: CHANGELOG (three-column layout + fold/tabs flags)

## Section 7: Scaffold and first-run output

### Step 14: The docs-shaped scaffold and the feature tour (task)
- [ ] 1. Scope: scaffold bartleby.yml (minimal, docs-shaped, no blog, no markwright section); index.md (what to do next); feature tour page (each markwright + pymdownx feature, source beside result); README quickstart with click-to-load opt-in; cli.py --blog
- [ ] 2. Tooling: frontend-design, tutorial-writing, style-linting, python (--blog); new site/build/serve
- [ ] 3. Do: rewrite scaffold for docs shape; author feature tour; add --blog reusing Step 7 block; README quickstart
- [ ] 4. Verify: new site + build exits 0 no warnings, home + tour render, tour shows every feature; --blog adds blog type + builds; lint clean
- [ ] 5. Document: scaffold README quickstart; add scaffold pages to nav

### Step 15: Hugo-style first-run output for `new site` and `serve` (feature)
- [ ] 1. RED: new site result lists created entries + next command (cd <dir> && bartleby serve), json carries same; serve startup summary has page count + bound URL + stop hint (formatter unit-tested)
- [ ] 2. Document: new/updated output dataclass docstrings
- [ ] 3. GREEN: output.py extend NewSiteOutput + serve-startup result (to_text/to_dict); cli.py populate both
- [ ] 4. RED: integration (new site prints created entries + exact next command)
- [ ] 5. GREEN: wire minimally
- [ ] 6. REFACTOR: reuse resolved host/port from Step 4
- [ ] 7. Document: none here
- [ ] 8. Verify: summaries carry real values (page count + URL from build) + `just check`

## Section 8: Docs, acknowledgments, correctness, and the final gate

### Step 16: Document the config, enable, markwright, and layout surface from the schema (task)
- [ ] 1. Scope: docs configuration.md (from schema), enable how-to, markwright + click-to-load how-to, CLI reference updates (--set/--base-url/config/enable/disable), three-column layout in theme docs; docs nav; schema-to-docs drift test
- [ ] 2. Tooling: diataxis, tutorial-writing, style-linting, python (drift test); config schema --output json; build/lint docs
- [ ] 3. Do: generate/write config reference from schema + drift test; write how-tos; update CLI reference; writing hard rules
- [ ] 4. Verify: build/lint clean; drift test passes; both-way flag/command/section cross-check
- [ ] 5. Document: add new pages to docs nav

### Step 17: Acknowledgments and the license compatibility check (task)
- [ ] 1. Scope: ACKNOWLEDGMENTS.md (each borrowed source, what was taken, license, MIT-compatibility note); linked from README + docs
- [ ] 2. Tooling: style-linting; upstream license files + web check for Zensical license + sun icon license
- [ ] 3. Do: enumerate borrowings incl. theme-system visual inspirations; record license + verdict; resolve sun icon (credit or replace)
- [ ] 4. Verify: every entry names source + license + verdict; no unconfirmed/incompatible asset remains (grep themes for the icon)
- [ ] 5. Document: ACKNOWLEDGMENTS.md; link from README + docs

### Step 18: Correctness sweep for first-run claims (feature)
- [ ] 1. RED: new site --blog feed carries sample post (RSS + Atom); feature tour HTML has output class for every claimed feature; highlighted code references highlight CSS (HTML + compiled theme CSS); docs feeds carry entries per enabled type
- [ ] 2. Document: none beyond tests
- [ ] 3. GREEN: fix any false claim (missing feed entry, unstyled highlight, non-rendering tour feature)
- [ ] 4. RED: integration (scaffold + build: home links resolve, tour renders every feature, feeds carry entries)
- [ ] 5. GREEN: wire minimally
- [ ] 6. REFACTOR: reuse Step 8 feed-content assertions
- [ ] 7. Document: none
- [ ] 8. Verify: every first-run claim has a failing-if-broken test + `just check`

### Step 19: Final gate for Goal 8 (task)
- [ ] 1. Scope: CHANGELOG (finalize Unreleased), README (first-run if drifted); no version bump
- [ ] 2. Tooling: python; just check; clean-venv wheel install; browser
- [ ] 3. Do: just check green; clean install; new site + serve -> three-column + tour from small config; --full-config lists every option; enable blog feeds carry entries; wheel bundles scaffold + both themes; walk Goal 8 success criteria
- [ ] 4. Verify: just check green AND clean-env reproduces three-column site + tour + --full-config + working enable feeds; success-criteria checklist with evidence for Mason
- [ ] 5. Document: finalize CHANGELOG + README
