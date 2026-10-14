---
title: "Override a Single Theme Template"
description: "Replace one template or partial from the active theme without forking the theme."
date: 2026-06-02
audience: theme-author
tags:
  - theme
  - templates
authors:
  - mason
---

You can replace any theme template, including the header, from your project without copying the rest of the theme.
This guide replaces the `partials/header.html` partial that the default `scrivener` theme provides.

<!-- more -->

## Step 1: Find the Template to Replace

Run `bartleby theme inspect` and look for the file you want to change:

```bash
bartleby theme inspect
```

Each line names a theme file and the layer that provides it.
For the header, the line is:

```
templates/partials/header.html  (scrivener)
```

The path after `templates/` is the name you override.
Here it is `partials/header.html`.

## Step 2: Create the Override

Create the same path under `overrides/` in your project root:

```
mysite/
├── bartleby.yml
├── content/
└── overrides/
    └── partials/
        └── header.html
```

## Step 3: Write the Replacement

Bartleby searches `overrides/` before the theme, so your file wins.
It receives the same template context as the original: `site`, `page`, `nav`, `config`, and the rest.

```html
<header class="my-custom-header">
  <a href="/" class="site-brand">{{ site.title }}</a>
  <nav>
    <ul>
      {% for item in nav %}
      <li><a href="{{ item.url }}">{{ item.title }}</a></li>
      {% endfor %}
    </ul>
  </nav>
</header>
```

This header omits the search trigger and the color-mode toggle that the `scrivener` header renders.
To keep them, include `partials/search_trigger.html` when `feature('search')` is on, and copy the toggle button from the original header.

## Step 4: Build

```bash
bartleby build
```

Every page now uses your header, and no other theme file changed.
Run `bartleby theme inspect` again to confirm.
The original line now ends with `[shadowed by overrides/partials/header.html]`.

## Next Steps

- To change many files, run `bartleby theme eject` to copy the whole theme into your project and edit it there.
  The [CLI reference](../../reference/pages/cli.md#bartleby-theme) describes the command.
- To decide between `overrides/` and `templates/`, read [Customization seams](../../concepts/customization-seams.md).
- For the full search order, read [Templates and the lookup cascade](../../concepts/templates.md).
