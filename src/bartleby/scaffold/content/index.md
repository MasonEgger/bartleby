---
title: Welcome
description: A new Bartleby site, with a short tour of what it builds and where to edit it.
---

This is a new Bartleby site.
Every page is a Markdown file under `content/` with YAML front matter at the top, and `README.md` in the project root has the commands you need.

## What You Get

- Pages, a blog with tags, RSS and Atom feeds, full-text search, a sitemap, and light and dark modes, all from one `bartleby build`.
- A plain Markdown copy of every page next to its HTML, plus `llms.txt`, `llms-full.txt`, `schema.json`, and `content-index.json`, so AI crawlers and coding agents can read the site without scraping it.
- `bartleby validate` and `bartleby lint`, which catch bad front matter, broken links, and missing descriptions before you publish. Errors name the file, the key, and the fix.
- `bartleby generate-skill`, which writes skills into `.claude/skills/` that teach a coding agent this site's content types, front matter, and commands.
- No Node toolchain: Bartleby is a Python package, and the bundled themes ship with compiled CSS.

## Where to Start

- Read the [welcome post](/blog/posts/welcome/) to see a published post.
- Run `bartleby new post "My First Post"` to start a draft.
- Edit `bartleby.yml` to change the title, the navigation, or the theme. For the Material look, set `theme.name` to `material`.
