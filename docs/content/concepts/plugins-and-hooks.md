---
title: "Plugins and Hooks"
description: "How Bartleby finds hook functions and dispatches build events to them."
---

Bartleby has one extension model: functions named after build events.
A function named `on_page_markdown` runs for every page, and a function named `on_env` runs once when the Jinja2 environment is ready.
Bartleby finds these functions in two places.
Your project's `hooks/*.py` files are the first.
Installed packages that register an entry point in the `bartleby.plugins` group are the second.

## The Hooks Directory

```
mysite/
└── hooks/
    ├── inject_banner.py
    └── jinja_extras.py
```

A hook file is a plain Python module:

```python
# hooks/inject_banner.py
def on_page_markdown(markdown, page, config):
    if page.output_url == "/":
        return f"# Banner!\n\n{markdown}"
    return markdown
```

At build start, Bartleby reads each `hooks/*.py` file in alphabetical order and skips files whose names start with `_`.
It registers every module-level function whose name matches a known event.
A hook file can import an underscore-prefixed sibling module at the top of the file, which is the way to share helper code between hooks.

## Installed Plugins

A package can ship hooks of its own.
It declares an entry point in the `bartleby.plugins` group that names a module, and Bartleby registers that module's `on_<event>` functions the same way it registers a hook file.
To turn an installed plugin off without uninstalling it, map its entry point name to `false` under `plugins` in `bartleby.yml`.

At equal priority, installed plugins run first, in alphabetical order by entry point name, and your project's hooks run last.

## Events and Dispatch

Bartleby dispatches 16 events across the build, from `on_startup` to `on_shutdown`.
The [plugin hook reference](../reference/pages/plugin-hooks.md) lists each event with its signature, its return value, and its place in the build.
The [build pipeline reference](../reference/pages/build-pipeline.md) shows the same events in sequence.

Most events pass a value through the handlers.
A handler that returns `None` leaves the value unchanged.
Any other return value replaces it for the handlers that run next.
That rule makes a hook safe to write as "change this page if it matches, otherwise do nothing."

## Ordering

When several handlers register for the same event, the one with the highest priority runs first.
A handler with no priority has priority 0.
You set one with the `@event_priority` decorator from `bartleby.plugins`, as the [hook reference](../reference/pages/plugin-hooks.md#priority-ordering) shows.

## The Internal BasePlugin

`BasePlugin` is an internal base class that Bartleby uses to group its own handlers.
User extensions should always be module-level functions.
