---
title: "Choose and Customize a Theme"
description: "Pick a bundled theme, recolor it with tokens, extend it, override one template, and inspect the result."
date: 2026-10-10
audience: new-user
tags:
  - theme
  - customization
authors:
  - mason
---

Bartleby ships three themes, and you can change any of them without forking Bartleby.
This guide walks through five tasks: pick a theme, recolor it, extend it, override one template, and inspect what you built.
A last section covers ejecting a theme when you want to own every file.

<!-- more -->

You need a Bartleby site with a `bartleby.yml`, such as the one that `bartleby new site` scaffolds.
Run every command from the directory that holds `bartleby.yml`.

## Step 1: Pick a Bundled Theme

Bartleby bundles three themes:

| Theme | What it is |
|-------|------------|
| `base` | Unstyled templates, the search script, and the icons that every other theme builds on |
| `material` | A header bar, navigation tabs, a section sidebar, and a table of contents in an indigo palette |
| `scrivener` | Bartleby's own theme: a ruled-ledger reading layout with serif text on pale paper |

Set `theme.name` in `bartleby.yml`.
When you set nothing, Bartleby uses `scrivener`.

```yaml
theme:
  name: material
  features:
    - search
    - nav.tabs
    - nav.sidebar
```

`features` switches on optional behavior.
Both `material` and `scrivener` implement all eight features.
The [themes reference](../../reference/pages/themes.md#features) lists them.
Build the site to see the result:

```bash
bartleby build
```

If you enable a feature that no theme in the chain implements, the build prints a warning that names the theme and the feature.

## Step 2: Recolor the Theme with Tokens

Tokens change a theme's colors, fonts, and corner radius without touching a template.
You set them under `theme.tokens`, as a flat map of dotted names to CSS values.

Each bundled theme reads its own set of tokens, taken from its `tailwind.css`:

| Theme | Tokens it reads |
|-------|-----------------|
| `scrivener` | `color.primary`, `color.accent`, `color.bg`, `color.text`, `color.bg-dark`, `color.text-dark`, `font.text`, `font.ui`, `font.code`, `radius` |
| `material` | `color.primary`, `color.accent`, `color.bg`, `color.text`, `color.bg-dark`, `color.text-dark`, `font.text`, `font.code`, `radius` |
| `base` | None. It ships no stylesheet. |

The only difference between the first two rows is `font.ui`, which `scrivener` uses for navigation and metadata.
Add the tokens you want to change:

```yaml
theme:
  name: scrivener
  tokens:
    color.primary: "#0b6e4f"
    color.accent: "#c2410c"
```

Tokens reach the page only after you compile the theme CSS:

```bash
bartleby theme compile
```

The command prints a one-line summary:

```
Compiled theme CSS to .bartleby/theme.css (340 classes, cached binary, 2286 ms)
```

The first run needs the Tailwind standalone binary.
Bartleby uses a `tailwindcss` on your `PATH`, then a cached copy, and downloads a checksum-verified copy when it finds neither.
The `binary` part of the summary tells you which one it used: `path`, `cached`, or `downloaded`.

Compiling writes `.bartleby/tokens.css`:

```css
:root {
  --bb-color-primary: #0b6e4f;
  --bb-color-accent: #c2410c;
}
```

It then compiles the theme's styles on top of that file.
The next `bartleby build` copies `.bartleby/theme.css` to `css/main.css` in the output.
Run `bartleby theme compile` again each time you change a token.

## Step 3: Extend a Bundled Theme

Tokens cannot change markup.
To change markup for the whole site, write a small theme that extends a bundled one and holds only the files you want to replace.

Create a theme directory in your project with a `theme.yml` manifest:

```
mysite/
├── bartleby.yml
└── themes/
    └── ledger/
        ├── theme.yml
        └── templates/
            └── partials/
                └── footer.html
```

The manifest names the theme and its parent:

```yaml
name: ledger
description: Scrivener with a shorter footer.
extends: scrivener
```

Put the replacement file at the same path that the parent uses, under `templates/`:

```html
<footer class="site-footer">
  <p class="site-meta">Built with Bartleby {{ build.bartleby_version }}.</p>
</footer>
```

Point `bartleby.yml` at the directory with `theme.path`:

```yaml
theme:
  path: themes/ledger
  features:
    - search
    - nav.sidebar
```

Bartleby resolves the chain leaf-first.
It finds `partials/footer.html` in `ledger` and every other template in `scrivener`, then in `base`.
The child theme also inherits the parent's features, `tailwind.css`, and `tailwind.config.js`, so tokens and `bartleby theme compile` keep working.

## Step 4: Override a Single Template

For a one-file change you do not need a theme at all.
Create the file under `overrides/` in your project root, at the same path the theme uses without the leading `templates/`:

```
mysite/
└── overrides/
    └── partials/
        └── footer.html
```

Bartleby searches `overrides/` before every theme layer, so your file wins.
The guide [Override a Single Theme Template](override-theme-template.md) walks through this in full.

## Step 5: Inspect the Chain

Run `bartleby theme inspect` to see what the build uses and where each file comes from.
The first line names the theme and its chain.
Each following line is a file and the layer that provides it.

```
Theme ledger (chain: ledger -> scrivener -> base)
icons/fontawesome-brands/github.svg  (base)
...
templates/partials/footer.html  (ledger)
templates/partials/header.html  (scrivener)
```

A theme template that one of your project files replaces gets a note at the end of its line:

```
templates/partials/footer.html  (ledger)  [shadowed by overrides/partials/footer.html]
```

Add `--output json` for the same data as JSON, with `chain` and a `files` list whose entries have `path`, `kind`, `layer`, and `shadowed_by`.

## Step 6: Eject When You Want the Whole Theme

If you want to edit many files, copy the theme into your project:

```bash
bartleby theme eject
```

```
Ejected theme 'scrivener' (56 files) to themes/scrivener
Add this to bartleby.yml:
theme:
  path: themes/scrivener
```

Eject flattens the chain.
The directory holds every template, static file, icon, and Tailwind source that the build uses, with the child's version winning any shared path.
Its `theme.yml` has no `extends`, so the theme stands alone.

An ejected theme is a complete, readable system.
A coding agent can open the directory, read the manifest, and edit templates and styles with no other context.
That is the reason Bartleby treats the theme as plain files and not as a package you cannot see into.

Use `--to` to pick another directory, and `--force` to overwrite one that exists:

```bash
bartleby theme eject --to themes/ledger --force
```

Eject also copies `tailwind.css`, `tailwind.config.js`, and `safelist.txt`, so `bartleby theme compile` works on the ejected theme with no extra steps.
The [write a theme](write-a-theme.md#the-safelist) guide explains what the safelist is for.

## Next Steps

- To build a theme from scratch or ship one as a package, read [Write a Theme](write-a-theme.md).
- For every manifest key, feature, token, and `theme` flag, read the [themes reference](../../reference/pages/themes.md).
- To see how the theme chain fits the rest of the lookup, read [Templates and the lookup cascade](../../concepts/templates.md).
