---
title: "Markdown Extensions"
description: "Every Markdown extension Bartleby loads by default."
tags:
  - configuration
---

Bartleby loads the extensions below on every build, in this order.
Override the config of any of them with `markdown_extensions` in `bartleby.yml`.
An override for an extension Bartleby configures itself merges over the bundled options, so a key you set wins and the rest stay.
See [Markdown pipeline](../../concepts/markdown-pipeline.md) for why the order matters and how overrides merge.

## `markwright`

The `markwright:` section of `bartleby.yml` selects and configures these extensions.
It takes the keys of a `markwright.toml`: `enable` or `disable`, `warn`, and one table per extension.
Without the section, every extension loads and every embed loads eagerly.
`warn` is on unless you set it to `false`: when `fence.allowed_environments` leaves out an environment a page names, the build logs a warning with the page and the name, because the directive stays in the code block as text.
Set `load: click` on an embed to hold it back until the reader clicks it.
See [Configure markwright and Click-to-Load Embeds](../../guides/posts/configure-markwright.md), and markwright's own documentation for each extension's options.

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

Bartleby sets options on three of these, and a `markdown_extensions` override merges over them.

`pymdownx.tabbed` runs with `alternate_style` on, which is the style the bundled themes expect.
Setting another `pymdownx.tabbed` key, such as `separator`, keeps the alternate style; set `alternate_style: false` if you need the other markup.

`pymdownx.arithmatex` runs with `generic` on.
Inline math renders as `<span class="arithmatex">\(...\)</span>` and a block as `<div class="arithmatex">\[...\]</div>`, which MathJax 3 and KaTeX's auto-render script read with their default delimiters.
Bartleby ships no math renderer; add the script of either one to your templates.

`pymdownx.emoji` runs on the `twemoji` index with the `to_alt` generator, so `:smile:` renders as the character and the page makes no request to an emoji CDN.
To render images instead, name a generator by its dotted path:

```yaml
markdown_extensions:
  - name: pymdownx.emoji
    config:
      emoji_generator: pymdownx.emoji.to_svg
```

`emoji_generator` and `emoji_index` take a dotted path to any callable pymdownx accepts, such as `pymdownx.emoji.to_png` or `pymdownx.emoji.emojione`; a path that names nothing is a config error.

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

## Accessibility Pass

After every extension has run, Bartleby's own pass (`bartleby.accessibility`) adds the cues that assistive technology and color-blind readers need, so every theme gets them.

- Each admonition title and `???` summary starts with an icon for the type (an Octicon from the `base` theme, overridable by a theme that ships `icons/octicons/<name>-16.svg`) and, when the title is custom, hidden text that reads the type word first, as in "Danger: Custom Title".
- Each `[environment NAME]` code block starts with hidden text that reads "Environment NAME." before the code; the two bundled themes also print the name as a tag in the block's corner.
- Each task-list checkbox is named after its item text, and each table is keyboard focusable so a wide one can scroll.
- The YouTube embed gets a title, the image-compare slider a label, and the slideshow keyboard focus.

The icon per type: `note` and `info` use `info`; `abstract` and `example` use `book`; `tip` uses `light-bulb`; `success` uses `check-circle`; `question` uses `question`; `warning` uses `alert`; `failure` uses `x-circle`; `danger` uses `stop`; `bug` uses `bug`; `quote` uses `quote`.
A type outside this list gets `info`.
