---
title: "Front Matter"
description: "How Bartleby reads the YAML block at the top of a page and when it validates it."
---

Every Markdown file may start with a YAML block between two `---` lines.
That block is the page's front matter.
Bartleby parses it, moves the fields it knows onto the page object, and checks the rest against the schema for the page's content type.

## A Complete Example

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

## Three Kinds of Keys

Bartleby sorts every key in the block into one of three groups.

**Standard fields** have a meaning built into the build.
`title`, `description`, `date`, `draft`, `template`, `url`, `url_base`, `slug`, and `authors` all belong here.
They set the page's metadata, its URL, its template, and its byline.

**Taxonomy values** are keys that match a taxonomy name in `bartleby.yml`.
In the example, `tags` and `categories` are taxonomy values.
Bartleby collects them across the site to build the taxonomy listing pages.
See [Taxonomies](taxonomies.md).

**Custom metadata** is everything else.
In the example, `difficulty` and `last_verified` are custom metadata.
Bartleby stores them on the page as `page.custom_metadata`, where templates can read them.
A content type can declare a schema for these fields.

The [front matter fields reference](../reference/pages/front-matter-fields.md) lists each standard field with its type and default.

## When Validation Happens

Validation runs before any page renders.
It checks custom metadata against the content type's `metadata` schema, and it checks author keys against `.authors.yml`.
It also rejects a page whose title is empty.
A failure stops `bartleby build` and is reported by `bartleby validate`, with the file path and field name in the message.

Fields that the schema does not name are allowed.
The schema only constrains the fields it lists.

The [validation guide](../guides/posts/validate-metadata.md) walks through declaring a schema and reading the errors.
