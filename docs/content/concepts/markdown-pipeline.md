---
title: "Markdown Pipeline"
description: "The ordering that lets markwright and pymdownx coexist, and how you override extension config."
---

Bartleby uses [Python-Markdown](https://python-markdown.github.io/) and loads the extensions you would otherwise enable yourself.
The setting you change is `markdown_extensions` in `bartleby.yml`, which overrides the config of individual extensions.

## Extension Load Order

Order matters when several extensions work on the same content.
Bartleby keeps one invariant:

1. The `markwright.fence` preprocessor (priority 40) extracts `[label script.py]`, `[secondary_label]`, and `[environment]` directives from code blocks.
2. The `pymdownx.superfences` preprocessor (priority 25) converts fenced blocks to HTML.
3. The `markwright.fence` postprocessor (priority 25) injects the extracted labels and environment classes back into the HTML.

The directives survive because markwright runs before superfences on the way in and after it on the way out.

## Bundled Extensions

Bartleby loads extensions from three groups: markwright, pymdownx, and standard Python-Markdown.
The [Markdown extensions reference](../reference/pages/markdown-extensions.md) lists every one.

## Overriding Extension Config

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

A string entry replaces the default extension with the same name, or adds a new extension if none matches.
A `{name, config}` mapping passes the `config` dict to Python-Markdown as `extension_configs`.
