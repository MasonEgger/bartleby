---
title: "Agent integration"
description: "Why every page ships as Markdown and JSON-LD alongside HTML."
---

Bartleby treats AI agents as a first-class audience. Every page is published in multiple formats so the same URL serves browsers, LLM crawlers, and structured-data consumers.

## What gets published

For every published page:

- `index.html` — the rendered HTML for browsers
- `index.md` — the raw Markdown variant for LLM crawlers
- `<script type="application/ld+json">` block embedded in the HTML head — schema.org structured data

For the whole site:

- `/llms.txt` — structured site overview with one `- [title](url.md): description` line per published page, grouped by content type
- `/llms-full.txt` — the raw Markdown body of every page concatenated under `---` separators
- `/robots.txt` — references the sitemap and includes per-bot Allow/Disallow directives from config

## Configuration

Every output is gated on a `config.ai` toggle in `bartleby.yml`:

```yaml
ai:
  llms_txt: true
  llms_full_txt: true
  markdown_variants: true
  robots:
    allow:
      - GPTBot
      - Anthropic-User
    disallow:
      - BadBot
```

The defaults publish llms.txt, llms-full.txt, and Markdown variants. Set any toggle to `false` to skip.

## JSON-LD schema

The bundled `partials/jsonld.html` emits `@type=Article` for pages tied to a content type (with `datePublished` derived from `page.date`) and `@type=WebPage` for static pages. Every JSON-LD block carries `headline`, `description`, and `url`.

## Why this matters

When an LLM agent comes across a Bartleby site, it doesn't need to parse JavaScript-rendered HTML or follow redirects through a paywall. It can `GET /llms.txt` for the site map, `GET /<url>/index.md` for clean Markdown content, and (if it wants metadata) parse the embedded JSON-LD. Human readers get the polished HTML; agents get the same content in a format that's cheaper to consume.

This is the design pillar that motivates Bartleby's choice to build features like `llms.txt` and Markdown variants into the core rather than leaving them as a plugin.
