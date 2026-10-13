# Changelog

All notable changes to Bartleby are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed (Breaking)

The scaffold from `bartleby new site` is now a docs site, not a blog.
A new site has a home page, a feature tour, and a small `bartleby.yml` with no content types.
The blog is opt-in: run `bartleby new site --blog`, or `bartleby enable blog <name>` on an existing site.
Anything that scripted the old scaffold and expected `content/blog/` or a sample post must pass `--blog`.

A key left null in `bartleby.yml` now reads as its default, the same as leaving the key out.
A bare `enabled:` on a content type, `site.feed.enabled:`, and the `ai.*` flags that default to true used to read as false.
A null `site.title` or `site.url` used to become the string "None" and is now treated as missing.
Write `false` to turn a flag off.

The `on_serve` hook now receives a `uvicorn.Server` instead of an `http.server.ThreadingHTTPServer`.
A plugin that read attributes of the old server object sees a different type.
The hook is typed `object`, so the signature is unchanged.

`bartleby enable blog <name>` writes `rss` and `atom` under the content type's `feeds`.
Each enabled blog now publishes its own RSS and Atom feeds, and the combined site feed includes it.
A disabled content type produces no output on any surface: no listing, pages, feeds, taxonomy pages, `schema.json` entry, or generated skill.

The default theme is now `scrivener`, which replaces the old built-in look.
Set `theme.name: material` to keep an indigo, mkdocs-material style layout.

The `theme:` section of `bartleby.yml` now uses Bartleby-native names.
Old mkdocs-material names are a `ConfigError` that names the replacement.

| Old | New |
| --- | --- |
| `theme.features: navigation.tabs` | `nav.tabs` |
| `theme.features: navigation.sections` | `nav.sidebar` |
| `theme.features: navigation.indexes` | `nav.section-index` |
| `theme.features: navigation.top` | `nav.back-to-top` |
| `theme.palette` (for example `primary`, `accent`) | `theme.tokens` (for example `color.primary`, `color.accent`) |
| `theme.font` (for example `text`, `code`) | `theme.tokens` (for example `font.text`, `font.code`) |

The native feature names are `search`, `search.highlight`, `nav.tabs`, `nav.sidebar`, `nav.toc-fold`, `nav.section-index`, `nav.back-to-top`, `content.code.copy`, and `color-mode.toggle`.
Any other mkdocs-material feature (`navigation.footer`, `navigation.tracking`, `content.code.annotate`, `content.code.select`, `content.tabs.link`, `content.tooltips`, `content.footnote.tooltips`, `content.action.edit`, `content.action.view`, `search.suggest`, `search.share`, `toc.follow`) is not a Bartleby feature and is rejected.

`page.excerpt` is now plain text, and the rendered excerpt moved to `page.excerpt_html`.
Listings render the HTML; feeds and `llms.txt` use the plain text.
A theme template that printed `post.excerpt | safe` must print `post.excerpt_html | safe`.

### Removed (Breaking)

`theme.color_mode.toggle` is a `ConfigError`.
The `color-mode.toggle` feature is the only switch for the light and dark toggle.
`ai.skills.include_examples` is a `ConfigError`, because generated skills never included examples.
`bartleby serve --dirty` is gone.
Incremental rebuilds are a non-goal, and the flag always ran a full rebuild.

### Added

`bartleby new site` prints what it created and the exact next command, with the path quoted when it holds a space.
`bartleby serve` prints the build summary, the bound URL, and how to stop, after the socket binds, so `--port 0` shows the real port.
`serve --events` opens with a matching `ready` object, and `--output json` carries the same data as text.

`--full-config` on `bartleby new site` writes every option Bartleby accepts, each at its default with a one-line comment, on top of the minimal scaffold's config.
The site name, the `nav`, and the six starter theme features are kept, and the `content_types` and `taxonomies` blocks are a commented-out example rather than live keys, so the site builds the same pages as the minimal scaffold and `schema.json` lists no `example` type.
It is generated from `CONFIG_SCHEMA`, the one schema behind config validation, `config schema`, and the configuration reference, and a test fails when any accepted key is missing from it.

