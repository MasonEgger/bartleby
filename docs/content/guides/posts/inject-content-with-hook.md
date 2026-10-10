---
title: "Inject Content with a Hook"
description: "Use the on_page_markdown hook to transform content before rendering."
date: 2026-06-02
audience: plugin-author
tags:
  - hooks
  - plugins
authors:
  - mason
---

Sometimes you want to inject content into every page without touching the source files.
A sponsor banner on the home page, an "edit this page" link in the footer, and a deprecation notice on old posts are all examples.
The `on_page_markdown` hook is the right tool.

<!-- more -->

## Step 1: Create the Hook

Create `hooks/inject_banner.py` with an `on_page_markdown` function:

```python
# hooks/inject_banner.py

def on_page_markdown(markdown, page, config):
    if page.output_url == "/":
        banner = (
            "> :warning: This documentation covers the development version. "
            "[See stable docs.](https://stable.example.com/)\n\n"
        )
        return banner + markdown
    return markdown
```

## Step 2: Build

```bash
bartleby build
```

The hook fires once per page, right after shortcodes run and before Python-Markdown renders the source.
Returning a string replaces the working source.
Returning `None` leaves it untouched.

## Step 3: Inject Conditionally

The hook receives the full `Page` object, so any front matter field or URL is available:

```python
import datetime

def on_page_markdown(markdown, page, config):
    if page.date and page.date < datetime.date(2024, 1, 1):
        notice = (
            "> :warning: This post is from 2023 or earlier "
            "and may be out of date.\n\n"
        )
        return notice + markdown
    return markdown
```

If several hooks transform `on_page_markdown`, set their order with `@event_priority`.
The [plugin hook reference](../../reference/pages/plugin-hooks.md#priority-ordering) shows how.

## See Also

- [Plugins and hooks](../../concepts/plugins-and-hooks.md): the discovery model
- [Plugin hook events](../../reference/pages/plugin-hooks.md): the full event list
