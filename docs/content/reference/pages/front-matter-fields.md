---
title: "Front Matter Fields"
description: "Standard fields, taxonomy values, and the custom metadata schema."
tags:
  - front matter
  - configuration
---

Every Markdown file may begin with a YAML front matter block.
Bartleby recognizes the fields below by name.
Anything else goes to `page.custom_metadata`, where a content type's `metadata` schema can validate it.
See [Front matter](../../concepts/front-matter.md) for how the three groups work together.

## Standard Fields

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `title` | string | filename without extension | Page title. An empty title fails validation. |
| `description` | string or null | `None` | Meta description, Open Graph description, and Twitter card text |
| `date` | date | `None` | Publication date. It drives feeds, taxonomy sort order, and JSON-LD `datePublished`. |
| `draft` | bool | `false` | When `true`, `bartleby build` skips the page unless you pass `--include-drafts` |
| `template` | string or null | `None` | Template to use for this page |
| `url` | string or null | `None` | Replace the generated URL with a custom path |
| `url_base` | string or null | `None` | Replace only the URL base prefix. `url_format` still applies. |
| `slug` | string or null | `None` | Override the slug that `{slug}` placeholders use |
| `authors` | list of strings | `[]` | Author keys from `.authors.yml` |

## Taxonomy Values

Any front matter key that matches a taxonomy declared in `bartleby.yml` becomes a list of taxonomy values.
Bartleby coerces every value to a string.

```yaml
tags:
  - python
  - temporal
categories:
  - devops
```

## Custom Metadata

Anything that is not a standard field or a taxonomy name goes to `page.custom_metadata`.
A content type's `metadata` schema can constrain these fields:

```yaml
content_types:
  tutorials:
    path: tutorials/posts
    metadata:
      difficulty:
        type: string
        required: true
        choices:
          - beginner
          - intermediate
          - advanced
      last_verified:
        type: date
      featured:
        type: boolean
      view_count:
        type: integer
```

Each field takes `type` (required), `required` (default `false`), and `choices`.
The supported `type` values are:

| Type | Accepts |
|------|---------|
| `string` | Any string |
| `integer` | An integer. Booleans are rejected, even though Python treats `bool` as an `int`. |
| `boolean` | `true` or `false` |
| `date` | An ISO date string or a YAML date |
| `list` | Any YAML list |

Validation runs before rendering.
Each error names the file, the field, and the problem.
The [validation guide](../../guides/posts/validate-metadata.md) shows real error output.