`--set key.path=value` on `build`, `serve`, and `validate` overrides config for one run without touching the file.
The key must be one the schema lists or sit under an open mapping (`markwright`, `theme.tokens`, `theme.icon_packs`, `ai.robots`); a misspelled key is an error that names the closest known one.
A string key takes the text as typed, and every other key parses the value as YAML and checks it against the key's type, so `--set site.title=Yes` is the text `Yes` and `--set dev_server.port=notaport` is an error naming the expected type.
The value goes through the same validator as the file, and an error names `--set` as its source, cross-field errors on a parent key (`theme: set only one of name, path, or package`) and markwright errors included.
A token name keeps its dots: `--set theme.tokens.color.primary=red` sets the one token `color.primary`.
`--base-url` overrides `site.url` for one run, so canonical and absolute URLs use it; it must be an absolute `http` or `https` URL with a host.
Environment-variable overrides are not part of this release.

The new `bartleby config` command group reads and writes config.
`config show` prints the resolved config with the source of each value (default, file, or `--set`).
`config get` prints one key and exits non-zero on an unknown key.
`config set` types the value by the key as `--set` does, validates the edited config (the `markwright` section included), and writes it into `bartleby.yml` with the file's comments, key order, byte order mark, and line endings intact, replacing the file in one step.
A read-only file, an unwritable directory, a `--config` path that is a directory, a repeated key, and a tab indent are each a `config_error` with a fix, not a traceback.
`config schema --output json` lists every key with its type, default, allowed values, and a one-line description.

`bartleby enable <content-type> <name>` adds a content type to `bartleby.yml`, and appends a `nav` entry when `nav` is explicit and has none, so the listing is reachable.
`bartleby disable <name>` sets `enabled: false` and keeps the block and the `nav` entry; it takes no shape, because the block is already in the file.
`bartleby new post --type <name>` on a disabled type is a usage error whose fix reads `run bartleby enable blog <name>`, and `bartleby schema <name>` reports `enabled: false` for it.
`enable` merges the config a blog needs, and running it twice changes nothing.
A site can enable the same shape more than once, so `bartleby enable blog tutorials` adds a second blog at `tutorials/`.

A `markwright:` section in `bartleby.yml` has the same shape as `markwright.toml`.
Bartleby validates it and passes it to the extensions through markwright's public config API, so it never reimplements markwright's schema.
A `markwright.toml` or `[tool.markwright]` table is ignored with one warning.
Embeds load eagerly by default.
A site opts into click-to-load per embed with `load: click`, and both bundled themes ship the script and styles that swap the preview for the embed.
Those assets load only on pages that print a click preview.

The dev server serves the theme's `404.html` for missing pages.
An enabled content type with no published posts writes a valid empty feed, so the alternate link a page advertises never returns 404.

A new `ACKNOWLEDGMENTS.md` credits every bundled library and icon pack, the Lucide-derived sun icon, and the projects that shaped the design, each with its license and a compatibility verdict.
It ships in the wheel's license files.
`THIRD-PARTY-NOTICES` now records htmx as Zero-Clause BSD (it said BSD 2-Clause) and Alpine.js with its upstream copyright years.

Docs pages now read as three columns in both bundled themes: the section navigation on the left, the page in the middle, and the page table of contents on the right.
Below 76rem the table of contents hides, and below 60rem the navigation folds behind a toggle.
A listing has no headings, so it gets two columns instead of an empty third.
The new `nav.toc-fold` feature folds the table of contents into the left navigation.
The current page's headings appear under its own entry in the tree, and the right column goes away.
`nav.tabs` already moves top-level sections into header tabs, so there is no second flag for that layout.
A header nav item for a section with no URL of its own now links to the section's first page, for every site, with or without `nav.tabs`.
On narrow screens the header nav wraps to its own scrolling row, code blocks scroll inside their box, and wide tables scroll inside theirs.

The feature tour at `content/tour/index.md` shows every markwright and pymdownx feature as its source followed by the live result, with embeds loading eagerly.
The scaffold README shows how to opt into click-to-load with `load: click` under `markwright:`.
`bartleby new site --blog` uses the same block as `bartleby enable blog blog`, and it combines with `--full-config`.

