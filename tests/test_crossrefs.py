# ABOUTME: Tests for cross-reference link resolution and validation.
# Rewrites .md hrefs, preserves absolute/anchor links, and detects broken targets.

from __future__ import annotations

from pathlib import Path

from bartleby.content import Page
from bartleby.crossrefs import (
    CrossRefError,
    resolve_all_crossrefs,
    resolve_page_crossrefs,
)


def _page(source: str, output_url: str) -> Page:
    page = Page(
        source_path=Path(source),
        abs_source_path=Path("/abs") / source,
        title=source,
    )
    page.output_url = output_url
    return page


def test_md_link_rewritten() -> None:
    """A relative ``.md`` link is rewritten to the target page's output URL."""
    current = _page("blog/posts/my-post.md", "/blog/posts/my-post/")
    target = _page("tutorials/posts/deploy.md", "/tutorials/posts/deploy/")
    html = '<a href="../../tutorials/posts/deploy.md">deploy</a>'
    new_html, errors = resolve_page_crossrefs(html, current, [current, target], Path("/content"))
    assert errors == []
    assert 'href="/tutorials/posts/deploy/"' in new_html


def test_absolute_url_unchanged() -> None:
    """An absolute URL is left untouched."""
    current = _page("blog/posts/my-post.md", "/blog/posts/my-post/")
    html = '<a href="https://example.com">ex</a>'
    new_html, errors = resolve_page_crossrefs(html, current, [current], Path("/content"))
    assert new_html == html
    assert errors == []


def test_anchor_link_unchanged() -> None:
    """A bare anchor (``#section``) is left untouched."""
    current = _page("blog/posts/my-post.md", "/blog/posts/my-post/")
    html = '<a href="#section">jump</a>'
    new_html, errors = resolve_page_crossrefs(html, current, [current], Path("/content"))
    assert new_html == html
    assert errors == []


def test_non_md_link_unchanged() -> None:
    """A relative non-``.md`` link (e.g. PDF) is left untouched."""
    current = _page("blog/posts/my-post.md", "/blog/posts/my-post/")
    html = '<a href="slides.pdf">slides</a>'
    new_html, errors = resolve_page_crossrefs(html, current, [current], Path("/content"))
    assert new_html == html
    assert errors == []


def test_broken_link_detected() -> None:
    """A ``.md`` link with no matching page produces a CrossRefError."""
    current = _page("blog/posts/my-post.md", "/blog/posts/my-post/")
    html = '<a href="missing.md">missing</a>'
    _new, errors = resolve_page_crossrefs(html, current, [current], Path("/content"))
    assert len(errors) == 1
    assert isinstance(errors[0], CrossRefError)
    assert "missing.md" in errors[0].target_path
    assert errors[0].source_path == "blog/posts/my-post.md"


def test_md_link_with_anchor() -> None:
    """``other.md#section`` becomes ``<url>#section`` after rewriting."""
    current = _page("blog/posts/my-post.md", "/blog/posts/my-post/")
    target = _page("about.md", "/about/")
    html = '<a href="../../about.md#mission">about</a>'
    new_html, errors = resolve_page_crossrefs(html, current, [current, target], Path("/content"))
    assert errors == []
    assert 'href="/about/#mission"' in new_html


def test_resolve_all_crossrefs() -> None:
    """``resolve_all_crossrefs`` rewrites HTML on each page and aggregates errors."""
    a = _page("blog/posts/a.md", "/blog/posts/a/")
    b = _page("blog/posts/b.md", "/blog/posts/b/")
    a.rendered_content = '<a href="b.md">b</a>'
    b.rendered_content = '<a href="missing.md">missing</a>'
    errors = resolve_all_crossrefs([a, b], Path("/content"))
    assert 'href="/blog/posts/b/"' in a.rendered_content
    assert len(errors) == 1
    assert errors[0].source_path == "blog/posts/b.md"


def test_index_md_link() -> None:
    """A link to ``../../about.md`` from nested content resolves to the right URL."""
    current = _page("blog/posts/my-post.md", "/blog/posts/my-post/")
    target = _page("about.md", "/about/")
    html = '<a href="../../about.md">about</a>'
    new_html, errors = resolve_page_crossrefs(html, current, [current, target], Path("/content"))
    assert errors == []
    assert 'href="/about/"' in new_html
