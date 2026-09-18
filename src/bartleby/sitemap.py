# ABOUTME: Sitemap.xml and robots.txt generation.
# Emits the standard sitemap protocol XML plus a robots.txt with AI crawler directives.

from __future__ import annotations

import gzip
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from pathlib import Path

    from bartleby.config import AIConfig, SiteConfig
    from bartleby.content import Page


_SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def generate_sitemap(pages: list[Page], site: SiteConfig) -> str:
    """Render the sitemap XML for ``pages``.

    :param pages: All pages (drafts are filtered out internally).
    :param site: The site config (used for absolute URLs).
    :returns: Sitemap XML as a UTF-8 string with declaration.
    """
    root = ET.Element(f"{{{_SITEMAP_NS}}}urlset")
    for page in pages:
        if page.draft:
            continue
        url_element = ET.SubElement(root, f"{{{_SITEMAP_NS}}}url")
        ET.SubElement(url_element, f"{{{_SITEMAP_NS}}}loc").text = _absolute(
            site.url, page.output_url
        )
        if page.date is not None:
            ET.SubElement(url_element, f"{{{_SITEMAP_NS}}}lastmod").text = page.date.isoformat()
    ET.register_namespace("", _SITEMAP_NS)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def write_sitemap(pages: list[Page], site: SiteConfig, output_dir: Path) -> None:
    """Write ``sitemap.xml`` and ``sitemap.xml.gz`` under ``output_dir``."""
    xml = generate_sitemap(pages, site)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "sitemap.xml").write_text(xml, encoding="utf-8")
    (output_dir / "sitemap.xml.gz").write_bytes(gzip.compress(xml.encode("utf-8")))


def generate_robots_txt(site: SiteConfig, ai_config: AIConfig) -> str:
    """Render the robots.txt body, including AI crawler directives from config."""
    lines: list[str] = [
        "User-agent: *",
        "Allow: /",
        "",
    ]
    for crawler in ai_config.robots.get("allow", []):
        lines.extend([f"User-agent: {crawler}", "Allow: /", ""])
    for crawler in ai_config.robots.get("disallow", []):
        lines.extend([f"User-agent: {crawler}", "Disallow: /", ""])
    lines.append(f"Sitemap: {_absolute(site.url, '/sitemap.xml')}")
    return "\n".join(lines) + "\n"


def write_robots_txt(
    site: SiteConfig,
    ai_config: AIConfig,
    output_dir: Path,
    *,
    static_override_exists: bool = False,
) -> None:
    """Write ``robots.txt`` unless ``static/robots.txt`` already provided one."""
    if static_override_exists:
        return
    (output_dir / "robots.txt").write_text(generate_robots_txt(site, ai_config), encoding="utf-8")


def _absolute(site_url: str, path: str) -> str:
    """Join the site URL with a path, ensuring a single ``/`` between them."""
    return site_url.rstrip("/") + "/" + path.lstrip("/")
