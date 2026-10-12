# Goal 8 Success Criteria Evidence

Gate run: 2026-10-12, branch `v0.1.1`, tree at commit `bbb006e` plus the CHANGELOG and README edits of this step.
Every run below used the wheel built from this tree and installed into a fresh venv, from a directory outside the repo, with the repo's `.venv` not active.
Paths in this file use `$GATE` for the scratch directory `.../scratchpad/gate`.
The scratchpad is temporary, so the screenshots are described here in prose; the commands reproduce them.

## Verdict Summary

- Success criteria section: 9 lines. 3 met, 6 met with a note, 0 not met.
- Goal 8 testable claims: 28 lines. 16 met, 12 met with a note, 0 not met.
- The governing bar (Mason is willing to send it to people) is marked "met with a note" because the evidence is delivered here and the judgment is Mason's.
- No defect was found that needed a `src/` change.

## Clean-Install Method

```bash
uv build --wheel --out-dir $GATE/wheel /path/to/bartleby
uv venv $GATE/venv --python 3.14
uv pip install -p $GATE/venv/bin/python $GATE/wheel/bartleby_ssg-0.1.0-py3-none-any.whl
cd $GATE/work                      # outside the repo
env -u VIRTUAL_ENV $GATE/venv/bin/bartleby new site gate-site
```

The wheel file list carries every asset the first run needs:

- `bartleby/scaffold/README.md`, `bartleby.yml`, `content/index.md`, `content/tour/index.md`
- `bartleby/scaffold/content/tour/{after,before,slide-1,slide-2,slide-3}.svg`
- `bartleby/scaffold_blog/.authors.yml` and `content/blog/posts/welcome.md`
- `bartleby/themes/scrivener/static/css/main.css` and `bartleby/themes/material/static/css/main.css`
- `bartleby/themes/base/static/js/click_to_load.js` and `static/css/click_to_load.css`
- `bartleby/THIRD-PARTY-NOTICES`
- `bartleby_ssg-0.1.0.dist-info/licenses/ACKNOWLEDGMENTS.md`

## The Success Criteria Section

### Criterion 1: Theme System

> The theme system works end to end: `theme.name`, `theme.path`, and `theme.package` select a theme; `extends` composes; `eject` and `inspect` expose the whole resolved system; the bundled themes resolve through the same loader as a path theme.

Commands, from the clean venv, in a fresh scaffold:

```text
$ bartleby theme inspect | head -2
Theme scrivener (chain: scrivener -> base)
icons/fontawesome-brands/github.svg  (base)
$ bartleby theme eject --to themes/mine      # prints: theme: path: themes/mine
$ bartleby build --strict --set theme.path=themes/mine --set theme.name=
Built 2 pages (12 static files) into site/
```

The full suite covers the selectors and `extends`: `tests/test_theme_loader.py` (34 tests), `tests/test_theme_commands.py` (20), `tests/test_theme.py`, `tests/test_theme_collections.py`.
`theme.package` is covered by the entry-point tests in `tests/test_theme_loader.py`; I did not install a third-party theme package in the clean venv.

Verdict: met.

### Criterion 2: Both Themes Render Polished Sites

> Both `material` and `scrivener` render a polished, professional-looking site out of the box, verified in a browser across home, listing, post, docs page (sidebar and table of contents), taxonomy, and 404 pages, with no custom CSS, and switching between them from config changes the look and nothing else.

Commands: headless Chromium against `bartleby serve` from the clean venv, `gate-site` (scaffold) and `gate-blog` (`new site --blog`), then `config set theme.name material` and the same shots.
Shots at 1280x900 and 390x844, light and dark, for home and the tour, plus 1280x800 listing, post, taxonomy, and 404 in each theme.
Index: `$GATE/shots/INDEX.md`.

What I saw, scrivener:

- Home at 1280: three columns.
  Left nav (Home bold, Feature Tour), a 640px reading column with "Welcome" and the five steps, and a right TOC with six entries.
  Code block has a Copy button.
  Dark mode is a near-black page with the same layout.
- Tour at 1280: the right TOC lists every section and subsection.
  Fence label bars ("app.py") render, Python tokens are colored (blue keyword, purple builtin, green string).
