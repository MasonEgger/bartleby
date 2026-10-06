---
title: "Validate post metadata at build time"
description: "Catch missing required fields, type mismatches, and invalid choices before deployment."
date: 2026-06-02
audience: existing-user
tags:
  - configuration
  - validation
authors:
  - mason
---

Bartleby validates per-content-type metadata against a schema you declare in `bartleby.yml`. Errors surface as part of `bartleby build` and `bartleby validate`, with the offending file and field named.

<!-- more -->

## Step 1: Declare a schema

In your content type config:

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
```

## Step 2: Write content that exercises the schema

```yaml
---
title: "Deploy with Temporal"
date: 2026-03-01
difficulty: intermediate
last_verified: 2026-04-15
featured: false
---
```

## Step 3: Validate

```bash
bartleby validate
```

If everything is in order, you get:

```
validation passed
```

If a tutorial is missing `difficulty`, the build prints:

```
tutorials/posts/no-difficulty.md: required field 'difficulty' is missing
```

If you set `difficulty: expert`:

```
tutorials/posts/wrong-choice.md: 'expert' is not one of the allowed choices: 'beginner', 'intermediate', 'advanced'
```

If `last_verified: yesterday`:

```
tutorials/posts/bad-date.md: expected date for 'last_verified', got unparseable string
```

## Use validate in CI

`bartleby validate` exits 0 on success, 1 on any error. Wire it into your CI pipeline before the build step to catch problems fast:

```yaml
# .github/workflows/site.yml
- run: bartleby validate
- run: bartleby build
```

## Notes

- Author keys in `authors:` front matter are also validated — unknown keys are reported the same way.
- The standard `title` field is required for every page, regardless of content type or metadata schema.
- Custom metadata that's not in the schema is allowed; the schema only constrains the fields it names.
