---
title: "Override a single theme template"
description: "Replace the bundled header partial without forking the whole theme."
date: 2026-06-02
audience: existing-user
tags:
  - theme
  - templates
authors:
  - mason
---

The built-in theme ships with a `partials/header.html` that renders the site title, primary navigation, and (when enabled) a dark-mode toggle. You can replace it with your own without touching anything else in the theme.

<!-- more -->

## Step 1: Create the override

Drop a file at `overrides/partials/header.html` in your project root:

```
mysite/
├── bartleby.yml
├── content/
└── overrides/
    └── partials/
        └── header.html
```

## Step 2: Write the replacement

Bartleby's template lookup checks `overrides/` before the bundled theme. Any template you put under `overrides/` with a matching path wins. Your replacement gets the same template context — `site`, `page`, `nav`, `config`, etc.

```html
<header class="my-custom-header">
  <a href="/" class="site-brand">{{ site.title }}</a>
  <nav>
    <ul>
      {% for item in nav %}
      <li><a href="{{ item.url }}">{{ item.title }}</a></li>
      {% endfor %}
    </ul>
  </nav>
</header>
```

## Step 3: Build

```bash
bartleby build
```

Every page in the rendered output now uses your header. No other theme files changed.

## When to use overrides vs. templates

- **`overrides/`** is for replacing theme chrome (header, footer, base, SEO partials). It mirrors the bundled theme's file layout.
- **`templates/`** is for content-type layouts (`templates/blog/post.html`) and site-wide defaults (`templates/defaults/page.html`).

Both win over the bundled theme; the difference is intent. See [Templates and the lookup cascade](../../concepts/templates.md) for the full search order.
