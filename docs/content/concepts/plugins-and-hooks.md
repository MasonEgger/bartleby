---
title: "Plugins and hooks"
description: "File-based hook discovery and event dispatch — no entry points, no subclasses."
---

Bartleby has no public plugin API and no entry-point discovery. User extensions live in `hooks/*.py` at the project root. Bartleby imports each file at build start and registers any module-level function whose name matches a known event.

## The hooks directory

```
mysite/
└── hooks/
    ├── inject_banner.py
    └── jinja_extras.py
```

A hook file is just a Python module:

```python
# hooks/inject_banner.py
def on_page_markdown(markdown, page, config):
    if page.output_url == "/":
        return f"# Banner!\n\n{markdown}"
    return markdown
```

Bartleby globs `hooks/*.py`, skips files starting with `_`, imports each, and registers every module-level function whose name matches a known event.

## Hook events

| Event | Signature | Returns |
|-------|-----------|---------|
| `on_startup` | `(command: str)` | `None` |
| `on_shutdown` | `()` | `None` |
| `on_config` | `(config)` | modified config or `None` |
| `on_pre_build` | `(config)` | `None` |
| `on_files` | `(files, config)` | modified files or `None` |
| `on_pages` | `(pages, config)` | modified pages list or `None` |
| `on_nav` | `(nav, config)` | modified `Navigation` or `None` |
| `on_env` | `(env, config)` | modified `jinja2.Environment` or `None` |
| `on_pre_page` | `(page, config)` | modified page or `None` |
| `on_page_read_source` | `(page, config)` | modified source or `None` |
| `on_page_markdown` | `(markdown, page, config)` | modified markdown or `None` |
| `on_page_content` | `(html, page, config)` | modified HTML or `None` |
| `on_page_context` | `(context, page, config)` | modified context or `None` |
| `on_post_page` | `(output, page, config)` | modified output or `None` |
| `on_post_build` | `(config)` | `None` |
| `on_build_error` | `(error)` | `None` |
| `on_serve` | `(server, config)` | `None` |

A handler returning `None` leaves the threaded value unchanged; any non-`None` return replaces it for downstream handlers.

## Ordering with @event_priority

When multiple handlers register for the same event, they fire in priority order — highest first. Unprioritised handlers default to priority 0.

```python
from bartleby.plugins import event_priority

@event_priority(50)
def on_page_markdown(markdown, page, config):
    # Runs before any unprioritised handler.
    return markdown.replace("YEAR", "2026")
```

The decorator works on both module-level functions in `hooks/*.py` and methods on the internal `BasePlugin` class.

## Internal BasePlugin

`BasePlugin` is Bartleby's internal-only base class for grouping related handlers. It's not part of the public API — user extensions should always use module-level functions in `hooks/`.
