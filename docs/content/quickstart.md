---
title: "Quickstart"
description: "Scaffold, edit, and build your first Bartleby site in five minutes."
---

This quickstart walks through scaffolding a new site, writing a post, and producing the rendered HTML output.

## Step 1: Create a site

```bash
bartleby new site mysite
cd mysite
```

The `new site` command lays down the standard project skeleton:

```
mysite/
├── bartleby.yml
├── .authors.yml
├── content/
│   ├── index.md
│   └── blog/
│       └── posts/
├── templates/
├── static/
└── hooks/
```

The generated `bartleby.yml` sets up a single `blog` content type with `readtime` enabled and an `<!-- more -->` excerpt separator.

## Step 2: Write a post

```bash
bartleby new post "Hello World" --type blog
```

This creates `content/blog/posts/hello-world.md` with a front-matter stub:

```markdown
---
title: "Hello World"
date: 2026-06-02
draft: true
---

Write something here.
```

Open the file and replace the body with whatever you want. Set `draft: false` when you're ready to publish.

## Step 3: Build the site

```bash
bartleby build
```

Bartleby renders every page to `site/`:

```
mysite/site/
├── index.html
├── blog/
│   └── posts/
│       └── hello-world/
│           ├── index.html
│           └── index.md          # Markdown variant for LLMs
├── search/
│   └── search_index.json
├── blog/
│   └── feed.xml
├── sitemap.xml
├── robots.txt
├── llms.txt
└── llms-full.txt
```

## Step 4: Validate before building (optional)

If you want to check the config and front matter without rendering:

```bash
bartleby validate
```

This catches missing required metadata fields, unknown author keys, and undefined taxonomy references early.

## Step 5: Preview locally

Bartleby ships with a development server that watches for content changes:

```bash
bartleby serve
```

Then open <http://127.0.0.1:8000/> in your browser.

## What's next

- Read the [Concepts](concepts/index.md) pages to understand Bartleby's model of content, URLs, and templates.
- Browse the [Guides](guides/index.md) for task-oriented walkthroughs.
- Use the [Reference](reference/index.md) for exhaustive configuration and API details.
