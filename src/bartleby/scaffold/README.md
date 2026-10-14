# ${name}

A static site built with [Bartleby](https://pypi.org/project/bartleby-ssg/).

## Quickstart

Install Bartleby, then serve the site from this directory:

```bash
pip install bartleby-ssg
bartleby serve
```

The server builds the site, prints its address (http://127.0.0.1:8000/), and rebuilds when a file changes.

Edit `content/index.md` for the home page.
Add more pages as Markdown files under `content/`, and list them in the `nav` section of `bartleby.yml`.
`content/tour/index.md` is a feature tour; delete it and its entry in `nav` when you no longer need it.

## Commands

| Command | What it does |
| --- | --- |
| `bartleby serve` | Builds the site, serves it, and rebuilds when a file changes |
| `bartleby build` | Writes the finished site to `site/` |
| `bartleby validate` | Checks `bartleby.yml` and every page's front matter |
| `bartleby lint` | Checks links, descriptions, orphan pages, and accessibility (alt text, heading order, link names), with a fix for each finding |
| `bartleby generate-skill` | Writes agent skills for this site into `.claude/skills/` |

Add `--help` to any command for its options, or `--output json` for machine-readable output.

## Layout

| Path | What goes there |
| --- | --- |
| `bartleby.yml` | Site title, URL, navigation, and theme features |
| `content/` | Pages as Markdown; other files here are copied next to the page that uses them |
| `templates/` | Your own templates, which take precedence over the theme's |
| `static/` | Files copied to the site root as-is |
| `hooks/` | Python plugins that run during the build |

## Load Embeds on Click

Embeds in the tour (YouTube, CodePen, Twitter, Instagram) load live by default.
Eager loading is the default, so `bartleby.yml` has no `markwright:` section.
To hold an embed back until the reader clicks it, add a `markwright:` section to `bartleby.yml`:

```yaml
markwright:
  youtube:
    load: click
```

The same `load: click` key works under `codepen`, `twitter`, and `instagram`.
Until the reader clicks, the page contacts no provider.

## Add a Blog

A blog is opt-in.
A site created with `bartleby new site my-site --blog` has one, with a sample post.
For any other site, run this to add it:

```bash
bartleby enable blog blog
```

It adds a `blog` content type and the `tags` taxonomy to `bartleby.yml`.
Once the blog exists, `bartleby new post "Title"` starts a draft in `content/blog/posts/`.

## Before You Deploy

Set `site.url` in `bartleby.yml` to the address the site will live at.
Feeds, the sitemap, canonical links, and the agent files are built from it.
