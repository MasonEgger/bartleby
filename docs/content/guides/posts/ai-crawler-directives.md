---
title: "Configure AI Crawler Directives"
description: "Allow or block specific AI bots from indexing your site through robots.txt."
date: 2026-06-02
audience: new-user
tags:
  - ai
  - configuration
authors:
  - mason
---

Bartleby generates `robots.txt` for you and adds per-bot Allow and Disallow directives from `bartleby.yml`.
This guide covers the common patterns: block specific bots, allow specific bots, or take over the file entirely.

<!-- more -->

## The Default

Without any `ai.robots` config, the generated `robots.txt` is permissive:

```
User-agent: *
Allow: /

Sitemap: https://example.com/sitemap.xml
```

## Block Specific Bots

To block one or more AI crawlers entirely, list them under `ai.robots.disallow`:

```yaml
# bartleby.yml
ai:
  robots:
    disallow:
      - GPTBot
      - ClaudeBot
      - PerplexityBot
```

Bartleby appends a block for each bot, just before the `Sitemap` line:

```
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: PerplexityBot
Disallow: /
```

## Allow Specific Bots Explicitly

The default `User-agent: *` group already allows everyone.
An allow entry adds a named group with `Allow: /` for that bot, which records your intent in the file.

```yaml
ai:
  robots:
    allow:
      - GPTBot
```

## Use a Static Override

For finer control, such as `Crawl-delay` directives or per-path rules, put a hand-written `robots.txt` in `static/`:

```
mysite/
└── static/
    └── robots.txt
```

Bartleby detects the file and skips generating one.
The static file copies to `site/robots.txt` unmodified.

## See Also

- [Agent integration](../../concepts/agents-and-llms.md): why publishing for agents and allowing crawlers are separate decisions
- [bartleby.yml configuration](../../reference/pages/configuration.md#ai): every `ai` key
