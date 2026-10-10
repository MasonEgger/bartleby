# Bartleby 0.1.x Stabilization TODO: Theme System and Showcase

Mirrors plan.md. Check sub-steps as execute-plan completes them; a step is done when all its sub-steps are checked.

## Section 1: Theme system core

### Step 1: Theme manifest and resolver (feature)
- [x] 1. RED: fixtures (parent, child extends parent, cyclic-a/b) + tests for manifest parse, missing/invalid manifest, leaf-first chain, cycle error, extends-bundled, bad path, package entry point
- [x] 2. Document: theme_loader.py module docstring (manifest schema, three sources, chain semantics)
- [x] 3. GREEN: theme_loader.py (ThemeManifest, ThemeLayer, ResolvedTheme, ThemeError, load_manifest, resolve_theme) + themes/__init__.py
- [x] 4. RED: bundled-name resolution tests (xfail until Step 6/11)
- [x] 5. GREEN: wire minimally
- [x] 6. REFACTOR: per-field manifest helpers in config.py style
- [x] 7. Document: none beyond docstring
- [x] 8. Verify: coverage + `just check`

### Step 2: Resolution chain drives templates, static assets, and icons (feature)
- [x] 1. RED: cascade tests (search bases order, parent fallback, child wins, overrides/ beats all), static copy child-wins, icon lookup leaf-first
- [x] 2. Document: docstrings for template_search_bases, resolve_template_name, icon lookup
- [x] 3. GREEN: templates.py takes ResolvedTheme; icons.py chain-aware; build.py resolves once + copies static root-first
- [x] 4. RED: integration build on theme.path fixture child
- [x] 5. GREEN: wire into build.py
- [x] 6. REFACTOR: drop get_theme_templates_dir/get_theme_static_dir
- [x] 7. Document: none beyond docstrings
- [x] 8. Verify: coverage + `just check`

### Step 3: Native theme config vocabulary and the feature contract (feature)
- [x] 1. RED: one-of name/path/package; native feature names only; tokens map; logo/favicon/icon_packs; old mkdocs names -> ConfigError with hint; unimplemented-feature warning tests
- [x] 2. Document: ThemeConfig docstrings + THEME_FEATURES constant docstring
- [x] 3. GREEN: config.py new fields + validation + migration-hint error; build.py warning; templates.py fed native list
- [x] 4. RED: CLI integration for breaking-change error + warning text
- [x] 5. GREEN: wire CLI output
- [x] 6. REFACTOR: THEME_FEATURES and manifest validation adjacent
- [x] 7. Document: CHANGELOG breaking-change table
- [x] 8. Verify: coverage + `just check`

### Step 4: Per-theme Tailwind compile and token emission (feature)
- [x] 1. RED: leaf-first --config/--input with parent fallback; --content over all layers + project dirs; tokens -> .bartleby/tokens.css with --bb-* vars; empty tokens file present
- [x] 2. Document: compile_theme_css docstring
- [x] 3. GREEN: theme_compile.py takes ResolvedTheme + tokens; cli.py passes resolved theme
- [x] 4. RED: skip-guarded real-binary compile of base
- [x] 5. GREEN: wire minimally
- [x] 6. REFACTOR: shared "nearest layer providing path" helper
- [x] 7. Document: Justfile theme-css loops over bundled themes
- [x] 8. Verify: coverage + `just check`

### Step 5: `bartleby theme eject` and `bartleby theme inspect` (feature)
- [x] 1. RED: eject flattens chain leaf-wins with no `extends`; refuses overwrite without --force; --to honored; inspect lists provider layer + overrides shadowing; --format json stable
- [x] 2. Document: handler docstrings + argparse help
- [x] 3. GREEN: cli.py subparsers; theme_loader flatten_chain + inspect_chain result dataclasses
- [x] 4. RED: e2e eject material -> theme.path -> edit partial -> build shows edit (permanent test)
- [x] 5. GREEN: wire minimally
- [x] 6. REFACTOR: share per-file layer walk with Step 4 helper
- [x] 7. Document: none here
- [x] 8. Verify: coverage + `just check`

### Step 6: Split the existing theme into bundled `base` and `material` (task)
- [x] 1. Scope: themes/base + themes/material layout; delete theme/; update imports
- [x] 2. Tooling: python; pytest, just check
- [x] 3. Do: git mv into layout; write both theme.yml; replace Material-named feature() calls with native; un-xfail base/material tests; docs/bartleby.yml -> material temporarily
- [x] 4. Verify: `just check` green; `bartleby build docs/` exits 0
- [x] 5. Document: spec.md Component boundaries theme block

## Section 2: The `material` theme

### Step 7: Material design sources (task)
- [x] 1. Scope: themes/material/{tailwind.config.js,tailwind.css,safelist.txt}
- [x] 2. Tooling: frontend-design; theme compile on scratch project
- [x] 3. Do: dark mode on [data-theme], Material-faithful palette/type via --bb-* tokens, typography plugin, component + layout classes
- [x] 4. Verify: compile exits 0 with prose + component rules
- [x] 5. Document: config comment block

