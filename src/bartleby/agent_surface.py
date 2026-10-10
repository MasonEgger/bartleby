# ABOUTME: Static agent surface: schema.json and content-index.json build artifacts.
# Reuses the schema derivation and curates page fields (semantic in, mechanical out).

"""Static agent surface artifacts.

Both files are written at the site root as UTF-8 JSON with sorted keys and two-space
indentation, so the same input yields byte-identical output (no timestamps, no build date).
They describe published pages only.

``schema.json`` is one object with these keys:

* ``site``: ``title``, ``description``, ``url``, and ``language`` (always ``en``).
* ``content_types``: one object per configured content type, in config order, in the shape
  of ``bartleby schema <type>``.
* ``taxonomies``: each taxonomy with ``name``, ``slug_format``, and the ``terms`` in use
  with their ``count`` over published pages.
* ``authors``: the public authors, in the shape of ``bartleby schema authors``.
* ``theme``: ``name`` (the leaf theme), ``chain`` (theme names, leaf first), and
  ``features``, an object of three sorted lists.
  ``enabled`` is what ``theme.features`` in ``bartleby.yml`` asks for.
  ``implemented`` is the union of ``features`` across the manifests in the chain.
  ``active`` is the intersection, which is what the built site can actually do.
  An agent reads ``active`` to know what to rely on; a name in ``enabled`` but not in
  ``implemented`` is a feature the build warned about and did not render.
* ``resources``: absolute URLs for ``sitemap``, ``llms_txt``, ``content_index``, and a
  ``feeds`` list of ``{content_type, format, url}`` objects.

``content-index.json`` is ``{"count": N, "content": [...]}``, one entry per published page
in discovery order (sorted by source path).
Each entry carries ``title``, ``type`` (``null`` for a page with no content type), absolute
``url`` and ``md_url``, then ``description``, ``date``, ``authors``, one key per taxonomy,
and one key per custom metadata field when the page sets them.
Fields that configure the build (template, draft, URL overrides) are left out.

Error-message contract: an :class:`AgentSurfaceError` names the colliding page source
(relative to ``content/``) and the reserved output path, with a hint to rename the page
or set a different ``url``, as ``content/<page>: would overwrite the generated artifact
'<path>' (fix: ...)`` (see :func:`bartleby.errors.format_error`).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from bartleby.content_query import select_published
from bartleby.errors import format_error
from bartleby.feeds import aggregate_feed_path, feed_path
from bartleby.llm import markdown_variant_url
from bartleby.schema_introspection import (
    derive_authors_schema,
    derive_content_type_schema,
    derive_taxonomies_schema,
)
from bartleby.urls import absolute_url

if TYPE_CHECKING:
    from pathlib import Path

    from bartleby.authors import Author
    from bartleby.config import BartlebyConfig, SiteConfig
    from bartleby.content import Page
    from bartleby.theme_loader import ResolvedTheme

# Generated artifact paths a user content page must never collide with.
SCHEMA_JSON_PATH = "schema.json"
CONTENT_INDEX_PATH = "content-index.json"


class AgentSurfaceError(Exception):
    """Raised when user content collides with a generated agent-surface artifact.

    :ivar source_path: The colliding page, relative to ``content/``.
    :ivar artifact: The reserved output path the page would overwrite.
    """

    def __init__(self, source_path: str, artifact: str) -> None:
        super().__init__(
            format_error(
                f"would overwrite the generated artifact {artifact!r}",
                source=f"content/{source_path}",
                hint=(
                    f"rename the page, or set a different `url:` in its front matter; "
                    f"{artifact} is reserved for the agent surface"
                ),
            )
        )
        self.source_path = source_path
        self.artifact = artifact


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
    theme: ResolvedTheme,
) -> dict[str, object]:
    """Build the schema.json site manifest as a JSON-serialisable mapping.

    The static equivalent of ``bartleby schema``: site identity, content-type
    schemas, taxonomy terms, public authors, and resource locations. Reuses the
    Step 11 schema derivation so the static manifest and the CLI agree.

    :param pages: Content pages (drafts are filtered here so taxonomy counts
        reflect only published content).
    :param config: The loaded site configuration.
    :param authors: The authors mapping.
    :param theme: The resolved theme chain the build renders with.
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
        "theme": _theme_block(config, theme),
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
        entry["url"] = absolute_url(config.site.url, page.output_url)
        entry["md_url"] = absolute_url(config.site.url, markdown_variant_url(page.output_url))
        entries.append(entry)
    return {"count": len(entries), "content": entries}


