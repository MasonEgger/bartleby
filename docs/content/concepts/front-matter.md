---
title: "Front matter"
description: "Standard fields, taxonomy values, custom metadata, and build-time validation."
---

Every Markdown file may start with a YAML front matter block delimited by `---` lines. Bartleby parses the block, slots the standard fields onto the page object, and validates per-content-type schemas at build time.

## A complete example

```yaml
---
title: "Deploy with Temporal"
description: "Learn how to deploy workflows with Temporal"
date: 2026-03-01
draft: false
template: custom-tutorial.html
url: custom/path/to/page
slug: deploy-with-temporal
authors:
  - mason
  - guest
tags:
  - python
  - temporal
categories:
  - devops
difficulty: intermediate
last_verified: 2026-03-10
---
```

## Standard fields

These fields are recognised on every page regardless of content type:

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Page title — **required** for every page |
| `description` | string | Used for meta description, OG description, Twitter card |
| `date` | date | Publication date, used in feeds, taxonomy sort, JSON-LD `datePublished` |
| `draft` | bool | Defaults to `false`; `true` excludes the page from production builds |
| `template` | string | Override the template lookup for this page |
| `url` | string | Replace the generated URL with a custom path |
| `url_base` | string | Replace just the URL base prefix; `url_format` still applies |
| `slug` | string | Override the slug used by `{slug}` placeholders in `url_format` |
| `authors` | list | Author keys from `.authors.yml` |

## Taxonomy values

Any front matter key that matches a configured taxonomy name (`tags`, `categories`, etc.) becomes a taxonomy value list on the page. They're collected during the build to populate `/tags/`, `/tags/python/`, and per-content-type variants.

## Custom metadata

Anything else lands in `page.custom_metadata` and can be validated by a content type's `metadata` schema:

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
```

If a tutorial is missing `difficulty`, has a non-date `last_verified`, or sets `difficulty: expert`, `bartleby build` fails with the file path and field name in the error message. `bartleby validate` runs the same checks without rendering.

## Author validation

Author keys are validated against `.authors.yml`. An unknown key produces a build error pointing at the offending page.
