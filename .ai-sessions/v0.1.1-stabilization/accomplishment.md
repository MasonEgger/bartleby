# Accomplishment: 0.1.x Stabilization, Theme System and Showcase

**Archived**: 2026-10-12
**Convergence**: converged (160 of 160 sub-steps checked; Mason's visual sign-off and the 0.1.x-vs-0.2.0 version call were the two open items, both resolved in his favor since)

## Spec Slice

Goals 1 through 6 of spec.md: stabilize 0.1.x into something worth showing people.
The cycle built one feature, the theme system (Goal 2): a theme is a directory with a `theme.yml` manifest, selected by `theme.name`, `theme.path`, or `theme.package`, composable through `extends`, with `bartleby theme eject` and `theme inspect` exposing the whole resolved system.
Three bundled themes ship: `base` (no visual opinion), `material` (the mkdocs-material look), and `scrivener` (Bartleby's own identity and the default).
On top of that system it fixed the docs showcase (Goal 3), sharpened the developer experience and error messages (Goal 4), made the agent surface correct and consistent across both visual themes (Goal 5), and documented the public interfaces (Goal 6).

## What Got Done

- Theme system core: manifest loader and extends-chain resolver, cascade through templates, static assets, and icons, Bartleby-native config vocabulary and the feature contract, per-theme Tailwind compile with token emission, and `theme eject` / `theme inspect` (Steps 1-5).
- Split the one hardwired theme into bundled `base` and `material` (Step 6).
- Built the `material` theme end to end: design sources, shell and content templates, docs layout with sidebar, TOC, and tabs, and taxonomy, 404, search, and interactive partials (Steps 7-10).
- Built the `scrivener` theme to the same feature set, extending `base` and sharing no files with `material`, and made it the default (Steps 11-14).
- Compiled, shipped, and browser-verified both themes across every page type in both color modes at desktop and mobile (Step 15).
- Fixed the docs content, switched the docs to `scrivener`, wrote the theme-system documentation, and ran a visual polish pass on the showcase (Steps 16-19).
- Made error messages name the file, the key, and the fix, and made the scaffold build and render well out of the box (Steps 20-21).
- Made the agent surface correct and consistent on both themes: a Markdown variant and JSON-LD per published page, correct `llms.txt`, `schema.json`, and `content-index.json` with a theme block, and generated skills that match the real site shape (Steps 22-24).
- Documented and stabilized the public interfaces and ran the final stabilization gate from a clean-venv wheel install (Steps 25-26).

## Deferred or Dropped

- The `bartleby migrate mkdocs` command: the chosen answer for migrators, deferred to a later cycle (spec.md Deferred).
- Additional bundled themes beyond `base`, `material`, and `scrivener`: deferred.
- The version bump itself: the plan stayed version-agnostic; Mason's call was to stay on 0.1.x, with 0.2.0 as the next stable release.

## Notable Decisions

- A theme system with a set of default themes, not one hand-polished theme (Mason, 2026-10-09). This reframed the cycle from "polish the theme" to "build the theme system" after a grep found the shipped CSS was a placeholder and the compile path fed Tailwind a bare directive string.
- Bartleby-native theme vocabulary with no mkdocs-material alias layer; the Material-named `theme.features` were replaced, a documented breaking config change allowed in 0.x.
- `base` carries no visual opinion; `material` and `scrivener` both extend it and nothing else, which is what proves the vocabulary is not Material-shaped.
- Bundled themes resolve through the same loader as a user's path theme, and are tested as path themes under `tests/fixtures/themes/`.

## Files Touched

- `src/bartleby/theme_loader.py`, `src/bartleby/theme_compile.py` (new and rewritten theme machinery)
- `src/bartleby/themes/{base,material,scrivener}/` (the three bundled themes, replacing `src/bartleby/theme/`)
- `src/bartleby/{config,templates,icons,navigation,build,cli}.py` (chain-aware resolution, native config, CLI theme commands)
- `src/bartleby/{llm,agent_surface,schema_introspection,skills,export}.py` (agent surface correctness)
- `src/bartleby/errors.py` and the raise sites across the YAML-backed modules
- `docs/content/**`, `docs/bartleby.yml`, `docs/.authors.yml` (showcase and theme docs)
- `tests/**` (resolver, cascade, compile, theme commands, scaffold output, agent surface, docs reference)
- `CHANGELOG.md`, `CLAUDE.md`, `spec.md`

## Lessons Cross-Reference

- See `.ai-sessions/lessons.md`, the 2026-10-09 and 2026-10-10 entries: the "polish vs build the theme" grep-the-artifact-first lesson, the validator-cluster-on-public-outputs finding, the docs-vs-code coverage test, the shared-helper grep after a refactor, and the final-gate clean-wheel-install lesson.
