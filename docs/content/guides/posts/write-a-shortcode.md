---
title: "Write a Custom Shortcode"
description: "Build a reusable Jinja2 fragment that authors call from Markdown with the [% ... %] syntax."
date: 2026-06-02
audience: existing-user
tags:
  - shortcodes
  - templates
authors:
  - mason
---

Shortcodes let authors call reusable template fragments from inside Markdown.
This guide builds a `youtube` shortcode that embeds a YouTube video from a video ID.

<!-- more -->

## Step 1: Create the Shortcode Template

Create `shortcodes/youtube.html`:

```html
<div class="youtube-embed">
  <iframe
    src="https://www.youtube.com/embed/{{ id }}"
    title="{{ title or 'YouTube video' }}"
    frameborder="0"
    allow="accelerometer; autoplay; clipboard-write;
           encrypted-media; gyroscope; picture-in-picture"
    allowfullscreen>
  </iframe>
</div>
```

## Step 2: Use It in a Post

```markdown
---
title: "Conference Talk"
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

The shortcode renders before Markdown processing.
The resulting HTML then passes through Python-Markdown as raw HTML.

## Step 4: Wrap Content with a Block Shortcode

The `youtube` shortcode is inline, with no closing tag.
A shortcode that wraps content uses the block form:

```markdown
[% note %]
This paragraph is wrapped in a styled note container.
It can span multiple lines and include **markdown**.
[% /note %]
```

Its template reads the body from the `content` variable:

```html
<!-- shortcodes/note.html -->
<div class="shortcode-note">
  {{ content }}
</div>
```

## See Also

- [Shortcodes reference](../../reference/pages/shortcodes.md): the full syntax and the variables a template receives
- [Customization seams](../../concepts/customization-seams.md): where `shortcodes/` fits with the other extension points
