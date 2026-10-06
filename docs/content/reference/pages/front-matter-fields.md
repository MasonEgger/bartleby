---
title: "Front matter fields"
description: "Standard fields, taxonomy values, and custom metadata schema."
tags:
  - front-matter
  - configuration
---

Every Markdown file may begin with a YAML front matter block. The fields below are recognised by name; anything else flows into `page.custom_metadata` and can be validated by a content type's `metadata` schema.

## Standard fields

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `title` | string | (filename stem) | Page title — required for build success on every page |
| `description` | string \| null | `None` | Meta description, OG description, Twitter card |
| `date` | date | `None` | Publication date — drives feeds, taxonomy sort, JSON-LD `datePublished` |
| `draft` | bool | `false` | When `true`, excluded from `bartleby build` (set `--include-drafts` to override) |
| `template` | string \| null | `None` | Override the template lookup for this page |
| `url` | string \| null | `None` | Replace the generated URL with a custom path |
| `url_base` | string \| null | `None` | Replace just the URL base prefix |
| `slug` | string \| null | `None` | Override the slug used by `{slug}` placeholders |
| `authors` | list[string] | `[]` | Author keys from `.authors.yml` |

## Taxonomy values

Any front-matter key matching a taxonomy declared in `bartleby.yml` becomes a taxonomy value list. Values are always coerced to strings.

```yaml
tags:
  - python
  - temporal
categories:
  - devops
```

## Custom metadata

Anything not in the standard set and not matching a taxonomy name flows into `page.custom_metadata`. A content type's `metadata` schema can constrain these fields:

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

Supported `type` values:

- `string`
- `integer` — rejects `bool` (which is an `int` subclass in Python)
- `boolean`
- `date` — accepts ISO date strings or YAML date objects
- `list` — accepts any YAML list

Validation runs before rendering. Errors include the file path, field name, and a human-readable explanation.

## Reading custom metadata in templates

```jinja2
{% if page.custom_metadata.difficulty %}
<span class="difficulty difficulty-{{ page.custom_metadata.difficulty }}">
  {{ page.custom_metadata.difficulty }}
</span>
{% endif %}
```
