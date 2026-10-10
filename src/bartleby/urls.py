# ABOUTME: URL generation for pages based on content type config and front matter.
# Supports path-based defaults, url_format placeholders, and per-page overrides.

from __future__ import annotations

import re
import string
from typing import TYPE_CHECKING

from slugify import slugify as _raw_slugify

if TYPE_CHECKING:
    from bartleby.config import BartlebyConfig, ContentTypeConfig
    from bartleby.content import Page


_DATE_PLACEHOLDER = re.compile(r"\{date(?::([^}]+))?\}")
_SLUG_REPLACEMENTS: list[list[str]] = [["&", " and "]]


def absolute_url(site_url: str, path: str) -> str:
    """Join the site URL and a path with exactly one ``/`` between them.

    :param site_url: The configured ``site.url``, with or without a trailing slash.
    :param path: A root-relative path or output URL, with or without a leading slash.
    :returns: The absolute URL.
    """
    return site_url.rstrip("/") + "/" + path.lstrip("/")


def slugify(text: str) -> str:
    """Bartleby's URL slug helper — python-slugify with ``&`` mapped to ``and``."""
    return _raw_slugify(text, replacements=_SLUG_REPLACEMENTS)


def generate_url(page: Page, content_type: ContentTypeConfig | None) -> str:
    """Generate the output URL for ``page``.

    :param page: The page being placed.
    :param content_type: The page's content type config, or ``None`` for
        pages that do not belong to one.
    :returns: A URL string starting with ``/`` and ending with ``/``.
    :raises ValueError: When ``url_format`` references ``{date}`` but the
        page has no date.
    """
    if page.url_override is not None:
        return _normalise(page.url_override)

    if content_type is None:
        return _normalise(_path_to_url(page))

    url_base = page.url_base_override or content_type.url_base
    url_format = content_type.url_format

    if url_format is not None:
        formatted = _format_url(url_format, page)
        prefix = url_base.strip("/") if url_base is not None else ""
        joined = f"{prefix}/{formatted.strip('/')}" if prefix else formatted.strip("/")
        return _normalise(joined)

    if url_base is not None:
        return _normalise(f"{url_base.strip('/')}/{_slug_for(page)}")

    return _normalise(_path_to_url(page))


def generate_all_urls(pages: list[Page], config: BartlebyConfig) -> None:
    """Populate ``page.output_url`` for every page in ``pages``.

    :param pages: Pages discovered by content discovery.
    :param config: Parsed Bartleby config (used to look up content type
        configs by ``page.content_type_name``).
    """
    for page in pages:
        content_type = (
            config.content_types.get(page.content_type_name) if page.content_type_name else None
        )
        page.output_url = generate_url(page, content_type)


def _format_url(format_str: str, page: Page) -> str:
    """Render ``url_format`` substituting slug, date, title, and categories placeholders."""
    result = _DATE_PLACEHOLDER.sub(lambda match: _format_date(page, match.group(1)), format_str)
    formatter = string.Formatter()
    parts: list[str] = []
    for literal, field_name, _spec, _conv in formatter.parse(result):
        parts.append(literal)
        if field_name is None:
            continue
        parts.append(_resolve_field(field_name, page))
    return "".join(parts)


def _format_date(page: Page, spec: str | None) -> str:
    """Format the page's date with ``spec`` (defaults to ISO ``%Y-%m-%d``)."""
    if page.date is None:
        raise ValueError(
            f"page {page.source_path!s} has no date but url_format references {{date}}"
        )
    return page.date.strftime(spec or "%Y-%m-%d")


def _resolve_field(field_name: str, page: Page) -> str:
    """Resolve a non-date URL placeholder to a slug string."""
    if field_name == "slug":
        return _slug_for(page)
    if field_name == "title":
        return slugify(page.title)
    if field_name == "categories":
        values = page.taxonomy_values.get("categories", [])
        return slugify(values[0]) if values else ""
    raise ValueError(f"unknown url_format placeholder: {{{field_name}}}")


def _slug_for(page: Page) -> str:
    """The page's URL slug — front-matter override wins, else slugified filename stem."""
    if page.slug_override:
        return slugify(page.slug_override)
    return slugify(page.abs_source_path.stem)


def _path_to_url(page: Page) -> str:
    """Convert ``content/foo/bar.md`` into ``/foo/bar/`` (or ``/foo/`` for ``index.md``)."""
    parts = list(page.source_path.parts)
    if parts[-1] == "index.md":
        parts = parts[:-1]
    else:
        parts[-1] = page.source_path.stem
    return "/" + "/".join(parts) if parts else "/"


def _normalise(url: str) -> str:
    """Ensure a URL starts with ``/``, ends with ``/``, and has no doubled slashes."""
    text = url.strip()
    if not text.startswith("/"):
        text = "/" + text
    if not text.endswith("/"):
        text = text + "/"
    while "//" in text:
        text = text.replace("//", "/")
    return text