The new `config_edit` module is the one writer behind `config set`, `enable`, and `new site --full-config`.

markwright emits class hooks and ships no CSS, so both bundled themes now style them.
`scrivener` and `material` each skin fence labels and secondary labels, the five fence environments, command, super-user, custom and line-number prefixes, highlight marks, YouTube, CodePen, Twitter and Instagram embeds, the slideshow, and the image compare, in light and dark mode.

The docs now cover the configuration and layout surface.
The configuration reference lists every `bartleby.yml` key with its type, default, allowed values, and required flag, and a test regenerates that list from `CONFIG_SCHEMA` and fails when the page differs.
Three new guides cover enabling content types, configuring markwright and click-to-load embeds, and configuring from the command line.
The CLI reference documents `--set`, `--base-url`, `config`, `enable`, `disable`, the `new site` and `serve` output, and the `ready` event on the `--events` stream.
The themes reference documents the three-column layout, `nav.toc-fold`, and the phone-width behavior.

- `theme.name`, `theme.path`, and `theme.package` select a theme; set at most one.
- `theme.tokens` is a flat map of dotted design-token names to CSS values.
- A feature enabled in `theme.features` that the active theme does not implement logs a build warning.
  The build still succeeds.
- The single hardwired `theme/` package is replaced by a theme system.
  A theme is a directory with a `theme.yml` manifest, and it can build on another theme with `extends`.
- Three themes ship with Bartleby.
  `base` holds the shared templates, scripts, and icons that every other theme builds on.
  `material` is an indigo header bar, navigation tabs, a section sidebar, and a table of contents, in the style of mkdocs-material.
  `scrivener` is the default: a plain reading layout in the system sans, neutral colors, and one accent for the current page, with a light and a dark palette.
- Both `material` and `scrivener` ship compiled CSS, so a site builds with no Tailwind install and no custom CSS.
  Each has a section sidebar that folds behind a toggle on narrow screens, search with `?h=` result highlighting, and a color-mode toggle.
- `bartleby theme eject` copies the active theme, flattened, into one editable directory (`themes/<name>` by default; `--to` and `--force` are available).
  Point `theme.path` at that directory and edit the templates directly.
- The color-mode toggle in both bundled themes is a switch with a sun and a moon icon, shared from `base` as `partials/color_mode_toggle.html`.
- `bartleby new site` writes a `README.md` with the commands and the project layout.
- `bartleby theme inspect` lists every theme file with the layer that provides it, so you can see which files a project, an ejected theme, or a bundled theme supplies.

### Changed

The dev server now runs on Starlette and uvicorn.
Pages and the live-reload WebSocket share one port, so the reload script connects to the page's own host and port.
A busy port fails fast with a `--port` hint before any build runs, and `--port` must be 0 to 65535.
A rebuild that hits a labeled error reports it and keeps the watcher alive.
`serve` takes `--set` and `--base-url` along with the flags it had before.
Changes that land within 100 ms of each other are one rebuild and one reload, so an editor's save (probe, rename, write, unlink) no longer runs seven builds.
The `rebuild` event carries `output_dir`, and `output_dir` in `ready`, `rebuild`, and `bartleby build` is the path the build wrote: relative to the project when under it (`build/site/`), absolute otherwise, instead of the directory's bare name.
The server watches the selected theme's directories, a `theme.path` inside or outside the project, and rebuilds when a theme template, static file, or manifest changes.
In text mode a failed rebuild prints each error to stderr and a good one prints `Rebuilt N pages in X ms`.
Changing `output_dir` while serving moves the output and the serving to the new directory.

`pymdownx.tabbed` now defaults to `alternate_style`, so content tabs render in the shape both themes style.
A `markdown_extensions` override for an extension Bartleby configures (`pymdownx.tabbed`, `pymdownx.arithmatex`, `pymdownx.emoji`) merges over the bundled options instead of replacing them, so setting one key keeps the rest.
The tour's Critic Markup source block prints the literal markers instead of being processed itself.

`pymdownx.arithmatex` runs in generic mode.
Inline math is `<span class="arithmatex">\(...\)</span>` and a block is `<div class="arithmatex">\[...\]</div>`, which MathJax 3 and KaTeX's auto-render script typeset as they come; before, the output was MathJax 2 `<script type="math/tex">` markup that neither reads.
Both themes center a math block and let it scroll sideways.

