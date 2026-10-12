# Bartleby

## Starting context

Captured verbatim from Mason during the 2026-10-06 retrofit.

On the project and why it is being re-specced:

"That old spec is dated, this is one of my first projects so it's using bpe before it was even bpe. So we need to get this setup properly as it will be one of my flagship projects."

On the current state and the near-term direction:

"We have to stabilize just this version. I just checked the Docs and they don't render for shit. I don't know if we have a base theme yet, but we need to get to one. We need to make the developer an agent experience the absolute best it can possibly be. So basically we won't even be getting to a 0.2.0 until we can actually have something we're proud of showing off to people. At this point in time, I'm not even sending it to people. It's that bad."

On the first-run review against MkDocs, Material for MkDocs, Sphinx (with furo), Hugo, and Zensical (2026-10-11):

"I really like the default experience for zensical and mkdocs material's landing page. I think that's probably one of the best looking ones given the things that you showed me. I like the dual column docs and that's how most people build their docs now. So since this is a documentation site we should do that kind of dual or triple column thing basically column space content, space column."

"Full support should be baked in for Mark Wright. In reality that is our flagship marked down processing the library. I wrote it so I say integrated as you want."

"As you take anything from these other tools, such as any direct code or any inspiration you get, I think it would be wise for us to acknowledge this just for inspiration, but also because we need to be sure that we're remaining in compliance with their open source licenses."

"It's for me first. I want to rewrite my blog with this."

## Project overview

Bartleby is a batteries-included, agents-first static site generator written in Python (3.14+).
It is published on PyPI as `bartleby-ssg`; the import package and the CLI command are both `bartleby`.

It takes Markdown with YAML front matter and produces a site built for two audiences at once.
For humans: HTML, bundled themes (`scrivener` by default, `material` for that look), and client-side search (lunr.js).
For agents: a Markdown variant of every page, `llms.txt` and `llms-full.txt`, JSON-LD, `schema.json`, `content-index.json`, and deterministic agent-skill generation.
Treating AI crawlers and coding agents as a first-class audience alongside humans is the project's differentiator.

It is general-purpose, not docs-only: blog, taxonomies, listings, pagination, RSS and Atom feeds, sitemap, SEO tags, cross-references, shortcodes, and a `hooks/*.py` plugin seam.
Rendering is Python-Markdown plus pymdownx plus markwright; templates are Jinja2; the theme CSS compiles via the Tailwind standalone CLI, so users need no Node toolchain.
The argparse CLI exposes authoring commands (`new`, `build`, `serve`, `validate`), agent-facing commands (`schema`, `content`, `render`, `lint`, `export`, `generate-skill`), a `theme` command, and (Goal 8) `enable` and `disable` for content types and a `config` command, plus a dev server with live reload.

Current state: the mechanics are built and tested (567 tests, mypy strict, ruff, an end-to-end smoke test) and 0.1.0 is installable from PyPI.
What remains before the project is presentable is quality, not features.
The default theme output and the docs site do not yet render to a standard worth showing people, and that is the focus of this specification.

## Available tooling

Tools the `bpe:validator` agent should consult when reviewing diffs in `/bpe:goal` runs.
`/bpe:plan` propagates these to per-section declarations in plan.md.

**MCPs:**
- (none apply)

**Skills:**
- python:python
- content-design:diataxis
- content-design:style-linting
- content-design:tutorial-writing

**Notes:** Validator consults `python:python` for all code under `src/bartleby/` and `tests/` (strict typing, ruff, pytest, idioms). For changes to `docs/` content and to theme templates, it consults the content-design skills for Diataxis structure, prose style, and tutorial conventions. No domain MCPs apply. The project's full gate is `just check` (ruff lint and format check, mypy strict, pytest, and an e2e smoke test); `/bpe:goal` autodetects `pytest` from `pyproject.toml`, but `just check` is the canonical pass to hold diffs to.

## External tool candidates

