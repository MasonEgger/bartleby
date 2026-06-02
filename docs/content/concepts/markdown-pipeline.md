---
title: "Markdown pipeline"
description: "The extensions Bartleby loads and the ordering that makes do-markdown and pymdownx coexist."
---

Bartleby uses [Python-Markdown](https://python-markdown.github.io/) with every extension you'd normally need to enable yourself loaded by default. The user-facing surface area is just `markdown_extensions` in `bartleby.yml`, which lets you override individual extension configs.

## Extension load order

Order matters when multiple extensions touch the same content. The key invariant Bartleby maintains:

1. `do_markdown.fence` preprocessor (priority 40) extracts `[label script.py]`, `[secondary_label]`, and `[environment]` directives from code blocks
2. `pymdownx.superfences` preprocessor (priority 25) converts fenced blocks to HTML
3. `do_markdown.fence` postprocessor (priority 25) injects the extracted labels and environment classes back into the HTML

This is why directives like `[label]` survive the fence processing: do-markdown gets the first and last word.

## Bundled extensions

**do-markdown** (first-class):

- `do_markdown.fence` — code block labels, secondary labels, environment tags, line numbers, command prefixes
- `do_markdown.highlight` — inline `<^>text<^>` highlights
- `do_markdown.youtube`, `do_markdown.codepen`, `do_markdown.twitter`, `do_markdown.instagram` — embed blocks
- `do_markdown.slideshow` — image slideshows
- `do_markdown.image_compare` — before/after image sliders

**pymdownx**:

- `pymdownx.superfences` — fenced code blocks
- `pymdownx.highlight` + `pymdownx.inlinehilite` — syntax highlighting via Pygments
- `pymdownx.tabbed` — content tabs
- `pymdownx.details` — collapsible sections
- `pymdownx.tasklist` — `- [x]` checkboxes
- `pymdownx.arithmatex` — math
- `pymdownx.keys` — keyboard key markup
- `pymdownx.mark`, `pymdownx.caret`, `pymdownx.tilde` — inline annotations
- `pymdownx.critic` — Critic Markup
- `pymdownx.smartsymbols`, `pymdownx.emoji` — symbol expansion
- `pymdownx.snippets` — `--8<--` file inclusion
- `pymdownx.blocks.caption` — figure captions

**Standard Python-Markdown**:

- `tables`, `toc`, `attr_list`, `def_list`, `footnotes`, `admonition`, `abbr`, `md_in_html`

## Overriding extension config

Use `markdown_extensions` in `bartleby.yml` to add configuration:

```yaml
markdown_extensions:
  - name: pymdownx.snippets
    config:
      base_path:
        - includes
  - name: pymdownx.highlight
    config:
      use_pygments: true
      pygments_style: monokai
```

A string entry replaces an existing default with the same name (or adds a new one if not present). A `{name, config}` mapping passes the `config` dict through as `extension_configs` to Python-Markdown.
