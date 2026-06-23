# Lessons Learned

## Recent
<!-- 10 most recent lessons, newest first -->

- Stdlib response attributes are typed `Any` under mypy strict: `http.client.HTTPResponse.status` from `urllib.request.urlopen` triggers `no-any-return` when compared and returned directly; cast with `int(response.status)` before the bool comparison (2026-06-23)
- Static-artifact builders (schema.json, content-index.json) should filter drafts themselves via `select_published`, not trust the caller to pre-filter; a unit test that passes raw `pages` to `build_schema_json` otherwise inflates taxonomy term counts with draft tags. Filter inside every builder so the contract holds regardless of call site (2026-06-22)
- `bartleby new post` scaffolds with `draft: true`, so a CLI test that creates a post and asserts it appears in `content list` (which excludes drafts by default) will silently fail; in published-listing tests write a `draft: false` post directly instead of relying on the scaffold default (2026-06-22)
- For the `bartleby schema` agent surface, derive "in-use" taxonomy terms by calling the existing `build_taxonomies` collector instead of re-walking `page.taxonomy_values`; the schema's notion of a term then matches exactly what the build indexes, and the same derivation function is reusable by the static `schema.json` step (2026-06-22)
- For dev-server hot reload of `hooks/*.py`, read the source text and `compile`/`exec` it into a fresh module each rebuild; `importlib.util.spec_from_file_location` + `exec_module` serves a STALE hook on sub-second edits because `SourceFileLoader`'s bytecode cache is keyed on mtime, and the file's mtime is unchanged within the same second the server last loaded it (2026-06-22)
- A value-threading hook dispatch (`run_event`: item-first, non-None return replaces) does not fit every spec hook. Query hooks whose first positional is real data (`on_page_read_source(page, config)`) need a kwargs-only first-non-None dispatch; zero-arg lifecycle hooks (`on_shutdown()`) need a no-item dispatch. Forcing them through `run_event` collides on the threaded item (2026-06-22)
- When a new render helper forwards args into an existing context builder, copy that builder's param types verbatim (`list[Any]`, `dict[str, Any]`); mypy strict treats `dict`/`list` as invariant, so a "tighter" `list[object]`/`Sequence` annotation breaks the forward (`list[NavItem]` is not a `list[object]`) (2026-06-22)
- When gating existing template markup behind a Jinja global (e.g. a `feature()` helper), grep `tests/` for every assertion string on that markup first — multiple test files build their own bare `jinja2.Environment` and each needs the global registered, or pre-existing assertions on the now-gated markup go red (2026-06-22)
- In a build test, a project template that exists only to bump the template-tree mtime must not shadow a theme template; `templates/base.html` containing `{% extends 'base.html' %}` self-references through the cascade and hits Jinja's recursion limit. Use a unique non-cascade name like `custom-partial.html` (2026-06-22)
- When asserting that vendored/minified third-party code does NOT contain a marker, match the exact original stub string, not a generic word — minified Alpine.js contains an internal `__placeholder` token, so a `"placeholder" not in text` check false-positived against the real bundle (2026-06-22)
## Architecture

- Static-artifact builders (schema.json, content-index.json) should filter drafts themselves via `select_published`, not trust the caller to pre-filter; passing raw `pages` to `build_schema_json` otherwise inflates taxonomy term counts with draft tags. Filter inside every builder so the contract holds regardless of call site (2026-06-22)
- For the `bartleby schema` agent surface, derive "in-use" taxonomy terms by calling the existing `build_taxonomies` collector instead of re-walking `page.taxonomy_values`; the schema's notion of a term then matches exactly what the build indexes, and the same derivation function is reusable by the static `schema.json` step (2026-06-22)
- CLI command results plug into the shared `output.render()` path for free by implementing the `output.Result` protocol (`exit_code`/`to_dict`/`to_text`); a new command needs no formatter changes and inherits sorted-key byte-stable JSON (2026-06-22)

## Typing

- When a new render helper forwards args into an existing context builder, copy that builder's param types verbatim (`list[Any]`, `dict[str, Any]`); mypy strict treats `dict`/`list` as invariant, so a "tighter" `list[object]`/`Sequence` annotation breaks the forward (`list[NavItem]` is not a `list[object]`) (2026-06-22)
- Stdlib response attributes are typed `Any` under mypy strict: `http.client.HTTPResponse.status` from `urllib.request.urlopen` triggers `no-any-return` when compared and returned directly; cast with `int(response.status)` before the bool comparison (2026-06-23)

## Testing