### Step 8: Material shell and content templates (task)
- [x] 1. Scope: header, nav, footer, page, post, list under themes/material
- [x] 2. Tooling: frontend-design; build docs
- [x] 3. Do: classes, base blocks, prose wrappers, layout-prose/layout-docs; preserve variables + toggle
- [x] 4. Verify: prose wrapper + header classes + excerpts present; exit 0; no UndefinedError
- [x] 5. Document: none

### Step 9: Material docs layout: sidebar, TOC, tabs (task)
- [x] 1. Scope: nav.html, sidebar.html, toc.html, page.html; navigation.py index pointer if needed
- [x] 2. Tooling: frontend-design, python (navigation.py only); build docs with nav.sidebar on
- [x] 3. Do: implement partials + blocks; update material theme.yml features
- [x] 4. Verify: tabs + sidebar + TOC on concept page; no sidebar on listing; no warnings
- [x] 5. Document: none

### Step 10: Material taxonomy, 404, search, and interactive partials (task)
- [ ] 1. Scope: taxonomy, taxonomy_index, 404, search, back_to_top, code_copy
- [ ] 2. Tooling: frontend-design; build docs
- [ ] 3. Do: classes; search.highlight gated; preserve Alpine/HTMX; manifest gains search.highlight
- [ ] 4. Verify: pages styled; highlight works; exit 0; no UndefinedError
- [ ] 5. Document: none

## Section 3: The `scrivener` theme

### Step 11: Scrivener design direction and sources (task)
- [ ] 1. Scope: themes/scrivener/{theme.yml,tailwind.config.js,tailwind.css,safelist.txt}; default theme -> scrivener; un-xfail test
- [ ] 2. Tooling: frontend-design (real design effort here)
- [ ] 3. Do: write sources; present direction (palette, type, three adjectives) for Mason
- [ ] 4. Verify: compile exits 0; `just check` green after default flip
- [ ] 5. Document: design-direction comment block

### Step 12: Scrivener shell and content templates (task)
- [ ] 1. Scope: header, nav, footer, page, post, list under themes/scrivener
- [ ] 2. Tooling: frontend-design; build scratch scaffold on scrivener
- [ ] 3. Do: implement against base blocks; preserve variables + toggle
- [ ] 4. Verify: home/post/listing carry classes + prose; exit 0; no UndefinedError
- [ ] 5. Document: none

### Step 13: Scrivener docs layout: sidebar, TOC, tabs (task)
- [ ] 1. Scope: nav.html, sidebar.html, toc.html, page.html under themes/scrivener
- [ ] 2. Tooling: frontend-design; build docs on scrivener
- [ ] 3. Do: implement; no shared files with material
- [ ] 4. Verify: tabs + sidebar + TOC; no sidebar on listing; no warnings
- [ ] 5. Document: none

### Step 14: Scrivener taxonomy, 404, search, and interactive partials (task)
- [ ] 1. Scope: taxonomy, taxonomy_index, 404, search, back_to_top, code_copy
- [ ] 2. Tooling: frontend-design; build docs
- [ ] 3. Do: implement incl. search.highlight; preserve attributes
- [ ] 4. Verify: styled; highlight works; exit 0; no UndefinedError
- [ ] 5. Document: none

## Section 4: Compile, ship, and browser-verify both themes

### Step 15: Regenerate, ship, and visually verify `material` and `scrivener` (task)
- [ ] 1. Scope: both themes' static/css/main.css regenerated + committed; source fixes
- [ ] 2. Tooling: frontend-design, python; just theme-css, new/build/serve, run/claude-in-chrome
- [ ] 3. Do: regenerate; scaffold on each theme + docs on scrivener; screenshot 6 page types x 2 modes x 2 widths per theme; eject -> edit -> build -> inspect story; fix + recompile
- [ ] 4. Verify: `just check` green AND screenshots polished AND eject/inspect works; surface to Mason
- [ ] 5. Document: CHANGELOG (system, three themes, eject/inspect, breaking config)

## Section 5: Theme docs and the docs showcase

### Step 16: Catalog every docs rendering defect (task)
- [ ] 1. Scope: inventory in scratchpad
- [ ] 2. Tooling: diataxis, style-linting; build/lint/serve
- [ ] 3. Do: build + lint; walk pages; classify by Diataxis; flag old-config content
- [ ] 4. Verify: every entry has path + specific defect
- [ ] 5. Document: save inventory

