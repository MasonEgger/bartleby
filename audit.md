# Bartleby Audit

Running record of findings from the post-implementation evaluation framework
in [`review.md`](review.md). Each section corresponds to one numbered test.

## Outstanding work — tracker

All issues across this audit at a glance. Detailed notes in each test
section below.

| ID | Severity | Area | Title | Status |
|---|---|---|---|---|
| Bug 1 | HIGH | Templates | Author bylines empty on every blog post | ✅ FIXED 2026-06-02 |
| Bug 2 | HIGH | Templates | Listing + taxonomy term pages render empty | ✅ FIXED 2026-06-02 |
| Bug 3 | MEDIUM | Scaffolding | New-site config doesn't opt blog into tags | ✅ FIXED 2026-06-02 |
| Bug 4 | LOW | Output | Sitemap omits listing + taxonomy URLs | ✅ FIXED 2026-06-02 |
| Deferral 1 | HIGH | Theme JS | Alpine/HTMX/lunr bundles are 200-byte stubs — theme interactivity is dead | 🔴 OPEN |
| Deferral 6 | HIGH | Dev server | `bartleby serve` has no watchdog + no WebSocket — no live reload | 🔴 OPEN |
| Deferral 2 | MEDIUM | Theme CSS | "Tailwind" is hand-written CSS; docs/spec misrepresent the styling stack | 🟡 OPEN |
| Deferral 3 | MEDIUM | Icons | Only 4 sample SVGs ship; `get_icon_path` returns None for everything else | 🟡 OPEN |
| Deferral 5 | MEDIUM | Crossrefs | `--strict` flag was parsed and ignored | ✅ FIXED 2026-06-02 |
| Deferral 7 | MEDIUM | Plugin hooks | 12 of 17 declared events never fire — user handlers silently no-op | 🟡 OPEN |
| Deferral 4 | LOW | Async build | `async_build` is `asyncio.to_thread(build)` — no real CPU parallelism | 🟢 OPEN |
| Deferral 8 | LOW | Working tree | Pre-existing uncommitted spec/plan + test-only diffs | 🟢 OPEN |
| Hook config | — | Tooling | Session-scoped Stop hook re-fires on met goals and over-claims process gaps | 📝 [later.md](later.md) |
| Design 1 | LOW | Content | `parse_front_matter` matches `---` without requiring newline after; misparse possible on docs starting `---foo` | 🟢 OPEN |
| Design 2 | LOW | Content | `parse_front_matter` swallows non-dict YAML silently (no error surfaced) | 🟢 OPEN |
| Design 3 | MEDIUM | Templates | `build_page_context` flattens `Page` into a hand-built dict — closed schema is why Bugs 1+2 happened. Pass the dataclass directly | 🟡 OPEN |
| Design 4 | MEDIUM | Build | `on_pages` hook fires BEFORE draft filter — plugins operate on pages that will be discarded | 🟡 OPEN |
| Design 5 | MEDIUM | Build | No per-page error isolation — one bad page aborts the whole build with a stack trace | 🟡 OPEN |
| Design 6 | LOW | Plugins | `KNOWN_EVENTS` has 17 names; `BasePlugin` has 16 methods. `on_pages` is missing from BasePlugin | 🟢 OPEN |
| Design 7 | LOW | Build | Magic strings (`"listing_kind"`, `"taxonomy_kind"`, `"term"`, `"index"`) should be StrEnum or constants | 🟢 OPEN |

**Recommended ship-0.1.0 punch list (priority order):**

1. Deferral 1 — vendor real Alpine/HTMX/lunr bundles. Without them
   every advertised theme interaction is a no-op.
2. Deferral 6 — wire `watchdog.Observer` + `websockets` into
   `DevServer.run()`. The README implies live reload works; it
   doesn't.
3. Deferral 8 — commit the safe test/fixture diffs; review the
   spec/plan diffs and either commit them or drop the local changes.
4. Deferral 2 — either compile real Tailwind output (standalone
   CLI, no Node required) or reword the docs/spec to drop the
   Tailwind framing.

**0.2.0+ material:** Deferrals 3, 4, 7 + Design 3 (drop the
`build_page_context` dict adapter) + Design 4 (move `on_pages` past
the draft filter) + Design 5 (per-page error isolation). Design 1,
2, 6, 7 are nice-to-have polish.

---

## Test 1 — End-to-end smoke test

**When**: 2026-06-02
**Method**: Scaffolded a fresh site in `/tmp/bartleby-smoke/demo`, ran
`bartleby new site demo && bartleby new post "Hello" --type blog && bartleby build`,
inspected the rendered HTML, search index, llms.txt, sitemap, and Markdown
variants.

### What works end-to-end

- Scaffold (`new site` creates the correct skeleton — `bartleby.yml`,
  `.authors.yml`, `content/`, `templates/`, `static/`, `hooks/`)
- `new post` slugifies the title (`"Hello"` → `hello.md`) and writes a
  `draft: true` front matter stub
- Build runs in ~130ms producing 3 pages + theme assets + auxiliary files
- HTML5 structure: DOCTYPE, viewport meta, canonical, OG, Twitter Card
- Post body renders with TOC anchor IDs and the excerpt separator preserved
- `og:type=article` + `article:published_time` correctly emitted for blog post
- `og:type=website` for the static index
- Readtime calculated and shown (`1 min read`)
- Excerpt extracted (visible in llms.txt entry)
- Tag rendered in post footer
- Search index includes per-page entries plus per-section anchored entries,
  with `tags` propagated and a lunr-compatible config block
- Markdown variant published next to each HTML file (body only, no front matter)
- llms.txt structured by content type with excerpt-derived descriptions
- Sitemap, gzipped sitemap, and robots.txt all generated

