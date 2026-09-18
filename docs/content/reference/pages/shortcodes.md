---
title: "Shortcodes"
description: "[% ... %] syntax and template fragment lookup."
tags:
  - shortcodes
  - templates
---

Shortcodes are Jinja2 fragments invoked from inside Markdown. They use `[% ... %]` delimiters instead of `{% %}` to avoid colliding with Jinja2 syntax in theme templates.

## Syntax

**Block form** — opens with the name, closes with `/name`:

```markdown
[% note %]
This is important.
[% /note %]
```

**Inline form** — single tag, no closing:

```markdown
Built with Bartleby [% version %].
```

**Arguments** — `key="value"` pairs after the name:

```markdown
[% callout type="warning" title="Careful" %]
Mind the gap.
[% /callout %]
```

## Template lookup

Each shortcode renders through `shortcodes/<name>.html`. The Jinja2 environment searches the project's `shortcodes/` directory first, then any path on its search list, so theme-bundled shortcodes can also be picked up.

A typical template:

```html
<!-- shortcodes/note.html -->
<div class="shortcode-note">
  {{ content }}
</div>
```

```html
<!-- shortcodes/callout.html -->
<div class="callout callout-{{ type }}">
  <h3>{{ title }}</h3>
  {{ content }}
</div>
```

## Template context

The shortcode template receives:

- Everything from the shortcode invocation's surrounding context (typically `build` and `page`)
- A `content` variable carrying the body of a block shortcode (empty string for inline forms)
- One variable per `key="value"` argument

So `[% callout type="warning" title="Careful" %]body[% /callout %]` exposes `type`, `title`, and `content` to the template.

## When shortcodes run

Shortcode preprocessing runs before markdown rendering. The post-shortcode source flows through the `on_page_markdown` plugin hook and then into Python-Markdown. This means a shortcode can produce markdown that further extensions (admonitions, tables, etc.) will parse.

## Error behaviour

A shortcode referencing a non-existent template raises `ShortcodeError` with the offending name. The build fails fast; there's no silent passthrough.
