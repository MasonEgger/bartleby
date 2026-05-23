# ABOUTME: RSS 2.0 and Atom 1.0 feed generation per content type.
# Emits feed XML based on content type opt-ins in bartleby.yml.

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from pathlib import Path

    from bartleby.config import BartlebyConfig, SiteConfig
    from bartleby.content import Page


_ATOM_NS = "http://www.w3.org/2005/Atom"


def generate_rss(pages: list[Page], content_type_name: str, site: SiteConfig) -> str:
    """Render an RSS 2.0 feed for ``pages`` belonging to ``content_type_name``."""
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = f"{site.title} — {content_type_name.title()}"
    ET.SubElement(channel, "link").text = _absolute(site.url, f"/{content_type_name}/")
    ET.SubElement(channel, "description").text = site.description or ""

    for page in _sorted_pages(pages):
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = page.title
        ET.SubElement(item, "link").text = _absolute(site.url, page.output_url)
        ET.SubElement(item, "description").text = page.excerpt or page.description or ""
        if page.date is not None:
            ET.SubElement(item, "pubDate").text = _rfc822(page.date)
    return _serialise(rss)


def generate_atom(pages: list[Page], content_type_name: str, site: SiteConfig) -> str:
    """Render an Atom 1.0 feed for ``pages`` belonging to ``content_type_name``."""
    feed = ET.Element(f"{{{_ATOM_NS}}}feed")
    ET.SubElement(
        feed, f"{{{_ATOM_NS}}}title"
    ).text = f"{site.title} — {content_type_name.title()}"
    ET.SubElement(feed, f"{{{_ATOM_NS}}}id").text = _absolute(site.url, f"/{content_type_name}/")
    ET.SubElement(
        feed,
        f"{{{_ATOM_NS}}}link",
        href=_absolute(site.url, f"/{content_type_name}/atom.xml"),
        rel="self",
    )
    ET.SubElement(feed, f"{{{_ATOM_NS}}}updated").text = _atom_updated_now()

    for page in _sorted_pages(pages):
        entry = ET.SubElement(feed, f"{{{_ATOM_NS}}}entry")
        ET.SubElement(entry, f"{{{_ATOM_NS}}}title").text = page.title
        ET.SubElement(
            entry,
            f"{{{_ATOM_NS}}}link",
            href=_absolute(site.url, page.output_url),
            rel="alternate",
        )
        ET.SubElement(entry, f"{{{_ATOM_NS}}}id").text = _absolute(site.url, page.output_url)
        ET.SubElement(entry, f"{{{_ATOM_NS}}}summary").text = (
            page.excerpt or page.description or ""
        )
        if page.date is not None:
            ET.SubElement(entry, f"{{{_ATOM_NS}}}updated").text = _atom_date(page.date)
    return _serialise(feed)


def generate_feeds(pages: list[Page], config: BartlebyConfig, output_dir: Path) -> None:
    """Write all configured feeds to ``output_dir``."""
    by_type: dict[str, list[Page]] = {}
    for page in pages:
        if page.draft or page.content_type_name is None:
            continue
        by_type.setdefault(page.content_type_name, []).append(page)

    for content_type_name, content_type in config.content_types.items():
        type_pages = by_type.get(content_type_name, [])
        if not content_type.feeds:
            continue
        feed_dir = output_dir / content_type_name
        feed_dir.mkdir(parents=True, exist_ok=True)
        if "rss" in content_type.feeds:
            (feed_dir / "feed.xml").write_text(
                generate_rss(type_pages, content_type_name, config.site), encoding="utf-8"
            )
        if "atom" in content_type.feeds:
            (feed_dir / "atom.xml").write_text(
                generate_atom(type_pages, content_type_name, config.site), encoding="utf-8"
            )


def _sorted_pages(pages: list[Page]) -> list[Page]:
    """Reverse-chronological with undated last."""
    dated = sorted(
        (page for page in pages if page.date is not None),
        key=lambda page: page.date,  # type: ignore[arg-type, return-value]
        reverse=True,
    )
    undated = [page for page in pages if page.date is None]
    return dated + undated


def _absolute(site_url: str, path: str) -> str:
    """Join the site URL with a path, ensuring a single ``/`` between them."""
    return site_url.rstrip("/") + "/" + path.lstrip("/")


def _rfc822(date: datetime.date) -> str:
    """Format ``date`` as an RFC 822 string (midnight UTC)."""
    dt = datetime.datetime.combine(date, datetime.time(0, 0, 0), tzinfo=datetime.UTC)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def _atom_date(date: datetime.date) -> str:
    """Format ``date`` as an Atom-compatible ISO 8601 timestamp."""
    dt = datetime.datetime.combine(date, datetime.time(0, 0, 0), tzinfo=datetime.UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _atom_updated_now() -> str:
    """Atom feed-level ``<updated>`` timestamp — build-time clock, not a page date."""
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _serialise(element: ET.Element) -> str:
    """Serialise an ElementTree node to a UTF-8 XML string with declaration."""
    ET.register_namespace("", _ATOM_NS)
    return ET.tostring(element, encoding="unicode", xml_declaration=True)