`pymdownx.emoji` renders `:smile:` as the character itself (the `twemoji` index with the `to_alt` generator).
Before, every emoji was an `<img>` fetched from an EmojiOne CDN when the page opened.
A site that wants images sets `emoji_generator` to a dotted path such as `pymdownx.emoji.to_svg` under `markdown_extensions`; `emoji_index` takes a dotted path the same way.

The `markwright` section's `warn` is on unless the site sets it to `false`.
With `fence.allowed_environments` set, a page that names an environment outside the list gets one build warning per name, with the page and a fix; before, the directive stayed in the code block as text with no message.

Errors name the file, the key path or id, and a concrete fix, in one shape: `<file>: <key path>: <message> (fix: <hint>)`.
`bartleby.yml` now rejects unknown top-level keys, unknown metadata field types, and a non-list `choices`.
Invalid YAML in `bartleby.yml`, `.authors.yml`, `theme.yml`, and page front matter is a clean error, not a traceback.
A duplicated author id is an `author_error`.
A build with no `content/` directory fails and says how to fix it.
A page that would overwrite `schema.json` or `content-index.json` is an `agent_surface_error` with exit code 1.

`--quiet` hides warnings and the text confirmation of `new`, `build`, and `generate-skill`.
`--verbose` logs per-phase progress to stderr, and the two flags cannot be combined.
`ai.skills.regenerate_on_build` rewrites the skills after `bartleby build`.
`theme.logo` and `theme.favicon` render in all three bundled themes.
They are paths relative to `static/`, or full URLs.

`llms.txt` and `llms-full.txt` use absolute URLs, and each page summary is one line.
`urls.absolute_url` is the one place that builds an absolute URL, so the sitemap, feeds, SEO tags, `llms.txt`, and `content-index.json` agree.
`schema.json` has a `theme` block with the theme name, its `extends` chain, and three feature lists: `enabled`, `implemented`, and `active`.
`active` is the intersection and is the list an agent should rely on.
The four agent files are byte-identical across builds of the same content.

Generated skills (`bartleby-write`, `bartleby-review`, `bartleby-ops`) are built from the same introspection as `schema.json`.
They list real source directories, fields, authors, taxonomy terms, the active theme and its feature split, and commands with their real flags.
Generated skills contain no placeholders.

`export --include-html` returns real rendered HTML from the build's own render path.
During that export `on_startup` receives `"export"`, and the page hooks fire.

The public reference docs (hooks, config schema, template context, CLI, theme manifest, agent output formats) were corrected against the code.
`tests/test_docs_reference.py` compares 28 surfaces in both directions, so a change to code or docs that drifts apart fails the suite.
The docs site builds on the Scrivener theme, with a corrected listing, excerpt, and tag display, and a new `errors.md` reference page.

### Fixed

- `output_dir` set to `.`, `..`, `content`, or any other directory the build reads is a `config_error` with a fix, from the file and from `--set`.
  Before, the build deleted the project before failing on the missing staging directory.
  The build itself refuses to replace an output directory that holds `bartleby.yml` or `content/`, as a last guard.
- The output swap moves the old output aside, moves the new one in, and only then deletes the old one, so a failed move leaves the previous output in place and no request lands on an empty directory.
  Before, the old output was deleted first.
- A symlinked `output_dir` keeps the link and replaces its target.
  Before, the build died on "Cannot call rmtree on a symbolic link".
- The output directory gets the mode a plain `mkdir` would under the current umask.
  Before, it was always `0700`, because the staging directory came from `mkdtemp`.
- A rebuild that fails outside the labeled errors, such as a hook file with a syntax error or a `bartleby.yml` missing mid-save, is reported with the exception's type and message and the watcher stays alive.
  Before, the watcher thread died and `serve` never rebuilt again, in silence.
  The `--events` contract holds: a `change` is always followed by a `rebuild` or an `error`.
- The dev server serves a page in any encoding and returns 404 when a page vanishes between the lookup and the read.
  Before, a Latin-1 file and a mid-swap request were each a 500 with a traceback.
