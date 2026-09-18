# ABOUTME: Tests for SEO meta tag generation.
# Covers Open Graph, Twitter Card, canonical URL, and fallback behaviour.

from __future__ import annotations

import datetime
from pathlib import Path

from bartleby.config import SiteConfig
from bartleby.content import Page
from bartleby.seo import (
    generate_all_meta_tags,
    generate_canonical_url,
    generate_og_tags,
    generate_twitter_tags,
)


def _page(
    *,
    source: str = "blog/posts/p.md",
    title: str = "Post",
    description: str | None = None,
    date: datetime.date | None = None,
    content_type_name: str | None = "blog",
) -> Page:
    page = Page(
        source_path=Path(source),
        abs_source_path=Path("/abs") / source,
        title=title,
        description=description,
        date=date,
        content_type_name=content_type_name,
    )
    page.output_url = "/" + source.removesuffix(".md") + "/"
    return page


def _site(*, default_image: str | None = None, twitter: str | None = None) -> SiteConfig:
    return SiteConfig(
        title="Site",
        url="https://example.com",
        description="Site description",
        default_image=default_image,
        twitter=twitter,
    )


def test_og_tags_from_page_data() -> None:
    """Open Graph tags reflect the page's title, description, and image."""
    page = _page(description="page-desc")
    page.custom_metadata["image"] = "/img/cover.png"
    tags = generate_og_tags(page, _site())
    assert tags["og:title"] == "Post"
    assert tags["og:description"] == "page-desc"
    assert tags["og:image"].endswith("/img/cover.png")


def test_og_type_article_for_posts() -> None:
    """Pages tied to a content type get ``og:type=article``."""
    tags = generate_og_tags(_page(content_type_name="blog"), _site())
    assert tags["og:type"] == "article"


def test_og_type_website_for_pages() -> None:
    """Pages outside any content type get ``og:type=website``."""
    tags = generate_og_tags(_page(content_type_name=None), _site())
    assert tags["og:type"] == "website"


def test_twitter_card_tags() -> None:
    """Twitter Card tags include card, title, description, and image."""
    page = _page(description="page-desc")
    page.custom_metadata["image"] = "/img/cover.png"
    tags = generate_twitter_tags(page, _site())
    assert tags["twitter:card"] == "summary_large_image"
    assert tags["twitter:title"] == "Post"
    assert tags["twitter:description"] == "page-desc"
    assert tags["twitter:image"].endswith("/img/cover.png")


def test_canonical_url() -> None:
    """Canonical URL combines ``site.url`` with the page's ``output_url``."""
    url = generate_canonical_url(_page(), _site())
    assert url == "https://example.com/blog/posts/p/"


def test_fallback_to_site_defaults() -> None:
    """Missing page fields fall back to site-wide defaults."""
    page = _page(description=None)
    tags = generate_og_tags(page, _site(default_image="/img/default.png"))
    assert tags["og:description"] == "Site description"
    assert tags["og:image"].endswith("/img/default.png")


def test_article_tags() -> None:
    """Article-typed pages with dates expose ``article:published_time``."""
    page = _page(date=datetime.date(2026, 3, 1), content_type_name="blog")
    tags = generate_og_tags(page, _site())
    assert tags["article:published_time"] == "2026-03-01"


def test_twitter_handle_included() -> None:
    """When ``site.twitter`` is configured, ``twitter:site`` is emitted."""
    tags = generate_twitter_tags(_page(), _site(twitter="@bartleby"))
    assert tags["twitter:site"] == "@bartleby"


def test_generate_all_meta_tags_shape() -> None:
    """``generate_all_meta_tags`` exposes ``og``, ``twitter``, and ``canonical`` keys."""
    payload = generate_all_meta_tags(_page(), _site())
    assert "og" in payload
    assert "twitter" in payload
    assert "canonical" in payload
