# ABOUTME: Tests for RSS and Atom feed generation.
# Covers feed structure, item ordering, absolute URLs, and per-content-type emission.

from __future__ import annotations

import datetime
import xml.etree.ElementTree as ET
from pathlib import Path

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
from bartleby.feeds import generate_atom, generate_feeds, generate_rss


def _post(*, source: str, title: str, date: datetime.date, html: str = "<p>body</p>") -> Page:
    page = Page(
        source_path=Path(source),
        abs_source_path=Path("/abs") / source,
        title=title,
        date=date,
        content_type_name="blog",
        description=f"{title} description",
    )
    page.output_url = "/" + source.removesuffix(".md") + "/"
    page.rendered_content = html
    page.excerpt = f"{title} excerpt"
    return page


def _config(*, feeds: list[str] | None = None) -> BartlebyConfig:
    return BartlebyConfig(
        site=SiteConfig(title="Site", url="https://example.com", description="Site desc"),
        nav=None,
        theme=ThemeConfig(),
        authors_file=".authors.yml",
        content_types={
            "blog": ContentTypeConfig(
                name="blog",
                path="blog/posts",
                pagination=PaginationConfig(),
                feeds=feeds if feeds is not None else ["rss", "atom"],
            ),
        },
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


def test_rss_valid_xml() -> None:
    """The RSS feed parses cleanly as XML."""
    posts = [_post(source="blog/posts/a.md", title="A", date=datetime.date(2026, 3, 1))]
    xml = generate_rss(posts, "blog", _config().site)
    ET.fromstring(xml)


def test_rss_channel_metadata() -> None:
    """``<channel>`` carries title, link, and description."""
    posts = [_post(source="blog/posts/a.md", title="A", date=datetime.date(2026, 3, 1))]
    xml = generate_rss(posts, "blog", _config().site)
    root = ET.fromstring(xml)
    channel = root.find("channel")
    assert channel is not None
    assert channel.findtext("title")
    assert channel.findtext("link", "").startswith("https://example.com")
    assert channel.findtext("description")


def test_rss_item_fields() -> None:
    """Each ``<item>`` has title, link, description, and pubDate."""
    posts = [_post(source="blog/posts/a.md", title="A", date=datetime.date(2026, 3, 1))]
    xml = generate_rss(posts, "blog", _config().site)
    root = ET.fromstring(xml)
    item = root.find("channel/item")
    assert item is not None
    assert item.findtext("title") == "A"
    assert item.findtext("link", "").startswith("https://example.com")
    assert item.findtext("description")
    assert item.findtext("pubDate")


def test_rss_item_count() -> None:
    """The feed emits one item per post passed in."""
    posts = [
        _post(source=f"blog/posts/p{i}.md", title=f"P{i}", date=datetime.date(2026, 1, i + 1))
        for i in range(3)
    ]
    xml = generate_rss(posts, "blog", _config().site)
    items = ET.fromstring(xml).findall("channel/item")
    assert len(items) == 3


def test_rss_absolute_urls() -> None:
    """Every ``<link>`` in the feed is absolute (uses site.url)."""
    posts = [_post(source="blog/posts/a.md", title="A", date=datetime.date(2026, 3, 1))]
    xml = generate_rss(posts, "blog", _config().site)
    root = ET.fromstring(xml)
    for link in root.iter("link"):
        text = link.text or ""
        assert text.startswith("https://example.com")


def test_atom_valid_xml() -> None:
    """The Atom feed parses cleanly as XML."""
    posts = [_post(source="blog/posts/a.md", title="A", date=datetime.date(2026, 3, 1))]
    xml = generate_atom(posts, "blog", _config().site)
    ET.fromstring(xml)


def test_atom_entry_fields() -> None:
    """Each ``<entry>`` carries title, link, summary, and updated."""
    posts = [_post(source="blog/posts/a.md", title="A", date=datetime.date(2026, 3, 1))]
    xml = generate_atom(posts, "blog", _config().site)
    root = ET.fromstring(xml)
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", namespace)
    assert entry is not None
    assert entry.findtext("atom:title", "", namespace) == "A"
    assert entry.findtext("atom:summary", "", namespace)
    assert entry.findtext("atom:updated", "", namespace)


def test_feed_only_for_configured_types(tmp_path: Path) -> None:
    """A content type without ``feeds`` configured produces no feed files."""
    posts = [_post(source="blog/posts/a.md", title="A", date=datetime.date(2026, 3, 1))]
    generate_feeds(posts, _config(feeds=[]), tmp_path)
    assert not (tmp_path / "blog" / "feed.xml").exists()
    assert not (tmp_path / "blog" / "atom.xml").exists()


def test_rss_feed_path(tmp_path: Path) -> None:
    """RSS feeds land at ``{content_type}/feed.xml``."""
    posts = [_post(source="blog/posts/a.md", title="A", date=datetime.date(2026, 3, 1))]
    generate_feeds(posts, _config(feeds=["rss"]), tmp_path)
    assert (tmp_path / "blog" / "feed.xml").exists()


def test_atom_feed_path(tmp_path: Path) -> None:
    """Atom feeds land at ``{content_type}/atom.xml``."""
    posts = [_post(source="blog/posts/a.md", title="A", date=datetime.date(2026, 3, 1))]
    generate_feeds(posts, _config(feeds=["atom"]), tmp_path)
    assert (tmp_path / "blog" / "atom.xml").exists()


def test_feed_items_reverse_chronological() -> None:
    """Feed items appear newest-first regardless of input order."""
    older = _post(source="blog/posts/old.md", title="Old", date=datetime.date(2026, 1, 1))
    newer = _post(source="blog/posts/new.md", title="New", date=datetime.date(2026, 5, 1))
    xml = generate_rss([older, newer], "blog", _config().site)
    titles = [item.findtext("title") for item in ET.fromstring(xml).findall("channel/item")]
    assert titles == ["New", "Old"]