- `serve --port 70000` is a usage error, and `--host ::1` binds an IPv6 socket.
  Before, the first was an `OverflowError` traceback and the second failed with a wrong port hint.
- Deleting or moving a whole directory out of the project rebuilds.
  Before, directory events were dropped.
- `build(..., dry_run=flag)` accepts a `bool` variable under mypy; only literal `True` and `False` were typed before.
- Every published page has a Markdown variant, including pages with an empty body.
  The `text/markdown` alternate link renders only when the variant exists, so `ai.markdown_variants: false` no longer leaves a link that returns 404.
- JSON-LD is `Article` for posts, `CollectionPage` for generated listing and taxonomy pages, and `WebPage` otherwise.
  Each carries `name` alongside `headline`.
- Any build or `export --include-html` `BuildError` after `on_startup` now fires `on_build_error` and then `on_shutdown`, once each.
  That includes a missing `content/` directory, metadata validation, a strict-mode cross-reference failure, and an asset collision.
  Before, some of these skipped both, so a plugin that opened a resource in `on_startup` never got to release it.
- A successful `export --include-html` fires `on_shutdown` exactly once, as a build does.
- Relative `.md` links in a listing intro (`content/{type}/index.md`) now resolve to the target page's URL.
  Before, they were left as `.md` links that returned 404.
- Excerpts no longer show literal backticks and other Markdown syntax (see the breaking change for `page.excerpt` above).
- Taxonomy pages scoped to a content type are titled by their scope ("Tags in Guides"), so they no longer look like duplicates of the global tag pages.
- A listing row for a page without a date drops the date column in `scrivener`.
- Posts with no date, author, or reading time no longer render an empty meta paragraph under the title.
- Posts and listings in both bundled themes now get the section sidebar and table of contents that pages get.
  The sidebar needs the section's pages listed under it in `nav`, because `nav` keeps a content-type directory as one link.
- With `nav.tabs`, `nav.sidebar`, `nav.section-index`, and `nav.toc-fold` all on, a section's index page keeps its table of contents in both themes: the sidebar title links to the index page and the headings fold under it.
  Before, the fold removed the right column and the sidebar printed nothing, because the index page is not repeated as a child under `nav.section-index`.
- `bartleby new site` quotes the site name for YAML, so a name with a double quote or a backslash lands in `site.title` as typed, and a failure after the directory is made removes it so a retry does not stop at "already exists".
- `schema.json` lists only the taxonomies an enabled content type uses.
  Before, a taxonomy that only a disabled type opted into appeared with no terms while its pages were not built.
- Live reload works: the injected script connects to the page's own host and port.
- A string key left null in `bartleby.yml` (`output_dir:` with nothing after it) reads as its default instead of the text `None`, so a build never writes into `None/`.
- `site.url` is validated: it must be an absolute `http` or `https` URL with a host, so the sitemap never carries `<loc>/</loc>` or a scheme-less address.
- A key written twice in one mapping is rejected with its line number, where PyYAML used to keep the second value silently; `bartleby validate` and `config set` now agree.
- A YAML date in a `config set` or `--set` value is carried as its ISO text, so `config set markwright.x 2026-01-01` no longer crashes in `json.dumps`.
- A markwright error names the config file that was loaded (`--config other.yml`) or `--set`, instead of a hard-coded `bartleby.yml`.
- One file edit triggers one rebuild.
  The watcher ignores open and close events, so the build reading its own sources no longer starts another build.
- `bartleby serve` flushes its startup line, so the URL shows up when output is piped.
- Highlighted code is colored in both bundled themes, in light and dark mode.
  The Pygments token classes under `.highlight` had no CSS, so every block rendered in one color.
  `scrivener` uses a quiet palette with one blue for keywords, and `material` uses its violet, green, orange, blue, and teal code colors.
  Every color holds a 4.5:1 contrast ratio on the code background.
- A non-integer `site.feed.limit`, `content_types.<name>.pagination.per_page`, or `dev_server.port` is a labeled error with a fix hint, from the file, `--set`, and `config set`.
  Before, `--set site.feed.limit=oops` printed a Python traceback.
- A boolean key set to anything but `true` or `false` is a labeled error.
  Before, `maybe` was read as true.