Cached from `/bpe:plan` Pass 2 discovery (bpe:cheap-research) on 2026-10-08.
Installed entries can be folded into plan.md per-section Tools blocks; not-installed entries are leads for later, not available to the validator yet.

- frontend-design:frontend-design :: installed (official plugin); distinctive, production-grade front-end visual design guidance, fits theme polish across page types :: /home/mmegger/.claude/plugins/cache/claude-plugins-official/frontend-design/
- content-design:diataxis :: installed; Diataxis doc authoring for the docs-site cleanup :: mmegger-private-plugins/content-design
- content-design:style-linting :: installed; prose linting and voice for docs-site copy :: mmegger-private-plugins/content-design
- Frontend Design Review (dauquangthanh/hanoi-rainbow) :: not installed; UI/UX quality, design-system compliance, accessibility, responsive review :: https://claudemarketplaces.com/skills/dauquangthanh/hanoi-rainbow/frontend-design-review
- Tailwind CSS Accessibility (josiahsiegel) :: not installed; WCAG 2.2 reference for accessible Tailwind UIs :: https://claudemarketplaces.com/skills/josiahsiegel/claude-plugin-marketplace/tailwindcss-accessibility
- Frontend Design Deslop (samber/cc-skills) :: not installed; counters generic AI-looking output, strategy-first typography and color tokens :: https://claudemarketplaces.com/skills/samber/cc-skills/frontend-design-deslop

**Gap:** no Jinja2-specific, llms.txt, JSON-LD/schema.org, or HTML-validation skill was found; those sections rely on `python:python` plus hand review.

## Goals

1. Stabilize 0.1.x into something worth showing off.
   No 0.2.0 until the default output and the docs are presentable, and no features beyond the two named below.
   The tool is not being sent to anyone in its current state, and that is the bar to clear.
   This cycle builds two features.
   The first is the theme system in Goal 2, because (Mason, 2026-10-09) without deciding it there is nothing to stabilize and nothing to build toward.
   The second is the first-run work in Goal 8, because (Mason, 2026-10-11) the comparison showed a newcomer's first five minutes are where Bartleby falls behind.
