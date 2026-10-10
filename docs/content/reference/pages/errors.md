---
title: "Error Messages"
description: "How Bartleby words its errors, and the fix for each common one."
tags:
  - cli
---

Bartleby errors name where the problem is and what to change.
Every structured error has the same shape:

```text
<file>: <key path>: <message> (fix: <hint>)
```

- The file is the one the problem lives in, such as `bartleby.yml`, `.authors.yml`, or a theme's `theme.yml`.
- The key path is the field or id inside it, such as `site.url` or `content_types.blog.metadata.rating.type`.
- The hint says what to change.

Any part can be missing when it does not apply.
A page-level error from `build` starts with the page's source path instead of a config file.

The CLI prints the message after `error [code]` on stderr and exits 1.
With `--output json` it is the `error` value of one JSON object on stdout.
See [CLI commands](cli.md) for the codes and exit codes.
`BARTLEBY_DEBUG=1` shows the full Python traceback.

## Common Errors

| Code | Message contains | Fix |
|------|------------------|-----|
| `config_error` | `unknown top-level key` | Fix the spelling. The hint suggests the closest valid key, or lists them all. |
| `config_error` | `required field is missing` | Add the named key. A site needs `site.title` and `site.url`. |
| `config_error` | `invalid YAML at line N` | Fix the indentation, quotes, or brackets at that line of `bartleby.yml`. |
| `config_error` | `unknown field type` | Set `type` under `content_types.<name>.metadata.<field>` to `string`, `integer`, `boolean`, `date`, or `list`. |
| `config_error` | `references undefined taxonomy` | Declare the taxonomy under `taxonomies:`, or remove it from the content type. |
| `config_error` | `theme.color_mode.toggle` | Add `color-mode.toggle` to `theme.features` and delete the key. |
| `config_error` | `ai.skills.include_examples` | Delete the key. Generated skills carry no example pages. |
| `author_error` | `duplicate key` | Keep one entry per author id in `.authors.yml`. |
| `author_error` | `missing required field 'name'` | Add `name:` under the author id. |
| `build_error` | `unknown author key` | Use one of the ids the message lists, or add the id to `.authors.yml`. |
| `build_error` | `content_types.<type>.metadata.<field>` | Fix the page's front matter, or relax the schema line the message names. |
| `build_error` | `content directory does not exist` | Run from the directory that holds `bartleby.yml`, or create `content/`. |
| `build_error` | `unknown shortcode` | Create `shortcodes/<name>.html` under `templates/`, or fix the name. |
| `theme_error` | `missing theme.yml` | A theme directory needs a `theme.yml` with a `name`. `bartleby theme eject` copies a working one. |
| `theme_error` | `theme path does not exist` | Point `theme.path` at an existing directory, relative to the project. |
| `theme_error` | `unknown bundled theme` | Use `base`, `material`, or `scrivener`, or use `theme.path`. |
| `agent_surface_error` | `would overwrite the generated artifact` | Rename the page or set another `url:`. `schema.json` and `content-index.json` are reserved. |
| `content_error` | `invalid YAML` | Fix the page's front matter between its two `---` lines. |

The `build` command collects every page error before it stops, so one run lists them all.
