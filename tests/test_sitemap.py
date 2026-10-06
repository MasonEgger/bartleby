# ABOUTME: Tests for sitemap.xml and robots.txt generation.
# Covers XML validity, absolute URLs, AI crawler directives, and static-override behavior.

from __future__ import annotations

import datetime
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

from bartleby.config import AIConfig, SiteConfig
from bartleby.content import Page
from bartleby.sitemap import (
    generate_robots_txt,
    generate_sitemap,
    write_robots_txt,
    write_sitemap,
)


def _page(*, source: str, date: datetime.date | None = None, draft: bool = False) -> Page:
    page = Page(
        source_path=Path(source),
        abs_source_path=Path("/abs") / source,
        title=source,
        date=date,
        draft=draft,
    )
    page.output_url = "/" + source.removesuffix(".md") + "/"
    return page


def _site() -> SiteConfig:
    return SiteConfig(title="Site", url="https://example.com", description="d")


def test_sitemap_valid_xml() -> None:
    """The sitemap parses as valid XML."""
    xml = generate_sitemap([_page(source="a.md", date=datetime.date(2026, 3, 1))], _site())
    ET.fromstring(xml)


def test_sitemap_includes_all_pages() -> None:
    """All non-draft pages produce a ``<url>`` element."""
    pages = [
        _page(source="a.md", date=datetime.date(2026, 3, 1)),
        _page(source="b.md", date=datetime.date(2026, 4, 1)),
    ]
    xml = generate_sitemap(pages, _site())
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = ET.fromstring(xml).findall("sm:url", namespace)
    assert len(urls) == 2


def test_sitemap_excludes_drafts() -> None:
    """Draft pages are skipped."""
    pages = [
        _page(source="a.md", date=datetime.date(2026, 3, 1)),
        _page(source="b.md", date=datetime.date(2026, 3, 2), draft=True),
    ]
    xml = generate_sitemap(pages, _site())
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = ET.fromstring(xml).findall("sm:url", namespace)
    assert len(urls) == 1


def test_sitemap_has_absolute_urls() -> None:
    """Every ``<loc>`` is an absolute URL rooted at site.url."""
    pages = [_page(source="a.md", date=datetime.date(2026, 3, 1))]
    xml = generate_sitemap(pages, _site())
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [loc.text for loc in ET.fromstring(xml).findall("sm:url/sm:loc", namespace)]
    assert all(loc and loc.startswith("https://example.com") for loc in locs)


def test_sitemap_lastmod() -> None:
    """Pages with dates expose a ``<lastmod>`` element."""
    pages = [_page(source="a.md", date=datetime.date(2026, 3, 1))]
    xml = generate_sitemap(pages, _site())
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    lastmod = ET.fromstring(xml).findtext("sm:url/sm:lastmod", "", namespace)
    assert lastmod == "2026-03-01"


def test_sitemap_gz_generated(tmp_path: Path) -> None:
    """``write_sitemap`` also writes a ``.gz`` next to the XML."""
    pages = [_page(source="a.md", date=datetime.date(2026, 3, 1))]
    write_sitemap(pages, _site(), tmp_path)
    gz_path = tmp_path / "sitemap.xml.gz"
    assert gz_path.exists()
    decompressed = gzip.decompress(gz_path.read_bytes()).decode("utf-8")
    assert "https://example.com" in decompressed


def test_robots_txt_references_sitemap() -> None:
    """robots.txt includes the absolute sitemap URL."""
    text = generate_robots_txt(_site(), AIConfig())
    assert "Sitemap: https://example.com/sitemap.xml" in text


def test_robots_txt_ai_allow() -> None:
    """``ai.robots.allow`` entries become ``User-agent`` + ``Allow: /`` directives."""
    ai = AIConfig(robots={"allow": ["GPTBot"]})
    text = generate_robots_txt(_site(), ai)
    assert "User-agent: GPTBot" in text
    assert "Allow: /" in text


def test_robots_txt_ai_disallow() -> None:
    """``ai.robots.disallow`` entries become ``User-agent`` + ``Disallow: /`` directives."""
    ai = AIConfig(robots={"disallow": ["BadBot"]})
    text = generate_robots_txt(_site(), ai)
    assert "User-agent: BadBot" in text
    assert "Disallow: /" in text


def test_robots_txt_no_ai_config() -> None:
    """With no AI robots entries, robots.txt has only the sitemap line and a default allow."""
    text = generate_robots_txt(_site(), AIConfig())
    assert "User-agent: GPTBot" not in text
    assert "User-agent: *" in text


def test_static_robots_overrides(tmp_path: Path) -> None:
    """If ``static/robots.txt`` is present, ``write_robots_txt`` does not overwrite it."""
    output = tmp_path / "site"
    output.mkdir()
    (output / "robots.txt").write_text("static override")
    write_robots_txt(_site(), AIConfig(), output, static_override_exists=True)
    assert (output / "robots.txt").read_text() == "static override"
