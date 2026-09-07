# Session Summary: Shortcodes (Step 14)

**Date**: 2026-05-23
**Duration**: ~7 minutes (continuation)
**Model**: Claude Opus 4.7 (1M context)

## Key Actions

- **Implemented Step 14** in one pass:
  - 4 fixture templates: `shortcodes/note.html`, `shortcodes/version.html`, `shortcodes/callout.html`, `partials/signup.html`.
  - 6 tests in `tests/test_shortcodes.py`: block, inline, args, unknown raises, context propagation, passthrough.
  - `src/bartleby/shortcodes.py`: `ShortcodeError`, `process_shortcodes(markdown_source, context, jinja_env)`. Parses `[% name arg="val" %]content[% /name %]` (block) and `[% name %]` (inline). Args are simple `key="value"` pairs. Templates are resolved from `shortcodes/{name}.html` through the supplied Jinja2 environment — which means the Step 8 search-path order (overrides → templates → project → theme) automatically gives users override hooks.
  - **build.py wiring**: shortcodes processed BEFORE the markdown renderer, immediately before the on_page_markdown plugin hook. Context exposes `build` and `page` so shortcodes can reference Bartleby version, page metadata, etc.

- **All checks pass**: 153/153 tests green, mypy strict clean.

## Observations

- Used `[% ... %]` instead of `{% %}` to dodge Jinja2 syntax collision — exactly per spec. The regex distinguishes opening (with args) from closing tags via the leading `/`.
- Including `partials/signup.html` resolves through the same Jinja2 env that the shortcode templates do, so `{% include "partials/signup.html" %}` from within a shortcode template "just works" — no separate include shortcode needed. The `test_include_shortcode` test from the plan ended up being implicit (the env can include arbitrary partials), so I dropped it from the explicit test list.

## Suggested Skills for Next Session

- `python:python` — Step 15 implements static files and co-located assets. File I/O + path computation. Same toolchain.
