---
title: "Enable Content Types"
description: "Add a blog, a tutorials section, or any named content type with bartleby enable, then turn it off and on again."
date: 2026-10-12
audience: existing-user
tags:
  - configuration
authors:
  - mason
---

A fresh site has no content types.
The `bartleby enable` command adds one to `bartleby.yml` for you, and `bartleby disable` turns it off without deleting anything.
In this guide, you will add a `tutorials` section next to a `blog`, publish to both, and read the feeds each one produces.

<!-- more -->

## Prerequisites

You need a Bartleby site with a `bartleby.yml`.
If you have none, run `bartleby new site mysite` and move into the new directory.
To start with a blog already in place, run `bartleby new site mysite --blog` instead.

## Step 1: Enabling a Content Type

Run `enable` with a shape and a name:

```bash
bartleby enable blog tutorials
```

`blog` is the shape, the only one Bartleby ships.
`tutorials` is the name you choose.
The command prints `Added blog content type 'tutorials' to bartleby.yml`.

The command writes up to three things to `bartleby.yml`.
It adds a `tutorials` block under `content_types`, with the path `tutorials/posts`, `readtime`, an excerpt separator, the `tags` taxonomy, and `feeds: [rss, atom]`.
It adds the `tags` taxonomy when the site does not declare it yet.
When the file has an explicit `nav` with no entry for the type, it appends `- Tutorials: tutorials/`, so the new listing is reachable from the header.

The command leaves other files alone.
It does not create `content/tutorials/posts/`; you do that in the next step.

## Step 2: Writing the First Page

Create a draft in the new type:

```bash
bartleby new post "Build Your First Site" --type tutorials
```

The command creates `content/tutorials/posts/build-your-first-site.md`, along with the missing directories.
Set `draft: false` in its front matter when the page is ready to publish.

## Step 3: Checking the Section in Your Navigation

If your `bartleby.yml` has an explicit `nav`, `enable` has already added the new section to it:

```yaml
nav:
  - Home: index.md
  - Blog: blog/
  - Tutorials: tutorials/
```

A directory target such as `tutorials/` points at the type's listing page.
Move the entry, or rename its title, as you like; `enable` adds one only when no entry links to `tutorials/` yet.
A site without a `nav` key builds its navigation from the content tree, so this step does not apply to it.

## Step 4: Reading the Feeds

Run `bartleby build`.
Each enabled type that has `feeds` publishes its own files under its URL, and the site publishes one combined feed at the root:

| File | Contents |
|------|----------|
| `blog/feed.xml`, `blog/atom.xml` | Posts from `blog` only |
| `tutorials/feed.xml`, `tutorials/atom.xml` | Pages from `tutorials` only |
| `feed.xml`, `atom.xml` | The newest items from every type that has `feeds` |

The `site.feed` block controls the combined feed.
Use `include` to merge only some types, `limit` to change the 50-item default, and `enabled: false` to drop the combined feed:

```yaml
site:
  feed:
    include: [blog, tutorials]
    limit: 25
```

A type listed in `include` must define `feeds`.
To keep a type out of every feed, remove its `feeds` key.

## Step 5: Enabling More Than One of a Shape

You can enable the same shape under as many names as you like.
The mason.dev site runs three blogs this way:

```bash
bartleby enable blog blog
bartleby enable blog tutorials
bartleby enable blog speaking
```

Each name gets its own path, listing, taxonomy pages, and pair of feeds, and the combined feed at the site root carries all three.

## Step 6: Turning a Type Off and On

To stop building a type, run `disable`:

```bash
bartleby disable tutorials
```

The command takes only the name, because the block is already in the file.
It sets `enabled: false` on the `tutorials` block and leaves every other key as it was, the `nav` entry included.
The build then skips the type's pages, listing, and feeds, and the type drops out of the combined feed.
Your content files stay where they are.
With the `Tutorials: tutorials/` entry from Step 3 still in place, the next build prints `WARNING: nav entry 'Tutorials' links to the disabled content type 'tutorials'; remove the entry or set content_types.tutorials.enabled to true`.
Remove the nav entry while the type is off, or keep it and expect the warning.
`bartleby new post --type tutorials` refuses while the type is off, with the fix `run bartleby enable blog tutorials`, and `bartleby schema tutorials` prints `enabled: false`.

To turn the type back on, run `enable` again:

```bash
bartleby enable blog tutorials
```

The command prints `Re-enabled content type 'tutorials' in bartleby.yml` and sets `enabled: true`.
Running `enable` on a type that is already on changes nothing and says so.
Running `disable` on a name that `bartleby.yml` does not define exits with code `2` and lists the names it does know.

You can also edit the flag by hand, or set it from the command line: `bartleby config set content_types.tutorials.enabled false`.

## See Also

- [CLI reference for `enable` and `disable`](../../reference/pages/cli.md#bartleby-enable)
- [Content type options](../../reference/pages/configuration.md#content_types) and the [full option list](../../reference/pages/configuration.md#option-reference)
- [Content Organization](../../concepts/content-organization.md)
