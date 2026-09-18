---
title: "Add a custom Jinja2 filter"
description: "Register a filter via the on_env hook and use it in templates."
date: 2026-06-02
audience: theme-author
tags:
  - hooks
  - templates
authors:
  - mason
---

Sometimes you need a small template helper — uppercase shouting, slug coercion, currency formatting. The cleanest way to add one is the `on_env` hook.

<!-- more -->

## Step 1: Create the hook file

```
mysite/
└── hooks/
    └── jinja_extras.py
```

## Step 2: Register the filter

```python
# hooks/jinja_extras.py

def on_env(env, config):
    env.filters["shout"] = lambda text: text.upper() + "!"
    env.filters["currency"] = lambda amount: f"${amount:,.2f}"
    return env
```

Bartleby globs `hooks/*.py` at build start and registers every module-level function whose name matches a known event. `on_env` fires once, right after the Jinja2 environment is created.

## Step 3: Use the filter in a template

```jinja2
<h1>{{ page.title | shout }}</h1>
<p>Subscription: {{ page.custom_metadata.price | currency }}</p>
```

## Notes

- Filters registered this way are available to every template — theme, overrides, your own, and shortcode fragments.
- Return the modified `env` from the hook. Returning `None` is also accepted (the env is mutated in place), but explicit returns make the data flow obvious.
- If two hook files register a filter with the same name, the later registration wins. Use `@event_priority(n)` to control the order.

## See also

- [Plugins and hooks](../../concepts/plugins-and-hooks.md) — the discovery model
- [Plugin hook events](../../reference/pages/plugin-hooks.md) — full event catalogue
