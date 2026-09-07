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
    FeedConfig,
    PaginationConfig,
    SiteConfig,
    TaxonomyConfig,
    ThemeConfig,
)
from bartleby.content import Page
from bartleby.feeds import (
    compute_aggregate_types,
    feed_links_for_page,
    generate_aggregate_atom,
    generate_aggregate_rss,
    generate_atom,
    generate_feeds,
    generate_rss,
)


def _post(
    *,
    source: str,
    title: str,
    date: datetime.date,
    html: str = "<p>body</p>",
    content_type: str = "blog",
) -> Page:
    page = Page(
        source_path=Path(source),
        abs_source_path=Path("/abs") / source,
        title=title,
        date=date,
        content_type_name=content_type,
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


def _multi_config(
    *,
    blog_feeds: list[str] | None = None,
    news_feeds: list[str] | None = None,
    feed: FeedConfig | None = None,
) -> BartlebyConfig:
    """A config with a ``blog`` and a ``news`` content type plus a ``site.feed``."""
    return BartlebyConfig(
        site=SiteConfig(
            title="Site",
            url="https://example.com",
            description="Site desc",
            feed=feed if feed is not None else FeedConfig(),
        ),
        nav=None,
        theme=ThemeConfig(),
        authors_file=".authors.yml",
        content_types={
            "blog": ContentTypeConfig(
                name="blog",
                path="blog/posts",
                pagination=PaginationConfig(),
                feeds=blog_feeds if blog_feeds is not None else ["rss", "atom"],
            ),
            "news": ContentTypeConfig(
                name="news",
                path="news/posts",
                pagination=PaginationConfig(),
                feeds=news_feeds if news_feeds is not None else ["rss", "atom"],
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


def _mixed_posts() -> list[Page]:
    """A blog post and a news post on different dates."""
    return [
        _post(
            source="blog/posts/b.md",
            title="Blog post",
            date=datetime.date(2026, 3, 1),
            content_type="blog",
        ),
        _post(
            source="news/posts/n.md",
            title="News post",
            date=datetime.date(2026, 4, 1),
            content_type="news",
        ),
    ]


def test_aggregate_scope_empty_include_covers_all_feed_types() -> None:
    """An empty ``include`` aggregates every content type that has feeds enabled."""
    config = _multi_config(feed=FeedConfig(include=[]))
    assert compute_aggregate_types(config) == ["blog", "news"]


def test_aggregate_scope_empty_include_excludes_feedless_types() -> None:
    """A content type with no feeds of its own stays out of the empty-include aggregate."""
    config = _multi_config(news_feeds=[], feed=FeedConfig(include=[]))
    assert compute_aggregate_types(config) == ["blog"]


def test_aggregate_scope_non_empty_include_restricts() -> None:
    """A non-empty ``include`` restricts the aggregate to exactly those types."""
    config = _multi_config(feed=FeedConfig(include=["news"]))
    assert compute_aggregate_types(config) == ["news"]


def test_aggregate_merges_sorts_and_caps() -> None:
    """Items merge across types, sort date-descending, and truncate to ``limit``."""
    older = _post(
        source="blog/posts/old.md",
        title="Old",
        date=datetime.date(2026, 1, 1),
        content_type="blog",
    )
    middle = _post(
        source="news/posts/mid.md",
        title="Mid",
        date=datetime.date(2026, 2, 1),
        content_type="news",
    )
    newer = _post(
        source="blog/posts/new.md",
        title="New",
        date=datetime.date(2026, 3, 1),
        content_type="blog",
    )
    config = _multi_config(feed=FeedConfig(limit=2))
    xml = generate_aggregate_rss([older, newer, middle], config)
    titles = [item.findtext("title") for item in ET.fromstring(xml).findall("channel/item")]
    assert titles == ["New", "Mid"]


def test_aggregate_item_carries_source_category() -> None:
    """Each aggregate item carries a ``<category>`` naming its source content type."""
    config = _multi_config(feed=FeedConfig())
    xml = generate_aggregate_rss(_mixed_posts(), config)
    root = ET.fromstring(xml)
    by_title = {
        item.findtext("title"): item.findtext("category") for item in root.findall("channel/item")
    }
    assert by_title["Blog post"] == "blog"
    assert by_title["News post"] == "news"


def test_aggregate_atom_item_carries_category() -> None:
    """The Atom aggregate tags each entry with its source content type."""
    config = _multi_config(feed=FeedConfig())
    xml = generate_aggregate_atom(_mixed_posts(), config)
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml)
    terms: set[str | None] = set()
    for entry in root.findall("atom:entry", namespace):
        category = entry.find("atom:category", namespace)
        assert category is not None
        terms.add(category.get("term"))
    assert terms == {"blog", "news"}


def test_aggregate_feeds_written_at_root(tmp_path: Path) -> None:
    """``/feed.xml`` and ``/atom.xml`` land at the output root per ``formats``."""
    config = _multi_config(feed=FeedConfig(formats=["rss", "atom"]))
    generate_feeds(_mixed_posts(), config, tmp_path)
    assert (tmp_path / "feed.xml").exists()
    assert (tmp_path / "atom.xml").exists()


def test_aggregate_formats_respected(tmp_path: Path) -> None:
    """Only the formats listed in ``site.feed.formats`` are written at the root."""
    config = _multi_config(feed=FeedConfig(formats=["rss"]))
    generate_feeds(_mixed_posts(), config, tmp_path)
    assert (tmp_path / "feed.xml").exists()
    assert not (tmp_path / "atom.xml").exists()


def test_aggregate_disabled_writes_nothing(tmp_path: Path) -> None:
    """``site.feed.enabled: false`` writes no root-level aggregate files."""
    config = _multi_config(feed=FeedConfig(enabled=False))
    generate_feeds(_mixed_posts(), config, tmp_path)
    assert not (tmp_path / "feed.xml").exists()
    assert not (tmp_path / "atom.xml").exists()


def test_aggregate_title_defaults_to_site_title() -> None:
    """The aggregate channel title falls back to ``site.title`` when unset."""
    config = _multi_config(feed=FeedConfig())
    xml = generate_aggregate_rss(_mixed_posts(), config)
    assert ET.fromstring(xml).findtext("channel/title") == "Site"


def test_aggregate_title_override() -> None:
    """An explicit ``site.feed.title`` becomes the aggregate channel title."""
    config = _multi_config(feed=FeedConfig(title="Firehose"))
    xml = generate_aggregate_rss(_mixed_posts(), config)
    assert ET.fromstring(xml).findtext("channel/title") == "Firehose"


def test_feed_links_homepage_advertises_aggregate() -> None:
    """The homepage (no content type) advertises only the aggregate feed."""
    config = _multi_config(feed=FeedConfig(formats=["rss", "atom"]))
    home = _post(source="index.md", title="Home", date=datetime.date(2026, 1, 1))
    home.content_type_name = None
    home.output_url = "/"
    links = feed_links_for_page(home, config)
    hrefs = [link["href"] for link in links]
    assert "/feed.xml" in hrefs
    assert "/atom.xml" in hrefs
    assert not any("/blog/" in href for href in hrefs)


def test_feed_links_content_type_page_advertises_type_feed_first() -> None:
    """A content-type page advertises its type feed first, the aggregate second."""
    config = _multi_config(feed=FeedConfig(formats=["rss"]))
    post = _post(source="blog/posts/a.md", title="A", date=datetime.date(2026, 1, 1))
    links = feed_links_for_page(post, config)
    hrefs = [link["href"] for link in links]
    assert hrefs[0] == "/blog/feed.xml"
    assert "/feed.xml" in hrefs[1:]


def test_feed_links_omitted_when_aggregate_disabled() -> None:
    """A disabled aggregate is not advertised on the homepage."""
    config = _multi_config(feed=FeedConfig(enabled=False))
    home = _post(source="index.md", title="Home", date=datetime.date(2026, 1, 1))
    home.content_type_name = None
    assert feed_links_for_page(home, config) == []