- Home and tour at 390: one column, header wraps to a nav row, a "Navigation" fold above the page, code blocks fit, no sideways scroll.
- Listing: dated row with title and excerpt.
  Post: title, meta line (date, author, reading time), code block, tag chip, left nav and a one-entry TOC.
  Taxonomy: "Tags, 1 term" with a count.
  404: large "404", home button, section chips.

What I saw, material:

- Indigo header bar, left nav with the active page in indigo, a long right TOC with an active rule, light-weight headings, admonitions in tinted boxes, task-list checkboxes, compare slider with an indigo handle.
- Home and tour at 390: indigo header with a nav row, a native "Navigation" select, one column, no overflow.
- Listing, post, taxonomy (card for the term), and 404 (indigo "404", button, chips) all render with theme chrome.

Overflow probe (`document.documentElement.scrollWidth` against `clientWidth`) for `/` and `/tour/` at 390 and 1280 in both themes: equal in all eight cases (375/375 and 1265/1265, the 15px being the scrollbar).
Switching `theme.name` changed only the look: the same pages, nav, TOC entries, and content rendered in both.

Verdict: met with a note.
Note: material caps the content column at 40rem when a page has no sidebar and no TOC, leaving the right of a 1280 viewport empty (commit `3b35ad5` flagged it).
Mason should look at that page shape.

### Criterion 3: Docs Site

> The docs site builds and renders cleanly, looks good, and is fit to be the public showcase for the project.

```text
$ (cd docs && uv run bartleby build --strict)
Built 76 pages (7 static files) into site/        # exit 0, no warnings
```

Screenshot of Concepts, Markdown Pipeline at 1280x900 in scrivener and in material (`--set theme.name=material`): header tabs (Home, Installation, Quickstart, Concepts, Guides, Reference), the Concepts section nav with the current page marked, the page, and a three-entry right TOC.
Numbered lists and inline code render cleanly in both.
`tests/test_docs_reference.py` compares 28 surfaces in both directions and passes in the full suite.

Verdict: met with a note.
Note: whether it is fit to be the public face of the project is Mason's judgment; the build and the render are clean.
The docs also carry a known 404 link: the `ACKNOWLEDGMENTS.md` link points at `blob/main` and fails until this branch merges.

### Criterion 4: A Newcomer's First Run

> A newcomer can go install, scaffold a site, add content, build, serve, and see a good-looking result without hitting rough edges; errors are clear and actionable.

Real output, clean venv:

```text
$ bartleby new site gate-site
Created site at gate-site/
  README.md
  bartleby.yml
  content/
  hooks/
  static/
  templates/
Next: cd gate-site && bartleby serve
$ cd gate-site && bartleby build --strict
Built 2 pages (12 static files) into site/        # exit 0, no warnings
$ bartleby serve --port 0
Built 2 pages (12 static files) into site/
Serving at http://127.0.0.1:38915/
Press Ctrl+C to stop
```

Add content: `bartleby enable blog news`, `bartleby new post "Gate Post" --type news`, set `draft: false`, rebuild: 5 pages.
Errors seen: `error [config_error] --set: site.feed.limit: must be an integer (fix: write `limit: 50`)` (exit 1), `error [config_error] --set: theme.features: must be a list (fix: write `features: [search, nav.tabs]`)`, `error [config_error] bartleby.yml: markwright: unknown configuration key: 'bogus' (fix: ...)`, and `no bartleby.yml at <path> (fix: run from the directory holding bartleby.yml, ...)`.
Every one is labeled and carries a fix.
`tests/test_first_run_output.py`, `tests/test_scaffold.py`, `tests/test_correctness.py` pin these.

Verdict: met with a note.
Note: `enable` adds no `nav` entry (the quickstart says so), so a newcomer who enables a blog must add `- Blog: blog/` by hand; `new site --blog` adds it.
"Good-looking" is Mason's call.

### Criterion 5: The Agent Surface

> The agent surface is complete and consistent: every published page has a valid Markdown variant and JSON-LD; `llms.txt`, `schema.json`, and `content-index.json` are correct and documented; generated skills reflect the site's real shape.

```text
$ ls site/index.md site/tour/index.md                   # both exist
$ grep -c application/ld+json site/index.html site/tour/index.html     # 1 and 1
$ sha256sum site/{llms.txt,llms-full.txt,schema.json,content-index.json}; rebuild; diff   # BYTE-IDENTICAL
$ python -c "print(json.load(open('site/schema.json'))['theme'])"
{'chain': ['scrivener', 'base'], 'features': {'active': [...6 features], 'enabled': [same 6], 'implemented': [9 features]}, 'name': 'scrivener'}
$ bartleby generate-skill          # Generated 3 skills; grep for TODO/TBD/placeholder: none
```

