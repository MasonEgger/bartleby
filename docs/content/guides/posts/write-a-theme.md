---
title: "Write a Theme"
description: "Build a theme as a project directory or an installable package, on top of the base theme."
date: 2026-10-10
audience: theme-author
tags:
  - theme
  - templates
authors:
  - mason
---

A theme is a directory with a `theme.yml` manifest and some templates, static files, and icons.
This guide builds one on top of the `base` theme, first as a directory in your project and then as an installable package.

<!-- more -->

Start with [Choose and Customize a Theme](choose-and-customize-a-theme.md).
For every manifest key and flag, keep the [themes reference](../../reference/pages/themes.md) open beside this guide.

## Step 1: Create the Theme Directory

A theme directory has this shape.
Only `theme.yml` is required.

```
themes/inkwell/
├── theme.yml
├── templates/
├── static/
├── icons/
├── tailwind.css
├── tailwind.config.js
└── safelist.txt
```

`templates/`, `static/`, and `icons/` hold the files the build uses.
The last three files are the Tailwind sources, which Step 5 covers.
A theme that ships ready-made CSS can leave them out.

## Step 2: Write the Manifest

The manifest names the theme, says what it extends, and lists the features it implements:

```yaml
name: inkwell
description: A plain reading theme.
extends: base
features:
  - search
```

`name` is the only required key.
`version`, `description`, `extends`, and `features` are optional.
Each `features` entry must be one of the eight native feature names, or the theme fails to load with an error that lists the valid ones.

For a full example, here is the manifest of the bundled `scrivener` theme, unchanged:

```yaml
name: scrivener
description: Bartleby's own theme. A ruled-ledger reading layout with a margin rule, serif text, and a pale paper palette.
extends: base
features:
  - search
  - search.highlight
  - nav.tabs
  - nav.sidebar
  - nav.section-index
  - nav.back-to-top
  - content.code.copy
  - color-mode.toggle
```

It extends `base`, so it supplies only the files that differ.
Declaring a feature in the manifest is a promise that the templates honor `feature('<name>')`.
Bartleby does not check the promise.
It only warns when a site enables a feature that no manifest in the chain declares.

## Step 3: Extend Base and Fill Its Blocks

`extends: base` gives you working templates, the search script, Alpine, HTMX, lunr, and a set of icons.
Everything else is yours to replace.
Bartleby looks up an `extends` value as a bundled theme name first, then as a sibling directory of your theme, then as an installed package.

The base layout is `templates/base.html`.
Your page templates extend it and fill these blocks:

| Block | What goes there |
|-------|-----------------|
| `head_extra` | Extra tags for `<head>` |
| `header` | The site header. By default it includes `partials/header.html`, then the search modal. |
| `nav` | A top navigation region, empty by default |
| `sidebar` | A sidebar region, empty by default |
| `content` | The page body. By default it prints `page.content`. |
| `toc` | A table of contents region, empty by default |
| `footer` | The footer. By default it includes `partials/footer.html`. |
| `scripts` | Scripts at the end of `<body>`, including the `extra_js` files |

The build looks for these template names, each of which you can override: `page.html`, `defaults/post.html`, `defaults/list.html`, `404.html`, `taxonomy.html`, and `taxonomy_index.html`.
The [lookup cascade](../../concepts/templates.md) explains how a page picks one.

To show a post's tags as links, loop over `page.taxonomy_links.tags` and use each entry's `url`.
Do not build the URL from the tag text, because the slug format and the content type scope both change it.
The [template context reference](../../reference/pages/template-context.md) lists the fields.

A minimal `templates/page.html`:

```html
{% extends "base.html" %}
{% block content %}
<article data-search-highlight-root>
  <h1>{{ page.title }}</h1>
  {{ page.content | safe if page.content else "" }}
</article>
{% endblock %}
```

Every template receives the context that the [template context reference](../../reference/pages/template-context.md) lists.

## Step 4: Honor the Shared Contracts

Some behavior lives in `base`, so every theme that extends it must keep a few promises.
Break one and the matching feature fails quietly.

- **The reading column.** Mark the element that holds the page body with the `data-search-highlight-root` attribute.
  The search script highlights matches only inside it.
  Without the attribute it falls back to `main article`, then `main`.
  The bundled themes also give that element a layout class: `prose-column` in `scrivener`.
- **The search event.** The search component opens on a `bartleby:search-open` event on `window`.
  A trigger button dispatches it with `window.dispatchEvent(new CustomEvent('bartleby:search-open'))`.
  The component also opens on `/` and on Ctrl+K or Cmd+K, so search stays reachable if you drop the trigger.
