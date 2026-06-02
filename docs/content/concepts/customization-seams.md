---
title: "Customization seams"
description: "The seven directories that customize a Bartleby site without forking the core."
---

Bartleby exposes seven customization seams that let you change behaviour without modifying the Bartleby package itself. Drop a file into the right directory and the build picks it up automatically.

## 1. `overrides/`

Files here replace bundled theme templates of the same name. Use this when you want to change the chrome (header, footer, base layout) without writing a content-type template.

```
overrides/
└── partials/
    └── header.html        # Replaces the bundled header
```

## 2. `templates/`

Project-level templates for content types and defaults. See [Templates and the lookup cascade](templates.md).

```
templates/
├── blog/
│   └── post.html
└── defaults/
    └── page.html
```

## 3. `partials/`

Reusable Jinja2 fragments. Resolvable from any template via `{% include "partials/<name>.html" %}` because the project root is on the Jinja2 search path.

```
partials/
├── banner.html
└── sponsor.html
```

## 4. `data/`

YAML and TOML files auto-loaded into the template context under `data`. The file stem becomes the key:

```
data/
├── schedule.yaml          # → data.schedule
└── contacts.toml          # → data.contacts
```

In a template: `{{ data.schedule.days }}` or `{{ data.contacts.primary.name }}`.

## 5. `shortcodes/`

Jinja2 fragments invoked from Markdown with `[% name args="..." %]content[% /name %]` syntax. Resolved from `shortcodes/<name>.html`.

```
shortcodes/
├── note.html
├── version.html
└── callout.html
```

In Markdown: `[% note %]Important![% /note %]` renders through `shortcodes/note.html`.

## 6. `hooks/`

Python modules with module-level `on_<event>` functions auto-registered as plugin hooks. See [Plugins and hooks](plugins-and-hooks.md).

```python
# hooks/inject_banner.py
def on_page_markdown(markdown, page, config):
    if page.output_url == "/":
        return f"# Banner!\n\n{markdown}"
    return markdown
```

## 7. `extra_css` / `extra_js` in `bartleby.yml`

Asset paths injected into every page's `<head>` and end-of-body:

```yaml
extra_css:
  - css/site.css
  - css/print.css
extra_js:
  - js/analytics.js
```

Paths are relative to the site root and are typically dropped into `static/` so they end up on disk at those locations.
