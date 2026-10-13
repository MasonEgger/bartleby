---
title: "Configure Bartleby from the Command Line"
description: "Override, read, and write bartleby.yml values with --set, --base-url, and the config commands."
date: 2026-10-12
audience: new-user
tags:
  - configuration
authors:
  - mason
---

You can change Bartleby's configuration without opening `bartleby.yml`.
Overrides apply for one run, and the `config` commands read and write the file.
In this guide, you will override values for a build, find out where each value comes from, and write a change back to the file.

<!-- more -->

## Prerequisites

You need a Bartleby site with a `bartleby.yml`.
Run `bartleby new site mysite` and move into the directory if you want a scratch site to try each command on.

## Step 1: Overriding a Value for One Run

Add `--set KEY.PATH=VALUE` to `build`, `serve`, or `validate`:

```bash
bartleby build --set site.title="Staging Site" --set site.feed.limit=10
```

The key path is the dotted path of the key in `bartleby.yml`, and it must be one that `bartleby config schema` lists.
A misspelled key such as `site.titel` is an error that names the closest known key.
The flag repeats, and `bartleby.yml` stays as it was.
A string key takes the text as typed, so `site.title=Yes` sets the title to the word `Yes`.
Every other key parses the value as YAML, so `10` is an integer, `true` is a boolean, and a flow list such as `'theme.features=[search, nav.sidebar]'` is a list; a value of the wrong type, such as `dev_server.port=notaport`, is an error that names the expected type.
Keys under `markwright` and `theme.tokens` are open, so any name works there, and a token name keeps its dots: `--set theme.tokens.color.primary=red` sets the one token `color.primary`.
Quote a value that your shell would otherwise split or expand.

To preview the Material theme without editing the file:

```bash
bartleby serve --set theme.name=material
```

On `serve`, the override holds for the whole session, including every rebuild.

## Step 2: Setting the Base URL

Feeds, the sitemap, canonical links, and the agent files are built from `site.url`.
To build for another address, use `--base-url`:

```bash
bartleby build --base-url https://staging.example.com
```

The flag is a shortcut for `--set site.url=...`, and it wins when you pass both.
All three commands accept it.
The value must be an absolute `http` or `https` URL with a host; an empty value or `staging.example.com` without a scheme is an error, so the sitemap never carries a relative `<loc>`.

## Step 3: Reading Errors from an Override

When an override breaks the config, the error names `--set` as its source, in place of `bartleby.yml`:

```
error [config_error] --set: theme.features: unknown feature 'bogus': not a Bartleby feature (fix: use one of the native features: ...)
```

A flag without an equals sign gets the same label and a fix that shows the right shape:

```
error [config_error] --set: override 'site.feed.enabled' has no '=' (fix: write --set key.path=value, such as --set site.title=Hello)
```

## Step 4: Showing Every Resolved Value

Print the whole config as the build sees it:

```bash
bartleby config show
```

Each line holds a key path, its value, and where the value came from:

```
ai.llms_txt                               = true  (default)
site.feed.limit                           = 25  (file)
site.title                                = "Zed"  (--set)
```

The three labels are `default` for a value you never set, `file` for a value written in `bartleby.yml`, and `--set` for an override.
`--base-url` reads as `--set`, because it is an override of `site.url`.
`config show` accepts `--set` and `--base-url`, so you can check what an override does before you build with it.

With `--output json`, the command returns a `values` list of objects with `path`, `value`, and `source`.

## Step 5: Reading One Value

Print one value with `config get`:

```bash
bartleby config get site.title
```

A string prints bare, and any other value prints as JSON.
A key that does not exist exits with code `2` and points you at `config show` and `config schema`.

## Step 6: Writing a Value to the File

To change `bartleby.yml` itself, use `config set`:

```bash
bartleby config set site.title "My Site"
bartleby config set dev_server.port 9000
```

The command types the value by the key, as `--set` does: text for a string key, YAML for the rest, so `"My Site"` and `Hello: World` stay text and `9000` is an integer.
It then checks the edited config, the `markwright` section included, and only then writes the file in one step.
It keeps your comments, the order of your keys, and the file's byte order mark and line endings.
A value the config rejects leaves the file untouched, as does a file that cannot be written.

## Step 7: Listing Every Accepted Key

To see which keys exist, ask the schema:

```bash
bartleby config schema --output json
```

The result has a `fields` list.
Each entry holds a key `path`, its `type`, `default`, `choices`, a `description`, and whether it is `required`.
The command reads no project file, so you can run it anywhere.
The [configuration reference](../../reference/pages/configuration.md#option-reference) is generated from the same list.

## Step 8: Starting a Site with Every Option Listed

To see every option in context, scaffold a site with the full config:

```bash
bartleby new site mysite --full-config
```

The generated `bartleby.yml` keeps the site name, the `nav`, and the theme features of the minimal scaffold, and lists every other option at its default, with its description as a comment.
The `content_types` and `taxonomies` blocks are a commented-out example named `example`; uncomment and rename it to add a type, or run `bartleby enable blog <name>`.
The site builds the same pages as the minimal scaffold until you change something.
Delete the lines you do not need.
Without the flag, the file holds only what the site needs to build.

## See Also

- [CLI reference for `config`](../../reference/pages/cli.md#bartleby-config)
- [Configuration reference](../../reference/pages/configuration.md)
