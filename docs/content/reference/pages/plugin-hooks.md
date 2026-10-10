---
title: "Plugin Hook Events"
description: "Every event, its signature, and where it fires in the build."
tags:
  - hooks
  - plugins
---

This page lists the hook events Bartleby dispatches.
Define a module-level function named `on_<event>` in `hooks/*.py`, or in a module that an installed plugin exposes, to register a handler.
See [Plugins and hooks](../../concepts/plugins-and-hooks.md) for how Bartleby finds handlers.

Every event except `on_serve` fires during `bartleby build`.
Step numbers refer to the [build pipeline](build-pipeline.md).

## Return Values

Events fall into three kinds:

- **Threaded events** pass a value, such as the config or the HTML, through every handler.
  A handler that returns `None` leaves the value unchanged.
  Any other return value replaces it for the next handler.
- **Notification events** ignore the return value.
- **Query events** (only `on_page_read_source`) stop at the first handler that returns something other than `None`.

## Lifecycle

### `on_startup`

Fires at the start of every build, with the argument `"build"`.
Step 3, notification event.

```python
def on_startup(command: str) -> None: ...
```

### `on_shutdown`

Fires at the end of every build, after `on_post_build`, and after `on_build_error` when a build fails.
Step 36, notification event.
The event takes no arguments.

```python
def on_shutdown() -> None: ...
```

## Configuration and Setup

### `on_config`

Fires once, right after the config loads.
Step 3, threaded event.

```python
def on_config(config: BartlebyConfig) -> BartlebyConfig | None: ...
```

### `on_pre_build`

Fires after `on_config` and before authors and content load.
Step 3, notification event.

```python
def on_pre_build(config: BartlebyConfig) -> None: ...
```

### `on_files`

Fires after content discovery and draft filtering.
The first argument is the list of content pages.
Return a modified list to replace the working set.
Generated taxonomy and listing pages are not in the list.
Step 8, threaded event.

```python
def on_files(
    files: list[Page], config: BartlebyConfig
) -> list[Page] | None: ...
```

### `on_nav`

Fires after Bartleby builds the navigation and links previous and next pages.
Step 15, threaded event.

```python
def on_nav(nav: Navigation, config: BartlebyConfig) -> Navigation | None: ...
```

### `on_env`

Fires after Bartleby creates the Jinja2 environment.
Use it to register filters and globals.
Step 16, threaded event.

```python
def on_env(
    env: jinja2.Environment, config: BartlebyConfig
) -> jinja2.Environment | None:
    env.filters["shout"] = lambda text: text.upper() + "!"
    return env
```

## Per-Page Events

These events fire for every page, including the generated listing and taxonomy pages.
The step numbers show where in the build each one runs.

### `on_pre_page`

Fires before Bartleby processes a page.
Step 18, notification event.

```python
def on_pre_page(page: Page, config: BartlebyConfig) -> None: ...
```

### `on_page_read_source`

Fires before shortcodes run.
Return a string to use in place of the page's source.
The first handler that returns a string wins, and later handlers do not run.
Step 18, query event.

```python
def on_page_read_source(page: Page, config: BartlebyConfig) -> str | None: ...
```

### `on_page_markdown`

Fires after shortcodes run and just before Markdown renders.
Most content rewriting belongs here.
Step 18, threaded event.

```python
def on_page_markdown(
    markdown: str, page: Page, config: BartlebyConfig
) -> str | None:
    return markdown.replace("@user", "[@user](/people/user/)")
```

### `on_page_content`

Fires after Markdown renders and before template assembly.
The value is the page's HTML body.
Step 18, threaded event.

```python
def on_page_content(
    html: str, page: Page, config: BartlebyConfig
) -> str | None: ...
```

### `on_page_context`

Fires after Bartleby builds the template context and before the template renders.
Step 20, threaded event.

```python
def on_page_context(
    context: dict[str, object], page: Page, config: BartlebyConfig
) -> dict[str, object] | None: ...
```

### `on_post_page`

Fires after the template renders and before Bartleby writes the file.
Modify the final HTML here.
Step 20, threaded event.

```python
def on_post_page(output: str, page: Page, config: BartlebyConfig) -> str | None:
    return output.replace("BUILD_TIME", str(datetime.datetime.now()))
```

## After the Build

### `on_post_build`

Fires after the new output replaces `site/`.
It also fires at the end of a `--dry-run` build.
Step 36, notification event.

```python
def on_post_build(config: BartlebyConfig) -> None: ...
```

### `on_build_error`

Fires when Markdown rendering or template rendering fails for one or more pages.
The argument is the `BuildError`, which holds every collected page error.
Metadata validation errors and strict-mode cross-reference errors raise before this point and do not fire the event.
Step 18 or 20, notification event.

```python
def on_build_error(error: BuildError) -> None: ...
```

### `on_serve`

Fires when the dev server starts.
It is the only event that `bartleby build` does not fire.
Notification event.

```python
def on_serve(server: object, config: BartlebyConfig) -> None: ...
```

## Priority Ordering

Use `@event_priority(n)` from `bartleby.plugins` to order handlers within an event.
The handler with the highest priority runs first, and handlers without a priority default to 0.

```python
from bartleby.plugins import event_priority

@event_priority(99)
def on_page_markdown(markdown, page, config):
    return f"<!-- generated {page.title} -->\n{markdown}"
```

The decorator works on module-level functions in `hooks/*.py` and in installed plugin modules.