`llms.txt` lists both pages with absolute `https://example.com/...` URLs and one-line summaries.
Tests: `tests/test_agent_surface.py::test_agent_outputs_are_identical_across_two_builds`, `tests/test_llm.py`, `tests/test_skills.py`.

Verdict: met.

### Criterion 6: Public Interfaces

> The public interfaces (hooks, config schema, template context, agent output formats) are documented and stable enough to build on.

`tests/test_docs_reference.py` defines 28 surfaces and compares each with the code in both directions, including `test_configuration_reference_is_the_schema`, which regenerates the config reference from `CONFIG_SCHEMA` byte for byte.
The suite passes (1275 tests).
The CHANGELOG now calls out the breaking changes.

Verdict: met with a note.
Note: "stable enough" is a promise about the future that no run proves; the drift test is the mechanism.

### Criterion 7: New Site, Serve, Full Config, Enable

> `bartleby new site` then `bartleby serve` gives a three-column docs site with a working feature tour from a small `bartleby.yml`, `--full-config` lists every accepted option, and `bartleby enable blog <name>` adds a blog whose RSS and Atom feeds carry entries.

Three columns and the tour: criterion 2 and the serve run above (home, tour at 200, 404 for a missing page, tour page 38489 bytes).
The scaffold `bartleby.yml` is 16 lines.

`--full-config`:

```text
$ bartleby new site --full-config gate-full          # prints "bartleby.yml (every option, from --full-config)"
$ bartleby config schema --output json              # 57 fields
57 of 57 schema paths present in gate-full/bartleby.yml (15 templated <name> paths matched by their placeholder entries); 57 of 57 descriptions present
$ bartleby build --strict          # in gate-full: Built 3 pages
```

`enable` feeds, parsed with `xml.etree` after adding a published post to `news`:

```text
site/feed.xml          1 ['Gate Post']
site/atom.xml          1 ['Gate Post']
site/news/feed.xml     1 ['Gate Post']
site/news/atom.xml     1 ['Gate Post']
```

A second walk (`new site --blog`, then `enable blog tutorials` and a post in each): `site/feed.xml` and `site/atom.xml` carried `['Welcome to Bartleby', 'T1']`, `site/blog/feed.xml` carried the blog post, `site/tutorials/feed.xml` and `atom.xml` carried `T1`.
Tests: `tests/test_new_site_full_config.py::test_full_config_covers_every_schema_path`, `tests/test_enable.py`, `tests/test_feeds.py`.

Verdict: met.

### Criterion 8: just check and a Clean Install

> `just check` is green, and `bartleby-ssg` installs and runs from a clean environment.

```text
$ just check          # ruff lint + format check, mypy strict, pytest, smoke
1275 passed in 90.83s
3 passed (tests/test_smoke.py)
EXIT 0
```

The wheel built, installed into a fresh Python 3.14 venv with its dependencies (starlette, uvicorn, ruamel.yaml, markwright, and the rest), and every command above ran from it.

Verdict: met with a note.
Note: this installs the wheel built from the branch, not a PyPI release.
PyPI `bartleby-ssg` 0.1.0 is the older code; the version stays 0.1.0 until Mason cuts a release.

### Criterion 9: The Governing Bar

> Mason is willing to send it to people and show it off.
> This is the governing bar.

This file, the screenshots, and the clean-install walk are the evidence.
I cannot judge the bar.