### Step 17: Fix docs content and switch the docs to the Scrivener theme (task)
- [ ] 1. Scope: docs/content/**, docs/bartleby.yml, docs/.authors.yml
- [ ] 2. Tooling: diataxis, tutorial-writing, style-linting
- [ ] 3. Do: work inventory; reconcile nav; switch config to scrivener + native features; writing hard rules
- [ ] 4. Verify: build exits 0 no warnings AND lint clean
- [ ] 5. Document: route engine bugs to later sections

### Step 18: Write the theme-system documentation (task)
- [ ] 1. Scope: guides choose-and-customize-a-theme.md + write-a-theme.md; reference themes.md; update concepts customization-seams.md + templates.md
- [ ] 2. Tooling: diataxis, tutorial-writing, style-linting; real CLI output
- [ ] 3. Do: write against real code/manifests; worked example from a bundled theme.yml; eject-for-agents angle
- [ ] 4. Verify: build/lint clean; every flag/key in docs exists in code and vice versa
- [ ] 5. Document: add pages to docs nav

### Step 19: Visual polish pass on the docs showcase (task)
- [ ] 1. Scope: docs/content/** copy/structure; docs/bartleby.yml features
- [ ] 2. Tooling: frontend-design, diataxis; build/serve/browser
- [ ] 3. Do: review all page types incl. theme pages, both modes, both widths; tune (theme CSS frozen unless defect)
- [ ] 4. Verify: screenshots show polished showcase; surface to Mason
- [ ] 5. Document: CHANGELOG if structure changed

## Section 6: Developer experience

### Step 20: Clear, actionable error messages (feature)
- [ ] 1. RED: config/author/metadata/theme-path/build error tests (file + key/id + hint; substring assertions)
- [ ] 2. Document: error-message contracts in docstrings
- [ ] 3. GREEN: enrich raise sites incl. theme_loader.py
- [ ] 4. RED: CLI integration asserts text + non-zero exit
- [ ] 5. GREEN: wire CLI/formatter
- [ ] 6. REFACTOR: one file+key+hint helper
- [ ] 7. Document: troubleshooting note if warranted
- [ ] 8. Verify: coverage + `just check`

### Step 21: Scaffolding that builds and renders well out of the box (feature)
- [ ] 1. RED: scaffold layout; theme.name scrivener + native features in manifest; build produces outputs with no warnings
- [ ] 2. Document: quickstart matches scaffold
- [ ] 3. GREEN: adjust scaffold defaults in cli.py
- [ ] 4. RED: e2e scaffold -> build asserts scrivener classes + no UndefinedError
- [ ] 5. GREEN: wire minimally
- [ ] 6. REFACTOR: remove dead starter assets
- [ ] 7. Document: refresh installation/quickstart incl. "theme.name: material" pointer
- [ ] 8. Verify: coverage + `just check`

## Section 7: Agent surface consistency and correctness

### Step 22: Every published page has a valid Markdown variant and JSON-LD (feature)
- [ ] 1. RED: index.md per published page; JSON-LD valid with required fields; drafts excluded; parametrized over both themes
- [ ] 2. Document: per-page guarantee in llm.py
- [ ] 3. GREEN: close gaps in llm.py / base jsonld partial
- [ ] 4. RED: integration counts + parse
- [ ] 5. GREEN: wire into build.py if needed
- [ ] 6. REFACTOR: share published-page set with sitemap/feeds
- [ ] 7. Document: agent-surface reference note
- [ ] 8. Verify: coverage + `just check`

### Step 23: llms.txt, schema.json, and content-index.json are correct (feature)
- [ ] 1. RED: llms.txt/llms-full.txt; schema.json incl. theme block; content-index published only
- [ ] 2. Document: format/field contract per module
- [ ] 3. GREEN: fix defects; add theme block
- [ ] 4. RED: integration on docs fixture; theme block matches config
- [ ] 5. GREEN: wire into build.py
- [ ] 6. REFACTOR: share extraction with Step 22
- [ ] 7. Document: expand agent-surface reference
- [ ] 8. Verify: coverage + `just check`

### Step 24: Generated skills reflect the real site shape (feature)
- [ ] 1. RED: determinism; real content types/fields; taxonomies/authors; ops skill mentions theme + theme commands
- [ ] 2. Document: contract in skills.py
- [ ] 3. GREEN: fix nondeterminism/placeholders; add theme facts
- [ ] 4. RED: integration vs schema.json
- [ ] 5. GREEN: wire minimally
- [ ] 6. REFACTOR: reuse schema_introspection
- [ ] 7. Document: generated-skill contract
- [ ] 8. Verify: coverage + `just check`

## Section 8: Public interface documentation and final gate

### Step 25: Document and stabilize the public interfaces (task)
- [ ] 1. Scope: reference pages incl. themes.md + agent-output-formats
- [ ] 2. Tooling: diataxis, python; schema/inspect introspection as cross-check
- [ ] 3. Do: enumerate real surfaces; correct pages; prefer generated lists; writing hard rules
- [ ] 4. Verify: both-way cross-check; build/lint docs clean
- [ ] 5. Document: stability statement in spec.md/README

### Step 26: Final stabilization gate (task)
- [ ] 1. Scope: CHANGELOG, README, version (Mason: 0.1.x vs 0.2.0)
- [ ] 2. Tooling: python; just check; clean-venv wheel install; browser
- [ ] 3. Do: `just check`; clean install; scaffold/build/serve on scrivener then material; wheel contains three themes; walk Success criteria
- [ ] 4. Verify: just check green AND clean-env serves good-looking site on both themes; checklist with evidence for Mason
- [ ] 5. Document: finalize CHANGELOG/README
