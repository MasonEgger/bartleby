---
title: "Inject content with a hook"
description: "Use the on_page_markdown hook to transform content before rendering."
date: 2026-06-02
audience: plugin-author
tags:
  - hooks
  - plugins
authors:
  - mason
---

Sometimes you want to inject content into every page without touching the source files — a sponsor banner on the home page, an "edit this page" link in the footer, a deprecation notice on old posts. The `on_page_markdown` hook is the right tool.

<!-- more -->

## Step 1: Create the hook

```python
# hooks/inject_banner.py

def on_page_markdown(markdown, page, config):
    if page.output_url == "/":
        banner = "> :warning: This documentation covers the development version. [See stable docs.](https://stable.example.com/)\n\n"
        return banner + markdown
    return markdown
```

## Step 2: Build

```bash
bartleby build
```

The hook fires once per page, immediately before the markdown is handed to Python-Markdown. Returning a modified string replaces the working source; returning `None` leaves it untouched.

## Conditional injection

The hook receives the full `Page` object, so any front matter or URL is available:

```python
import datetime

def on_page_markdown(markdown, page, config):
    if page.date and page.date < datetime.date(2024, 1, 1):
        notice = "> :warning: This post is from 2023 or earlier and may be out of date.\n\n"
        return notice + markdown
    return markdown
```

## Ordering with @event_priority

If multiple hooks transform `on_page_markdown`, control the order with `@event_priority`. Higher priority runs first.

```python
from bartleby.plugins import event_priority

@event_priority(50)
def on_page_markdown(markdown, page, config):
    # Runs before any unprioritised handler.
    return markdown.replace("YEAR", "2026")
```

## See also

- [Plugins and hooks](../../concepts/plugins-and-hooks.md) — discovery model and priorities
- [Plugin hook events](../../reference/pages/plugin-hooks.md) — full event catalogue
