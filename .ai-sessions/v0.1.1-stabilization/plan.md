# Bartleby 0.1.x Stabilization Plan: Theme System and Showcase

Turn the published-but-unpresentable 0.1.0 into something Mason is willing to show people.
The engine mechanics are built and tested (spec.md "Current state").
What was missing is a real theme, and Mason's 2026-10-09 direction is that the fix is a theme *system* with a set of default themes on it, not a single hand-polished theme.
Sections 1-5 build that system, the two visual themes, and the docs on top of it.
Sections 6-8 are the rest of stabilization (DX, agent surface, public interfaces, final gate).

## Root-cause findings (verified against the tree, 2026-10-08)

1. **The shipped theme CSS is a placeholder.** `src/bartleby/theme/static/css/main.css` is 116 hand-written lines whose header reads "placeholder until Step 25 compiles full Tailwind output." It was never replaced.
2. **The compile path produces nothing useful.** `theme_compile.py` feeds the Tailwind binary the literal string `@tailwind base;@tailwind components;@tailwind utilities;` over stdin with no `--config`. No `tailwind.config.js`, no tokens, and the typography plugin is never enabled, so `prose` in `safelist.txt` generates nothing.
3. **Templates carry almost no classes.** `page.html`, `defaults/post.html`, `defaults/list.html` are bare `<article>`/`<h1>`/`<ul>`. Markdown body HTML lands in an unstyled `<article>` with no `prose` wrapper.
4. **Semantic class names have no backing rules.** Partials reference `header-inner`, `site-title`, `site-nav`, `toc-sidebar`, etc.; only the placeholder defines them.
5. **There is no docs layout.** `navigation.py` builds nested `NavItem`s (`children`, `is_section`), but `partials/nav.html` renders a flat top level and `partials/toc.html` is never included. No sidebar, no TOC.
6. **Most theme feature flags are accepted and ignored.** `config.py` recognizes about 18 mkdocs-material `theme.features` names; templates act on three.
7. **There is exactly one theme, hardwired.** `theme/__init__.py` exposes one templates dir and one static dir; `templates.py`, `icons.py` (`_icons_root`), and the CLI compile handler all point at it. `ThemeConfig` has no `name`/`path`. No manifest, no contract, no selection, no inheritance.

## Design decisions (confirmed by Mason, 2026-10-09)