### Bugs surfaced (prioritized)

#### Bug 1 — HIGH — Author objects not resolved into the template context

**Symptom**: A blog post with `authors: [default]` in front matter and a
matching `default` entry in `.authors.yml` renders an empty author line in
the default post template:

```html
<p>By
    
</p>
```

**Root cause**: `src/bartleby/templates.py::build_page_context` exposes
`"authors": list(page.author_keys)` — a list of strings, not resolved
`Author` objects. The default post template iterates and tries
`{{ author.name }}`, which is undefined on a string and renders empty
under Jinja2 autoescape.

**Why tests miss it**: `test_build.py` checks the rendered HTML file
exists. It never asserts on the byline. The Step 3 `resolve_authors`
function exists in `src/bartleby/authors.py` and is unit-tested, but
nothing in the build pipeline calls it.

**Fix sketch**:
- In `build.py`, call `resolve_authors(page.author_keys, authors)` and
  pass the resolved list into `build_page_context`.
- Or pass the `authors` dict into `build_page_context` and resolve there.
- Either way, `page_namespace["authors"]` becomes `list[Author]` so
  `{{ author.name }}`, `{{ author.url }}`, `{{ author.avatar }}` work
  in templates.
- Add an integration test that builds the fixture site and asserts the
  resolved author's name appears in the rendered post HTML.

**Files touched**: `src/bartleby/build.py`, `src/bartleby/templates.py`
(maybe), `tests/test_build.py` (new assertion).

---

#### Bug 2 — HIGH — Blog listing pages render an empty post list

**Symptom**: After building the smoke-test site (1 published blog post),
`site/blog/index.html` contains:

```html
<section>
  <h1>Blog</h1>
  <ul>
    <!-- nothing here -->
  </ul>
</section>
```

**Root cause**: `src/bartleby/listings.py::_build_listing_page` stuffs
the post list into `custom_metadata["posts"]`. The bundled list
template (`src/bartleby/theme/templates/defaults/list.html`) reads:

```jinja
{% set listed = paginator.items if paginator else page.posts %}
```

But `build_page_context` only hoists a fixed set of fields into the
page namespace (`title`, `description`, `date`, `content`, …). It
does *not* expose `custom_metadata` entries as page attributes, so
`page.posts` is undefined and the loop iterates over nothing.

The same is true for `page.intro_content` and `page.paginator`.

**Why tests miss it**: `test_listings.py` asserts that the
`custom_metadata["posts"]` list is correct on the virtual `Page`
object — but it never renders a template. The `test_build.py`
integration test checks that `site/blog/index.html` exists, but
not that it contains any posts.

**Fix sketch** (one or the other):
- **Option A**: In `build_page_context`, copy listing-specific
  `custom_metadata` keys onto the page namespace when the page is a
  listing (`page.custom_metadata.get("listing_kind") == "content_type"`).
  Same for taxonomy pages.
- **Option B**: Update the bundled list template to read
  `page.custom_metadata.posts` directly. (Less ergonomic for end users.)
- Add an integration assertion that the listing HTML contains at least
  one `<a href="...">` to each published post.

**Files touched**: `src/bartleby/templates.py` or
`src/bartleby/theme/templates/defaults/list.html`,
`tests/test_build.py` (new assertion).

---

#### Bug 3 — MEDIUM — Scaffolded `bartleby.yml` doesn't opt the blog type into the tags taxonomy

**Symptom**: After `bartleby new site demo` and writing a post with
`tags: [greeting]`, no `/tags/` or `/tags/greeting/` pages are
generated. A fresh user has no way to discover why.

**Root cause**: `src/bartleby/cli.py::_DEFAULT_CONFIG` declares
`tags` at the site level but does not include `taxonomies: [tags]`
under the `blog` content type. The taxonomy collector requires
explicit opt-in per content type.

**Why tests miss it**: `test_cli.py::test_new_site_valid_config`
verifies the generated config loads — it doesn't run a build against
a post with tags.

