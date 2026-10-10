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

The `new site` command prints `Created site at mysite/` and lays down a small project with a home page and one published sample post:

```
mysite/
├── bartleby.yml
├── .authors.yml
├── content/
│   ├── index.md
│   └── blog/
│       └── posts/
│           └── welcome.md
├── hooks/
├── static/
└── templates/
```

The generated `bartleby.yml` selects the `scrivener` theme and turns on its navigation, search, code-copy, and color-mode toggle features.
It lists Home and Blog in `nav`, and it sets up a single `blog` content type.
That type turns on `readtime`, uses `<!-- more -->` as the excerpt separator, and opts in to the `tags` taxonomy.
The empty `hooks/`, `static/`, and `templates/` directories are where plugin hooks, static files, and template overrides go.

To see the Material look instead, set `theme.name: material` in `bartleby.yml` and rebuild.

## Step 2: Writing a Post

Create a post under the `blog` content type:

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
The scaffold's own `welcome.md` is already published, so your first build has a post to show.

## Step 3: Building the Site

Render the site:

```bash
bartleby build
```

Bartleby prints a summary line like this one:

```
Built 7 pages (5 static files) into site/
```

The rendered site lands in `site/`:

```
mysite/site/
├── 404.html
├── atom.xml
├── blog/
│   ├── index.html
│   ├── posts/
│   │   └── welcome/
│   │       ├── index.html
│   │       └── index.md          # Markdown variant for LLMs
│   └── tags/             # Per-tag pages for the blog
├── content-index.json
├── css/
│   └── main.css
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
└── tags/
    ├── bartleby/
    │   └── index.html
    └── index.html
```

The `js/` directory holds the search and interactivity scripts that the theme ships.

## Step 4: Validating Before You Build

Check the config and front matter without rendering anything:

```bash
bartleby validate
```

On a clean site, the command prints `validation passed (2 files checked)` for the scaffold.
It catches missing required metadata fields, unknown author keys, undefined taxonomy references, template overrides that point nowhere, and broken cross-references.

## Step 5: Previewing Locally

Start the development server:

```bash
bartleby serve
```

Open <http://127.0.0.1:8000/> in your browser.
You see the home page, a Blog tab that lists the welcome post, and a toggle in the header for dark mode.
The server rebuilds the site when you change a file, and it includes drafts.

## What's Next

- Read the [Concepts](concepts/index.md) pages to understand Bartleby's model of content, URLs, and templates.
- Browse the [Guides](guides/index.md) for task-oriented walkthroughs.
- Use the [Reference](reference/index.md) for configuration, CLI, and API details.