- **A theme system with a set of default themes**, not one polished theme. The engine defines a theme contract; bundled themes are ordinary themes that implement it.
- **Bartleby-native theme vocabulary.** Config keys, feature names, and design tokens are on Bartleby's own terms. No alias layer to mkdocs-material names (two names per key forever would muddy a public interface). A one-shot `bartleby migrate mkdocs` command is the right answer for migrators and is **deferred** to a later cycle (spec.md Roadmap). The current Material-named `theme.features` are replaced; this is a documented breaking config change, allowed in 0.x.
- **Path and package themes are the primary mechanism, now.** A theme is a directory with a manifest. `theme.name` selects a bundled theme, `theme.path` a project directory, `theme.package` an installed entry point. Bundled themes live at `src/bartleby/themes/<name>/` in the same layout and resolve through the same loader, so they are tested as path themes.
- **Whole-system visibility beats blind overrides.** `extends:` in the manifest gives surgical overrides with the parent still fully visible; `bartleby theme eject` copies the entire resolved theme into the project so a person or a coding agent can read the whole system; `bartleby theme inspect` prints, per file, which layer provides it. The existing `overrides/` directory stays and is modeled as an anonymous project theme that extends the active theme (same resolution chain, no second mechanism).
- **Three bundled themes:** `base` (no visual opinion: the metadata partials, feed/alternate links, search wiring, the block skeleton), `material` (faithful to mkdocs-material's look, for people who want that shape), and `scrivener` (Bartleby's own identity, named for Melville's scrivener). `material` and `scrivener` both `extends: base` and are independent of each other, which is what proves the vocabulary is not Material-shaped.
- **The docs site uses the `scrivener` theme.** Material is browser-verified on a scaffold.

**Assumptions I made (flag if wrong):**
- The Bartleby-original theme is named `scrivener` (Mason, 2026-10-09), after Bartleby the Scrivener.
- The default theme for a fresh scaffold is `scrivener`; `material` is opt-in.
- The manifest is `theme.yml` (YAML, matching `bartleby.yml` and `.authors.yml`, parsed in the project's YAML-backed-module style).
- Whether the breaking config change ships as 0.1.x or justifies 0.2.0 is Mason's call; the plan is version-agnostic.

## Spec fences honored

- **Non-goals (spec.md):** no step touches build speed, async/incremental builds, dynamic/CMS features, hosting/deployment, or a plugin marketplace. A theme registry/marketplace is explicitly NOT built; `theme.package` is a plain entry point, the same seam plugins already use.
- **Deferred (spec.md Roadmap, added 2026-10-09):** the mkdocs migration command and additional bundled themes beyond the three above are not implemented here.
- **Goal 7 (fountain-py)** stays post-stabilization.

## Current Status

Legend: [ ] not started, [~] in progress, [x] complete.

- [ ] Section 1: Theme system core (Steps 1-6)
- [ ] Section 2: The `material` theme (Steps 7-10)
- [ ] Section 3: The `scrivener` theme (Steps 11-14)
- [ ] Section 4: Compile, ship, and browser-verify both themes (Step 15)
- [ ] Section 5: Theme docs and the docs showcase (Steps 16-19)
- [ ] Section 6: Developer experience (Steps 20-21)
- [ ] Section 7: Agent surface consistency and correctness (Steps 22-24)
- [ ] Section 8: Public interface documentation and final gate (Steps 25-26)

---

## Section 1: Theme system core

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: uv run ruff check --output-format=json src/ tests/, uv run mypy src/

Everything here is Python with hidden-bug potential, so every step is TDD. The bundled themes are exercised through path-theme fixtures under `tests/fixtures/themes/`, per Mason's direction that defaults are tested the way user themes are.

### Step 1: Theme manifest and resolver

**NOTE**: New module `src/bartleby/theme_loader.py` (the bundled-theme data lives in a `src/bartleby/themes/` package, so the module cannot be named `themes.py`). Follow the YAML-backed-module skeleton in CLAUDE.md (`from __future__ import annotations`, `TYPE_CHECKING` block, `Any` at the YAML boundary narrowed by `isinstance`, `@dataclass(slots=True)`, a `ThemeError` exception). Copy the entry-point discovery pattern from `plugins.py` (`importlib.metadata.entry_points(group=...)`) for packaged themes under a new group `bartleby.themes`.

```text
1. RED: Write resolver tests first:
   - Create tests/fixtures/themes/parent/theme.yml, tests/fixtures/themes/child/theme.yml (extends: parent), and tests/fixtures/themes/cyclic-a / cyclic-b (each extends the other), each with a templates/ dir holding one distinct file.
   - Create tests/test_theme_loader.py:
     - Test that loading a theme dir parses name, version, description, extends, and features from theme.yml into a ThemeManifest dataclass.
     - Test that a missing theme.yml, or one missing `name`, raises ThemeError naming the directory and the key.
     - Test that resolving `child` yields a chain [child, parent] leaf-first.
     - Test that resolving a cyclic extends raises ThemeError naming both themes.
     - Test that `extends` naming a bundled theme (e.g. `base`) resolves to `src/bartleby/themes/base`.
     - Test that resolve-by-path with a nonexistent directory raises ThemeError naming the path.
     - Test that resolve-by-package consults the `bartleby.themes` entry-point group (monkeypatch `importlib.metadata.entry_points`) and raises ThemeError naming the package when absent.

2. Document:
   - Module docstring for theme_loader.py stating the manifest schema, the three resolution sources (name -> bundled, path -> project dir, package -> entry point), and the leaf-first chain semantics.

3. GREEN: Write MINIMAL code to make tests pass:
   - Create src/bartleby/theme_loader.py with ThemeManifest, ThemeLayer (name, root: Path, manifest), ResolvedTheme (chain: list[ThemeLayer], with helpers `templates_dirs()`, `static_dirs()`, `icons_dirs()` returning leaf-first lists of existing dirs), ThemeError, `load_manifest(root)`, `resolve_theme(name|path|package, project_dir)`.
   - Create src/bartleby/themes/__init__.py (ABOUTME header; exposes `bundled_theme_root(name) -> Path`).

4. RED: Add integration tests:
   - Test that `resolve_theme` for each bundled name that will exist after Step 6 (`base`, `material`, `scrivener`) succeeds once those dirs exist; mark xfail until Step 6 lands, then un-xfail there.

5. GREEN: Wire minimally (no further production code expected).

6. REFACTOR: Keep manifest parsing in per-field helpers mirroring config.py's style.

7. Update documentation: none beyond the docstring (Step 18 writes the theme-author docs).

8. Verify meaningful coverage of resolution and error paths and run `just check`.
```

### Step 2: Resolution chain drives templates, static assets, and icons

**NOTE**: Today `templates.py` calls `get_theme_templates_dir()`, `icons.py` hardcodes `_icons_root()` to `theme/icons`, and `build.py` copies one theme static dir via `assets.copy_static_files`. All three must consume a `ResolvedTheme` chain. Cascade order becomes: project `overrides/` -> project `templates/`, `partials/`, `shortcodes/` -> each theme layer leaf-first. For static and icons, copy/search root-first so the child layer wins on collisions. Do not change `overrides/` semantics for users; it is simply the first layer.

```text
1. RED: Write cascade tests first:
   - In tests/test_templates.py:
     - Test that `template_search_bases(project_dir, resolved_theme)` returns project dirs first, then the chain's templates dirs leaf-first.
     - Test that `resolve_template_name` finds a template provided only by the parent layer when the child does not override it, and prefers the child's copy when both provide it.
     - Test that a project `overrides/` file still beats every theme layer.
   - In tests/test_assets.py:
     - Test that copying static for a [child, parent] chain yields the parent's unique files, the child's unique files, and the child's version of a shared path.
   - In tests/test_icons.py:
     - Test that icon lookup searches the chain's icons dirs leaf-first and returns the child's icon on collision.

2. Document:
   - Update the docstrings of `template_search_bases`, `resolve_template_name`, and `_icons_root`'s replacement to describe the chain.

3. GREEN: Write MINIMAL code to make tests pass:
   - templates.py: accept a ResolvedTheme (threaded from build.py) instead of calling get_theme_templates_dir().
   - icons.py: replace `_icons_root()` with a chain-aware lookup taking the icons dirs list.
   - build.py: resolve the theme once from config (Step 3 adds the config keys; until then resolve the bundled default) and copy each layer's static dir root-first.

4. RED: Add integration tests:
   - Build a fixture site whose config points `theme.path` at tests/fixtures/themes/child and assert the rendered page used the child's template and the output contains the parent's static file.

5. GREEN: Wire into build.py minimally.

6. REFACTOR: Remove `get_theme_templates_dir` / `get_theme_static_dir` from `theme/__init__.py` once nothing imports them (the package itself is deleted in Step 6).

7. Update documentation: none beyond docstrings.

8. Verify meaningful coverage and run `just check`.
```

### Step 3: Native theme config vocabulary and the feature contract

**NOTE**: `ThemeConfig` in `config.py` currently has `palette`, `color_mode`, `features` (mkdocs names), `icon_packs`, `logo`, `favicon`, `font`. Replace with Bartleby-native keys. Unknown feature names are a `ConfigError`; a feature enabled in config but absent from the active theme's manifest `features` list is a build warning (the theme contract decided earlier). Define the native feature names once, in theme_loader.py or config.py, and import everywhere.

```text
1. RED: Write config and contract tests first:
   - In tests/test_config.py:
     - Test that `theme:` accepts exactly one of `name`, `path`, `package`; two at once raises ConfigError naming the keys; none defaults to name = the bundled default theme.
     - Test that `theme.features` accepts only the native names (`search`, `search.highlight`, `nav.tabs`, `nav.sidebar`, `nav.section-index`, `nav.back-to-top`, `content.code.copy`, `color-mode.toggle`) and rejects an unknown name with ConfigError naming the key path and the bad value.
     - Test that `theme.tokens` parses a flat map of dotted token names (`color.primary`, `color.accent`, `font.text`, `font.code`, `radius`, ...) to strings, rejecting non-string values.
     - Test that `logo`, `favicon`, and `icon_packs` still parse.
     - Test that the old mkdocs-style names (`navigation.tabs`, `palette`, `font`) produce a ConfigError whose message points to the native replacement (actionable breaking-change error).
   - In tests/test_build.py:
     - Test that an enabled feature absent from the active theme manifest emits exactly one warning naming the feature and the theme.
     - Test that fully implemented features emit no warning and that an unimplemented one does not fail the build.

2. Document:
   - config.py docstrings for the new ThemeConfig fields; a single `THEME_FEATURES` constant with a docstring listing each name and what it means.

3. GREEN: Write MINIMAL code to make tests pass:
   - config.py: new ThemeConfig fields (`name`, `path`, `package`, `features`, `tokens`, `color_mode`, `icon_packs`, `logo`, `favicon`), the native feature set, the one-of validation, and the migration-hint error for old names.
   - build.py: after resolving the theme, compute enabled-minus-manifest and warn through the existing output path.
   - templates.py: `make_feature_checker` unchanged in behavior, fed the native list.

4. RED: Add integration tests:
   - Drive the breaking-change error and the unimplemented-feature warning through the CLI and assert the user-facing text.

5. GREEN: Wire CLI output minimally.

6. REFACTOR: Keep THEME_FEATURES and the manifest `features` validation adjacent so they are maintained together.

7. Update documentation:
   - CHANGELOG.md: breaking config change entry with the old -> new name table.

8. Verify meaningful coverage and run `just check`.
```

### Step 4: Per-theme Tailwind compile and token emission

**NOTE**: `compile_theme_css` in `theme_compile.py` must compile the *resolved theme*: the input CSS and `tailwind.config.js` come from the nearest layer that has them (leaf-first), content globs cover every layer's templates plus the project dirs, and `theme.tokens` from config are emitted as CSS custom properties (`--bb-<token-with-dashes>`) in a generated file the input CSS imports, so a user can recolor without touching the theme. The Justfile `theme-css` recipe compiles the shipped `main.css` for every bundled theme.

```text
1. RED: Write compile tests first:
   - In tests/test_theme_compile.py:
     - Test that the command uses `--config` and `--input` from the leaf layer when it has them, and falls back to the parent's when the leaf does not (fixture child without tailwind sources extending a parent with them).
     - Test that `--content` includes every chain layer's templates glob plus the project override dirs, and no longer feeds the inline directive string over stdin.
     - Test that `theme.tokens` {"color.primary": "#123456"} produces a tokens CSS file containing `--bb-color-primary: #123456;` and that the compile input references it.
     - Test that an empty tokens map produces an empty-but-present tokens file (the input CSS import must not fail).
   - Monkeypatch subprocess.run; do not run a real binary in unit tests.

2. Document:
   - compile_theme_css docstring: chain-aware source resolution and token emission.

3. GREEN: Write MINIMAL code to make tests pass:
   - theme_compile.py: take a ResolvedTheme and the tokens map; resolve sources leaf-first; write `<project>/.bartleby/tokens.css`; build the arg list.
   - cli.py `_cmd_theme_compile`: resolve the theme from config and pass it.

4. RED: Add integration tests:
   - Skip-guarded real-binary test: compile the `base` bundled theme and assert non-empty output.

5. GREEN: Wire minimally.

6. REFACTOR: Single helper for "nearest layer providing <relative path>" shared by templates/static/tailwind lookups.

7. Update documentation:
   - Justfile: `theme-css` loops over `src/bartleby/themes/*/` compiling each theme's `static/css/main.css` with its own config/input; update the recipe comment.

8. Verify meaningful coverage and run `just check`.
```

### Step 5: `bartleby theme eject` and `bartleby theme inspect`

**NOTE**: These two commands are the answer to the blind-override problem. `eject` copies the resolved chain, flattened leaf-wins, into `./themes/<name>/` with a manifest that no longer `extends`, so the whole system is in one readable directory; it prints the `theme.path` line to put in `bartleby.yml`. `inspect` lists every template, static, and icon file in the resolved theme with the layer that provides it (and whether a project `overrides/` shadows it), in text and JSON via the `output.py` formatter pattern. Both are agent-facing as much as human-facing: JSON output must be stable.

```text
1. RED: Write command tests first:
   - In tests/test_cli.py (or tests/test_theme_commands.py):
     - Test that `theme eject` on the [child, parent] fixture writes ./themes/child/ containing the parent's unique files, the child's files, the child's version of shared paths, and a theme.yml with no `extends`.
     - Test that `theme eject` refuses to overwrite an existing target dir without `--force`, with an error naming the dir.
     - Test that `theme eject --to <dir>` honors the destination.
     - Test that `theme inspect` output lists each file with its providing layer, marks a file shadowed by project overrides/, and that `--format json` yields a stable, sorted structure.

2. Document:
   - Docstrings on the two handlers; argparse help text that says what each is for in one sentence.

3. GREEN: Write MINIMAL code to make tests pass:
   - cli.py: add `eject` and `inspect` subparsers under `theme`; handlers call theme_loader helpers `flatten_chain(resolved, dest)` and `inspect_chain(resolved, project_dir)` returning result dataclasses with `to_dict`/`to_text` like ThemeCompileResult.

4. RED: Add integration tests:
   - Eject the `material` bundled theme (once Step 6 lands) into a scratch project, set `theme.path`, edit one partial, build, and assert the edit shows in the output. This is the user story Mason described; keep it as a permanent e2e test.

5. GREEN: Wire minimally.

6. REFACTOR: Share the per-file layer-resolution walk between inspect and the Step 4 "nearest layer" helper.

7. Update documentation: none here (Step 18).

8. Verify meaningful coverage and run `just check`.
```

### Step 6: Split the existing theme into bundled `base` and `material` (task)

**NOTE**: Move `src/bartleby/theme/` into the new layout. `base` gets what is not a visual opinion: `base.html` skeleton with named blocks (`head_extra`, `header`, `nav`, `sidebar`, `content`, `toc`, `footer`, `scripts`), `partials/jsonld.html`, `partials/seo_meta.html`, the feed/alternate-link head markup, search index wiring, the JS vendor files, and `404.html`/`page.html`/`defaults/*` as minimal unstyled fallbacks so a theme that extends base renders everything. `material` gets the current visual partials (`header`, `nav`, `footer`, `toc`, `search`, `back_to_top`, `code_copy`, `taxonomy*`) and the current `safelist.txt`; its manifest `extends: base`. Icons move to `base/icons/`. The `scrivener` theme dir is created in Step 11.

```text
1. Scope:
   - Artifact(s): src/bartleby/themes/base/{theme.yml,templates/**,static/js/*,icons/**}, src/bartleby/themes/material/{theme.yml,templates/**,static/css/main.css,safelist.txt}; delete src/bartleby/theme/; update every import (`templates.py`, `icons.py`, `cli.py`, `build.py`, tests).
   - Desired end state: `resolve_theme("material")` yields [material, base]; the smoke test and every template test pass with the default theme set to `scrivener` falling back to `material` until Step 11 creates it (set the default to `material` in this step and flip it in Step 11).

2. Tooling:
   - Skills: python:python
   - MCPs: none
   - External: `uv run pytest`, `just check`.

3. Do the work:
   - `git mv` the files into the new layout; write both theme.yml manifests (material: `features: [search, nav.back-to-top, content.code.copy, color-mode.toggle]` reflecting what its templates actually do today; base: `features: []`).
   - Replace the Material-named `feature('navigation.top')`/`feature('content.code.copy')` calls in templates with the native names from Step 3.
   - Un-xfail the Step 1 bundled-name tests for `base` and `material`.
   - Update `docs/bartleby.yml` to `theme: {name: material, features: [search, nav.tabs, color-mode.toggle]}` temporarily (Step 17 switches it to the Bartleby theme).

4. Verify:
   - `just check` green (ruff, mypy, pytest, smoke), and `uv run bartleby build docs/` exits 0 with the material theme.

5. Document:
   - spec.md Component boundaries: replace "The `theme/` package" with `theme_loader.py` and "the `themes/` package (bundled `base`, `material`, `scrivener`)".
```

---

## Section 2: The `material` theme

**Tools:**
- Skills: frontend-design:frontend-design, python:python
- MCPs: none
- Linters: none

`material` is faithful to mkdocs-material's *look and layout* for people who want that shape: header bar in the primary color, navigation tabs, left section sidebar, right TOC, admonitions, content tabs, search modal. Use the `/home/mmegger/Code/MasonEgger/mkdocs-material` checkout to confirm structure and visual intent; do not copy its CSS (CLAUDE.md: reimplemented, not ported). All files live under `src/bartleby/themes/material/`. These steps are markup and design sources; each verifies by building a site and grepping output, since no HTML linter is in the gate.

### Step 7: Material design sources (task)

```text
1. Scope:
   - Artifact(s): src/bartleby/themes/material/tailwind.config.js, src/bartleby/themes/material/tailwind.css, src/bartleby/themes/material/safelist.txt
   - Desired end state: a config with `darkMode: ['selector', '[data-theme="dark"]']`, a Material-faithful palette and Roboto-style font stack expressed through the `--bb-*` token variables (so `theme.tokens` can recolor it), the typography plugin enabled with a `prose` theme, and an input CSS that imports `.bartleby/tokens.css`, declares the Tailwind directives, and defines every semantic component class the material templates use (enumerate from the current partials and the old placeholder main.css) plus `.layout-docs`, `.layout-prose`, `.sidebar-nav`, `.nav-tabs`, `.toc-nav`.

2. Tooling:
   - Skills: frontend-design:frontend-design (fidelity to the Material look without copying CSS)
   - External: the pinned Tailwind binary via `uv run bartleby theme compile` on a scratch project using `theme.name: material`.

3. Do the work:
   - Write the three files with ABOUTME headers; read token defaults from `--bb-*` variables with sensible fallbacks so the theme renders with an empty tokens map.

4. Verify:
   - `uv run bartleby theme compile` on a scratch project with `theme.name: material` exits 0 and the output contains `prose` rules and the component classes.

5. Document:
   - Comment block in tailwind.config.js naming the palette/type decisions and the fidelity target.
```

### Step 8: Material shell and content templates (task)

**NOTE**: Files under `themes/material/templates/`: `partials/header.html`, `partials/nav.html`, `partials/footer.html`, and overrides of base's `page.html`, `defaults/post.html`, `defaults/list.html`. Preserve every context reference and the Alpine color-mode toggle; wrap Markdown bodies in `prose dark:prose-invert`; post/list use `.layout-prose`, page uses `.layout-docs`.

```text
1. Scope:
   - Artifact(s): the six templates above
   - Desired end state: Material-faithful header, tabs-capable nav, footer with prev/next and build meta; prose-styled bodies; styled post meta; listing as cards/rows with excerpts; styled pagination.

2. Tooling:
   - Skills: frontend-design:frontend-design
   - External: `uv run bartleby build docs/` (docs are on material until Step 17).

3. Do the work:
   - Add utility and component classes; fill base's blocks; keep all variables and includes.

4. Verify:
   - Build the docs; grep a concept page for the `prose` wrapper and header classes; grep a guides listing for excerpts; exit 0, no `UndefinedError`.

5. Document: none.
```

### Step 9: Material docs layout: sidebar, TOC, tabs (task)

**NOTE**: `nav.html` renders tabs when `feature('nav.tabs')`; a new `partials/sidebar.html` walks `nav` recursively (`item.children`, `is_section`) marking the current page when `feature('nav.sidebar')`; `partials/toc.html` is included in `page.html`'s `toc` block when `page.toc` is non-empty; `nav.section-index` links a section title to its index page. If the NavItem data lacks an index-page pointer, add the minimal field in `navigation.py` with a test (that part is Python; the section Tools block covers it).

```text
1. Scope:
   - Artifact(s): partials/nav.html, partials/sidebar.html (new), partials/toc.html, page.html under themes/material/templates/; possibly navigation.py + tests/test_navigation.py for the index pointer.
   - Desired end state: docs pages show tabs, a collapsible sidebar tree with the current page marked, and an active-tracking TOC; blog/list pages stay single-column. The material manifest `features` list is updated to include `nav.tabs`, `nav.sidebar`, `nav.section-index`.

2. Tooling:
   - Skills: frontend-design:frontend-design, python:python (only for navigation.py)
   - External: `uv run bartleby build docs/` with `nav.sidebar` enabled in a scratch copy of docs/bartleby.yml.

3. Do the work:
   - Implement the three partials and the page.html blocks; update themes/material/theme.yml features.

4. Verify:
   - Build with tabs + sidebar on: concept page carries the tab bar, the sidebar tree with current marked, and a TOC of its headings; a blog listing has no sidebar; exit 0, no `UndefinedError`; no feature warnings.

5. Document: none here.
```

### Step 10: Material taxonomy, 404, search, and interactive partials (task)

```text
1. Scope:
   - Artifact(s): themes/material/templates/{taxonomy.html,taxonomy_index.html,404.html,partials/search.html,partials/back_to_top.html,partials/code_copy.html}
   - Desired end state: taxonomy pages and index list cleanly; 404 is branded and helpful; search modal (with `search.highlight` term marking when enabled), back-to-top, and code-copy are styled consistently in both color modes. Manifest features gain `search.highlight`.

2. Tooling:
   - Skills: frontend-design:frontend-design
   - External: `uv run bartleby build docs/`.

3. Do the work:
   - Add classes; implement highlight in search.html gated by `feature('search.highlight')`; keep all Alpine/HTMX attributes and variables; do not touch base's jsonld/seo_meta.

4. Verify:
   - Build the docs: 404, a taxonomy term page, and the taxonomy index carry the expected classes; search results mark matched terms when the flag is on; exit 0, no `UndefinedError`.

5. Document: none.
```

---

## Section 3: The `scrivener` theme

**Tools:**
- Skills: frontend-design:frontend-design, python:python
- MCPs: none
- Linters: none

Scrivener is Bartleby's own identity and the docs showcase, named for Melville's scrivener. It `extends: base`, not `material`, and shares no partials with material; that independence is what proves the vocabulary and the `extends` mechanism are general. The directory is `src/bartleby/themes/scrivener/`. It must implement the same feature set as material (tabs, sidebar, section index, TOC, search + highlight, back-to-top, code copy, color-mode toggle) so the two are interchangeable from config.

### Step 11: Scrivener design direction and sources (task)

```text
1. Scope:
   - Artifact(s): src/bartleby/themes/scrivener/{theme.yml,tailwind.config.js,tailwind.css,safelist.txt}; flip the default theme name in config.py to `scrivener`; un-xfail the Step 1 bundled-name test for it.
   - Desired end state: a distinctive, non-templated identity (palette, type, spacing rhythm, radius) chosen with the frontend-design skill and recorded in a comment block; tokens exposed as `--bb-*` with fallbacks; typography plugin themed; component classes defined for the layout regions and partials this theme will use; manifest `extends: base` with the full native feature list.

2. Tooling:
   - Skills: frontend-design:frontend-design (this is the one place to spend real design effort: the result must not read as "mkdocs with the colors swapped" or as generic AI output)
   - External: `uv run bartleby theme compile` on a scratch project with `theme.name: scrivener`.

3. Do the work:
   - Write the four files with ABOUTME headers; present the direction (palette, type, three adjectives) in the step notes for Mason to react to before Steps 12-14 build on it.

4. Verify:
   - Compile exits 0 with `prose` and component rules present; `just check` green after the default-theme flip.

5. Document:
   - The design-direction comment block in tailwind.config.js.
```

### Step 12: Scrivener shell and content templates (task)

```text
1. Scope:
   - Artifact(s): themes/scrivener/templates/{partials/header.html,partials/nav.html,partials/footer.html,page.html,defaults/post.html,defaults/list.html}
   - Desired end state: the shell and content pages in Scrivener's identity: header, nav, footer, prose-wrapped bodies, styled post meta, listing cards, pagination. Same context references and base blocks as material; different look.

2. Tooling:
   - Skills: frontend-design:frontend-design
   - External: `uv run bartleby build` on a scratch scaffold with `theme.name: scrivener`.

3. Do the work:
   - Implement the six templates against base's blocks; preserve all variables and the color-mode toggle.

4. Verify:
   - Build: home, a post, and a listing carry the theme's classes and prose wrappers; exit 0, no `UndefinedError`.

5. Document: none.
```

### Step 13: Scrivener docs layout: sidebar, TOC, tabs (task)

```text
1. Scope:
   - Artifact(s): themes/scrivener/templates/{partials/nav.html,partials/sidebar.html,partials/toc.html,page.html}
   - Desired end state: tabs, collapsible sidebar tree with current page marked, active-tracking TOC, section-index links, all in Scrivener's identity and gated by the same native feature names as material.

2. Tooling:
   - Skills: frontend-design:frontend-design
   - External: `uv run bartleby build docs/` with docs/bartleby.yml switched to `theme.name: scrivener` in a scratch copy.

3. Do the work:
   - Implement the partials and page blocks; no shared files with material.

4. Verify:
   - Build the docs on the scrivener theme with tabs + sidebar on: tab bar, sidebar tree, TOC present on a concept page; no sidebar on a listing; exit 0; no feature warnings.

5. Document: none.
```

### Step 14: Scrivener taxonomy, 404, search, and interactive partials (task)

```text
1. Scope:
   - Artifact(s): themes/scrivener/templates/{taxonomy.html,taxonomy_index.html,404.html,partials/search.html,partials/back_to_top.html,partials/code_copy.html}
   - Desired end state: the remaining page types and interactive partials in Scrivener's identity, including `search.highlight`.

2. Tooling:
   - Skills: frontend-design:frontend-design
   - External: `uv run bartleby build docs/`.

3. Do the work:
   - Implement; keep Alpine/HTMX attributes and variables; do not touch base's metadata partials.

4. Verify:
   - Build: 404, taxonomy term, taxonomy index styled; search highlight works when enabled; exit 0, no `UndefinedError`.

5. Document: none.
```

---

## Section 4: Compile, ship, and browser-verify both themes

**Tools:**
- Skills: python:python, frontend-design:frontend-design
- MCPs: none
- Linters: uv run ruff check --output-format=json src/ tests/, uv run mypy src/

### Step 15: Regenerate, ship, and visually verify `material` and `scrivener` (task)

**NOTE**: The acceptance gate for Goal 2. Ships both themes' real `static/css/main.css`, verifies each in a browser across every page type with zero custom CSS, and proves the path-theme and eject workflows end to end.

```text
1. Scope:
   - Artifact(s): src/bartleby/themes/{material,scrivener}/static/css/main.css (regenerated, committed); any token/markup fixes in Section 2/3 files.
   - Desired end state: both themes render polished across home, listing, post, docs page (sidebar + TOC), taxonomy, and 404, light and dark, desktop and mobile, with no user CSS. Switching `theme.name` between the two changes the look and nothing else. Eject -> edit -> build works as a user would do it.

2. Tooling:
   - Skills: frontend-design:frontend-design (judge the result), python:python (glue fixes)
   - MCPs: none
   - External: `just theme-css`, `uv run bartleby new`, `build`, `serve`, the `run` skill and/or claude-in-chrome for screenshots.

3. Do the work:
   - Run `just theme-css` for both themes.
   - Scaffold a throwaway site in the scratchpad; build and serve once with `theme.name: material` and once with `theme.name: scrivener`; also build the docs on `scrivener`.
   - Screenshot the six page types per theme in both color modes at desktop and mobile widths.
   - Run the user story: `bartleby theme eject` the scrivener theme into the scaffold, switch config to `theme.path`, change the footer, rebuild, confirm the change; run `bartleby theme inspect` and confirm it reports the ejected layer.
   - Fix defects in the Section 2/3 sources and recompile until both are presentable.

4. Verify:
   - `just check` green AND screenshots for both themes show a polished site across all six page types with zero custom CSS AND the eject/inspect story works. Surface the screenshots for Mason.

5. Document:
   - CHANGELOG.md: theme system, the three bundled themes, eject/inspect, and the breaking config change.
```

---

## Section 5: Theme docs and the docs showcase

**Tools:**
- Skills: content-design:diataxis, content-design:tutorial-writing, content-design:style-linting, frontend-design:frontend-design
- MCPs: none
- Linters: none

The docs live in `docs/content/` (source; `docs/site/` is gitignored output), configured by `docs/bartleby.yml`. They are a Bartleby site and the public showcase (Goal 3), and they now must also teach the theme system.

### Step 16: Catalog every docs rendering defect (task)

```text
1. Scope:
   - Artifact(s): a defect inventory in the scratchpad (not committed).
   - Desired end state: a file-by-file list of what renders wrong: broken cross-references, invalid front matter, malformed shortcodes/admonitions, stub pages, nav entries that 404, Diataxis-type mismatches, and content that describes the old theme config.

2. Tooling:
   - Skills: content-design:diataxis, content-design:style-linting
   - External: `uv run bartleby build docs/`, `uv run bartleby lint docs/`, `serve` + browser.

3. Do the work:
   - Build and lint the docs; walk every page in the browser; classify each page by Diataxis type; record defects against `docs/content/...` paths.

4. Verify:
   - Every entry names a specific path and a specific defect.

5. Document:
   - Save the inventory to the scratchpad; it drives Step 17.
```

### Step 17: Fix docs content and switch the docs to the Scrivener theme (task)

**NOTE**: Edit `docs/content/**`, `docs/bartleby.yml`, `docs/.authors.yml` only. Switch `docs/bartleby.yml` to `theme: {name: scrivener, features: [search, search.highlight, nav.tabs, nav.sidebar, nav.section-index, nav.back-to-top, content.code.copy, color-mode.toggle]}`. If a defect is an engine bug, record it for Sections 6-7; do not patch engine code here.

```text
1. Scope:
   - Artifact(s): docs/content/**, docs/bartleby.yml, docs/.authors.yml.
   - Desired end state: build and lint both exit clean on the scrivener theme with no feature warnings; every nav entry resolves; each page is sound for its Diataxis type; no page still describes the removed mkdocs-style config.

2. Tooling:
   - Skills: content-design:diataxis, content-design:tutorial-writing, content-design:style-linting (not content-design:voice; docs are refined voice)
   - External: `bartleby build docs/`, `bartleby lint docs/`.

3. Do the work:
   - Work the inventory; fix front matter, cross-refs, shortcodes, admonitions, stubs; reconcile nav; update config; honor the writing hard rules.

4. Verify:
   - `uv run bartleby build docs/` exits 0 with no warnings AND `uv run bartleby lint docs/` is clean.

5. Document:
   - Hand any engine bug found to the owning later section.
```

### Step 18: Write the theme-system documentation (task)

**NOTE**: New pages under `docs/content/`. Diataxis split: a how-to guide for using and customizing themes, a how-to for writing a theme, and a reference for the manifest, the native feature names, the tokens, and the `theme` CLI commands. The eject-then-read workflow is the agents-first angle: say explicitly that an ejected theme is a complete, readable system a coding agent can modify.

```text
1. Scope:
   - Artifact(s): docs/content/guides/posts/choose-and-customize-a-theme.md, docs/content/guides/posts/write-a-theme.md, docs/content/reference/pages/themes.md (manifest, feature names, tokens, `theme eject|inspect|compile`), and updates to docs/content/concepts/customization-seams.md and docs/content/concepts/templates.md to describe the resolution chain and replace the old overrides-only story.
   - Desired end state: a newcomer can pick a bundled theme, recolor it with tokens, extend it, eject it, inspect the chain, and write a path or package theme, from the docs alone.

2. Tooling:
   - Skills: content-design:diataxis (type per page), content-design:tutorial-writing (the guides), content-design:style-linting
   - External: `bartleby build docs/`, `bartleby lint docs/`; the real CLI output for the reference page.

3. Do the work:
   - Write the pages against the real code and manifests from Sections 1-3; include the actual `theme.yml` of a bundled theme as the worked example; honor the writing hard rules.

4. Verify:
   - Build and lint clean; every CLI flag and manifest key named in the docs exists in code (spot-check both directions).

5. Document:
   - This step is the documentation; add the new pages to docs/bartleby.yml nav.
```

### Step 19: Visual polish pass on the docs showcase (task)

```text
1. Scope:
   - Artifact(s): docs/content/** (copy/structure), docs/bartleby.yml (features) as needed.
   - Desired end state: the docs on the scrivener theme look good enough to be the public showcase.

2. Tooling:
   - Skills: frontend-design:frontend-design, content-design:diataxis
   - External: `build`, `serve`, browser + screenshots.

3. Do the work:
   - Review landing, concepts (sidebar + TOC), guides listing + a guide, the new theme pages, reference, taxonomy, both color modes, desktop and mobile; tune content and features. Theme CSS is frozen after Section 4 unless a real defect appears; if one does, fix it in the theme sources and recompile.

4. Verify:
   - Screenshots show a polished showcase; surface for Mason.

5. Document:
   - CHANGELOG.md if docs structure changed materially.
```

---

## Section 6: Developer experience

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: uv run ruff check --output-format=json src/ tests/, uv run mypy src/

### Step 20: Clear, actionable error messages

**NOTE**: The YAML-backed modules raise structured errors (`ConfigError(message, key_path)`, `AuthorError`, `ShortcodeError`, and now `ThemeError`). Make the messages a newcomer sees name the file, the key path or id, and a concrete fix. No handling for impossible scenarios.

```text
1. RED: Write error-message tests first:
   - In tests/test_config.py, tests/test_authors.py, tests/test_metadata.py, tests/test_theme_loader.py as the code dictates:
     - Test that an unknown top-level `bartleby.yml` key raises ConfigError naming the file and key path.
     - Test that a malformed content-type metadata schema names the content type and field.
     - Test that a missing/duplicate author id raises AuthorError naming the id and the authors file.
     - Test that a `theme.path` pointing at a dir without theme.yml raises ThemeError naming the path and saying what a theme dir needs.
     - Test that a build against a nonexistent content path names the path and how to fix it.
   - Assert on substrings, not exact strings.

2. Document:
   - Module docstrings stating each error's message contract.

3. GREEN: Write MINIMAL code to make tests pass:
   - Enrich the raise sites in config.py / authors.py / metadata.py / theme_loader.py / build.py using the existing structured exception fields.

4. RED: Add integration tests:
   - Drive each failure through the CLI and assert the text formatter surfaces the enriched message with a non-zero exit code.

5. GREEN: Wire the CLI/formatter minimally.

6. REFACTOR: Factor the "file + key path + hint" formatting into one helper.

7. Update documentation: a troubleshooting note in the docs reference if a common error warrants it.

8. Verify meaningful coverage and run `just check`.
```

### Step 21: Scaffolding that builds and renders well out of the box

**NOTE**: `bartleby new` (cli.py) must emit a site on `theme.name: scrivener` with the native feature list, that builds clean with no warnings and renders polished, so a newcomer succeeds immediately (Goal 4). Verify what the scaffold emits, not that argparse works.

```text
1. RED: Write scaffold-output tests first:
   - In tests/test_cli.py (or tests/test_scaffold.py):
     - Test that `bartleby new <dir>` creates bartleby.yml, at least one content type, a sample post, and the expected layout.
     - Test that the scaffolded bartleby.yml selects `theme.name: scrivener`, enables only native feature names present in that theme's manifest, and references only paths that exist.
     - Test that building the scaffolded site produces the expected home/listing/post output files with no warnings.

2. Document:
   - Update the quickstart docs to match the scaffold (coordinate with Section 5).

3. GREEN: Write MINIMAL code to make tests pass:
   - Adjust the scaffold defaults in cli.py and any bundled starter assets.

4. RED: Add integration test:
   - Scaffold into a temp dir, run the real build, assert the home page carries the scrivener theme's container/prose classes and there is no `UndefinedError`.

5. GREEN: Wire minimally.

6. REFACTOR: Remove dead starter assets or stale defaults.

7. Update documentation: refresh installation/quickstart to the real first-run experience, including "to see the Material look, set theme.name: material".

8. Verify meaningful coverage and run `just check`.
```

---

## Section 7: Agent surface consistency and correctness

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: uv run ruff check --output-format=json src/ tests/, uv run mypy src/

The agent surface is the differentiator (Goal 5). Modules: `llm.py`, `agent_surface.py`, `schema_introspection.py`, `content_query.py`, `skills.py`, `export.py`. The base theme now owns the JSON-LD and alternate-link markup, so these tests run against a build on either visual theme and must pass on both.

### Step 22: Every published page has a valid Markdown variant and JSON-LD

```text
1. RED: Write agent-output tests first:
   - In tests/test_llm.py:
     - Test that after a full build every published page has an `index.md` variant at its output URL.
     - Test that each emitted JSON-LD block is valid JSON with `@context`, `@type`, headline/name, and url for its page type.
     - Test that draft/excluded pages get neither.
   - Parametrize the build over `theme.name` in {material, scrivener}.

2. Document:
   - The per-page guarantee in the llm.py docstring.

3. GREEN: Write MINIMAL code to make tests pass:
   - Close gaps in llm.py (and base's jsonld partial if a field is missing).

4. RED: Add integration tests:
   - On a built fixture, variant count equals published count and every jsonld block parses.

5. GREEN: Wire into build.py minimally if needed.

6. REFACTOR: De-duplicate the published-page-set computation with sitemap/feeds.

7. Update documentation: note the guarantee in the agent-surface reference (Step 25 expands it).

8. Verify meaningful coverage and run `just check`.
```

### Step 23: llms.txt, schema.json, and content-index.json are correct

```text
1. RED: Write correctness tests first:
   - In tests/test_agent_surface.py and tests/test_llm.py:
     - Test that llms.txt lists the real sections/pages with correct titles and URLs and llms-full.txt includes bodies.
     - Test that schema.json reflects the actual content types, taxonomies, and author schema for a known fixture config, and now also the active theme's name and implemented features (so an agent knows what the site can do).
     - Test that content-index.json entries match the published pages and exclude drafts.

2. Document:
   - The format/field contract per artifact in the owning module docstring.

3. GREEN: Write MINIMAL code to make tests pass:
   - Fix defects in llm.py / agent_surface.py / schema_introspection.py; add the theme block to schema.json.

4. RED: Add integration tests:
   - Build the docs fixture; every content-index url resolves to a built page; schema.json's theme block matches docs/bartleby.yml.

5. GREEN: Wire into build.py minimally.

6. REFACTOR: Share extraction with Step 22.

7. Update documentation: expand the agent-surface reference (Step 25).

8. Verify meaningful coverage and run `just check`.
```

### Step 24: Generated skills reflect the real site shape

```text
1. RED: Write skill-generation tests first:
   - In tests/test_skills.py:
     - Test that generating twice for the same site is byte-identical.
     - Test that `bartleby-write` names the site's real content types and metadata fields/choices.
     - Test that the skills reference real taxonomies and author ids, and that `bartleby-ops` mentions the active theme and the `theme eject|inspect|compile` commands.

2. Document:
   - The determinism + fidelity contract in skills.py.

3. GREEN: Write MINIMAL code to make tests pass:
   - Fix nondeterminism and placeholder content; add the theme facts to the ops skill.

4. RED: Add integration tests:
   - Generate against the docs fixture; content types and fields match schema.json from Step 23.

5. GREEN: Wire minimally.

6. REFACTOR: Reuse schema_introspection output rather than re-deriving.

7. Update documentation: note the generated-skill contract in the agent reference.

8. Verify meaningful coverage and run `just check`.
```

---

## Section 8: Public interface documentation and final gate

**Tools:**
- Skills: python:python, content-design:diataxis, content-design:tutorial-writing
- MCPs: none
- Linters: uv run ruff check --output-format=json src/ tests/, uv run mypy src/

### Step 25: Document and stabilize the public interfaces (task)

**NOTE**: Public now: the 16 plugin hooks (`plugins.py`), the `bartleby.yml` schema including the new `theme` block (`config.py`), the template context and base-theme block names (`templates.py`, `themes/base`), the theme manifest (`theme_loader.py`), the agent output formats (Section 7), and the `theme` CLI commands. Reference stubs exist under `docs/content/reference/pages/`; Step 18 added `themes.md`.

```text
1. Scope:
   - Artifact(s): docs/content/reference/pages/{plugin-hooks,configuration,template-context,front-matter-fields,cli,shortcodes,build-pipeline,themes}.md and an agent-output-formats reference page (new if absent).
   - Desired end state: each page documents the real, current surface, cross-checked against the code both ways.

2. Tooling:
   - Skills: content-design:diataxis, python:python
   - MCPs: none
   - External: `bartleby schema`, `bartleby theme inspect --format json`, and other introspection output as cross-check sources.

3. Do the work:
   - Enumerate each surface from the code; write/correct the matching page; prefer introspection-generated lists; honor the writing hard rules.

4. Verify:
   - Every hook/key/context var/feature/manifest key/CLI flag in code appears in the docs and vice versa; build and lint docs clean.

5. Document:
   - A one-line stability statement in spec.md or README naming these interfaces as stable for 0.x.
```

### Step 26: Final stabilization gate (task)

```text
1. Scope:
   - Artifact(s): CHANGELOG.md (finalize the entry), README.md (if first-run drifted), pyproject.toml version (Mason decides 0.1.x vs 0.2.0).
   - Desired end state: every spec.md Success criterion is demonstrably met and `bartleby-ssg` installs and runs from a clean environment on both bundled visual themes.

2. Tooling:
   - Skills: python:python
   - MCPs: none
   - External: `just check`; a clean venv install of the built wheel; browser for the final visual confirmation.

3. Do the work:
   - `just check` green.
   - Build the wheel, install into a fresh venv in the scratchpad, scaffold + build + serve on `scrivener`, switch to `material`, rebuild; confirm both work with no repo on PATH and the wheel contains all three themes' files.
   - Walk the Success criteria in spec.md with evidence per line.

4. Verify:
   - `just check` green AND the clean-env install serves a good-looking site on both themes. Produce the Success-criteria checklist with evidence for Mason, who holds the governing bar.

5. Document:
   - Finalize CHANGELOG.md and README.md.
```

---

## Implementation Guidelines

- **TDD for Feature steps** (1, 2, 3, 4, 5, 20, 21, 22, 23, 24): failing test first, minimal code, refactor; test application logic, never the framework.
- **Task steps** (6-19, 25, 26) carry literal Scope/Tooling/Do/Verify/Document instructions; markup and docs steps verify by building a site and grepping output.
- **Bundled themes are path themes.** Nothing in the loader may special-case a bundled name beyond mapping it to a directory. Tests use `tests/fixtures/themes/` path themes first and bundled names second.
- **`base` has no visual opinion.** If a change to `base` would make a page look different, it belongs in `material` or `bartleby`.
- **`material` and `scrivener` share no files.** They both extend `base` and nothing else.
- **Design direction for `scrivener` is Mason's to react to** at Step 11 before Steps 12-14 build on it.
- **The gate is `just check`.** Hold every diff to it.
- **Code Style (CLAUDE.md):** ABOUTME headers, strict typing (`Any` only at the YAML boundary), single responsibility, validate at boundaries only, no impossible-scenario handling, evergreen names, preserve comments.
- **Writing hard rules** apply to docs, comments, commit messages, CHANGELOG: no em/en dashes, no banned words, straight quotes, one sentence per line in committed Markdown, Title Case headings.
- **Theme CSS freeze after Section 4** unless a genuine theme defect surfaces.
- **Scope discipline.** No migration tool, no fourth theme, no 0.2.0 features, no fountain-py. Record anything beyond this plan in spec.md's Deferred list.
- **Git workflow (CLAUDE.md):** never commit to main; work on `v0.1.1`. Commit only when Mason asks: session-summary -> commit-message -> `git commit -S -F commit-msg.md` -> `/init`. `commit-msg.md` stays gitignored.

## Success Metrics

The plan is done when all spec.md Success criteria hold:

1. The theme system works: `theme.name|path|package` select a theme, `extends` composes, `eject` and `inspect` expose the whole system, and the bundled themes resolve through the same loader as a path theme (Steps 1-6, 15).
2. Both `material` and `scrivener` render polished across home, listing, post, docs page, taxonomy, and 404 in a browser, zero custom CSS, switchable from config (Steps 7-15).
3. The docs site builds and renders cleanly on the `scrivener` theme, teaches the theme system, and is fit as the public showcase (Steps 16-19).
4. A newcomer scaffolds, builds, serves, and gets a good-looking result; errors are clear and actionable (Steps 20-21).
5. Agent surface complete and consistent on both themes; `schema.json` and the ops skill describe the active theme (Steps 22-24).
6. Public interfaces including the theme manifest and config block are documented and stable (Step 25).
7. `just check` green; `bartleby-ssg` installs and runs from a clean environment on both themes (Step 26).
8. Mason is willing to send it to people and show it off. Governing bar, confirmed at Step 26.