- A scalar where a list belongs is a labeled error that says a list is expected.
  This covers `theme.features`, `exclude_patterns`, `plugins`, `extra_css`, `extra_js`, `markdown_extensions`, `nav`, `content_types.<name>.taxonomies`, `content_types.<name>.feeds`, `ai.robots`, and `ai.agent_context.constraints`.
  Before, `--set theme.features=bogus` reported an unknown feature `b`, and several of these keys ignored the value without a word.
- `theme.color_mode.default` accepts only `light` or `dark`, and `site.feed.formats` and a content type's `feeds` accept only `rss` and `atom`.
  The allowed values come from the same list `config schema` prints.
- `taxonomies.<name>.slug_format` must be a string.
  `config set taxonomies.tags.slug_format '{slug}'` used to store a YAML mapping, so quote the pattern: `config set taxonomies.tags.slug_format '"{slug}"'`.
- `bartleby build` and `serve` report an unwritable project directory or output directory as a labeled error that names the directory and suggests `chmod` or `output_dir`, instead of a traceback.
  An `output_dir` on another filesystem no longer raises a traceback either.
- The docs site enables `feeds` for guides, so its feed links lead to feeds with entries.

### Dependencies

- markwright is now `>=0.3.0` (was `>=0.1.0`).
  Rendered output is unchanged for Bartleby's docs; 0.3.0 adds the public config API and click-to-load embeds that Bartleby will use, and fixes fence directives inside list items and indented fences.
- pymdown-extensions is now `>=11.0.1` (was `>=10.0`), the first release without PYSEC-2026-3654.
  The lock resolves 12.2, which escapes quotes in highlighted code as `&quot;` and `&#39;`, which a browser renders as the same text.
- pydantic arrives as a transitive dependency of markwright 0.3.0.
- ruamel.yaml (`>=0.19.1`) is new.
  Its round-trip loader writes `bartleby.yml` without losing the comments and key order in a file you wrote by hand.
- starlette (`>=1.7.0`) and uvicorn (`>=0.54.0`) are new, for the dev server.

## [0.1.0] - 2026-10-05

### Fixed

Remediation cycle addressing 20 confirmed findings from a multi-agent code review of the v1 branch (R1 through R17 in `spec.md`; some requirements cover more than one defect). R2 through R17 (19 findings) were code or test fixes; R1 was re-verified on the project's pinned Python 3.14 and dispositioned as not-a-defect (see below).

- R1 (CLI importability) does not reproduce on Python 3.14: PEP 758 legalizes the unparenthesized `except` tuple in `linting.py`, so the CLI already imports cleanly on the pinned interpreter and `linting.py` is left unchanged. An import-health regression gate (`tests/test_import_health.py`) was added so a real future import or syntax error in any module still fails the suite.
- `bartleby theme compile` always failed on a clean machine because the release checksum map was empty.
- CLI failures could surface a raw Python traceback instead of a clean, structured error.
- `bartleby serve` now serves the configured `output_dir`, not a hardcoded `site/`, and live reload is fully wired: a watchdog observer triggers rebuilds and a WebSocket channel reloads the browser.
- Cross-references now resolve before the lint orphan pass runs, so a page linked only via a `.md` crossref is no longer reported as orphaned.
- Draft pages and their co-located assets are excluded from production output everywhere, including the previously-missed shared-directory asset path; two pages sharing a bundle directory with a co-located asset now fail the build loudly instead of guessing an association.
- JSON-LD output is valid even when a page title contains characters that could break naive string interpolation (embedded quotes, `<`, `>`, `&`).
- Icon pack defaults merge with project overrides instead of being replaced by them.
- Listing intro content (`content/{type}/index.md`) now renders as HTML instead of being dropped.
- Shortcode protection covers multi-backtick inline code spans, not just single-backtick ones.
- Shortcode discovery checks all three documented lookup locations instead of only one.
- The aggregate site-wide feed is advertised in `schema.json`.
- The `hooks/` `sys.path` insertion is scoped to the discovery loop instead of leaking into the rest of the process.
- The temporary build directory is always cleaned up, including on a failed build.
- `static_file_count` counts only files actually copied, not every candidate considered.
- The end-to-end smoke test now exercises a custom `output_dir`, a draft page with a co-located asset, and a quoted title through both a build and a serve cycle, so this class of regression fails the smoke gate again if it recurs.

