# ${name}

A static site built with [Bartleby](https://pypi.org/project/bartleby-ssg/).

## Commands

Run these from this directory.

| Command | What it does |
| --- | --- |
| `bartleby serve` | Builds the site, serves it at http://127.0.0.1:8000/, and rebuilds when a file changes |
| `bartleby build` | Writes the finished site to `site/` |
| `bartleby new post "Title"` | Starts a draft post in `content/blog/posts/` |
| `bartleby validate` | Checks `bartleby.yml` and every page's front matter |
| `bartleby lint` | Finds broken links, missing descriptions, and orphan pages |
| `bartleby generate-skill` | Writes agent skills for this site into `.claude/skills/` |

Add `--help` to any command for its options, or `--output json` for machine-readable output.

## Layout

| Path | What goes there |
| --- | --- |
| `bartleby.yml` | Site title, URL, navigation, theme, and content types |
| `.authors.yml` | Authors that posts name in their `authors:` front matter |
| `content/` | Pages and posts as Markdown; other files here are copied next to the page that uses them |
| `templates/` | Your own templates, which take precedence over the theme's |
| `static/` | Files copied to the site root as-is |
| `hooks/` | Python plugins that run during the build |

## Publishing a Draft

New posts start with `draft: true`, which keeps them out of the build.
Change it to `draft: false` when the post is ready, or run `bartleby build --include-drafts` to preview every draft.

## Before You Deploy

Set `site.url` in `bartleby.yml` to the address the site will live at.
Feeds, the sitemap, canonical links, and the agent files are built from it.
