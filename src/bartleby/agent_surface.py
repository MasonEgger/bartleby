# ABOUTME: Static agent surface: schema.json and content-index.json build artifacts.
# Reuses the schema derivation and curates page fields (semantic in, mechanical out).

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from bartleby.content_query import select_published
from bartleby.feeds import aggregate_feed_path, feed_path
from bartleby.schema_introspection import (
    derive_authors_schema,
    derive_content_type_schema,
    derive_taxonomies_schema,
)

if TYPE_CHECKING:
    from pathlib import Path

    from bartleby.authors import Author
    from bartleby.config import BartlebyConfig, SiteConfig
    from bartleby.content import Page

# Generated artifact paths a user content page must never collide with.
SCHEMA_JSON_PATH = "schema.json"
CONTENT_INDEX_PATH = "content-index.json"


class AgentSurfaceError(Exception):
    """Raised when user content collides with a generated agent-surface artifact."""


def curate_page_fields(page: Page) -> dict[str, object]:
    """Curate a page's front matter into the semantic fields agents care about.

    The curation rule: semantic fields describe the content (title, description,
    date, updated, content type, taxonomy terms, authors, custom schema fields)
    and are included. Mechanical fields configure the build (template, draft, URL
    overrides, render toggles) and are excluded.

    :param page: A discovered content page.
    :returns: A mapping of the page's semantic fields only.
    """
    curated: dict[str, object] = {"title": page.title, "type": page.content_type_name}
    if page.description is not None:
        curated["description"] = page.description
    if page.date is not None:
        curated["date"] = page.date.isoformat()
    if page.author_keys:
        curated["authors"] = list(page.author_keys)
    for taxonomy_name, terms in page.taxonomy_values.items():
        curated[taxonomy_name] = list(terms)
    # Custom metadata-schema fields (e.g. difficulty) are semantic describers.
    for field_name, value in page.custom_metadata.items():
        curated[field_name] = _jsonable(value)
    return curated


def build_schema_json(
    pages: list[Page],
    config: BartlebyConfig,
    authors: dict[str, Author],
) -> dict[str, object]:
    """Build the schema.json site manifest as a JSON-serialisable mapping.

    The static equivalent of ``bartleby schema``: site identity, content-type
    schemas, taxonomy terms, public authors, and resource locations. Reuses the
    Step 11 schema derivation so the static manifest and the CLI agree.

    :param pages: Content pages (drafts are filtered here so taxonomy counts
        reflect only published content).
    :param config: The loaded site configuration.
    :param authors: The authors mapping.
    :returns: The schema.json payload.
    """
    published = select_published(pages)
    content_types = [
        derive_content_type_schema(name, config).to_dict() for name in config.content_types
    ]
    taxonomies = derive_taxonomies_schema(published, config).to_dict()["taxonomies"]
    author_entries = derive_authors_schema(authors).to_dict()["authors"]
    return {
        "site": {
            "title": config.site.title,
            "description": config.site.description,
            "url": config.site.url,
            "language": "en",
        },
        "content_types": content_types,
        "taxonomies": taxonomies,
        "authors": author_entries,
        "resources": _resource_locations(config),
    }


def build_content_index(pages: list[Page], config: BartlebyConfig) -> dict[str, object]:
    """Build the content-index.json payload: one curated entry per published page.

    :param pages: Content pages (drafts are filtered here).
    :param config: The loaded site configuration (for the absolute base URL).
    :returns: The content-index.json payload.
    """
    published = select_published(pages)
    entries: list[dict[str, object]] = []
    for page in published:
        entry = curate_page_fields(page)
        entry["url"] = _absolute(config.site.url, page.output_url)
        entry["md_url"] = _absolute(config.site.url, _md_variant_path(page.output_url))
        entries.append(entry)
    return {"count": len(entries), "content": entries}


def write_agent_surface(
    pages: list[Page],
    config: BartlebyConfig,
    authors: dict[str, Author],
    output_dir: Path,
) -> None:
    """Emit schema.json and content-index.json at the site root.

    :param pages: Content pages (drafts are filtered when building the index).
    :param config: The loaded site configuration.
    :param authors: The authors mapping.
    :param output_dir: The build output directory.
    :raises AgentSurfaceError: If a user page would overwrite either artifact.
    """
    _check_collisions(pages)
    schema = build_schema_json(pages, config, authors)
    index = build_content_index(pages, config)
    (output_dir / SCHEMA_JSON_PATH).write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    (output_dir / CONTENT_INDEX_PATH).write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )


def _check_collisions(pages: list[Page]) -> None:
    """Raise if any published page's output path collides with a generated artifact."""
    reserved = {SCHEMA_JSON_PATH, CONTENT_INDEX_PATH}
    for page in select_published(pages):
        normalised = page.output_url.strip("/")
        if normalised in reserved:
            raise AgentSurfaceError(
                f"content page {page.source_path} would overwrite the generated "
                f"artifact {normalised!r}; rename the page or its url override"
            )


def _resource_locations(config: BartlebyConfig) -> dict[str, object]:
    """Build the absolute-URL resource map (sitemap, llms.txt, content-index, feeds)."""
    feeds: list[dict[str, object]] = []
    for type_name, content_type in config.content_types.items():
        if "rss" in content_type.feeds:
            feeds.append(
                {
                    "content_type": type_name,
                    "format": "rss",
                    "url": _absolute(config.site.url, feed_path(type_name, "rss")),
                }
            )
        if "atom" in content_type.feeds:
            feeds.append(
                {
                    "content_type": type_name,
                    "format": "atom",
                    "url": _absolute(config.site.url, feed_path(type_name, "atom")),
                }
            )
    aggregate = config.site.feed
    if aggregate.enabled:
        if "rss" in aggregate.formats:
            feeds.append(
                {
                    "content_type": None,
                    "format": "rss",
                    "url": _absolute(config.site.url, aggregate_feed_path("rss")),
                }
            )
        if "atom" in aggregate.formats:
            feeds.append(
                {
                    "content_type": None,
                    "format": "atom",
                    "url": _absolute(config.site.url, aggregate_feed_path("atom")),
                }
            )
    return {
        "sitemap": _absolute(config.site.url, "/sitemap.xml"),
        "llms_txt": _absolute(config.site.url, "/llms.txt"),
        "content_index": _absolute(config.site.url, f"/{CONTENT_INDEX_PATH}"),
        "feeds": feeds,
    }


def schema_json_url(site: SiteConfig) -> str:
    """Absolute URL of the schema.json manifest (used by llms.txt discovery)."""
    return _absolute(site.url, f"/{SCHEMA_JSON_PATH}")


def content_index_url(site: SiteConfig) -> str:
    """Absolute URL of the content-index.json artifact (used by llms.txt discovery)."""
    return _absolute(site.url, f"/{CONTENT_INDEX_PATH}")


def _md_variant_path(output_url: str) -> str:
    """The .md variant path for an output URL (mirrors write_markdown_variant)."""
    stripped = output_url.strip("/")
    return "index.md" if not stripped else f"{stripped}/index.md"


def _jsonable(value: object) -> object:
    """Coerce a custom-metadata value into a JSON-serialisable form."""
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return value


def _absolute(site_url: str, path: str) -> str:
    """Join the site URL with a path, ensuring a single ``/`` between them."""
    return site_url.rstrip("/") + "/" + path.lstrip("/")
