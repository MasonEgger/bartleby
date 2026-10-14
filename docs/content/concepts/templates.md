---
title: "Templates and the Lookup Cascade"
description: "How Bartleby decides which Jinja2 template renders each page."
---

Every page goes through a six-level template lookup, and the first match wins.
The cascade lets you override one template without forking the whole theme.

## The Six-Level Cascade

For a page with a template type `<kind>` (`post`, `list`, `page`, `taxonomy`, or `taxonomy_index`), Bartleby builds a list of candidate names and takes the first one that exists:

1. The `template` field in the page's front matter, which returns at once
2. `{content_type}/taxonomy/{name}.html` and `{content_type}/taxonomy.html`, for taxonomy term pages of a content type
3. `{content_type}/{kind}.html`, a layout for one content type
4. `{content_type}/base.html`, a base for one content type
5. `defaults/{kind}.html`, a site-wide default
6. `{kind}.html` from the theme, and `page.html` as a last resort for any kind except `page`

Bartleby checks each candidate name against three places in order: your `overrides/` directory, your `templates/` directory, and the templates of each theme layer.
The first existing file wins.

## The Theme Chain

"The theme" is a chain, not one directory.
A theme can `extends` another, so the default `scrivener` theme sits on top of `base`.
Bartleby searches the leaf theme first and its parents after it, which lets a child replace any file it needs and inherit the rest.
`bartleby theme inspect` prints the chain and shows which layer provides each file.

Project files sit in front of the whole chain.
The search order for any template name is `overrides/`, `templates/`, the project root, then each theme layer from leaf to root.
That order is why an `overrides/` file can replace one template from any layer, and why a `theme.path` theme can replace many.
For the manifest and the rest of the theme system, read the [themes reference](../reference/pages/themes.md).

## The Jinja2 Search Path

Templates also find each other by name, through `{% extends %}` and `{% include %}`.
For those lookups, the Jinja2 environment searches these roots in order:

1. `overrides/`
2. `templates/`
3. The project directory itself
4. The theme chain, leaf first

Because the project directory is on the path, `{% include "partials/banner.html" %}` finds `partials/banner.html` at your project root.
Put a file in `overrides/` and it also beats a theme file of the same name for every `include` and `extends`.

## Template Context

Every template receives the same context: `site`, `page`, `nav`, `pages`, `taxonomies`, `config`, `build`, `data`, and more.
The [template context reference](../reference/pages/template-context.md) lists every key.

## Per-Page Template Override

Set `template` in the front matter:

```yaml
---
title: "Special Landing Page"
template: campaigns/launch.html
---
```

Bartleby resolves the name like any other template.
It checks `overrides/campaigns/launch.html`, then `templates/campaigns/launch.html`, then the project root, then the theme chain.
Use this for one-off page layouts that do not justify a new content type.