Verdict: met with a note (open: Mason's judgment).

## Goal 8 Testable Claims

### G1: Docs-Shaped Scaffold

> `bartleby new site` scaffolds a docs-shaped site: a home page that says what to do next, and one feature tour page that shows each markwright and pymdownx feature with its source beside the result.

Run above: home "Welcome" with Run the Site, Make the First Edit, Add a Page, Set Your Title and URL, Add a Blog When You Want One, Check Your Work; tour with code blocks, text formatting, blocks and layout, standard extras, embeds, images.
Tests: `tests/test_scaffold.py::test_tour_html_carries_the_output_of_every_feature_it_claims`, `::test_tour_shows_each_source_in_a_code_block`.

Verdict: met with a note.
Note: the tour leaves out `pymdownx.snippets` because it needs a file to include, and says so under "Not Shown Here".

### G2: Small Config

> Its `bartleby.yml` holds only what the site needs to build, so it stays small.

Observed: `site.title`, `site.url`, six theme features, a two-entry nav, 16 lines.
Test: `test_scaffold_config_is_minimal_and_defines_no_blog_or_markwright`.

Verdict: met.

### G3: Full Config

> `bartleby new site --full-config` writes every option Bartleby accepts instead, each set to its default with a one-line comment.

Observed: 57 of 57 schema paths and descriptions present; `config set site.title` on the file changed only the title line and kept every comment (diff shows one line).
Four fields have no real default and render as marked "(Example value; replace it.)".

Verdict: met with a note.
Note: the `<name>` entries (content types, taxonomies, metadata fields) render as one `example` entry each, not as live config.

### G4: One Schema, a Test Pins It

> The full config is generated from the same source as config validation and `schema.json`, and a test fails if any accepted key is missing from it.

Tests: `tests/test_config_schema.py` (drift against the dataclass defaults and against the top-level keys `config.py` accepts), `tests/test_new_site_full_config.py::test_full_config_covers_every_schema_path`.
The `schema.json` here means `config schema --output json`; the agent file `schema.json` is a different document (site manifest).

Verdict: met.

### G5: Dedicated Flags

> a few dedicated flags cover what changes run to run (`--port`, `--host`, `--include-drafts`, `--strict`, and a new `--base-url`).

Observed: `serve --help` lists `--host`, `--port`, `--base-url`, `--set`; `build --strict` and `build --include-drafts --strict` ran; `build --base-url https://gate.test` produced `<link rel="canonical" href="https://gate.test/">` on home and `https://gate.test/tour/` on the tour.

Verdict: met.

### G6: The --set Layer

> A repeatable `--set key.path=value` on `build`, `serve`, and `validate` overrides config for one run without touching the file; values parse as YAML and go through the same validator, with errors labeled as coming from `--set`.

Observed: `build --set site.title=Over` made the page title end in `Over`, and `config get site.title` still printed `Gate`; two `--set` flags on one build worked; `validate --set site.title=X` passed; `serve --set theme.name=material` served the material theme; `--set site.feed.limit=oops` gave `--set: site.feed.limit: must be an integer (fix: ...)`.

Verdict: met.

### G7: The config Group

> `bartleby config show` prints the resolved config with the source of each value (default, file, or `--set`), `config get` reads one key, `config set` validates and writes one key into `bartleby.yml` keeping its comments, and `config schema --output json` lists every key with its type, default, allowed values, and a one-line description.

Observed: `config show` rows end in `(default)` or `(file)`; `config get site.title` printed `gate-site`; `config set site.title Gate` printed `Set site.title to Gate in bartleby.yml`; `config schema --output json` returned `{"fields": [...57 objects with choices, default, description, path, repeatable, required, type], "status": ...}`.
The `(--set)` source tag is covered by `tests/test_config_commands.py`; I did not run `config show --set` by hand.

Verdict: met.

### G8: One Writer

> `--full-config`, `config schema`, and the configuration reference docs come from one schema, and `enable` and `config set` share one comment-preserving YAML writer.

Evidence: `config_edit.py` is the writer behind `config set`, `enable`, and `new site --full-config`; `tests/test_docs_reference.py::test_configuration_reference_is_the_schema`; `tests/test_config_edit.py`.

Verdict: met.

### G9: Opt-In Blog

> The blog is opt-in, through `bartleby new site --blog` or `bartleby enable <content-type> <name>` on an existing site, which merges the needed config if it is missing and is safe to run twice.
> `bartleby disable <content-type> <name>` turns it off through an `enabled` flag, not by deleting config.

Observed: `enable blog news` printed `Added blog content type 'news' to bartleby.yml` and added the type, feeds, and the `tags` taxonomy; the second run printed `Content type 'news' is already in bartleby.yml; left unchanged`; `disable blog speaking` wrote `enabled: false`, and the next build produced no `site/speaking`.

Verdict: met.

### G10: Multiple Instances and Feeds

> A site can enable the same content type more than once (mason.dev runs `blog`, `tutorials`, and `speaking`), and each enabled type publishes its own RSS and Atom feeds plus one combined site feed, with the existing per-type `feeds` key as the opt-out and `site.feed` controlling the combined feed.

Observed: `blog` and `tutorials` each had their own `feed.xml` and `atom.xml` with entries, and the combined feeds carried both posts; `speaking` was enabled then disabled and left no output.
The opt-out and `site.feed` controls are covered by `tests/test_feeds.py` and `tests/test_enable.py`; I did not toggle them by hand.

Verdict: met.

### G11: Print What Happened

> `new site` and `serve` print what Hugo prints: what was created and the next command, then the build summary, the URL, and how to stop.

Observed: the exact output quoted under criterion 4.
`serve --events` opens with a `ready` object (`tests/test_first_run_output.py::test_serve_events_startup_is_one_ready_object`).

Verdict: met.

### G12: Async Dev Server

> The dev server is async on Starlette and uvicorn, with file watching and live reload on the same port, after sphinx-autobuild's design.

Observed: `serve --port 0` on port 38915; `curl` of home and tour returned 200 and a missing page returned 404; a WebSocket client connected to `ws://127.0.0.1:38915/__bartleby_reload` and received the message `reload` after I appended a line to `content/index.md`; the rebuilt page contained the new text; SIGINT exited with code 0.
The injected script uses `location.host`, so there is no second port.

Verdict: met with a note.
Note: the rebuild rewrites the output directory in place, so a request that arrives mid-rebuild can 404 (commit `f764f4b`); an atomic swap is parked.
Also parked: a non-permission `OSError` during the output swap (a full disk during a cross-device move) surfaces unlabeled (commit `bbb006e`).

### G13: Three Columns and the Fold Flags

> The default docs layout is three columns (navigation, content, page table of contents), with `theme.features` flags to fold the table of contents into the left navigation and to move top-level sections into header tabs.

Observed: three columns in both themes (criterion 2); `build --strict --set 'theme.features=[nav.tabs, nav.toc-fold, search]'` built clean.
`nav.toc-fold` is covered by `tests/test_layout.py`; `nav.tabs` is the existing flag for header tabs, so no second flag was added (the spec says "flags").
I did not screenshot the fold layout in this gate.

Verdict: met with a note.

### G14: Bartleby's Own Markup

> The shape follows Zensical and Material for MkDocs; the markup and CSS are Bartleby's own, not a copy.

`ACKNOWLEDGMENTS.md` records the design inspiration and a no-stylesheet-copied line; the compiled CSS comes from Bartleby's own `tailwind.css` sources.
This holds by the file's statement and by the git history, not by a mechanical check.

Verdict: met with a note.
Note: the `md-button` class name is shared with Material for MkDocs; a class name is not copyrightable code (commit `61f7e61`).

### G15: Both Themes Style Every markwright Hook

> Both visual themes (`scrivener` and `material`) style every class hook markwright emits, and the starter feature tour shows each extension.

Observed in the tour crops: fence labels, secondary labels ("Output"), environments (local gray bar, third amber bar), prompts (`$`), highlight marks, critic markup, keyboard keys, tabs, collapsibles, admonitions, task lists, figures, footnotes, definition lists, abbreviations, slideshow, image compare.
`tests/test_scaffold.py::test_bundled_theme_css_styles_extension_output_the_tour_shows`.

Verdict: met with a note.
Note: four safelisted names compile to nothing, and only markwright's default label classes and the five documented environments are styled (commit `01bc0e1`).

### G16: The markwright Section

> A `markwright:` section in `bartleby.yml` has the same shape as `markwright.toml` ... validated and passed to the extensions at build time through markwright's public config API
> ... Only `bartleby.yml` counts: if a `markwright.toml` or `[tool.markwright]` table is also present, the build warns that it was ignored.

Observed: `--set markwright.bogus=1` gave `bartleby.yml: markwright: unknown configuration key: 'bogus' (fix: ...)`; `--set markwright.youtube.load=nope` gave `'load' must be one of eager, lazy, click; got 'nope'`; a stray `markwright.toml` printed `WARNING: ignored markwright.toml: only the `markwright:` section of bartleby.yml applies`.

Verdict: met.

### G17: Eager Embeds, Live Tour

> Embeds load eagerly by default, which is markwright's default, and the starter tour renders every embed live; the scaffold writes no `markwright:` section.

Observed: the scaffold `bartleby.yml` has no `markwright:` section.
In the screenshots YouTube rendered live (the video player with a play button) and Instagram rendered live (post card with 841 likes).
CodePen rendered blank: `codepen.io` returns 403 to every request from this sandbox, so I could not tell a markup fault from the block.
Twitter rendered its fallback link ("View tweet by @jack"); `platform.twitter.com/widgets.js` returned 200 to curl, but headless Chromium did not turn the link into a tweet card within the 6 second budget, so I could not confirm that one either.
The page does carry the provider script tags (3 matches for the twitter and codepen script hosts).

Verdict: met with a note.
Note: CodePen and Twitter live rendering is unverified here; the CodePen pen (`MattCowley/vwPzeX`) and the Instagram post (the markwright docs sample, `CkQuv3_LRgS`) are placeholders Mason should swap for real ones.

### G18: Click-to-Load

> Click-to-load is opt-in: a site sets `load: click` per embed in the `markwright:` section, and the scaffold README's quickstart shows how.
> Bartleby's themes ship the script and styles that swap the preview for the embed.

Observed: with `--set markwright.youtube.load=click` the tour built strict and the page referenced `click_to_load` twice (script and stylesheet); the default build loads neither (`tests/test_markwright_config.py::test_eager_embed_page_loads_no_click_assets`).
The scaffold README shows the opt-in (`test_readme_shows_the_click_to_load_opt_in`).
I did not click a preview in a browser.

Verdict: met with a note.

### G19: Claims Hold

> Anything the scaffold or docs claim works, works: feeds carry entries, code highlighting has CSS, and each claim has a test.

Observed: feeds carry entries (criterion 7); highlighted code is colored in both themes (tour screenshots); `tests/test_correctness.py` and `tests/test_enable.py` pin them.
The docs advertise an aggregate feed and the guides type now carries `rss` and `atom`.

Verdict: met.

### G20: Acknowledgments and License Check

> Code or design taken from another project is credited in an acknowledgments file, and its license is checked for compatibility with MIT before it lands.

`ACKNOWLEDGMENTS.md` ships under `dist-info/licenses/` in the wheel; `THIRD-PARTY-NOTICES` ships in the package; `tests/test_acknowledgments.py` fails when a vendored file or icon pack has no entry.

Verdict: met with a note.
Note: `pyproject.toml` declares the license expression `MIT` while the wheel bundles Apache-2.0, CC-BY-4.0, CC0-1.0, ISC, and 0BSD material.
A compound PEP 639 expression is Mason's decision.
The docs link to `ACKNOWLEDGMENTS.md` points at `blob/main`, which returns 404 until this branch merges.

### G21: Stays on 0.1.x

> Bartleby stays on 0.1.x through this work; 0.2.0 is the next stable release.

`pyproject.toml` reads `version = "0.1.0"` and the CHANGELOG section is `[Unreleased]`.

Verdict: met.

### G22: Solo First, Team Later

> The primary author is one person (a solo writer or a solo library author), and every default must grow cleanly into a small team.

The defaults are a small config, an opt-in blog, and `enable` for more content types; the `.authors.yml` file exists in the blog scaffold.
Nothing in this gate exercised a team workflow.
This holds by design and by the spec's wording, not by a real run.

Verdict: met with a note.

### G23: Markup in markwright, Behavior in Bartleby

> The split is markup in markwright and behavior in Bartleby: markwright emits the preview markup and ships no JS or CSS, and Bartleby's themes ship the script and styles that swap the preview for the embed.

The wheel carries `themes/base/static/js/click_to_load.js` and `static/css/click_to_load.css`, and both bundled themes style the previews (criterion 2 and G18).
markwright is unchanged by this work.

Verdict: met.

### G24: The Home Page and the Agent Files

> Bartleby leads as an agents-first SSG (CLAUDE.md) ... the starter home page.

Not a spec line, but a known gap: the scaffold home page no longer names `llms.txt` and the other agent files (commit `2162d50`).
`llms.txt`, `schema.json`, `content-index.json`, and the Markdown variants are all produced (criterion 5), but a newcomer reading the home page will not learn that.

Verdict: met with a note.

### G25: Shape First, Instance Second

> The first argument is a content-type shape and the second is the instance name: `bartleby enable blog tutorials` adds a second blog-shaped type at `tutorials/`.

Source: spec.md line 113.

Observed: the criterion 7 second walk ran `enable blog tutorials` on a `new site --blog` site, and `site/tutorials/feed.xml` carried the `T1` post.

Verdict: met.

### G26: markwright Fully Integrated

> markwright is fully integrated.
> Its eight extensions (markwright 0.3.0) are already on by default.

Source: spec.md lines 119-120.

Evidence: commit `9347453` built a probe page using all eight extensions byte-identical to the build before it.
`tests/test_markdown_pipeline.py::test_no_markwright_section_loads_markwright_default_extensions` shows that with no `markwright:` section the eight names load.

Verdict: met.

### G27: markwright's Own Option Defaults

> Bartleby uses markwright's own option defaults; when a default should change, it changes in markwright.

Source: spec.md line 122.

Evidence: commit `9347453` passes the `markwright:` section to `config_from_mapping` as written (`tests/test_markdown_pipeline.py::test_section_goes_to_config_from_mapping_and_options_reach_the_extensions`), and an absent section loads exactly what markwright selects from an empty config.
A grep of `src/` for `"load"` finds no markwright option literal; the only `eager` match is a comment in `markdown_pipeline.py`.

Verdict: met.

### G28: The Click-to-Load Host Script

> Bartleby follows markwright's Click-to-Load docs page for the host script and the provider processor calls.

Source: spec.md line 129.

Evidence: commit `0363c5b` added `click_to_load.js` and `click_to_load.css` to the base theme, and G18 shows the assets load only when a site sets `load: click`.

Verdict: met with a note.
Note: the swap script adds three deliberate changes beyond markwright's host script: a `data-mw-version` guard, a per-src promise map, and focus moved to the live element.

## For Mason

Open items, none of which blocks the gate:

1. CodePen and Instagram embed URLs in `content/tour/index.md`: CodePen (`MattCowley/vwPzeX`) could not be verified from the sandbox (403), and the Instagram post is markwright's docs sample.
   Swap both for URLs you want to show.
   Twitter (`jack/status/20`) also showed only its fallback link in headless Chromium; look at it in a real browser.
2. Non-atomic rebuild window in `serve`: a request during a rebuild can 404.
   Parked, with an atomic output swap as the fix.
3. A non-permission `OSError` during the output swap (a full disk on a cross-device move) surfaces unlabeled.
   Parked.
4. The material no-TOC content cap (40rem, right side empty at 1280) wants your eye.
5. The docs link to `ACKNOWLEDGMENTS.md` points at `blob/main` and 404s until this branch merges.
6. `pyproject.toml` says `MIT` while the wheel bundles other permissive licenses.
   A compound PEP 639 expression is your decision.
7. The home page no longer names `llms.txt` and the agent files.
   One line would fit the agents-first positioning.
8. `enable` writes no `nav` entry, so `enable blog news` needs `- News: news/` added by hand to show a tab.
9. Version stays 0.1.0, and the CHANGELOG section stays `[Unreleased]`.
   Release timing is yours.

To reproduce the clean-install walk:

```bash
GATE=/some/scratch/dir && mkdir -p $GATE/work && cd /path/to/bartleby
just check
uv build --wheel --out-dir $GATE/wheel
uv venv $GATE/venv --python 3.14
uv pip install -p $GATE/venv/bin/python $GATE/wheel/bartleby_ssg-0.1.0-py3-none-any.whl
unzip -l $GATE/wheel/*.whl | grep -Ei "scaffold|tour|click_to_load|ACKNOWLEDG|THIRD-PARTY|main.css"
cd $GATE/work                                   # outside the repo
B=$GATE/venv/bin/bartleby
env -u VIRTUAL_ENV $B new site gate-site && cd gate-site
env -u VIRTUAL_ENV $B build --strict
env -u VIRTUAL_ENV $B serve --port 0            # edit content/index.md, watch the reload, Ctrl+C
cd .. && $B new site --full-config gate-full && $B config schema --output json | python -c "import json,sys; print(len(json.load(sys.stdin)['fields']))"
cd gate-site && $B enable blog news && $B new post "Gate Post" --type news   # set draft: false
$B build --strict && ls site/feed.xml site/atom.xml site/news/feed.xml site/news/atom.xml
$B config show; $B config get site.title; $B config set site.title Gate
$B build --set site.title=Over; $B build --base-url https://gate.test
(cd /path/to/bartleby/docs && uv run bartleby build --strict)     # 76 pages
```