- **The search modal.** `base.html` includes `partials/search.html` right after the header, inside the `header` block, when the `search` feature is on.
  If you override the whole `header` block, include `partials/search.html` yourself.
  Write the modal markup against the `bartlebySearch()` Alpine component that `static/js/search.js` registers.
- **The navigation and table of contents helpers.** `partials/nav_macros.html` provides the `holds` and `first_url` macros, and `partials/toc_macros.html` provides `entries` and `tracker`.
  Import them with `{% from "partials/nav_macros.html" import holds %}` instead of copying the logic.
  Because your theme extends `base`, the imports resolve with no extra work.
- **The color-mode script.** When the `color-mode.toggle` feature is on, `base.html` runs a small script in `<head>` before the page paints.
  It reads the `localStorage` key `bartleby-color-mode`, falls back to `color_mode.default`, then to the system setting, and sets `data-theme` on `<html>`.
  Gate your toggle button on `feature('color-mode.toggle')` too.
  The button must write the same key, `bartleby-color-mode`, with the value `light` or `dark`, and set `document.documentElement.dataset.theme`.
- **The stylesheet link.** `base.html` links `/css/main.css`.
  Your theme provides that file in `static/css/main.css`, or users produce it with `bartleby theme compile`.

## Step 5: Add Styles and Compile Them

The bundled `material` and `scrivener` themes style themselves with Tailwind CSS.
They ship three source files:

- `tailwind.css` holds the component styles.
  Colors and fonts read `--bb-*` variables with fallbacks, such as `var(--bb-color-primary, #2a4b7c)`, so an empty `theme.tokens` map still renders.
- `tailwind.config.js` holds the Tailwind configuration.
  It reads the safelist, as the next section describes.
- `safelist.txt` lists classes that Tailwind must emit even when no template names them.

### The Safelist

Tailwind drops component classes that no template uses.
Markdown extensions emit classes such as admonition and highlight markers that never appear in a template, so the theme names them in `safelist.txt`: one class per line, with `#` starting a comment.

`tailwind.config.js` owns the reading.
It builds the path from `__dirname`, so the file is found beside the config wherever the theme lives:

```js
const fs = require("fs");
const path = require("path");

const safelist = fs
  .readFileSync(path.join(__dirname, "safelist.txt"), "utf8")
  .split("\n")
  .map((line) => line.trim())
  .filter((line) => line !== "" && !line.startsWith("#"));
```

Then the config passes `safelist` to Tailwind.
If your `tailwind.config.js` reads a `safelist.txt`, ship the file with the theme.
`bartleby theme eject` copies it along with the other Tailwind sources.

### How Compile Works

`bartleby theme compile` runs the Tailwind standalone binary like this:

1. It writes `.bartleby/tokens.css` from `theme.tokens`, even when the map is empty.
2. It writes `.bartleby/input.css`, which imports `tokens.css` first and then the nearest `tailwind.css` in the chain.
   If no layer has one, it uses the three `@tailwind` directives instead.
3. It takes `--config` from the nearest layer that has a `tailwind.config.js`.
4. It scans every layer's `templates/` plus your project's `overrides/`, `partials/`, `shortcodes/`, and `templates/` directories for classes.
5. It writes `.bartleby/theme.css`.

Because the wrapper imports the tokens, your theme does not import them.
It only has to read the `--bb-*` variables.

## Step 6: Use the Theme from Your Project

For a path theme, point `bartleby.yml` at the directory:

```yaml
theme:
  path: themes/inkwell
```

Relative paths resolve against the project directory.
Absolute paths work too.
Run `bartleby theme inspect` to confirm the chain.

## Step 7: Ship the Theme as a Package

A package theme is a Python package that exposes its theme directory through an entry point in the `bartleby.themes` group.
Lay the package out with the theme inside it:

```
bartleby-theme-inkwell/
├── pyproject.toml
└── bartleby_inkwell/
    ├── __init__.py
    └── theme/
        ├── theme.yml
        └── templates/
```

The package's `__init__.py` defines the directory:

```python
from pathlib import Path

THEME_DIR = Path(__file__).parent / "theme"
```

The entry point loads to that value.
It must be a `Path` or a `str` that names an existing directory:

```toml
[project.entry-points."bartleby.themes"]
inkwell = "bartleby_inkwell:THEME_DIR"
```

The name on the left, `inkwell`, is what sites put in `theme.package`.
Install the package into the environment that runs Bartleby, then select it:

```yaml
theme:
  package: inkwell
```

A package theme can extend another installed package theme by name, because an `extends` value falls back to the entry points.

## Next Steps

- To read a finished theme, run `bartleby theme eject` and open the directory.
- To look up a manifest key, a feature, or a flag, read the [themes reference](../../reference/pages/themes.md).
- To change one file on a single site, use [an override](override-theme-template.md) instead of a theme.
