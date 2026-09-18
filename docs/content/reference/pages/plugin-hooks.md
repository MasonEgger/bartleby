---
title: "Plugin hook events"
description: "Every event, its signature, and where it fires in the build."
tags:
  - hooks
  - plugins
---

This page is the canonical list of hook events Bartleby dispatches. Drop a module-level function named `on_<event>` into `hooks/*.py` to register a handler. See [Plugins and hooks](../../concepts/plugins-and-hooks.md) for the discovery model.

## Lifecycle

### on_startup

Fired when the CLI starts (reserved — not currently dispatched).

```python
def on_startup(command: str) -> None: ...
```

### on_shutdown

Fired when the CLI exits (reserved).

```python
def on_shutdown() -> None: ...
```

## Configuration

### on_config

Fires once at build start, immediately after the config is loaded. Return a modified config to replace it for the rest of the build.

```python
def on_config(config: BartlebyConfig) -> BartlebyConfig | None: ...
```

## Build setup

### on_pre_build

Fires after config but before any rendering (reserved).

### on_files

Fires after content discovery (reserved).

### on_pages

Fires after page discovery and draft filtering. Return a modified list to replace the working set.

```python
def on_pages(pages: list[Page], config: BartlebyConfig) -> list[Page] | None: ...
```

### on_nav

Fires after navigation construction (reserved).

### on_env

Fires after the Jinja2 environment is created. Use this to register custom filters and globals.

```python
def on_env(env: jinja2.Environment, config: BartlebyConfig) -> jinja2.Environment | None:
    env.filters["shout"] = lambda text: text.upper() + "!"
    return env
```

## Per-page

### on_pre_page

Fires before any page processing (reserved).

### on_page_read_source

Fires after a page's source is read from disk (reserved).

### on_page_markdown

Fires immediately before markdown rendering. Most common hook for content rewriting.

```python
def on_page_markdown(markdown: str, page: Page, config: BartlebyConfig) -> str | None:
    return markdown.replace("@user", "[@user](/people/user/)")
```

### on_page_content

Fires after markdown rendering, before template assembly (reserved).

### on_page_context

Fires after template context is built (reserved).

### on_post_page

Fires after template render, before writing to disk. Modify the final HTML here.

```python
def on_post_page(output: str, page: Page, config: BartlebyConfig) -> str | None:
    return output.replace("BUILD_TIME", str(datetime.datetime.now()))
```

## Post-build

### on_post_build

Fires after every page has been written (reserved).

### on_build_error

Fires when the build raises (reserved).

### on_serve

Fires when the dev server starts (reserved).

## Priority ordering

Use `@event_priority(n)` from `bartleby.plugins` to order handlers within an event. Higher priority runs first; unprioritised handlers default to 0.

```python
from bartleby.plugins import event_priority

@event_priority(99)
def on_page_markdown(markdown, page, config):
    return f"<!-- generated {page.title} -->\n{markdown}"
```

## "Reserved" hooks

Several events are listed above as "reserved" — the names are recognised by `discover_hooks` and the dispatch wiring is in place, but Bartleby's current build pipeline doesn't yet fire them. They're stable identifiers safe to register against; handlers will start firing when the corresponding pipeline phase is added.
