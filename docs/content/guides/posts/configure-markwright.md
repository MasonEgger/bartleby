---
title: "Configure markwright and Click-to-Load Embeds"
description: "Set up the markwright section of bartleby.yml, and hold embeds back until a reader clicks them."
date: 2026-10-12
audience: existing-user
tags:
  - configuration
authors:
  - mason
---

markwright is the extension set behind code block labels, line numbers, command prompts, and the YouTube, CodePen, Twitter, and Instagram embeds.
You configure it in a `markwright:` section of `bartleby.yml`.
A new site has no such section, and that is a working setup: every extension loads, and every embed loads its provider when the page opens.
In this guide, you will switch one embed to click-to-load, turn another extension off, and check that the settings took effect.

<!-- more -->

## Prerequisites

You need a Bartleby site with at least one page that holds an embed.
The tour that `bartleby new site` writes at `content/tour/index.md` has one of each.

Before you begin, note the shape of the section, which matches a `markwright.toml`:

- `enable` or `disable` is a list of extension names, and you set one of the two.
- `warn` is on by default; with `fence.allowed_environments` set, a page that names an environment outside the list gets a build warning, and `warn: false` silences it.
- One table per extension holds that extension's options.

The extension names are `fence`, `highlight`, `youtube`, `codepen`, `twitter`, `instagram`, `slideshow`, and `image_compare`.
Bartleby passes the section to markwright unchanged and markwright owns the schema, so for the options of each extension, read markwright's own documentation or the [`markwright` section of the configuration reference](../../reference/pages/configuration.md#markwright).

## Step 1: Loading an Embed on Click

Add a table for the embed and set `load`:

```yaml
markwright:
  youtube:
    load: click
```

`load` has two values that matter here:

| Value | Behavior |
|-------|----------|
| `eager` | The embed loads with the page. This is the default. |
| `click` | The page shows a preview with a load button, and the embed loads when the reader clicks it. |

Some embeds accept further values.
markwright lists the allowed ones in its error message when you set a value the embed does not take.

The same key works under `codepen`, `twitter`, and `instagram`.
Until the reader clicks, the page contacts no provider for that embed.

## Step 2: Checking the Swap

Build the site and open a page that holds the embed:

```bash
bartleby build
```

You see a preview in place of the live embed.
Click the load button, and the preview gives way to the embed.

The bundled themes ship everything the swap needs.
The `base` theme provides `click_to_load.js` and `click_to_load.css`, and `scrivener` and `material` both inherit them.
A page links the two files only when it holds a click-to-load preview, so a site that never uses `load: click` pays nothing for them.
If you write your own theme that extends `base`, you inherit the swap too.

## Step 3: Turning an Extension Off

To stop one extension from running, list it under `disable`:

```yaml
markwright:
  disable: [twitter]
  youtube:
    load: click
```

To run only a few extensions, list them under `enable` instead.
Setting both `enable` and `disable` is a config error.

## Step 4: Keeping Settings in One Place

Only the `markwright:` section of `bartleby.yml` counts.
A `markwright.toml` next to `bartleby.yml`, or a `[tool.markwright]` table in `pyproject.toml`, is never read.
When Bartleby finds either one, the build prints a warning such as this one:

```
WARNING: ignored markwright.toml: only the `markwright:` section of bartleby.yml applies
```

Move the settings into `bartleby.yml` and delete the stray file to clear the warning.

## Fixing a Rejected Section

markwright validates the section, and a bad value fails the build with markwright's own message and the file and key it came from:

```
error [config_error] bartleby.yml: markwright: [youtube] 'load' must be one of eager, lazy, click; got 'later' (fix: fix the `markwright:` section; it takes the same keys as markwright.toml)
```

An unknown key, or `enable` together with `disable`, fails the same way.

## See Also

- [`markwright` in the configuration reference](../../reference/pages/configuration.md#markwright)
- [Markdown extensions](../../reference/pages/markdown-extensions.md)
- [Markdown Pipeline](../../concepts/markdown-pipeline.md): why markwright loads before the pymdownx extensions