## [0.1.0] - 2026-06-23

First public release. Bartleby builds Markdown content into a static site with
search, feeds, taxonomies, an LLM-readable output layer, and an agent CLI.

### Added

#### Content and rendering

- Markdown rendering via Python-Markdown, pymdownx, and do-markdown, with the
  do-markdown fence preprocessor ordered ahead of pymdownx superfences.
- YAML front matter parsing into typed dataclasses, with author resolution and
  byline support.
- Co-located page assets (Hugo-style page bundles) that follow the page output
  URL rather than the source path.
- Shortcodes via `[% ... %]` syntax backed by Jinja2 fragments.
- Cross-references: relative `.md` links rewritten to output URLs.
- Five-level template lookup cascade with per-page `template:` overrides.
- Taxonomies (global and per-content-type), listing pages, and pagination.

#### Theme

- Built-in Material-style theme with dark mode.
- Vendored Alpine.js, HTMX, and lunr.js bundles with recorded versions and
  licenses (`THIRD-PARTY-NOTICES`).
- Hybrid Tailwind pipeline: package-built CSS shipped by default, with a
  `bartleby theme compile` command that resolves, caches, and SHA-256-verifies
  the standalone Tailwind CLI. The build prefers a compiled `.bartleby/theme.css`
  with no implicit download.
- Full icon packs with build-time tree-shaking; unused packs emit zero files.

#### Output layer

- Client-side search backed by a JSON index consumed by lunr.js.
- RSS 2.0 and Atom 1.0 feeds per content type plus a site-wide aggregate feed
  (`site.feed`) with contextual auto-discovery.
- Sitemap (plus gzipped variant) and `robots.txt` with AI-crawler directives.
- SEO output: Open Graph, Twitter Card, canonical URLs, JSON-LD.
- LLM output: `llms.txt`, `llms-full.txt`, and a Markdown variant alongside
  every HTML page.
- Standalone `404.html`.
- Static agent surface: `schema.json` and `content-index.json`, with curated
  public fields, per-page alternate links, and an `ai.agent_surface` toggle.

#### Plugin system

- All 16 plugin hook events fire with the documented arguments and return-value
  semantics; `BasePlugin` exposes matching no-op methods.
- Plugin discovery from `hooks/*.py` and from `bartleby.plugins` entry points,
  merged through one registration path with priority-then-registration ordering
  and a config disable list. Hook files can import sibling helper modules.

#### CLI and agent surface

- Commands: `new site`, `new post`, `build`, `validate`, `serve`, `theme
  compile`, `schema`, `content list`, `content get`, `render`, `lint`, `export`,
  `generate-skill`.
- `--output json` on every command, with stable result shapes and exit codes.
- `build --dry-run` reports what would be written without touching the output
  directory.
- Schema introspection for content types, authors, and taxonomies (public
  author fields only).
- `lint` checks broken links, missing descriptions, and orphan pages, with
  opt-in `--check-external`.
- `export` to JSONL, JSON, and CSV; deterministic skill generation.

#### Dev server

- Live reload with full rebuild on change across all watched paths, hook and
  config reload, last-good-build retention on failure, and an `--events` JSON
  stream. Reload wiring is serve-only and absent from production builds.

#### Build semantics

- Per-page errors are collected rather than failing on the first; the existing
  output directory is left untouched on failure and replaced via an atomic swap
  on success. Config errors fail fast.
- Clean error reporting (no traceback) with `BARTLEBY_DEBUG` to re-enable
  tracebacks; `on_build_error` fires once with the collected list.
- Configurable output directory (no longer hardcoded to `site/`).
- `validate` dry-runs URL generation and checks template existence for
  `template:` overrides and cross-references.

### Project

- Licensed under MIT.
- Python 3.14+, managed with uv; ruff, mypy (strict), and pytest for quality.

[Unreleased]: https://github.com/MasonEgger/bartleby/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/MasonEgger/bartleby/releases/tag/v0.1.0
