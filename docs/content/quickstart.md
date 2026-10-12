---
title: "Quickstart"
description: "Scaffold, edit, and build your first Bartleby site in five minutes."
---

This quickstart walks through scaffolding a new site, writing a post, and producing the rendered HTML output.
You need Bartleby installed first.
If you have not done that yet, follow the [Installation](installation.md) page.

## Step 1: Creating a Site

Run the scaffold command, then move into the new directory:

```bash
bartleby new site mysite
cd mysite
```

The command lists what it created and the command to run next:

```
Created site at mysite/
  README.md
  bartleby.yml
  content/
  hooks/
  static/
  templates/
Next: cd mysite && bartleby serve
```

The site is shaped like a docs site, with a home page that says what to do next and a feature tour:

```
mysite/
├── bartleby.yml
├── README.md
├── content/
│   ├── index.md
│   └── tour/
│       └── index.md
├── hooks/
├── static/
└── templates/
```

The generated `bartleby.yml` holds the site title and URL, a `nav` with Home and Feature Tour, and the theme features: search, search highlighting, the section sidebar, back-to-top, code-copy, and the color-mode toggle.
It defines no content types, because a blog is opt-in.
The `scrivener` theme is the default.
To see the Material look instead, set `theme.name: material` in `bartleby.yml` and rebuild.
The empty `hooks/`, `static/`, and `templates/` directories are where plugin hooks, static files, and template overrides go.

To see every option in a config file, scaffold with `--full-config`.
To start with a blog and a sample post, scaffold with `--blog`.

## Step 2: Writing a Post

Posts live in a content type, so add one first:

```bash
bartleby enable blog blog
```

The command prints `Added blog content type 'blog' to bartleby.yml`.
Then create a post:

```bash
bartleby new post "Hello World" --type blog
```

The command writes `content/blog/posts/hello-world.md` and prints its path.
The new file starts with a front matter stub:

```markdown
---
title: "Hello World"
date: 2026-06-02
draft: true
---

Write something here.
```

Replace the body with whatever you want.
A plain `bartleby build` skips drafts, so change `draft: true` to `draft: false` before the post should appear.
The `enable` command adds no `nav` entry, so add `- Blog: blog/` to `nav` in `bartleby.yml` if you want a Blog tab.

## Step 3: Building the Site

Render the site:

```bash
bartleby build
```

Bartleby prints a summary line like this one:

```
Built 5 pages (12 static files) into site/
```

The rendered site lands in `site/`:

```
mysite/site/
├── 404.html
├── atom.xml
├── blog/
│   ├── atom.xml
│   ├── feed.xml
│   ├── index.html
│   └── posts/
│       └── hello-world/
│           ├── index.html
│           └── index.md          # Markdown variant for LLMs
├── content-index.json
├── css/
├── feed.xml
├── index.html
├── index.md
├── js/
├── llms-full.txt
├── llms.txt
├── robots.txt
├── schema.json
├── search/
│   └── search_index.json
├── sitemap.xml
├── sitemap.xml.gz
├── tags/
│   └── index.html
└── tour/
    ├── after.svg
    ├── before.svg
    ├── index.html
    ├── index.md
    ├── slide-1.svg
    ├── slide-2.svg
    └── slide-3.svg
```

The `blog/` feeds carry the blog's posts, and `feed.xml` and `atom.xml` at the root carry the combined feed.
The `svg` files in `tour/` are the images the tour page uses; they follow the page's URL.
The `js/` directory holds the search and interactivity scripts that the theme ships.

## Step 4: Validating Before You Build

Check the config and front matter without rendering anything:

```bash
bartleby validate
```

On a clean site, the command prints `validation passed (3 files checked)` for this site.
It catches missing required metadata fields, unknown author keys, undefined taxonomy references, template overrides that point nowhere, and broken cross-references.

## Step 5: Previewing Locally

Start the development server:

```bash
bartleby serve
```

The command builds the site, then prints the build summary, the address, and how to stop:

```
Built 5 pages (12 static files) into site/
Serving at http://127.0.0.1:8000/
Press Ctrl+C to stop
```

Open <http://127.0.0.1:8000/> in your browser.
You see the welcome page, the Feature Tour in the sidebar, and a toggle in the header for dark mode.
The server rebuilds the site when you change a file, and it includes drafts.
Delete the tour and its `nav` entry when you no longer need it.

## What's Next

- Read the [Concepts](concepts/index.md) pages to understand Bartleby's model of content, URLs, and templates.
- Browse the [Guides](guides/index.md) for task-oriented walkthroughs.
- Use the [Reference](reference/index.md) for configuration, CLI, and API details.
- Learn to [change settings from the command line](guides/posts/configure-from-the-command-line.md) and to [add more content types](guides/posts/enable-content-types.md).
