---
title: "Markdown Extensions"
description: "Every Markdown extension Bartleby loads by default."
tags:
  - configuration
---

Bartleby loads the extensions below on every build, in this order.
Override the config of any of them with `markdown_extensions` in `bartleby.yml`.
See [Markdown pipeline](../../concepts/markdown-pipeline.md) for why the order matters and how overrides merge.

## `markwright`

| Extension | Purpose |
|-----------|---------|
| `markwright.fence` | Code block labels, secondary labels, environment tags, line numbers, and command prefixes |
| `markwright.highlight` | Inline emphasis with `<^>text<^>` |
| `markwright.youtube` | YouTube embed blocks |
| `markwright.codepen` | CodePen embed blocks |
| `markwright.twitter` | Twitter embed blocks |
| `markwright.instagram` | Instagram embed blocks |
| `markwright.slideshow` | Image slideshows |
| `markwright.image_compare` | Before and after image sliders |

## `pymdownx`

| Extension | Purpose |
|-----------|---------|
| `pymdownx.superfences` | Fenced code blocks |
| `pymdownx.highlight` | Code block coloring through Pygments |
| `pymdownx.inlinehilite` | Inline code coloring |
| `pymdownx.tabbed` | Content tabs |
| `pymdownx.details` | Collapsible sections |
| `pymdownx.tasklist` | `- [x]` checkboxes |
| `pymdownx.arithmatex` | Math |
| `pymdownx.keys` | Keyboard key markup |
| `pymdownx.mark` | Marked text |
| `pymdownx.caret` | Inserted text and superscript |
| `pymdownx.tilde` | Deleted text and subscript |
| `pymdownx.critic` | Critic Markup |
| `pymdownx.smartsymbols` | Symbol expansion |
| `pymdownx.emoji` | Emoji shortcodes |
| `pymdownx.snippets` | `--8<--` file inclusion |
| `pymdownx.blocks.caption` | Figure captions |

## Python-Markdown

| Extension | Purpose |
|-----------|---------|
| `tables` | Tables |
| `toc` | Table of contents entries for each page |
| `attr_list` | HTML attributes on Markdown elements |
| `def_list` | Definition lists |
| `footnotes` | Footnotes |
| `admonition` | Admonition blocks |
| `abbr` | Abbreviations |
| `md_in_html` | Markdown inside HTML blocks |
