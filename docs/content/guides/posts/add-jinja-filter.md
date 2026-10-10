---
title: "Add a Custom Jinja2 Filter"
description: "Register a filter with the on_env hook and use it in templates."
date: 2026-06-02
audience: plugin-author
tags:
  - hooks
  - templates
authors:
  - mason
---

Sometimes you need a small template helper, such as uppercase shouting, slug coercion, or currency formatting.
The cleanest way to add one is the `on_env` hook.

<!-- more -->

## Step 1: Create the Hook File

Create `hooks/jinja_extras.py` in your project:

```
mysite/
└── hooks/
    └── jinja_extras.py
```

## Step 2: Register the Filter

Add an `on_env` function that attaches your filters to the environment:

```python
# hooks/jinja_extras.py

def on_env(env, config):
    env.filters["shout"] = lambda text: text.upper() + "!"
    env.filters["currency"] = lambda amount: f"${amount:,.2f}"
    return env
```

Bartleby loads `hooks/*.py` at build start and registers each module-level function whose name matches a known event.
`on_env` fires once, right after the Jinja2 environment is created.

## Step 3: Use the Filter in a Template

```jinja2
<h1>{{ page.title | shout }}</h1>
<p>Subscription: {{ page.custom_metadata.price | currency }}</p>
```

## Notes

- Filters registered this way are available to every template, including theme templates, overrides, your own templates, and shortcode fragments.
- Return the modified `env` from the hook.
  Returning `None` also works, because the environment is changed in place, but an explicit return makes the data flow obvious.
- If two hook files register a filter with the same name, the later registration wins.
  Use `@event_priority(n)` to control the order.

## See Also

- [Plugins and hooks](../../concepts/plugins-and-hooks.md): the discovery model
- [Plugin hook events](../../reference/pages/plugin-hooks.md): the full event list