def write_agent_surface(
    pages: list[Page],
    config: BartlebyConfig,
    authors: dict[str, Author],
    theme: ResolvedTheme,
    output_dir: Path,
) -> None:
    """Emit schema.json and content-index.json at the site root.

    :param pages: Content pages (drafts are filtered when building the index).
    :param config: The loaded site configuration.
    :param authors: The authors mapping.
    :param theme: The resolved theme chain the build renders with.
    :param output_dir: The build output directory.
    :raises AgentSurfaceError: If a user page would overwrite either artifact.
    """
    _check_collisions(pages)
    schema = build_schema_json(pages, config, authors, theme)
    index = build_content_index(pages, config)
    (output_dir / SCHEMA_JSON_PATH).write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    (output_dir / CONTENT_INDEX_PATH).write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )


def _theme_block(config: BartlebyConfig, theme: ResolvedTheme) -> dict[str, object]:
    """Describe the active theme: its name, resolved chain, and feature lists."""
    enabled = set(config.theme.features)
    implemented = set(theme.implemented_features())
    return {
        "name": theme.chain[0].name,
        "chain": [layer.name for layer in theme.chain],
        "features": {
            "enabled": sorted(enabled),
            "implemented": sorted(implemented),
            "active": sorted(enabled & implemented),
        },
    }


def _check_collisions(pages: list[Page]) -> None:
    """Raise if any published page's output path collides with a generated artifact."""
    reserved = {SCHEMA_JSON_PATH, CONTENT_INDEX_PATH}
    for page in select_published(pages):
        normalised = page.output_url.strip("/")
        if normalised in reserved:
            raise AgentSurfaceError(page.source_path.as_posix(), normalised)


def _resource_locations(config: BartlebyConfig) -> dict[str, object]:
    """Build the absolute-URL resource map (sitemap, llms.txt, content-index, feeds)."""
    feeds: list[dict[str, object]] = []
    for type_name, content_type in config.content_types.items():
        if "rss" in content_type.feeds:
            feeds.append(
                {
                    "content_type": type_name,
                    "format": "rss",
                    "url": absolute_url(config.site.url, feed_path(type_name, "rss")),
                }
            )
        if "atom" in content_type.feeds:
            feeds.append(
                {
                    "content_type": type_name,
                    "format": "atom",
                    "url": absolute_url(config.site.url, feed_path(type_name, "atom")),
                }
            )
    aggregate = config.site.feed
    if aggregate.enabled:
        if "rss" in aggregate.formats:
            feeds.append(
                {
                    "content_type": None,
                    "format": "rss",
                    "url": absolute_url(config.site.url, aggregate_feed_path("rss")),
                }
            )
        if "atom" in aggregate.formats:
            feeds.append(
                {
                    "content_type": None,
                    "format": "atom",
                    "url": absolute_url(config.site.url, aggregate_feed_path("atom")),
                }
            )
    return {
        "sitemap": absolute_url(config.site.url, "/sitemap.xml"),
        "llms_txt": absolute_url(config.site.url, "/llms.txt"),
        "content_index": absolute_url(config.site.url, f"/{CONTENT_INDEX_PATH}"),
        "feeds": feeds,
    }


def schema_json_url(site: SiteConfig) -> str:
    """Absolute URL of the schema.json manifest (used by llms.txt discovery)."""
    return absolute_url(site.url, f"/{SCHEMA_JSON_PATH}")


def content_index_url(site: SiteConfig) -> str:
    """Absolute URL of the content-index.json artifact (used by llms.txt discovery)."""
    return absolute_url(site.url, f"/{CONTENT_INDEX_PATH}")


def _jsonable(value: object) -> object:
    """Coerce a custom-metadata value into a JSON-serialisable form."""
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return value
