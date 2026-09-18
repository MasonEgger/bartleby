---
title: "Configure AI crawler directives"
description: "Allow or block specific AI bots from indexing your site via robots.txt."
date: 2026-06-02
audience: new-user
tags:
  - ai
  - configuration
authors:
  - mason
---

Bartleby's `robots.txt` is auto-generated and includes per-bot Allow/Disallow directives sourced from `bartleby.yml`. This guide covers the common patterns: allow only specific bots, block specific bots, or opt out of AI training entirely.

<!-- more -->

## The default

Without any `ai.robots` config, Bartleby's `robots.txt` is permissive:

```
User-agent: *
Allow: /

Sitemap: https://example.com/sitemap.xml
```

## Block specific bots

To block one or more AI crawlers entirely:

```yaml
# bartleby.yml
ai:
  robots:
    disallow:
      - GPTBot
      - ClaudeBot
      - PerplexityBot
```

This appends:

```
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: PerplexityBot
Disallow: /
```

## Allow specific bots explicitly

The default `User-agent: *` already allows everyone. An explicit allow directive is only meaningful when you've blocked the bot globally elsewhere:

```yaml
ai:
  robots:
    allow:
      - GPTBot
```

## Use a static override

If you need finer control than the config exposes — custom `Crawl-delay` directives, per-path Allow/Disallow rules — drop a hand-written `robots.txt` into `static/`:

```
mysite/
└── static/
    └── robots.txt
```

Bartleby detects the override and skips generating one. The static file copies through to `site/robots.txt` unmodified.

## Why this matters

The `ai.robots` config sits next to the `llms_txt`, `llms_full_txt`, and `markdown_variants` toggles. Whether you publish for AI consumption is one decision; whether you allow crawlers to index your site is another. Bartleby treats them independently so you can publish llms.txt for human-directed agent queries while still blocking opportunistic crawlers.

## See also

- [Agent integration](../../concepts/agents-and-llms.md) — the design pillar behind these features
- [bartleby.yml configuration](../../reference/pages/configuration.md#ai) — full `ai` config block
