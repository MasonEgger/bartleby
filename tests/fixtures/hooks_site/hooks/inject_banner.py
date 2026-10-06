# ABOUTME: Sample hook that prepends a banner to the homepage markdown.
# Used by tests/test_plugins.py to verify hooks/*.py discovery.


def on_page_markdown(markdown, page, config):  # type: ignore[no-untyped-def]
    if getattr(page, "output_url", "") == "/":
        return f"# Banner!\n\n{markdown}"
    return markdown
