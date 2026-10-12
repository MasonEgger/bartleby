---
title: Welcome
description: Where to go first on a new Bartleby site, and the five changes that make it yours.
---

This is your new site.
It already builds, and the [Feature Tour](tour/index.md) shows every kind of content it can render.
Spend your first five minutes on these steps.

## Run the Site

From the project directory, start the dev server:

```bash
bartleby serve
```

Open http://127.0.0.1:8000/ in a browser.
The server rebuilds the site and reloads the page each time you save a file.

## Make the First Edit

This page is `content/index.md`.
Change a sentence, save the file, and watch the browser update.
The block between the `---` lines at the top is front matter.
It sets the page title and the description that search engines and agents read.

## Add a Page

Create `content/getting-started.md` with a title and a line of text:

```markdown
---
title: Getting Started
description: How to get started.
---

Your first paragraph goes here.
```

Then list the page in the `nav` section of `bartleby.yml`:

```yaml
nav:
  - Home: index.md
  - Getting Started: getting-started.md
```

## Set Your Title and URL

`bartleby.yml` holds the site title, the public URL, the navigation, and the theme features.
Set `site.url` to the address where the site will live before you deploy.
The sitemap, canonical links, and the agent files are all built from it.

## Add a Blog When You Want One

A blog is opt-in.
If this site has no blog, add one with a single command:

```bash
bartleby enable blog blog
```

The command adds a `blog` content type and the `tags` taxonomy to `bartleby.yml`.
To start a new site with the blog and a sample post already in place, run `bartleby new site my-site --blog`.

## Check Your Work

Run `bartleby build` to write the finished site to `site/`.
Run `bartleby lint` to find broken links, missing descriptions, and orphan pages before you publish.
