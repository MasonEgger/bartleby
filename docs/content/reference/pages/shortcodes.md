---
title: "Shortcodes"
description: "The [% ... %] syntax and how Bartleby finds shortcode templates."
tags:
  - shortcodes
  - templates
---

Shortcodes are Jinja2 fragments that you invoke from inside Markdown.
They use `[% ... %]` delimiters instead of `{% %}`, so they never collide with Jinja2 syntax in theme templates.

## Syntax

**Block form** opens with the name and closes with `/name`:

```markdown
[% note %]
This is important.
[% /note %]
```

**Inline form** is a single tag with no closing tag:

```markdown
Built with Bartleby [% version %].
```

**Arguments** are `key="value"` pairs after the name.
Values must use double quotes.

```markdown
[% callout type="warning" title="Careful" %]
Mind the gap.
[% /callout %]
```

Bartleby reads a shortcode as block form when a matching closing tag follows it later in the page.
Otherwise it reads the tag as inline.
Shortcode syntax inside fenced code blocks and inline code spans stays literal.

## Template Lookup

Each shortcode renders through `shortcodes/<name>.html`.
Bartleby looks for that name on the Jinja2 search path, in this order:

1. `overrides/`
2. `templates/`
3. The project root
4. The theme chain

For most sites, the file lives at `shortcodes/<name>.html` in the project root.
None of the bundled themes ships shortcodes.

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

## Template Context

A shortcode template receives:

- `build` and `page`, from the page being rendered
- `content`, the body of a block shortcode, with surrounding whitespace trimmed (an empty string for inline forms)
- One variable per `key="value"` argument

So `[% callout type="warning" title="Careful" %]body[% /callout %]` exposes `type`, `title`, and `content` to the template.

## When Shortcodes Run

Shortcodes run before Markdown rendering.
The result then passes through the `on_page_markdown` hook and into Python-Markdown.
A shortcode can therefore produce Markdown that later extensions, such as admonitions and tables, will parse.

## Errors

A shortcode that names a template Bartleby cannot find raises `ShortcodeError` with the name and the template to create, such as `unknown shortcode 'note' (fix: create shortcodes/note.html under your project's templates/ directory, or fix the name in the page)`.
The build fails, and there is no silent passthrough.
