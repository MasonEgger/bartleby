# ABOUTME: Tests for URL generation from page data and content type config.
# Covers path-based defaults, url_format placeholders, overrides, and batch generation.

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from bartleby.config import (
    AIConfig,
    BartlebyConfig,
    ContentTypeConfig,
    DevServerConfig,
    PaginationConfig,
    SiteConfig,
    TaxonomyConfig,
    ThemeConfig,
)
from bartleby.content import Page
from bartleby.urls import generate_all_urls, generate_url


def _page(
    *,
    source: str,
    title: str = "Sample",
    date: datetime.date | None = None,
    slug_override: str | None = None,
    url_override: str | None = None,
    url_base_override: str | None = None,
    content_type_name: str | None = None,
    taxonomy_values: dict[str, list[str]] | None = None,
) -> Page:
    return Page(
        source_path=Path(source),
        abs_source_path=Path("/abs") / source,
        title=title,
        date=date,
        slug_override=slug_override,
        url_override=url_override,
        url_base_override=url_base_override,
        content_type_name=content_type_name,
        taxonomy_values=taxonomy_values or {},
    )


def _content_type(
    *,
    name: str = "blog",
    path: str = "blog/posts",
    url_base: str | None = None,
    url_format: str | None = None,
) -> ContentTypeConfig:
    return ContentTypeConfig(
        name=name,
        path=path,
        url_base=url_base,
        url_format=url_format,
        pagination=PaginationConfig(),
    )


def test_path_based_default() -> None:
    """Top-level pages mirror their source path under content/."""
    page = _page(source="about.md")
    assert generate_url(page, None) == "/about/"


def test_path_based_nested() -> None:
    """Nested pages without a content type keep the directory structure."""
    page = _page(source="blog/posts/my-post.md")
    assert generate_url(page, None) == "/blog/posts/my-post/"


def test_path_based_index() -> None:
    """``index.md`` inside a section becomes the section's URL."""
    page = _page(source="blog/index.md")
    assert generate_url(page, None) == "/blog/"


def test_root_index() -> None:
    """The top-level ``index.md`` is the site root."""
    page = _page(source="index.md")
    assert generate_url(page, None) == "/"


def test_url_format_date_slug() -> None:
    """``url_format`` substitutes ``{slug}`` and a strftime-style ``{date:...}`` placeholder."""
    page = _page(
        source="blog/posts/my-post.md",
        date=datetime.date(2026, 3, 1),
        content_type_name="blog",
    )
    ctype = _content_type(url_format="{date:%Y/%m/%d}/{slug}")
    url = generate_url(page, ctype)
    assert "2026/03/01/my-post" in url


def test_url_base_overrides_path() -> None:
    """``url_base`` replaces the content type path when building the URL."""
    page = _page(
        source="blog/posts/my-post.md",
        date=datetime.date(2026, 3, 1),
        content_type_name="blog",
    )
    ctype = _content_type(url_base="blog", url_format="{date:%Y/%m/%d}/{slug}")
    assert generate_url(page, ctype) == "/blog/2026/03/01/my-post/"


def test_url_base_without_format() -> None:
    """``url_base`` without ``url_format`` falls back to ``{url_base}/{slug}``."""
    page = _page(source="blog/posts/my-post.md", content_type_name="blog")
    ctype = _content_type(url_base="blog")
    assert generate_url(page, ctype) == "/blog/my-post/"


def test_per_page_url_override() -> None:
    """Front-matter ``url`` short-circuits all other URL logic."""
    page = _page(source="blog/posts/my-post.md", url_override="custom/path")
    assert generate_url(page, _content_type()) == "/custom/path/"


def test_per_page_url_base_override() -> None:
    """Front-matter ``url_base`` swaps the prefix but keeps ``url_format``."""
    page = _page(
        source="blog/posts/my-post.md",
        date=datetime.date(2026, 3, 1),
        url_base_override="articles",
        content_type_name="blog",
    )
    ctype = _content_type(url_base="blog", url_format="{date:%Y/%m/%d}/{slug}")
    assert generate_url(page, ctype) == "/articles/2026/03/01/my-post/"


def test_slug_from_filename() -> None:
    """Without a front-matter slug, the URL slug derives from the filename stem."""
    page = _page(source="blog/posts/My Cool Post.md", content_type_name="blog")
    ctype = _content_type(url_format="{slug}")
    assert generate_url(page, ctype) == "/my-cool-post/"


def test_slug_from_front_matter() -> None:
    """Front-matter ``slug`` overrides the filename-derived slug."""
    page = _page(
        source="blog/posts/whatever.md",
        slug_override="custom-slug",
        content_type_name="blog",
    )
    ctype = _content_type(url_format="{slug}")
    assert generate_url(page, ctype) == "/custom-slug/"


def test_categories_placeholder() -> None:
    """``{categories}`` substitutes the first category slug from taxonomy_values."""
    page = _page(
        source="blog/posts/my-post.md",
        content_type_name="blog",
        taxonomy_values={"categories": ["Tools & Tips"]},
    )
    ctype = _content_type(url_format="{categories}/{slug}")
    assert generate_url(page, ctype) == "/tools-and-tips/my-post/"


def test_title_placeholder() -> None:
    """``{title}`` substitutes the slugified page title."""
    page = _page(
        source="blog/posts/whatever.md",
        title="My Great Title",
        content_type_name="blog",
    )
    ctype = _content_type(url_format="{title}")
    assert generate_url(page, ctype) == "/my-great-title/"


def test_trailing_slash_always_added() -> None:
    """Every generated URL ends with a single ``/``."""
    page = _page(source="blog/posts/my-post.md", url_override="custom/path")
    assert generate_url(page, None).endswith("/")
    page2 = _page(source="about.md")
    assert generate_url(page2, None).endswith("/")


def test_generate_urls_for_all_pages() -> None:
    """``generate_all_urls`` populates ``output_url`` on every page in place."""
    pages = [
        _page(source="about.md"),
        _page(source="blog/posts/post.md", content_type_name="blog"),
    ]
    config = BartlebyConfig(
        site=SiteConfig(title="t", url="u"),
        nav=None,
        theme=ThemeConfig(),
        authors_file=".authors.yml",
        content_types={"blog": _content_type()},
        taxonomies={"tags": TaxonomyConfig(name="tags", slug_format="{slug}")},
        exclude_patterns=[],
        markdown_extensions=[],
        plugins=[],
        extra_css=[],
        extra_js=[],
        ai=AIConfig(),
        dev_server=DevServerConfig(),
        config_dir=Path("/tmp"),
    )
    generate_all_urls(pages, config)
    assert pages[0].output_url == "/about/"
    assert pages[1].output_url == "/blog/posts/post/"


def test_missing_date_with_date_format_raises() -> None:
    """A ``url_format`` referencing ``{date}`` raises when the page has no date."""
    page = _page(source="blog/posts/my-post.md", content_type_name="blog")
    ctype = _content_type(url_format="{date:%Y/%m/%d}/{slug}")
    with pytest.raises(ValueError) as exc:
        generate_url(page, ctype)
    assert "date" in str(exc.value).lower()
