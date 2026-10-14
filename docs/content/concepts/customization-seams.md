---
title: "Customization Seams"
description: "The places where a Bartleby site changes behavior without forking the core."
---

Bartleby exposes a set of customization seams.
Each one lets you change behavior without modifying the Bartleby package.
Most seams are directories: drop a file into the right one and the build picks it up.
Two seams live in `bartleby.yml` instead: the theme, and `extra_css` with `extra_js`.

## The Theme

The theme sets the look of the whole site.
You choose one with `theme.name` for a bundled theme, `theme.path` for a directory in your project, or `theme.package` for an installed package.
A theme can `extends` another theme and replace only the files it needs, so a chain such as `scrivener` on top of `base` resolves leaf-first.

Choose this seam when you want a different design for the whole site.
`bartleby theme inspect` lists every theme file and the layer that provides it.
`bartleby theme eject` copies the whole chain into one directory you can edit.
Because a theme is plain files, a coding agent can read an ejected theme from top to bottom and change it with no other context.
To start, read [Choose and Customize a Theme](../guides/posts/choose-and-customize-a-theme.md).
To build your own, read [Write a Theme](../guides/posts/write-a-theme.md).

## `overrides/`

Files here replace theme templates of the same name.
Choose this seam to change one piece of the chrome, such as the header, the footer, or the base layout, while keeping the rest of the theme.
Bartleby searches `overrides/` before every theme layer, so a file here beats a theme file of the same name.

```
overrides/
└── partials/
    └── header.html        # Replaces the theme's header
```

## `templates/`

Project-level templates for content types and defaults.
Choose this seam when a content type needs its own layout.
See [Templates and the lookup cascade](templates.md).

```
templates/
├── blog/
│   └── post.html
└── defaults/
    └── page.html
```

## `partials/`

Reusable Jinja2 fragments.
Any template can include one with `{% include "partials/<name>.html" %}`, because the project root is on the Jinja2 search path.
Choose this seam for markup that several templates share.

```
partials/
├── banner.html
└── sponsor.html
```

## `data/`

YAML and TOML files that load into the template context under `data`.
The file stem becomes the key.
Choose this seam for structured content that is not a page, like a schedule.

```
data/
├── schedule.yaml          # → data.schedule
└── contacts.toml          # → data.contacts
```

In a template, write `{{ data.schedule.days }}` or `{{ data.contacts.primary.name }}`.

## `shortcodes/`

Jinja2 fragments that authors call from Markdown with `[% name args="..." %]content[% /name %]` syntax.
Bartleby resolves each one from `shortcodes/<name>.html`.
Choose this seam when authors need reusable markup inside prose.

```
shortcodes/
├── note.html
├── version.html
└── callout.html
```

In Markdown, `[% note %]Important![% /note %]` renders through `shortcodes/note.html`.

## `hooks/`

Python modules whose module-level `on_<event>` functions register as plugin hooks.
Choose this seam to change how the build behaves, not how a page looks.
See [Plugins and hooks](plugins-and-hooks.md).

```python
# hooks/inject_banner.py
def on_page_markdown(markdown, page, config):
    if page.output_url == "/":
        return f"# Banner!\n\n{markdown}"
    return markdown
```

## `extra_css` and `extra_js`

Two lists in `bartleby.yml` that add asset paths to every page.
Bartleby injects the CSS into the `<head>` and the JavaScript at the end of the body.
Choose this seam for small style or script additions.

```yaml
extra_css:
  - css/site.css
  - css/print.css
extra_js:
  - js/analytics.js
```

Paths are relative to the site root.
Put the files in `static/` so they end up on disk at those locations.
