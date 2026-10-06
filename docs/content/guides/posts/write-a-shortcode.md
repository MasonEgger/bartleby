---
title: "Write a custom shortcode"
description: "Build a reusable Jinja2 fragment invocable from Markdown with [% ... %] syntax."
date: 2026-06-02
audience: existing-user
tags:
  - shortcodes
  - templates
authors:
  - mason
---

Shortcodes let authors call into reusable template fragments from inside Markdown. This guide builds a `youtube` shortcode that embeds a YouTube video given a video ID.

<!-- more -->

## Step 1: Create the shortcode template

Drop a file at `shortcodes/youtube.html`:

```html
<div class="youtube-embed">
  <iframe
    src="https://www.youtube.com/embed/{{ id }}"
    title="{{ title or 'YouTube video' }}"
    frameborder="0"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
    allowfullscreen>
  </iframe>
</div>
```

## Step 2: Use it in a post

```markdown
---
title: "Conference talk"
date: 2026-06-02
---

Here's my talk from PyCon:

[% youtube id="dQw4w9WgXcQ" title="My PyCon talk" %]

The slides are also available below.
```

## Step 3: Build

```bash
bartleby build
```

The shortcode renders before markdown processing, so the resulting HTML flows through Python-Markdown as raw HTML (the `md_in_html` extension handles it cleanly).

## Block form vs. inline form

The `youtube` shortcode is inline (no closing tag). For shortcodes that wrap content, use the block form:

```markdown
[% note %]
This paragraph is wrapped in a styled note container.
It can span multiple lines and include **markdown**.
[% /note %]
```

```html
<!-- shortcodes/note.html -->
<div class="shortcode-note">
  {{ content }}
</div>
```

The block body becomes the `content` variable in the template.

## Available context

Shortcode templates receive:

- `content` — the body of a block shortcode (empty string for inline)
- One variable per `key="value"` argument
- The surrounding template context (`build`, `page`)

## See also

- [Shortcodes reference](../../reference/pages/shortcodes.md) — full syntax and lookup rules
- [Customization seams](../../concepts/customization-seams.md) — where `shortcodes/` fits with other extension points
