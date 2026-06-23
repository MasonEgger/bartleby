# ABOUTME: LLM-friendly output — llms.txt, llms-full.txt, markdown variants, JSON-LD.
# Produces the agent-readable artifacts that make Bartleby sites navigable by LLMs.

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from bartleby.config import BartlebyConfig, SiteConfig
    from bartleby.content import Page


def generate_llms_txt(pages: list[Page], config: BartlebyConfig) -> str:
    """Render the structured ``llms.txt`` overview pointing at .md variants.

    :param pages: All published pages (drafts already filtered upstream).
    :param config: The parsed config (used for site title, description, and
        content type grouping).
    :returns: The full ``llms.txt`` body as a UTF-8 string.
    """
    lines: list[str] = [f"# {config.site.title}", "", config.site.description or "", ""]
    # llms.txt is the discovery root for the whole machine-readable surface, so it
    # opens with absolute links to the static manifests an agent would otherwise
    # have no convention for finding.
    if config.ai.agent_surface:
        from bartleby.agent_surface import content_index_url, schema_json_url

        lines.append("## Machine-readable")
        lines.append("")
        lines.append(f"- [schema.json]({schema_json_url(config.site)}): site manifest")
        lines.append(
            f"- [content-index.json]({content_index_url(config.site)}): published content index"
        )
        lines.append("")
    grouped = _group_by_content_type(pages, config)
    for type_name, group in grouped.items():
        if not group:
            continue
        lines.append(f"## {type_name.title()}")
        lines.append("")
        for page in group:
            md_url = page.output_url.rstrip("/") + "/index.md"
            description = page.description or page.excerpt or page.title
            lines.append(f"- [{page.title}]({md_url}): {description}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate_llms_full_txt(pages: list[Page], config: BartlebyConfig) -> str:
    """Render ``llms-full.txt`` with the raw body of every published page inlined."""
    sections: list[str] = [f"# {config.site.title}", "", config.site.description or "", ""]
    for page in pages:
        if page.draft:
            continue
        sections.append("---")
        sections.append(f"# {page.title}")
        sections.append(f"URL: {page.output_url}")
        if page.date is not None:
            sections.append(f"Date: {page.date.isoformat()}")
        sections.append("")
        sections.append(page.raw_content.strip())
        sections.append("")
    return "\n".join(sections).rstrip() + "\n"


def write_markdown_variant(page: Page, output_dir: Path) -> None:
    """Write the page's raw markdown body to ``<output_url>/index.md``."""
    url = page.output_url.strip("/")
    destination = output_dir / "index.md" if not url else output_dir / url / "index.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(page.raw_content, encoding="utf-8")


def generate_jsonld(page: Page, site: SiteConfig) -> str:
    """Render the JSON-LD structured data block for ``page``."""
    jsonld_type = "Article" if page.content_type_name is not None else "WebPage"
    payload: dict[str, object] = {
        "@context": "https://schema.org",
        "@type": jsonld_type,
        "headline": page.title,
        "description": page.description or site.description or "",
        "url": _absolute(site.url, page.output_url),
    }
    if jsonld_type == "Article" and page.date is not None:
        payload["datePublished"] = page.date.isoformat()
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _group_by_content_type(pages: list[Page], config: BartlebyConfig) -> dict[str, list[Page]]:
    """Group ``pages`` by content type, keeping the config's content_types order."""
    groups: dict[str, list[Page]] = {name: [] for name in config.content_types}
    groups["pages"] = []
    for page in pages:
        if page.draft:
            continue
        key = page.content_type_name or "pages"
        if key not in groups:
            groups[key] = []
        groups[key].append(page)
    return groups


def _absolute(site_url: str, path: str) -> str:
    return site_url.rstrip("/") + "/" + path.lstrip("/")
