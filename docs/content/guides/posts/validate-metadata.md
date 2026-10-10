---
title: "Validate Post Metadata at Build Time"
description: "Catch missing required fields, type mismatches, and invalid choices before deployment."
date: 2026-06-02
audience: existing-user
tags:
  - configuration
  - validation
authors:
  - mason
---

Bartleby validates per-content-type metadata against a schema you declare in `bartleby.yml`.
Both `bartleby build` and `bartleby validate` report errors and name the offending file and field.

<!-- more -->

## Step 1: Declare a Schema

Add a `metadata` block to the content type:

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

The [front matter fields reference](../../reference/pages/front-matter-fields.md#custom-metadata) lists the supported types.

## Step 2: Write Content That Uses the Schema

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

When everything is in order, the command prints:

```
validation passed (2 files checked)
```

When it finds problems, it prints `validation failed`, then one line per error.
Each line has the file, an `E001` code, and the message.
For example:

```
validation failed (5 files checked)
tutorials/posts/bad-date.md:0 [E001] : authors: unknown author key 'nobody' (fix: use one of the known author ids (mason), or add the id to the authors file)
tutorials/posts/bad-date.md:0 [E001] : content_types.tutorials.metadata.last_verified: expected date for 'last_verified', got unparseable string (fix: write a date value in the front matter, or change the field's `type:` in the schema)
tutorials/posts/bad-date.md:0 [E001] : content_types.tutorials.metadata.featured: expected boolean for 'featured', got str (fix: write a boolean value in the front matter, or change the field's `type:` in the schema)
tutorials/posts/no-difficulty.md:0 [E001] : content_types.tutorials.metadata.difficulty: required field 'difficulty' is missing (fix: add `difficulty:` to this file's front matter, or set `required: false` in the schema)
tutorials/posts/wrong-choice.md:0 [E001] : content_types.tutorials.metadata.difficulty: 'expert' is not one of the allowed choices: 'beginner', 'intermediate', 'advanced' (fix: set `difficulty` to one of the listed choices)
```

Each message names the schema entry that the page broke, so you can find both the front matter line and the schema line.
The text after `fix:` says what to change.

Those lines come from four sample pages:

- `no-difficulty.md` leaves out the required `difficulty` field.
- `wrong-choice.md` sets `difficulty: expert`.
- `bad-date.md` sets `last_verified: yesterday`, `featured: maybe`, and an author key that is not in `.authors.yml`.

`bartleby build` runs the same checks.
It prints each failure as `error [build_error] <file>: <message>` on stderr and exits 1.

## Step 4: Use Validate in CI

`bartleby validate` exits 0 on success and 1 on any error.
Run it before the build step in your CI pipeline to catch problems early:

```yaml
# .github/workflows/site.yml
- run: bartleby validate
- run: bartleby build
```

Add `--output json` when a script needs to read the result.
The JSON has `valid`, `files_checked`, `errors`, and `warnings` keys.

## Notes

- Author keys in the `authors:` front matter are validated the same way.
- An empty `title` fails validation for any page.
  A missing `title` does not, because Bartleby falls back to the file name.
- Fields that the schema does not name are allowed.
  The schema only constrains the fields it lists.
