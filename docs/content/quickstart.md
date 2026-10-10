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

The `new site` command prints `Created site at mysite/` and lays down a small project:

```
mysite/
├── bartleby.yml
├── .authors.yml
└── content/
    └── index.md
```

The generated `bartleby.yml` sets up a single `blog` content type.
That type turns on `readtime`, uses `<!-- more -->` as the excerpt separator, and opts in to the `tags` taxonomy.
Bartleby creates the other directories, such as `templates/`, `static/`, and `hooks/`, only when you add them.

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
A plain `bartleby build` skips drafts, so change `draft: true` to `draft: false` before you build.

## Step 3: Building the Site

Render the site:

```bash
bartleby build
```

Bartleby prints a summary line like this one:

```
Built 4 pages (5 static files) into site/
```

The rendered site lands in `site/`:

```
mysite/site/
├── 404.html
├── atom.xml
├── blog/
│   ├── index.html
│   └── posts/
│       └── hello-world/
│           ├── index.html
│           └── index.md          # Markdown variant for LLMs
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
    └── index.html
```

The `js/` directory holds the search and interactivity scripts that the theme ships.

## Step 4: Validating Before You Build

Check the config and front matter without rendering anything:

```bash
bartleby validate
```

On a clean site, the command prints `validation passed (2 files checked)`.
It catches missing required metadata fields, unknown author keys, undefined taxonomy references, template overrides that point nowhere, and broken cross-references.

## Step 5: Previewing Locally

Start the development server:

```bash
bartleby serve
```

Open <http://127.0.0.1:8000/> in your browser.
The server rebuilds the site when you change a file, and it includes drafts.

## What's Next

- Read the [Concepts](concepts/index.md) pages to understand Bartleby's model of content, URLs, and templates.
- Browse the [Guides](guides/index.md) for task-oriented walkthroughs.
- Use the [Reference](reference/index.md) for configuration, CLI, and API details.
