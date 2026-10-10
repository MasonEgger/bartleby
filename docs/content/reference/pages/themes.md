---
title: "Themes"
description: "The theme manifest, resolution rules, native features, tokens, and the theme CLI commands."
tags:
  - themes
  - cli
---

A theme is a directory that holds a `theme.yml` manifest and optional `templates/`, `static/`, and `icons/` directories.
This page lists the manifest keys, how Bartleby resolves a theme, the native features, the token mechanics, and the `bartleby theme` commands.
The `theme:` block in `bartleby.yml` is in the [configuration reference](configuration.md#theme).
For task walkthroughs, read [Choose and Customize a Theme](../../guides/posts/choose-and-customize-a-theme.md) and [Write a Theme](../../guides/posts/write-a-theme.md).

## Bundled Themes

| Name | Extends | Features | Tailwind sources |
|------|---------|----------|------------------|
| `base` | none | none | none |
| `material` | `base` | all eight | `tailwind.css`, `tailwind.config.js`, `safelist.txt` |
| `scrivener` | `base` | all eight | `tailwind.css`, `tailwind.config.js`, `safelist.txt` |

`scrivener` is the default theme.

## Theme Sources

`theme:` in `bartleby.yml` selects a theme with one of three keys.
Setting more than one is an error.

| Key | Value | Resolves to |
|-----|-------|-------------|
| `name` | A bundled theme name | The theme under `bartleby/themes/` |
| `path` | A directory, absolute or relative to the project | That directory |
| `package` | An entry point name | The directory that the entry point loads to |

A package entry point belongs to the `bartleby.themes` group.
Its loaded value must be a `Path` or a `str` that names an existing directory.
In `pyproject.toml`:

```toml
[project.entry-points."bartleby.themes"]
inkwell = "bartleby_inkwell:THEME_DIR"
```

## Manifest Keys

`theme.yml` must be a YAML mapping.

| Key | Type | Required | Meaning |
|-----|------|----------|---------|
| `name` | string | yes | The theme's identifier |
| `version` | string | no | The theme's version |
| `description` | string | no | A one-line summary |
| `extends` | string | no | The name of the parent theme |
| `features` | list of strings | no | Native feature names the theme implements. Defaults to an empty list. |

A missing manifest, a missing `name`, a key of the wrong type, or an unknown feature name raises a theme error.

## Extends Resolution

Bartleby resolves `extends` in this order and takes the first match:

1. A bundled theme with that name.
2. A sibling directory of the extending theme with that name.
3. An entry point with that name in the `bartleby.themes` group.

The resolved chain is leaf-first: the requested theme, then each parent.
A cyclic chain is an error that prints the cycle.
For any file, the nearest layer that has it wins.

## Theme Directory Layout

| Path | Contents |
|------|----------|
| `theme.yml` | The manifest |
| `templates/` | Jinja2 templates, searched leaf-first |
| `static/` | Files copied to the output, such as `static/css/main.css` and `static/js/` |
| `icons/` | SVG icons, in one subdirectory per pack |
| `tailwind.css` | The Tailwind input for the theme's styles |
| `tailwind.config.js` | The Tailwind configuration. `--config` takes the nearest copy in the chain. |
| `safelist.txt` | Classes to always emit, read by the theme's `tailwind.config.js` |

`bartleby theme inspect` and `theme eject` cover `templates/`, `static/`, `icons/`, `tailwind.css`, `tailwind.config.js`, and `safelist.txt`.

## Template Search Order

The Jinja2 loader searches these directories in order:

1. `overrides/` in the project
2. `templates/` in the project
3. The project root
4. Each theme layer's `templates/`, leaf-first

## Base Blocks

`base.html` in the `base` theme defines these blocks:

| Block | Default content |
|-------|-----------------|
| `head_extra` | Empty |
| `header` | `partials/header.html`, then `partials/search.html` when `search` is on |
| `nav` | Empty |
| `sidebar` | Empty |
| `content` | `page.content` |
| `toc` | Empty |
| `footer` | `partials/footer.html` |
| `scripts` | The `extra_js` script tags |

## Features

Both `theme.features` in `bartleby.yml` and `features` in a manifest accept only these names.

| Feature | Effect |
|---------|--------|
| `search` | The search box and the client-side search index |
| `search.highlight` | Highlight the search terms on the page a result opens |
| `nav.tabs` | Top-level sections render as tabs in the header |
| `nav.sidebar` | The section tree renders as a sidebar |
| `nav.section-index` | A section's index page is the section's own nav entry |
| `nav.back-to-top` | A back-to-top button appears after scrolling |
| `content.code.copy` | Code blocks get a copy button |
| `color-mode.toggle` | The header shows a light and dark toggle |

Templates test a feature with `feature('<name>')`.
A feature that is enabled in `bartleby.yml` but declared by no manifest in the chain produces a build warning, not an error.
The toggle also needs `theme.color_mode.toggle: true`.

## Tokens

`theme.tokens` is a flat map of dotted names to string values.
A dotted name becomes a CSS custom property with the `--bb-` prefix and dashes: `color.primary` becomes `--bb-color-primary`.

```css
:root {
  --bb-color-primary: #0b6e4f;
}
```

`bartleby theme compile` writes this block to `.bartleby/tokens.css`, and writes an empty file when `tokens` is empty.
Tokens do not reach the page until you run the command.
Bartleby does not validate token names, so a name that no theme reads has no effect.

| Token | `base` | `material` | `scrivener` |
|-------|--------|------------|-------------|
| `color.primary` | no | yes | yes |
| `color.accent` | no | yes | yes |
| `color.bg` | no | yes | yes |
| `color.text` | no | yes | yes |
| `color.bg-dark` | no | yes | yes |
| `color.text-dark` | no | yes | yes |
| `font.text` | no | yes | yes |
| `font.ui` | no | no | yes |
| `font.code` | no | yes | yes |
| `radius` | no | yes | yes |

## Compiling Theme CSS

`bartleby theme compile` produces `.bartleby/theme.css`.

**Binary.** The command uses the first Tailwind standalone binary that it finds, in this order: `tailwindcss` on `PATH`, the cached binary at `<cache>/bartleby/tailwindcss-<version>`, then a download checked against a recorded SHA-256 digest.
The pinned version is 3.4.17.
The cache directory is `$XDG_CACHE_HOME/bartleby`, or `~/.cache/bartleby`.

**Input.** The command writes `.bartleby/input.css`, which imports `tokens.css` and then the absolute path of the nearest `tailwind.css` in the chain.
With no `tailwind.css` in the chain, it writes the three `@tailwind` directives instead.

**Content globs.** Tailwind scans `templates/**/*.html` in every theme layer.
It also scans `overrides/`, `partials/`, `shortcodes/`, and `templates/` in the project when they exist.

**Build use.** The build copies `.bartleby/theme.css` to `css/main.css` in the output when the file exists and is at least as new as every file in the project's `templates/` and in the `templates/` of any theme layer inside the project.
Otherwise it uses the theme's shipped `static/css/main.css`.

## Base Contracts

A theme that extends `base` keeps these promises:

| Contract | Detail |
|----------|--------|
| Highlight root | The element that holds the page body carries `data-search-highlight-root`. The search script falls back to `main article`, then `main`. |
| Search event | The search component opens on the `bartleby:search-open` window event, on `/`, and on Ctrl+K or Cmd+K. |
| Search modal | `base.html` includes `partials/search.html` inside the `header` block when `search` is on. |
| Helper macros | `partials/nav_macros.html` provides `holds` and `first_url`. `partials/toc_macros.html` provides `entries` and `tracker`. |
| Color mode | The pre-paint script in `base.html` reads the `localStorage` key `bartleby-color-mode`, then `theme.color_mode.default`, then the system setting. It sets `data-theme` on `<html>`. |
| Stylesheet | `base.html` links `/css/main.css`. |
| Safelist | A `tailwind.config.js` that reads `safelist.txt` builds the path from `__dirname`. |

## `bartleby theme`

All three subcommands accept the global flags `--output {text,json}`, `--config CONFIG`, `--quiet`, and `--verbose`.
The [CLI reference](cli.md#global-flags) describes them.
Each command reads the theme from `theme:` in the config file.

### `bartleby theme inspect`

```
bartleby theme inspect
```

Lists every theme file and the layer that provides it, sorted by path.

```
Theme ledger (chain: ledger -> scrivener -> base)
icons/fontawesome-brands/github.svg  (base)
...
templates/partials/footer.html  (ledger)  [shadowed by overrides/partials/footer.html]
```

The first line shows the theme and its chain.
A template that a file in `overrides/`, `templates/`, or the project root replaces ends with `[shadowed by <path>]`.
With `--output json`, the result has `status`, `theme`, `chain`, and `files`.
Each file has `path`, `kind`, `layer`, and `shadowed_by`.
`kind` is `template`, `static`, `icon`, or `tailwind`.

### `bartleby theme eject`

```
bartleby theme eject [--to DIR] [--force]
```

| Flag | Default | Purpose |
|------|---------|---------|
| `--to DIR` | `themes/<theme-name>` | The destination directory, relative to the project or absolute |
| `--force` | off | Overwrite files in an existing destination |

Eject copies each file from the layer that wins it into one directory.
It writes a `theme.yml` with the leaf theme's `name`, `version`, and `description`, the union of features from the whole chain, and no `extends`.

```
Ejected theme 'scrivener' (53 files) to themes/scrivener
Add this to bartleby.yml:
theme:
  path: themes/scrivener
```

An existing destination without `--force` is a theme error:

```
error [theme_error] /path/to/site/themes/scrivener already exists (use --force to overwrite)
```

The destination cannot be, contain, or sit inside a theme directory of the chain.
With `--output json`, the result has `status`, `theme`, `target`, `files`, and `config`.

### `bartleby theme compile`

```
bartleby theme compile [--refresh]
```

| Flag | Default | Purpose |
|------|---------|---------|
| `--refresh` | off | Skip `PATH` and the cache, and download the Tailwind binary again |

The command writes `.bartleby/tokens.css`, `.bartleby/input.css`, and `.bartleby/theme.css`.

```
Compiled theme CSS to .bartleby/theme.css (340 classes, cached binary, 2286 ms)
```

The binary is `path`, `cached`, or `downloaded`.
The class count is the number of rules in the output.
With `--output json`, the result has `status`, `css_path`, `binary`, `duration_ms`, and `classes_scanned`.
A Tailwind failure is a `theme_compile_error` that includes Tailwind's own message.

## Theme Errors

Theme problems exit with code 1 and the error code `theme_error`.

| Cause | Message contains |
|-------|---------------------|
| More than one of `name`, `path`, `package` | `specify exactly one of name, path, or package` |
| Unknown bundled theme | `unknown bundled theme` |
| `path` does not exist | `theme path does not exist` |
| Entry point missing | `theme package ... not found in entry-point group` |
| Missing manifest | `missing theme.yml` |
| Unknown feature | `unknown feature ... in 'features'` |
| Cyclic `extends` | `cyclic theme extends` |