- `bartleby new post` scaffolds with `draft: true`, so a CLI test that creates a post and asserts it appears in `content list` (which excludes drafts by default) will silently fail; in published-listing tests write a `draft: false` post directly instead of relying on the scaffold default (2026-06-22)
- When gating existing template markup behind a Jinja global (e.g. a `feature()` helper), grep `tests/` for every assertion string on that markup first — multiple test files build their own bare `jinja2.Environment` and each needs the global registered, or pre-existing assertions on the now-gated markup go red (2026-06-22)

- In a build test, a project template that exists only to bump the template-tree mtime must not shadow a theme template; `templates/base.html` containing `{% extends 'base.html' %}` self-references through the cascade and hits Jinja's recursion limit. Use a unique non-cascade name like `custom-partial.html` (2026-06-22)
- When asserting that vendored/minified third-party code does NOT contain a marker, match the exact original stub string, not a generic word — minified Alpine.js contains an internal `__placeholder` token, so a `"placeholder" not in text` check false-positived against the real bundle (2026-06-22)
- In CLI tests, a scaffolding helper (`new site`) that now prints its own structured result pollutes `capsys` stdout ahead of the command under test; clear capsys after setup, or parse only the last non-empty stdout line, before `json.loads` (2026-06-22)
- When migrating output from `print(..., file=sys.stderr)` to `logging.getLogger`, rewrite the asserting tests from `capsys` to `caplog` (with `caplog.at_level("WARNING", logger="bartleby")`) in the same dispatch — the suite otherwise goes red because capsys can no longer see logger output (2026-06-22)
- Integration tests that only check file *existence* miss content bugs. After `bartleby new site && bartleby new post && bartleby build`, the post template rendered an empty author byline and the listing page rendered an empty post list, yet every test passed because they stopped at `(site / "blog" / "index.html").exists()` (2026-06-02)
- Dogfooding documentation against the tool is a high-signal integration test — writing the docs for Bartleby's shortcode feature immediately surfaced a real bug where the preprocessor didn't respect fenced code blocks or inline `code` spans (2026-06-02)

## Tooling

- Launch long-lived local servers (`/bpe:review`, preview HTTP) with `setsid <cmd> > log 2>&1 < /dev/null &` — a plain background job gets reaped on shell teardown and a separately-run server gets killed by the background-task timeout; setsid in its own session survives both (2026-06-21)
- `do-markdown` is not on PyPI — must add `[tool.uv.sources]` with `path = "../do-markdown", editable = true` for local resolution (2026-05-02)

## Workflow

- When a plan splits RED and GREEN into separate sub-items, an autonomous one-commit-per-dispatch BPE executor must bundle the matching RED+GREEN pair in one dispatch, because the never-commit-a-red-suite rule forbids ending a dispatch on the RED-only sub-item (2026-06-22)
- When a `/bpe:brainstorm` decision and the drafted spec diverge, trust the `/bpe:review` + `/bpe:apply-review` cycle to catch it — the plugin-API "both in v1 vs staged" conflict surfaced exactly there and got resolved against the brainstorm (2026-06-21)
- Run the actual smoke test before trusting a review claim — a subagent reported front-matter leaking into `.md` variants; running `new site && build` and inspecting output refuted it before it reached the report (2026-06-21)
- Run `/bpe:lessons prune` periodically (not just at end of major work) — the BPE goal description called for it and the pile of redundant Python/YAML notes that accumulated across 27 implementation steps was real lint debt (2026-06-02)
- The previous session's "Suggested Skills for Next Session" line is a high-signal hint — trust it on the next `/bpe:execute-plan` and invoke those skills first, then layer on anything the current step uniquely needs (2026-05-23)
- Auto-loaded CLAUDE.md rules (arriving as system-reminders) are NOT equivalent to skills invoked via the Skill tool — bias toward invoking on uncertainty, since double-loading is harmless but skipping is not (2026-05-17)

## Plugin Development

- For dev-server hot reload of `hooks/*.py`, read the source text and `compile`/`exec` it into a fresh module each rebuild; `importlib.util.spec_from_file_location` + `exec_module` serves a STALE hook on sub-second edits because `SourceFileLoader`'s bytecode cache is keyed on mtime, and the file's mtime is unchanged within the same second the server last loaded it (2026-06-22)
- A value-threading hook dispatch (`run_event`: item-first, non-None return replaces) does not fit every spec hook. Query hooks whose first positional is real data (`on_page_read_source(page, config)`) need a kwargs-only first-non-None dispatch; zero-arg lifecycle hooks (`on_shutdown()`) need a no-item dispatch. Forcing them through `run_event` collides on the threaded item (2026-06-22)