2. A theme system and a set of default themes.
   A theme is a directory with a manifest (`theme.yml`), templates, static assets, Tailwind sources, and icons; it is selected by `theme.name` (bundled), `theme.path` (project directory), or `theme.package` (entry point), and may `extends` another theme.
   Bundled themes live under `src/bartleby/themes/` in that same layout and resolve through the same loader as a user's path theme.
   Three ship: `base` (no visual opinion: metadata partials, feed and alternate links, search wiring, the block skeleton), `material` (faithful to mkdocs-material's look, for people who want that shape), and `scrivener` (Bartleby's own identity, named for Melville's scrivener; the default for new sites and the docs).
   The theme vocabulary (config keys, feature names, design tokens) is Bartleby-native, with no alias layer to mkdocs-material names.
   `bartleby theme eject` copies the whole resolved theme into the project and `bartleby theme inspect` reports which layer provides each file, so the entire system is visible to people and coding agents rather than hidden behind blind single-file overrides.
   Both visual themes must reach professional quality across every page type (home, listing, post, docs page with sidebar and table of contents, taxonomy, 404) out of the box, with zero user styling required.
3. Docs that render cleanly.
   The docs site is itself a Bartleby site and is the primary dogfood and public showcase.
   It currently renders poorly; it must render correctly, look good, and stand as proof that Bartleby produces good-looking sites.
4. An excellent developer experience.
   Scaffolding, building, serving, configuration, and error messages should be smooth and clear enough that a newcomer succeeds without friction.
5. An excellent agent experience.
   The agents-first surface is the differentiator, so its outputs (per-page Markdown, `llms.txt`, `schema.json`, `content-index.json`, JSON-LD, generated skills) should be the strongest, most consistent, and most trustworthy part of the tool.
6. Trustworthy public interfaces.
   Now that 0.1.0 is published, the plugin hook API, the `bartleby.yml` schema, the template context, and the agent-output formats are effectively public.
   Stabilize and document them so people can build on them without being surprised by churn.
7. fountain-py integration (planned, after stabilization).
   First-class screenplay and Fountain content support is a committed future goal, sequenced as a post-0.1.x feature cycle, not before the tool is presentable.

8. A first-run experience as simple as Hugo's, with a docs layout as good as Zensical's (decided 2026-10-11, from the first-run comparison).
   The primary author is one person (a solo writer or a solo library author), and every default must grow cleanly into a small team.
   `bartleby new site` scaffolds a docs-shaped site: a home page that says what to do next, and one feature tour page that shows each markwright and pymdownx feature with its source beside the result.
   Its `bartleby.yml` holds only what the site needs to build, so it stays small.
   `bartleby new site --full-config` writes every option Bartleby accepts instead, each set to its default with a one-line comment, so no feature or option stays hidden because it was missing from the config (Mason, 2026-10-11).
   The full config is generated from the same source as config validation and `schema.json`, and a test fails if any accepted key is missing from it.
   Config is reachable from the CLI without one flag per option (decided 2026-10-11): a few dedicated flags cover what changes run to run (`--port`, `--host`, `--include-drafts`, `--strict`, and a new `--base-url`).
   A repeatable `--set key.path=value` on `build`, `serve`, and `validate` overrides config for one run without touching the file; values parse as YAML and go through the same validator, with errors labeled as coming from `--set`.
   `bartleby config show` prints the resolved config with the source of each value (default, file, or `--set`), `config get` reads one key, `config set` validates and writes one key into `bartleby.yml` keeping its comments, and `config schema --output json` lists every key with its type, default, allowed values, and a one-line description.
   `--full-config`, `config schema`, and the configuration reference docs come from one schema, and `enable` and `config set` share one comment-preserving YAML writer.
   The blog is opt-in, through `bartleby new site --blog` or `bartleby enable <content-type> <name>` on an existing site, which merges the needed config if it is missing and is safe to run twice.
   `bartleby disable <content-type> <name>` turns it off through an `enabled` flag, not by deleting config.
   The first argument is a content-type shape and the second is the instance name: `bartleby enable blog tutorials` adds a second blog-shaped type at `tutorials/`.
   A site can enable the same content type more than once (mason.dev runs `blog`, `tutorials`, and `speaking`), and each enabled type publishes its own RSS and Atom feeds plus one combined site feed, with the existing per-type `feeds` key as the opt-out and `site.feed` controlling the combined feed.
   `new site` and `serve` print what Hugo prints: what was created and the next command, then the build summary, the URL, and how to stop.
   The dev server is async on Starlette and uvicorn, with file watching and live reload on the same port, after sphinx-autobuild's design.
   The default docs layout is three columns (navigation, content, page table of contents), with `theme.features` flags to fold the table of contents into the left navigation and to move top-level sections into header tabs.
   The shape follows Zensical and Material for MkDocs; the markup and CSS are Bartleby's own, not a copy.
   markwright is fully integrated.
   Its eight extensions (markwright 0.3.0) are already on by default; what is missing is styling, because markwright ships no CSS by design and emits class hooks for the host to style.
   Both visual themes (`scrivener` and `material`) style every class hook markwright emits, and the starter feature tour shows each extension.
   Bartleby uses markwright's own option defaults; when a default should change, it changes in markwright.
   A `markwright:` section in `bartleby.yml` has the same shape as `markwright.toml` (`enable`, `disable`, `warn`, and one option table per extension) and is validated and passed to the extensions at build time through markwright's public config API (`config_from_mapping`, `selected_extensions`, `extension_configs`, added in markwright 0.3.0), so Bartleby never reimplements markwright's schema.
   Only `bartleby.yml` counts: if a `markwright.toml` or `[tool.markwright]` table is also present, the build warns that it was ignored.
   Embeds load eagerly by default, which is markwright's default, and the starter tour renders every embed live; the scaffold writes no `markwright:` section (revised 2026-10-11).
   Click-to-load is opt-in: a site sets `load: click` per embed in the `markwright:` section, and the scaffold README's quickstart shows how.
   The split is markup in markwright and behavior in Bartleby: markwright emits the preview markup and ships no JS or CSS, and Bartleby's themes ship the script and styles that swap the preview for the embed.
   markwright 0.3.0 (released 2026-10-11, from MasonEgger/markwright#11) supplies the click-to-load markup contract: a per-embed `load` option with `eager` (the default), `click` (a versioned preview with the live markup in a `<template>`), and `lazy` (YouTube only), and it injects provider scripts only when an eager embed is on the page.
   Bartleby follows markwright's Click-to-Load docs page for the host script and the provider processor calls.
   Anything the scaffold or docs claim works, works: feeds carry entries, code highlighting has CSS, and each claim has a test.
   Code or design taken from another project is credited in an acknowledgments file, and its license is checked for compatibility with MIT before it lands.
   Bartleby stays on 0.1.x through this work; 0.2.0 is the next stable release.

## Non-goals

1. Competing on raw build speed.
   Bartleby will not chase cold-build throughput against Zensical or Hugo; performance is not the pitch.
   An asyncio-based parallel or incremental build is a possible far-future consideration only, explicitly low priority, and not a current goal.
   The async dev server in Goal 8 is about serving, not build speed, and does not touch this.
2. Dynamic or CMS features.
   Bartleby stays a static generator: no server-rendered pages, no admin UI, no runtime backend.
3. Hosting or deployment.
   Bartleby generates the site; where it gets hosted is the user's responsibility.
4. A plugin marketplace or registry.
   Plugins stay simple local `hooks/*.py` files and entry-point packages; there is no curated ecosystem to maintain.
   The same holds for themes: `theme.package` is a plain entry point, and there is no theme registry.

## Roadmap / phase log

**Shipped:**
- none yet

**Deferred:**
- `bartleby migrate mkdocs`: a one-shot command that reads `mkdocs.yml`, writes `bartleby.yml`, and reports what did not map. The chosen answer for migrators instead of a config alias layer (decided 2026-10-09).
- Additional bundled themes beyond `base`, `material`, and `scrivener` (for example a blog-first theme).
- fountain-py integration (Goal 7).
- Multi-site linking (2026-10-11, not yet designed): cross-site links between related sites, a shared header and nav across sites (for example "the first three nav items from the parent site, then mine"), and an optional shared theme, all optional and configurable.
  Motivated by the PyTexas sites, where pytexas.org and its meetup site share a theme and the 2027 conference site does not.
- Config from environment variables (for example `BARTLEBY_SITE__BASE_URL`, as Hugo does) (2026-10-11): `--set` covers CI for now; add a third layer only when someone asks.
- Skill generation rework (2026-10-11): not in the Goal 8 plan; it gets its own plan section later.
  Generate skills for agents in general, not only Claude Code's layout, and only when a flag asks for it (`generate-skill` is already a separate command, and `ai.skills.regenerate_on_build` defaults to off).
- Any 0.2.0 feature work.

## Component boundaries

The implementation is 34 single-responsibility modules under `src/bartleby/`, grouped by build-pipeline phase.

Config layer:
- `config.py`: load and validate `bartleby.yml`.
- `authors.py`: author definition loading, validation, and resolution.
- `errors.py`: the shared `file: key path: message (fix: hint)` formatter behind every structured error.

Content layer:
- `content.py`: content discovery, front matter parsing, and page data objects.
- `metadata.py`: build-time metadata validation against content-type schemas.
- `urls.py`: URL generation from content-type config and front matter.

Rendering:
- `markdown_pipeline.py`: the Markdown rendering pipeline with all default extensions.
- `shortcodes.py`: `[% %]` shortcode preprocessing rendered as Jinja2 fragments.
- `templates.py`: the Jinja2 environment, template lookup cascade, and context building.
- `crossrefs.py`: cross-reference resolution, rewriting `.md` links to output URLs.

Structure:
- `navigation.py`: navigation from config or auto-generated from directory structure.
- `taxonomies.py`: term collection, page mapping, and taxonomy page generation.
- `listings.py`: content-type listing page generation.
- `pagination.py`: splitting listings into pages.

Output:
- `search.py`: client-side search index for lunr.js.
- `feeds.py`: RSS 2.0 and Atom 1.0 feeds, per content type and site-wide.
- `sitemap.py`: `sitemap.xml` and `robots.txt`.
- `seo.py`: Open Graph, Twitter Card, and canonical-URL meta tags.
- `assets.py`: static file copying and co-located asset handling.
- `icons.py`: icon pack management, resolution, and build-time tree-shaking.

Agent surface:
- `llm.py`: `llms.txt`, `llms-full.txt`, per-page Markdown variants, and JSON-LD.
- `agent_surface.py`: `schema.json` and `content-index.json` build artifacts.
- `schema_introspection.py`: derive content-type, author, and taxonomy schemas.
- `content_query.py`: list and get discovered pages with curated fields.
- `skills.py`: deterministic agent-skill generation (`bartleby-write` / `review` / `ops`).
- `export.py`: serialize published pages as JSONL, JSON, or CSV.

Theme:
- `theme_compile.py`: resolve the Tailwind standalone binary and compile the resolved theme's CSS, emitting `theme.tokens` as CSS custom properties.
- `theme_loader.py`: manifest parsing, name/path/package resolution, the `extends` chain, and the eject and inspect operations.
- The `themes/` package (replacing the former `theme/` package): the bundled `base`, `material`, and `scrivener` themes, each a complete theme directory.

Quality and plugins:
- `linting.py`: content quality checks (broken links, missing descriptions, orphans).
- `plugins.py`: base classes, hook dispatch, and `hooks/` directory discovery.

Orchestration and surfaces:
- `build.py`: the build pipeline orchestrator wiring all components together.
- `output.py`: structured result dataclasses plus a text/JSON formatter.
- `cli.py`: the argparse CLI commands.
- `server.py`: the dev server with live reload, file watching, and a full rebuild on every change (moving to Starlette and uvicorn with same-port reload under Goal 8).

## Success criteria

The stabilization is complete, and 0.2.0 work may begin, when all of the following hold.

- The theme system works end to end: `theme.name`, `theme.path`, and `theme.package` select a theme; `extends` composes; `eject` and `inspect` expose the whole resolved system; the bundled themes resolve through the same loader as a path theme.
- Both `material` and `scrivener` render a polished, professional-looking site out of the box, verified in a browser across home, listing, post, docs page (sidebar and table of contents), taxonomy, and 404 pages, with no custom CSS, and switching between them from config changes the look and nothing else.
- The docs site builds and renders cleanly, looks good, and is fit to be the public showcase for the project.
- A newcomer can go install, scaffold a site, add content, build, serve, and see a good-looking result without hitting rough edges; errors are clear and actionable.
- The agent surface is complete and consistent: every published page has a valid Markdown variant and JSON-LD; `llms.txt`, `schema.json`, and `content-index.json` are correct and documented; generated skills reflect the site's real shape.
- The public interfaces (hooks, config schema, template context, agent output formats) are documented and stable enough to build on.
- `bartleby new site` then `bartleby serve` gives a three-column docs site with a working feature tour from a small `bartleby.yml`, `--full-config` lists every accepted option, and `bartleby enable blog <name>` adds a blog whose RSS and Atom feeds carry entries.
- `just check` is green, and `bartleby-ssg` installs and runs from a clean environment.
- Mason is willing to send it to people and show it off. This is the governing bar.