**Fix sketch**: Add `taxonomies:\n      - tags` to the `blog` content
type block in `_DEFAULT_CONFIG`. Document the requirement in the
[Taxonomies concept page](docs/content/concepts/taxonomies.md) more
prominently (it's already covered, but worth front-loading).

**Files touched**: `src/bartleby/cli.py`,
`tests/test_cli.py` (new assertion that a post with tags produces tag
listing pages after build).

---

#### Bug 4 — LOW — Sitemap omits listing pages and taxonomy pages

**Symptom**: `sitemap.xml` for the smoke-test site contains only
`/blog/posts/hello/` and `/`. It does NOT contain `/blog/`
(the listing page that exists on disk at `site/blog/index.html`).

**Root cause**: `src/bartleby/build.py` calls
`write_sitemap(pages, config.site, output_dir)` — using `pages` (real
pages only), not `all_pages` (which includes the virtual listing and
taxonomy pages).

**Why tests miss it**: `test_sitemap.py` only tests sitemap generation
in isolation with arbitrary page lists. The build integration tests
don't introspect the sitemap.

**Fix sketch**: Pass `all_pages` to `write_sitemap` instead of `pages`.
Same for `build_search_index` (so search results include landing /
listing pages) and `generate_llms_txt` (so agents can find listings).

Add an integration test asserting the sitemap contains the listing URL.

**Files touched**: `src/bartleby/build.py`, `tests/test_build.py`
(new assertion).

---

### Summary

| # | Severity | Surface | Impact | Status |
|---|----------|---------|--------|--------|
| 1 | HIGH | Templates | Author bylines broken on every blog post for every user | **FIXED 2026-06-02** |
| 2 | HIGH | Templates | Listing pages broken — biggest user-visible failure | **FIXED 2026-06-02** |
| 3 | MEDIUM | Scaffolding | Fresh-user friction; tags appear to do nothing until config is hand-edited | **FIXED 2026-06-02** |
| 4 | LOW | Output | Listing/taxonomy URLs not discoverable via sitemap | **FIXED 2026-06-02** |

**Test quality finding**: the integration suite checks file *existence*
but not file *content*. Bugs 1, 2, and 4 all passed CI because their
respective tests stopped at `(site / "blog" / "index.html").exists()`.
A small batch of "assert this string appears in the rendered HTML"
assertions would have caught all three.

**Fix details:**
- Bug 1: `build_page_context` now accepts an `authors` dict and resolves
  `page.author_keys` into `Author` objects via `_resolve_author_objects`.
  `build()` passes the loaded authors through.
- Bug 2: Listing and taxonomy templates read `page.custom_metadata.*`
  (`posts`, `intro_content`, `paginator`) directly. The list template
  also had a wrong attribute name — `post.url` → `post.output_url`.
  Taxonomy term pages now carry their associated pages in
  `custom_metadata["posts"]` so the term template can iterate the
  actual list rather than ALL site pages.
- Bug 3: `_DEFAULT_CONFIG` in `cli.py` now includes `taxonomies: [tags]`
  under the scaffolded `blog` content type.
- Bug 4: `write_sitemap` now receives `all_pages` (real + virtual)
  instead of `pages` (real only).

**Test quality fix shipped alongside:** added 5 new content-level
assertions to `test_build.py` covering byline rendering, listing post
links, sitemap URL inclusion, and taxonomy term page contents. Added
`test_new_site_blog_opted_into_tags` to `test_cli.py`. The integration
suite now exercises content, not just file existence.

**Verified end-to-end:** a fresh `bartleby new site demo && bartleby new
post Hello --type blog && bartleby build` produces 7 pages (was 3), the
post HTML contains `By Site Author`, the listing has `<a
href="/blog/posts/hello/">Hello</a>` with the excerpt, `/tags/`,
`/tags/greeting/`, `/blog/tags/`, and `/blog/tags/greeting/` exist, and
the sitemap lists all of them.

---

## Test 2 — Audit the deferrals

**When**: 2026-06-02
**Method**: For each deferred item flagged in review.md, verify the current
state on disk, then sweep all session summaries for `defer|stub|placeholder|
TODO|reserved|future|later` to surface anything I'd missed.

### Confirmed deferrals (8)

#### Deferral 1 — Vendored JS bundles are stubs

**Location**: `src/bartleby/theme/static/js/{alpine,htmx,lunr}.min.js`
**State**: Each file is 200 bytes — a comment plus
`console.debug && console.debug("X placeholder");`. Nothing actually
runs client-side.

**Impact**: Every generated site references these scripts in `<head>`
via `<script defer src="/js/alpine.min.js">` etc., but the search
modal, dark-mode toggle, back-to-top button, and TOC scroll spy all
silently do nothing in a browser. The HTML *looks* interactive (the
Alpine `x-data` attributes are emitted) but no JavaScript ever
upgrades the markup.

**Real fix**: Vendor the actual minified bundles. They're tiny —
Alpine.js v3 is ~16KB gzipped, HTMX is ~14KB gzipped, lunr.js is
~9KB gzipped. Total cost: one download, one commit.

**Severity**: HIGH (release-blocking — the theme advertises features
that don't work).

---

#### Deferral 2 — Tailwind CSS is hand-written, not compiled

**Location**: `src/bartleby/theme/static/css/main.css` (116 lines)
**State**: A small handwritten stylesheet with CSS custom properties
for light/dark, base typography, admonition variants, code blocks,
search modal, TOC sidebar, back-to-top button, responsive breakpoint,
grid cards, and an `.md-button` rule. No Tailwind. No PostCSS config.
No `tailwind.config.{js,ts}` anywhere in the repo.

**Impact**: The README, spec.md, and several doc pages talk about
"Tailwind CSS". The reality is hand-written CSS that *looks*
Tailwind-flavoured in places. A user expecting to extend the theme
via Tailwind utility classes will not find any.

**Real fix**: Either
- (a) wire up the standalone Tailwind CLI (no Node.js install
  required), commit a real `tailwind.config.js`, and have the theme
  build script compile `main.css` from sources, OR
- (b) reword the docs/spec to drop the Tailwind framing and describe
  the theme as "hand-written, designed to coexist with user-provided
  Tailwind/styled-components/etc."

**Severity**: MEDIUM (cosmetic misrepresentation; nothing renders
incorrectly).

---

#### Deferral 3 — Icon packs ship one SVG each

**Location**: `src/bartleby/theme/icons/`
**State**:
```
material/account.svg
fontawesome-brands/github.svg
octicons/heart-fill-24.svg
simple/python.svg
```
Four files total. `get_icon_path("material-heart", ...)` returns `None`
because `material/heart.svg` doesn't exist.

**Impact**: The icons module works correctly — tree-shaking, pack
opt-in, slug parsing — but a user trying to render even basic
icons gets a `None` back from the resolver for anything except the
four sample files.

**Real fix**: Vendor the real icon packs as a build-time step (or
even just as a one-off mass copy). Material Design Icons is ~7000
SVGs, FontAwesome Brands ~500, Octicons ~200, Simple Icons ~3000.
Bundling all of them is ~30 MB on disk; tree-shaking ensures only
referenced icons ship per-site. Alternatively, distribute the icon
packs as optional pip extras (`bartleby[icons-material]`).

**Severity**: MEDIUM (advertised feature unusable until real packs
arrive; the infrastructure is correct).

---

#### Deferral 4 — Async build has no real parallelism

**Location**: `src/bartleby/build.py::async_build`
**State**:
```python
async def async_build(config_path, *, include_drafts=False) -> BuildResult:
    return await asyncio.to_thread(build, config_path, include_drafts=include_drafts)
```
A one-line wrapper. No `ProcessPoolExecutor`, no `aiofiles`, no
`asyncio.gather` over the post-render outputs. The sync `build()`
is still the canonical implementation; the async wrapper just pushes
it onto a worker thread.

**Impact**: The CLI's `bartleby build` runs through `asyncio.run(async_build(...))`,
so the entry point looks async, but build time is identical to a
direct synchronous call. The doc claim "real CPU parallelism is
future work" is honest.

**Real fix**: Three pieces:
- Make `markdown.Markdown` instances picklable across processes (or
  reconstruct them per-worker from picklable config).
- Dispatch `markdown.convert()` calls to a `ProcessPoolExecutor`.
- Run post-render outputs (search index, feeds, sitemap, llms.txt) in
  parallel via `asyncio.gather`.
- Audit that plugin hooks never cross the process boundary.

**Severity**: LOW (current build is fast enough for small/medium
sites; revisit if build times bite).

---

#### Deferral 5 — Crossref errors silently dropped

**Location**: `src/bartleby/build.py` — calls
`resolve_all_crossrefs(all_pages, content_dir)` and discards the
returned errors list.

**Impact**: A page that links `[other](nonexistent.md)` will get
the error recorded (Step 13 tests verify this), but the error is
never printed, logged, or made buildgate-fatal. Authors deploy
sites with broken cross-references and never know.

**Real fix**: 
- Print each `CrossRefError` to stderr at build end.
- When the CLI is invoked with `--strict`, fail the build (exit 1).
- The `--strict` flag is already in `cli.py::_build_parser` — it's
  parsed and ignored. Wire it through to a `strict` parameter on
  `build()`/`async_build()`.

**Severity**: MEDIUM (silent data quality failure; affects every
multi-page site with internal links).

**Status**: **FIXED 2026-06-02**. `build()` and `async_build()` now
accept `strict: bool = False`. Crossref errors print to stderr in
both modes; `strict=True` raises `ValueError` after printing. CLI
wires `args.strict` through. Two new tests in `test_build.py` cover
both paths.

---

#### Deferral 6 — Dev server is just a static file server

**Location**: `src/bartleby/server.py`
**State**: `DevServer.run()` spawns a synchronous
`http.server.SimpleHTTPRequestHandler` bound to `site/`. That's it.
There is no `watchdog.Observer` import, no WebSocket server, no
asyncio loop. `DevServer.handle_change()` exists as a method that
tests call directly, but nothing in `run()` ever invokes it because
nothing watches the filesystem.

**Impact**: `bartleby serve` today:
- Runs an initial build (with drafts)
- Serves `site/` over HTTP
- **Never rebuilds on file change** (you have to Ctrl-C and re-run)
- **Never pushes a reload to the browser**

The README/docs imply live reload works. It doesn't. This is the
biggest gap between advertised behaviour and reality.

**Real fix**:
- Add `watchdog.Observer` to watch `content/`, `templates/`,
  `static/`, `hooks/`, `data/`, `bartleby.yml`, `.authors.yml`.
- On change: dispatch to `DevServer.handle_change()` (which already
  classifies the change and triggers a rebuild).
- Add a WebSocket server (the `websockets` library is already a
  declared dependency) that pushes a `reload` message after every
  successful rebuild.
- Inject a `<script>` snippet into served HTML that opens the
  WebSocket and `location.reload()`s on message.

**Severity**: HIGH (advertised core feature doesn't work; users
following the quickstart will be confused).

---

#### Deferral 7 — Most plugin hook events are "reserved"

**Location**: `src/bartleby/build.py` only calls 5 of 17 declared
events: `on_config`, `on_pages`, `on_env`, `on_page_markdown`,
`on_post_page`.

**Reserved-but-not-fired** (12): `on_startup`, `on_shutdown`,
`on_pre_build`, `on_files`, `on_nav`, `on_pre_page`,
`on_page_read_source`, `on_page_content`, `on_page_context`,
`on_post_build`, `on_build_error`, `on_serve`.

**Impact**: Users can register handlers against these events and
get no errors at discovery time, but their handlers never fire.
The plugin hook reference doc page (which I wrote) labels these
"reserved" — but the labeling lives in prose, not in code. A user
following plugin examples from a Bartleby tutorial elsewhere
(MkDocs hooks, e.g.) could easily register an `on_pre_build`
handler expecting it to run.

**Real fix**: For each reserved event, identify the right phase of
the build pipeline and add a `plugins.run_event(...)` call site.
Most are one-line additions. `on_files` and `on_nav` would need a
slightly bigger rework because the current pipeline doesn't have a
single discrete "files" or "nav" object you can hand to a hook.

**Severity**: MEDIUM (silent failures for users who register against
reserved events; consider raising on registration of an unsupported
event instead).

---

#### Deferral 8 — Uncommitted spec/plan/test changes in working tree

**State**: `git status` shows:
- `plan.md` — 186 lines changed (spec/plan refinements made before
  the implementation session began)
- `spec.md` — 156 lines changed (same)
- `tests/fixtures/configs/full.yml` — 7 lines added (extra_css and
  extra_js fixture entries)
- `tests/test_config.py` — 10 lines added (a `test_extra_css_and_js_parsed`
  test plus 2 assertions in `test_default_values_applied`)

The corresponding code changes (extra_css / extra_js fields on
`BartlebyConfig`) **were** committed at some point — `git diff
src/bartleby/config.py` is empty. So the test+fixture additions are
test-only and would land cleanly.

The plan.md and spec.md edits are larger and look like real spec/plan
refinements (template cascade widened from 5 to 6 levels, customization
seams documented, Step 21 redesigned to drop entry_points). Worth
committing as a "spec/plan refinements" commit — they're already
reflected in the implementation.

**Real fix**: Two commits:
1. `Add extra_css/extra_js test coverage` — stage `tests/test_config.py`
   and `tests/fixtures/configs/full.yml`. Safe.
2. `Refine spec.md and plan.md for customization seams and hook system`
   — stage `plan.md` and `spec.md`. Review the diff before committing
   in case any part of the refinement is now stale.

**Severity**: LOW (test-only diffs are pure improvement; spec/plan
diffs are documentation that's already true).

---

### Summary table

| # | Severity | Area | Real impact | Status |
|---|----------|------|-------------|--------|
| 1 | HIGH | Vendor JS | Theme interactivity (search, toggle, TOC, back-to-top) is dead on arrival | **OPEN** |
| 6 | HIGH | Dev server | `bartleby serve` doesn't actually reload — advertised feature missing | **OPEN** |
| 2 | MEDIUM | Tailwind | Docs misrepresent the styling stack | **OPEN** |
| 3 | MEDIUM | Icons | Icon resolver returns `None` for everything except 4 sample SVGs | **OPEN** |
| 5 | MEDIUM | Crossrefs | Broken internal links silently shipped | **FIXED 2026-06-02** |
| 7 | MEDIUM | Hooks | 12 of 17 declared events never fire; user handlers silently no-op | **OPEN** |
| 4 | LOW | Async build | API exists; CPU parallelism doesn't | **OPEN** |
| 8 | LOW | Working tree | Pre-existing uncommitted spec/plan + test-only diffs from before this work | **OPEN** |

## Test 3 — Test quality vs. test count

**When**: 2026-06-02
**Method**: Read every test file (27 files, 3777 lines, 275 tests). For
each, classified the assertion pattern: does the test exercise real
behavior, or does it verify shape/existence/string-matching? Cross-checked
findings against the smoke-test bugs from Test 1.

### Tier 1 — Strong (21 files, ~75% of test surface)

These exercise input → behavior → output cleanly. They drive the unit
under test with real inputs, inspect the resulting object structure or
output content, and would catch regressions on the public contract.

| File | Why it's strong |
|------|-----------------|
| `test_config.py` | Load real YAML fixtures, assert on parsed dataclass fields and validation error messages |
| `test_authors.py` | Load + resolve, assert structure |
| `test_content.py` | Parse front matter, check field mapping + exclusion patterns |
| `test_metadata.py` | Validate against schema, assert on `ValidationError.field` and `.message` |
| `test_urls.py` | Input page + content type → expected URL string. Pure behavior. |
| `test_pagination.py` | Drive `paginate()` with various counts, check the chunked output |
| `test_taxonomies.py` | Term collection + counts + slug formats |
| `test_navigation.py` | Tree structure, prev/next linking, sort order |
| `test_crossrefs.py` | Input HTML → expected rewritten HTML + error list |
| `test_shortcodes.py` | Input markdown → rendered template output |
| `test_search.py` | Input pages → JSON structure (per-page + per-section entries with tags) |
| `test_feeds.py` | Input pages → XML, **parsed with `xml.etree`** to verify structure |
| `test_sitemap.py` | Same — XML parsed and checked, not string-matched |
| `test_seo.py` | Input page → meta tag dict |
| `test_icons.py` | Input icon name → resolved SVG path |
| `test_assets.py` | Input fixtures → file copies (with binary byte-fidelity check) |
| `test_markdown_pipeline.py` | Input markdown → HTML containing expected elements (`<table>`, `<input>` for tasks) |
| `test_templates.py` | Real template render through the 6-level lookup cascade |
| `test_llm.py` | Input pages → llms.txt + JSON-LD structures |
| `test_cli.py` | Real end-to-end `main(["new", "site", "mysite"])` → check file structure → chain `main(["new", "post", ...])` → check |
| `test_init.py` | Trivial smoke (12 lines) — version exists |

The XML feed/sitemap tests are noteworthy: they use `ElementTree.fromstring`
to parse the output and walk the tree, not string-match it. That's the
gold standard for testing structured output.

### Tier 2 — Mixed (4 files)

Exercise the unit but stop short of the integration point where bugs live.

#### `test_build.py` — 13 tests, missed bugs 1, 2, 4 from Test 1

Drives the full build pipeline against the fixture site (real
integration), but every assertion checks **file existence** or **a single
hardcoded string**. Sample:

```python
def test_build_renders_blog_post(project: Path) -> None:
    build(project / "bartleby.yml")
    rendered_dir = project / "site" / "blog" / "posts" / "first-post"
    assert (rendered_dir / "index.html").exists()    # only checks existence
```

```python
def test_build_renders_index_page(project: Path) -> None:
    build(project / "bartleby.yml")
    rendered = (project / "site" / "index.html").read_text(encoding="utf-8")
    assert "Welcome" in rendered                      # single token
```

No test reads `site/blog/index.html` and asserts the post is in the
listing. No test reads `site/blog/posts/first-post/index.html` and
asserts the author name appears. No test inspects `site/sitemap.xml`
to confirm listing URLs are included. **The listing-empty bug, the
empty-byline bug, and the missing-sitemap-URL bug all passed CI here.**

#### `test_theme.py` — 10 tests, string-matching on rendered templates

Renders each template fixture with a stub context, then string-matches
the output:

```python
assert "/css/main.css" in rendered                   # the link exists
assert "/js/alpine.min.js" in rendered               # the script tag exists
assert "theme-toggle" in rendered                    # the toggle markup exists
```

Tells you the template emits the right tags. Tells you **nothing** about
whether the linked CSS/JS does anything useful in a browser. The fact that
`alpine.min.js` is a 200-byte stub (Deferral 1 from Test 2) is invisible
here.

#### `test_theme_full.py` — 8 tests, weakest signal in the suite

Half the tests read the raw CSS file and check for class names:

```python
def test_css_has_admonition_styles() -> None:
    css_path = get_theme_templates_dir().parent / "static" / "css" / "main.css"
    text = css_path.read_text()
    assert ".admonition" in text
```

This tests that the **string** `".admonition"` appears in a file. Doesn't
verify the rule is well-formed, doesn't verify it gets applied, doesn't
even verify the CSS is valid. Could be replaced with `grep -q ".admonition"
src/bartleby/theme/static/css/main.css` in CI and lose nothing.

#### `test_listings.py` — 7 tests, missed bug 2 from Test 1

This is the most insidious. The tests verify the virtual `Page` object's
`custom_metadata["posts"]` field is correctly populated:

```python
posts_in_context = listing.custom_metadata["posts"]
assert isinstance(posts_in_context, list)
assert posts_in_context[0] is newer
```

This passes — the data structure is correct. But **no test renders the
listing template**, so the actual bug — that the template reads
`page.posts` (undefined) and not `page.custom_metadata.posts` — is
invisible. The unit is correct in isolation; the integration is broken.

### Tier 3 — Weak (2 files)

#### `test_server.py` — explicitly skips the real surface

The module docstring is honest:

> Network IO (HTTP + WebSocket) is intentionally not exercised in tests —
> instead we cover the rebuild dispatcher, change classification, and
> config plumbing.

10 tests; 7 are unit tests of pure functions (`classify_change`,
`should_trigger_full_rebuild`); 3 exercise `DevServer.build_once` and
`handle_change`. **No test exercises `DevServer.run()`** — the only
method end users actually invoke via `bartleby serve`. The hooks
listing in Test 2 (Deferral 6) confirms `run()` is just a bare
`http.server.SimpleHTTPRequestHandler`; there's nothing to test
because nothing watches files or pushes WebSocket reload.

#### `test_async_build.py` — tautological concurrency tests

Given `async_build` is literally:

```python
async def async_build(config_path, *, include_drafts=False):
    return await asyncio.to_thread(build, config_path, include_drafts=include_drafts)
```

…the tests verify:

- It produces output (i.e. `build()` still works)
- It produces the **same** output as `sync_build` (also tautological —
  same function, called through a thread wrapper)
- It writes the search index, sitemap (delegated to `build()`)
- It completes within 15 seconds (no hang)

What's **missing**: any test of actual concurrency. No assertion that two
pages render in parallel. No assertion that the event loop isn't blocked.
No assertion that `asyncio.gather` runs the post-render outputs
concurrently. Given the implementation is `to_thread(build)` and provides
no real parallelism (Deferral 4), the tests are honest about what's
there — but the suite would pass identically if `async_build` were
replaced with `def async_build(...): return build(...)` and
`asyncio.run()` removed from `cli.py`.

### Pattern findings

1. **`.exists()` over content inspection.** Integration tests stop at
   file existence. Three of the four high/medium bugs from Test 1
   (empty listing, empty byline, missing sitemap URLs) would have been
   caught by adding two-line assertions like `assert "Hello" in
   (site / "blog" / "index.html").read_text()` to existing tests.

2. **Unit tests stop at the dataclass.** `test_listings.py` and
   `test_taxonomies.py` correctly verify the virtual-page data
   structure, but never render the templates that consume those
   structures. The contract between the listings module and the listing
   template is untested.

3. **Theme tests don't test theme rendering.** They test template
   substrings and CSS file substrings. They would all pass even if every
   linked asset was a 404 or every CSS rule had broken syntax.

4. **The serve/async story is intentionally underspecified.** Both
   `test_server.py` and `test_async_build.py` document up front that
   they're not testing the surface that matters. That's honest — but
   it's also the reason `bartleby serve` doesn't have working live
   reload (Deferral 6) and `async_build` provides no concurrency
   (Deferral 4). No test would have flagged either gap.

### Quantification

- **27 test files, 275 tests, 3777 lines.**
- **Tier 1 (strong): 21 files (~78%)** — real behavior coverage
- **Tier 2 (mixed): 4 files (~15%)** — shape/string-matching where
  behavior testing would surface real bugs
- **Tier 3 (weak): 2 files (~7%)** — explicitly skip the real surface

Test **count** is honest as a coverage-breadth proxy. Test **quality**
is bimodal: the per-module unit tests are strong; the integration and
theme tests are shape-checks dressed up as integration tests.

### What would meaningfully improve the test suite

In rough priority order:

1. **Augment `test_build.py` with content assertions.** For each
   page type, after build, read the rendered HTML and assert on the
   substantive content (post body present, byline rendered with author
   name, listing contains links to every published post, taxonomy page
   contains the term name, sitemap contains every nav URL).
2. **Render the listing/taxonomy templates in their unit tests.**
   `test_listings.py` should assert `posts[0].title in rendered_html`,
   not just `posts[0] is newer_page`.
3. **Replace CSS-file-string-matching in `test_theme_full.py` with
   render-and-inspect.** If you want to verify admonition styling, render
   a page with an admonition and check the `<div class="admonition">`
   appears in the HTML, not that `.admonition` appears in the CSS source.
4. **Add a smoke test in CI that mimics the manual Test 1 above.**
   Scaffold + post + build + grep the rendered output for specific
   strings. ~20 lines; would catch every Test 1 bug.
5. **Once Deferrals 4 and 6 land for real, write actual concurrency
   tests and live-reload tests.** Until then, the existing skeletons
   are honest placeholders.

The smallest delta that buys the most signal: 8–10 new assertions in
`test_build.py` (item 1). That alone would have caught Bugs 1, 2, and 4
from the Test 1 smoke audit.

## Test 4 — Read the commits as a story

**When**: 2026-06-02
**Method**: Walked the full v1 branch history (34 commits), then deep-dove
the four commits flagged in `review.md` as architecturally load-bearing
(Steps 4, 8, 10, 21). Looked for design errors that compound downstream.

### Branch shape

34 commits on `v1`, all linear (no merges, no reverts, no fixup squashes).
The 27 implementation steps are bookended by 3 pre-Step-1 commits (spec
drafts + plan), 1 housekeeping commit between Steps 1 and 2 (gitignore +
pypi name), and 3 post-Step-27 commits (docs, audit fixes, audit
tracker). Every "Step N" commit follows the same shape: imperative title,
narrative body explaining the *why*, bulleted change list, and an
"All checks pass: N/N tests green" footer. Commit hygiene is exceptional.

Pre-existing modifications to `plan.md`, `spec.md`, `tests/fixtures/configs/
full.yml`, and `tests/test_config.py` were never folded in — they persist
as uncommitted diffs in the working tree (Deferral 8 in Test 2).

### Step 4 — `parse_front_matter` (commit 05bc8b0)

The bug-fix loop in the session summary was the obvious tell. The final
implementation is clean — but a real edge case slipped through:

**Issue A: Front matter detection is too loose.**
```python
if not text.startswith(FRONT_MATTER_DELIMITER):
    return {}, text
```
This matches any document starting with `---`, even `---horizontal rule`
or `---foo bar`. The closing-marker search will fail for most such
documents (returning the original text unchanged), so it's silent — but
a document starting with `---` whose body happens to contain `\n---`
somewhere will accidentally have its body chopped and the chopped chunk
fed to `yaml.safe_load`. Should require `text.startswith("---\n")` (or
EOF after `---`).

**Issue B: YAML parse failures are silently dropped.**
```python
parsed: Any = yaml.safe_load(front_matter_block)
if parsed is None:
    return {}, body
if not isinstance(parsed, dict):
    return {}, body
```
If `yaml.safe_load` returns a list, scalar, or anything non-dict, the
function returns empty metadata silently. Metadata validation will then
fire on the empty dict and complain about missing `title`, but the actual
parse error (e.g. tab indentation, malformed YAML) never surfaces. Worth
either logging or re-raising on non-dict YAML.

Neither issue is critical; both are paper cuts.

### Step 8 — Template system + 6-level cascade (commit c6978a1)

**Strong**: `resolve_template_name` iterates *candidates first, then
locations* (overrides → templates → theme). This is the correct ordering
— it means a content-type-specific template in the theme wins over a
generic defaults template in overrides. Inverting the loop order would
break the override semantics. The cascade tests cover this well.

**The architectural mistake that bit later**: `build_page_context`
flattens the `Page` dataclass into a hand-built dict:

```python
page_namespace: dict[str, object] = {
    "title": page.title,
    "description": page.description,
    ...
    "authors": list(page.author_keys),   # this is the Bug 1 location
}
```

The original commit message says this is "so templates can use
mkdocs-style `page.title` access without adapter classes". But Jinja2
reads dataclasses just fine — `page.title` works whether `page` is a
dict or a `Page` dataclass. The hand-built dict has two real costs:

1. **Closed schema.** Anything new on `Page` (like `slug_override` in
   Step 6, `previous`/`next` in Step 9) silently doesn't reach
   templates unless someone remembers to add it here. This is the
   surface that caused Bug 1 (`authors` exposed as raw key strings) and
   Bug 2 (`custom_metadata` not exposed at all, so listing templates
   couldn't see their post lists). Both bugs survived to release.
2. **Two parallel APIs.** Internal code reads `page.author_keys`,
   `page.custom_metadata`, `page.output_url`. Templates read
   `page.authors`, `page.custom_metadata`, `page.url`. The list template
   even had `post.url` instead of `post.output_url` because of this
   inconsistency.

The fix in commit `d212d95` patches the symptoms by exposing
`custom_metadata` and resolving authors. The real fix would be to drop
the dict adapter and pass the `Page` dataclass directly. Worth a
follow-up.

**Other Step 8 notes:**
- The "6-level cascade" is actually 7 levels — the `if template_type
  != "page": candidates.append("page.html")` line adds an unconditional
  bottom fallback to `page.html`. Doesn't break anything, but the
  docstring count is off by one.
- The fall-through return (`return candidates[-1]`) is silent. If
  nothing on disk matches, the function returns the deepest candidate
  name and lets Jinja2 raise `TemplateNotFound`. Honest but the error
  could be friendlier.

### Step 10 — MVP build pipeline (commit 44930e9)

**`build()` is 120 lines with no internal phase boundaries marked.**
Readable, but the logical phases (load, discover, validate, structure,
render, output) are inline rather than extracted. A reader has to parse
the structure mentally. Splitting into named helpers (`_load_inputs`,
`_filter_and_validate`, `_render_all_pages`, `_emit_outputs`) would
make the hook insertion points obvious and keep each phase under a
screen.

**Two real hook-placement issues:**

1. **`on_pages` fires BEFORE draft filtering.** A plugin that wants
   to augment the published page set sees drafts too, then build.py
   filters them out. Order should be: discover → filter drafts →
   on_pages. Right now it's: discover → on_pages → filter. Means
   a plugin like "add canonical URL" runs on drafts that won't ship.

2. **`on_env` fires AFTER `data = load_data_files`** but the env
   doesn't see the data either way; data goes into the template
   context separately. A plugin wanting to inject data via on_env
   has nowhere to attach it. Need either an `on_data` event or a
   way for `on_env` to mutate the data dict.

**Hardcoded output path.** `output_dir = project_dir / "site"` — not
configurable. Spec hardcodes `site/` so this is by design, but it
removes a customization seam users will eventually ask for.

**No per-page error isolation.** A single page rendering throwing
(bad shortcode, unparseable date) aborts the whole build with a
stack trace. Better: catch per-page, dispatch `on_build_error`, and
in non-strict mode continue with the remaining pages. Real
production sites need this.

**`from bartleby.theme import get_theme_templates_dir as _theme_dir`
is inside the function.** Should be a top-of-file import. Cosmetic.

### Step 21 — Plugin system (commit 4aa5b4d)

**Clean overall.** `register()` uses stable sort (registration order
preserved within a priority). `event_priority` decorator works on both
methods and module functions per the test suite. `discover_hooks`
correctly skips `_`-prefixed files. The negative test
(`test_no_entry_point_discovery`) is a great defensive measure — it
locks in the "no public plugin API" design decision so a future refactor
that re-adds entry_points will fail loudly.

**Real issue: BasePlugin has 16 methods; `KNOWN_EVENTS` has 17.**

```python
KNOWN_EVENTS: tuple[str, ...] = (
    "on_startup", "on_shutdown", "on_config", "on_pre_build",
    "on_files", "on_nav", "on_env", "on_pre_page",
    "on_page_read_source", "on_page_markdown", "on_page_content",
    "on_page_context", "on_post_page", "on_post_build",
    "on_build_error", "on_serve",
    "on_pages",                                  # 17th, no BasePlugin method
)
```

`on_pages` was added during Step 10 to support the build pipeline's
page-filter hook, but never made it into BasePlugin's method list. A
real `BasePlugin` subclass can't implement `on_pages` cleanly — they'd
have to add the method themselves. Either remove `on_pages` from
`KNOWN_EVENTS` and rename to something already declared, or add the
matching no-op method to `BasePlugin`.

**Minor: no cross-hook import support.** Each hook file is loaded into
an isolated namespace via `importlib.util.spec_from_file_location`. A
hook that does `import my_helper` where `my_helper` is a sibling in
`hooks/` will fail because the hooks directory isn't on `sys.path`.
Most real-world hook collections will want this. Workaround for users:
put helpers in a package they install separately.

**No reload semantics.** `discover_hooks` is single-shot. When the dev
server lands its watchdog (Deferral 6), changing a hook file won't
re-register its handlers without a server restart. The fixed
`module_name = f"_bartleby_hook_{path.stem}"` would make re-loading
overwrite the spec but might leak stale function references in the
PluginCollection. Worth solving alongside Deferral 6.

### Cross-step patterns

**A: `Page` is the central god-object.** Almost every module touches
the `Page` dataclass: discovery sets the basic fields, URL generation
sets `output_url`, navigation sets `previous`/`next`, markdown rendering
sets `rendered_content` and `excerpt`, taxonomy/listing generation
creates virtual `Page` instances. The dataclass is comprehensible
because it's flat (no nested mutation), but the *order* of who sets
what is implicit. Refactoring `Page` to a frozen builder pattern
(immutable handoffs between phases) would surface that ordering
explicitly. Probably 0.2.0 work.

**B: Virtual pages stuff state into `custom_metadata`.** Listing and
taxonomy modules create virtual `Page` instances with their structured
data buried in `custom_metadata["posts"]`, `custom_metadata["paginator"]`,
etc. This is what caused Bug 2. A real fix would be subclassing
`Page` (or a sibling type `VirtualPage`) with named attributes. The
present approach gets away with it because mypy doesn't complain about
dict accesses on `dict[str, object]` — but the contract between the
generator and the template is untyped.

**C: Magic strings.** `"taxonomy_kind"`, `"taxonomy_term"`,
`"listing_kind"`, `"index"`, `"term"`, `"content_type"` appear in
`listings.py`, `taxonomies.py`, and `build.py::_template_type_for`.
A typo in any of them silently dispatches to the wrong template type.
Should be `enum.StrEnum` or module-level constants.

### Verdict

The history is exceptionally well-structured for an unsupervised
27-step push. Every commit is self-contained, tests pass at every
boundary, and the architectural decisions are documented in the
commit bodies. The four load-bearing commits I called out as
high-risk:

- **Step 4 (`parse_front_matter`)**: two minor edge cases (loose start
  detection, silent YAML failure). Not currently biting.
- **Step 8 (template cascade)**: cascade is correct; the dict-adapter
  pattern in `build_page_context` is the architectural mistake that
  caused Bugs 1 and 2 and will continue to be a pain point.
- **Step 10 (build pipeline)**: hook placement for `on_pages` is wrong
  (fires before draft filter); no per-page error isolation; long
  function with implicit phases. None are bugs *today* but all three
  will hurt as the pipeline accretes work.
- **Step 21 (plugin system)**: clean overall; `on_pages` in
  `KNOWN_EVENTS` but not `BasePlugin` is a small consistency miss;
  no reload story for the future dev server.

Plus three cross-cutting findings:
- **`Page` is a god-object** with implicit phase ordering
- **Virtual pages use untyped `custom_metadata`** (cause of Bug 2)
- **Magic strings** (`"taxonomy_kind"`, `"listing_kind"`, etc.) should
  be enums

None of these block 0.1.0 shipping. All of them are reasonable
0.2.0–0.3.0 cleanup targets — adding them to the audit tracker below
as "Design 1-7" so they're queued alongside the existing deferrals.

## Test 5 — Lint the spec against the implementation

_Pending._

## Test 6 — Run /ultrareview on the branch

_Pending (user-triggered)._
