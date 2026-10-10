---
title: "Agent Integration"
description: "Why every page ships as Markdown and JSON-LD alongside HTML, and how agents discover the rest."
---

Bartleby treats AI agents as a first-class audience.
Bartleby publishes every page in more than one format, so the same URL serves browsers, LLM crawlers, and structured-data consumers.
The site also describes itself in machine-readable files, and the CLI gives coding agents the same view from the terminal.

## Per-Page Formats

Each published page gets two extra representations next to its HTML:

- `index.md` holds the page's Markdown body, without front matter, for LLM crawlers.
- A `<script type="application/ld+json">` block in the HTML head carries schema.org structured data.

The JSON-LD type is `Article` for pages that belong to a content type, with `datePublished` taken from the page date.
Static pages get `WebPage`.
Every block carries `headline`, `description`, and `url`.
The `jsonld.html` partial in the `base` theme emits the block.

## Site-Wide Files

The site root carries four files that describe the whole site:

- `llms.txt` is a site overview.
  It lists one link to the Markdown variant of each page, grouped by content type, plus links to the two JSON files below.
- `llms-full.txt` concatenates the Markdown body of every page, each under a `---` separator with its title, URL, and date.
- `schema.json` is a manifest of the site: its identity, the schema of each content type, the taxonomies and their terms, the public author list, and the locations of the sitemap, `llms.txt`, `content-index.json`, and feeds.
- `content-index.json` has one entry for every published page, with its title, content type, date, authors, taxonomy terms, custom metadata fields, HTML URL, and Markdown URL.

An agent can read `schema.json` to learn what kinds of content exist and which fields they need.
It can read `content-index.json` to find existing pages before it writes a new one.
Both files keep to the fields that describe content, and leave out build mechanics such as the template and the draft flag.

## Commands for Agents

The site-wide files are static.
The CLI answers the same questions live, and every command takes `--output json`:

- `bartleby schema` prints the schema of a content type, the authors, or the taxonomies.
  It uses the same derivation as `schema.json`, so the two agree.
- `bartleby content list` and `bartleby content get` query the pages.
- `bartleby render` renders one file for fast feedback.
- `bartleby export` writes the published content as JSONL, JSON, or CSV.
- `bartleby lint` checks content quality.
- `bartleby generate-skill` writes agent skills, described next.

The [CLI reference](../reference/pages/cli.md) lists every flag.

## Generated Skills

`bartleby generate-skill` writes three Markdown skill files from the shape of your site: `bartleby-write`, `bartleby-review`, and `bartleby-ops`.
The write and review skills list each content type with its required and optional fields.
They also list the authors and the taxonomy terms already in use.
The ops skill lists the commands for building, validating, querying, and exporting.

Generation is deterministic.
The same config and content always produce byte-identical files, with no language model, content analysis, or network call involved.
Voice, audience, and constraints appear in the skills only when you declare them under `ai.agent_context`.

## Publishing and Crawling Are Separate Decisions

Three toggles under `ai` control what Bartleby publishes: `llms_txt`, `llms_full_txt`, and `markdown_variants`.
A fourth, `agent_surface`, controls `schema.json` and `content-index.json`.
Whether crawlers may index the site is a different decision, and `robots.txt` handles it.
Keeping the two apart lets you publish `llms.txt` for agents that act on a person's request while still blocking opportunistic crawlers.
The [crawler directives guide](../guides/posts/ai-crawler-directives.md) shows how.

## Why This Is in the Core

An agent that visits a Bartleby site does not need to parse JavaScript-rendered HTML.
It can fetch `/llms.txt` for the site map and `/<url>/index.md` for clean Markdown.
It can also parse the embedded JSON-LD for metadata.
Human readers get the polished HTML, and agents get the same content in a format that costs fewer tokens to read.

That pillar of the design explains why Bartleby builds these features into the core and does not leave them to plugins.
The [configuration reference](../reference/pages/configuration.md#ai) lists every `ai` key.
