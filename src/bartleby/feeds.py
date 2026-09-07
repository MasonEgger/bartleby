# ABOUTME: RSS 2.0 and Atom 1.0 feed generation per content type and site-wide.
# Emits per-type feeds plus the homepage aggregate firehose from bartleby.yml.

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from pathlib import Path

    from bartleby.config import BartlebyConfig, SiteConfig
    from bartleby.content import Page


_ATOM_NS = "http://www.w3.org/2005/Atom"
_RSS_MIME = "application/rss+xml"
_ATOM_MIME = "application/atom+xml"
_FEED_FILENAMES = {"rss": "feed.xml", "atom": "atom.xml"}


def feed_path(content_type_name: str, feed_format: str) -> str:
    """Root-relative path of a per-content-type feed file.

    Shared with ``agent_surface._resource_locations`` so the URL advertised in
    schema.json can never drift from where ``generate_feeds`` writes the file.
    """
    return f"/{content_type_name}/{_FEED_FILENAMES[feed_format]}"


def aggregate_feed_path(feed_format: str) -> str:
    """Root-relative path of the site-wide aggregate feed file.

    Shared with ``agent_surface._resource_locations`` so the URL advertised in
    schema.json can never drift from where ``generate_feeds`` writes the file.
    """
    return f"/{_FEED_FILENAMES[feed_format]}"


def generate_rss(pages: list[Page], content_type_name: str, site: SiteConfig) -> str:
    """Render an RSS 2.0 feed for ``pages`` belonging to ``content_type_name``."""
    title = f"{site.title} — {content_type_name.title()}"
    link = _absolute(site.url, f"/{content_type_name}/")
    return _render_rss(_sorted_pages(pages), title, link, site, category=False)


def generate_atom(pages: list[Page], content_type_name: str, site: SiteConfig) -> str:
    """Render an Atom 1.0 feed for ``pages`` belonging to ``content_type_name``."""
    title = f"{site.title} — {content_type_name.title()}"
    feed_id = _absolute(site.url, f"/{content_type_name}/")
    self_href = _absolute(site.url, f"/{content_type_name}/atom.xml")
    return _render_atom(_sorted_pages(pages), title, feed_id, self_href, site, category=False)


def compute_aggregate_types(config: BartlebyConfig) -> list[str]:
    """Resolve which content types feed the site-wide aggregate.

    An empty ``site.feed.include`` covers every content type that has its own
    ``feeds`` enabled (config order). A non-empty list restricts the aggregate to
    exactly those types (validated at load time to all have their own feeds).
    """
    include = config.site.feed.include
    if include:
        return list(include)
    return [name for name, content_type in config.content_types.items() if content_type.feeds]


def generate_aggregate_rss(pages: list[Page], config: BartlebyConfig) -> str:
    """Render the site-wide aggregate RSS 2.0 feed from ``pages``."""
    feed = config.site.feed
    title = feed.title or config.site.title
    link = _absolute(config.site.url, "/")
    items = _aggregate_pages(pages, config)
    return _render_rss(items, title, link, config.site, category=True)


def generate_aggregate_atom(pages: list[Page], config: BartlebyConfig) -> str:
    """Render the site-wide aggregate Atom 1.0 feed from ``pages``."""
    feed = config.site.feed
    title = feed.title or config.site.title
    feed_id = _absolute(config.site.url, "/")
    self_href = _absolute(config.site.url, "/atom.xml")
    items = _aggregate_pages(pages, config)
    return _render_atom(items, title, feed_id, self_href, config.site, category=True)


def feed_links_for_page(page: Page, config: BartlebyConfig) -> list[dict[str, str]]:
    """Build the contextual ``rel="alternate"`` feed links for a page's head.

    A content-type page advertises that type's feed first, then the aggregate.
    Any other page (homepage, taxonomy, static) advertises only the aggregate.
    Each link is a dict with ``href``, ``type``, and ``title`` keys suitable for
    direct rendering in the template.
    """
    feed = config.site.feed
    links: list[dict[str, str]] = []

    content_type = (
        config.content_types.get(page.content_type_name)
        if page.content_type_name is not None
        else None
    )
    if content_type is not None and content_type.feeds:
        name = content_type.name
        if "rss" in content_type.feeds:
            links.append(_feed_link(feed_path(name, "rss"), _RSS_MIME, f"{name.title()} RSS"))
        if "atom" in content_type.feeds:
            links.append(_feed_link(feed_path(name, "atom"), _ATOM_MIME, f"{name.title()} Atom"))

    if feed.enabled:
        aggregate_title = feed.title or config.site.title
        if "rss" in feed.formats:
            links.append(
                _feed_link(aggregate_feed_path("rss"), _RSS_MIME, f"{aggregate_title} RSS")
            )
        if "atom" in feed.formats:
            links.append(
                _feed_link(aggregate_feed_path("atom"), _ATOM_MIME, f"{aggregate_title} Atom")
            )

    return links


def generate_feeds(pages: list[Page], config: BartlebyConfig, output_dir: Path) -> None:
    """Write all configured feeds to ``output_dir``.

    Per-content-type feeds land under ``{type}/feed.xml`` and ``{type}/atom.xml``.
    The site-wide aggregate, when enabled, lands at the output root as
    ``feed.xml`` and ``atom.xml`` per ``site.feed.formats``.
    """
    publishable = [page for page in pages if not page.draft and page.content_type_name is not None]
    by_type: dict[str, list[Page]] = {}
    for page in publishable:
        assert page.content_type_name is not None
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

    feed = config.site.feed
    if feed.enabled:
        output_dir.mkdir(parents=True, exist_ok=True)
        if "rss" in feed.formats:
            (output_dir / "feed.xml").write_text(
                generate_aggregate_rss(publishable, config), encoding="utf-8"
            )
        if "atom" in feed.formats:
            (output_dir / "atom.xml").write_text(
                generate_aggregate_atom(publishable, config), encoding="utf-8"
            )


def _aggregate_pages(pages: list[Page], config: BartlebyConfig) -> list[Page]:
    """Filter to in-scope types, sort date-descending, and cap at the configured limit."""
    in_scope = set(compute_aggregate_types(config))
    selected = [page for page in pages if page.content_type_name in in_scope]
    return _sorted_pages(selected)[: config.site.feed.limit]


def _render_rss(
    pages: list[Page], title: str, link: str, site: SiteConfig, *, category: bool
) -> str:
    """Build an RSS 2.0 document from already-sorted ``pages``."""
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = title
    ET.SubElement(channel, "link").text = link
    ET.SubElement(channel, "description").text = site.description or ""

    for page in pages:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = page.title
        ET.SubElement(item, "link").text = _absolute(site.url, page.output_url)
        ET.SubElement(item, "description").text = page.excerpt or page.description or ""
        if category and page.content_type_name is not None:
            ET.SubElement(item, "category").text = page.content_type_name
        if page.date is not None:
            ET.SubElement(item, "pubDate").text = _rfc822(page.date)
    return _serialise(rss)


def _render_atom(
    pages: list[Page],
    title: str,
    feed_id: str,
    self_href: str,
    site: SiteConfig,
    *,
    category: bool,
) -> str:
    """Build an Atom 1.0 document from already-sorted ``pages``."""
    feed = ET.Element(f"{{{_ATOM_NS}}}feed")
    ET.SubElement(feed, f"{{{_ATOM_NS}}}title").text = title
    ET.SubElement(feed, f"{{{_ATOM_NS}}}id").text = feed_id
    ET.SubElement(feed, f"{{{_ATOM_NS}}}link", href=self_href, rel="self")
    ET.SubElement(feed, f"{{{_ATOM_NS}}}updated").text = _atom_updated_now()

    for page in pages:
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
        if category and page.content_type_name is not None:
            ET.SubElement(entry, f"{{{_ATOM_NS}}}category", term=page.content_type_name)
        if page.date is not None:
            ET.SubElement(entry, f"{{{_ATOM_NS}}}updated").text = _atom_date(page.date)
    return _serialise(feed)


def _feed_link(href: str, mime: str, title: str) -> dict[str, str]:
    """Construct a single contextual feed-link descriptor for the template."""
    return {"href": href, "type": mime, "title": title}


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
