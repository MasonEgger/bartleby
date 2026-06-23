# ABOUTME: Content type listing page generation.
# Builds virtual Page objects for content type listings with optional intro content.

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from bartleby.content import Page, parse_front_matter
from bartleby.pagination import paginate

if TYPE_CHECKING:
    from bartleby.config import BartlebyConfig

#: ``custom_metadata`` key carrying the listing page kind.
LISTING_KIND_KEY = "listing_kind"


class ListingKind(StrEnum):
    """The kind of generated listing page.

    Stored under :data:`LISTING_KIND_KEY` in a page's ``custom_metadata`` and
    read back by the build's template-type dispatch. ``StrEnum`` compares equal
    to its string value, so templates reading the raw string are unaffected.
    """

    CONTENT_TYPE = "content_type"


def generate_listing_pages(
    pages: list[Page],
    config: BartlebyConfig,
    content_dir: Path,
) -> list[Page]:
    """Produce listing :class:`Page` objects for each content type.

    :param pages: All discovered content pages.
    :param config: Parsed Bartleby config.
    :param content_dir: The site's ``content/`` directory (used to read
        each content type's optional ``index.md`` intro file).
    :returns: List of virtual listing pages — one per listing URL (multiple
        when pagination is enabled).
    """
    listings: list[Page] = []
    pages_by_content_type: dict[str, list[Page]] = {}
    for page in pages:
        if page.draft:
            continue
        if page.content_type_name is None:
            continue
        pages_by_content_type.setdefault(page.content_type_name, []).append(page)

    for content_type_name, content_type in config.content_types.items():
        ordered = _sort_posts_newest_first(pages_by_content_type.get(content_type_name, []))
        intro_content = _read_intro_content(content_dir, content_type_name)
        base_url = "/" + content_type_name + "/"

        if content_type.pagination.enabled:
            paginated_pages = paginate(
                ordered,
                per_page=content_type.pagination.per_page,
                base_url=base_url,
                url_format=content_type.pagination.url_format,
            )
            for paginator_page in paginated_pages:
                listings.append(
                    _build_listing_page(
                        content_type_name=content_type_name,
                        url=_url_for_paginator(
                            paginator_page.page_number,
                            base_url,
                            content_type.pagination.url_format,
                        ),
                        posts=paginator_page.items,
                        intro_content=intro_content if paginator_page.page_number == 1 else "",
                        paginator=paginator_page,
                    )
                )
        else:
            listings.append(
                _build_listing_page(
                    content_type_name=content_type_name,
                    url=base_url,
                    posts=ordered,
                    intro_content=intro_content,
                )
            )
    return listings


def _sort_posts_newest_first(posts: list[Page]) -> list[Page]:
    """Return posts in reverse-chronological order, undated last."""
    dated = sorted(
        (post for post in posts if post.date is not None),
        key=lambda post: post.date,  # type: ignore[arg-type, return-value]
        reverse=True,
    )
    undated = [post for post in posts if post.date is None]
    return dated + undated


def _read_intro_content(content_dir: Path, content_type_name: str) -> str:
    """Read ``content/{type}/index.md`` body if present, otherwise empty string."""
    intro_path = content_dir / content_type_name / "index.md"
    if not intro_path.exists():
        return ""
    _metadata, body = parse_front_matter(intro_path.read_text(encoding="utf-8"))
    return body


def _build_listing_page(
    *,
    content_type_name: str,
    url: str,
    posts: list[Page],
    intro_content: str,
    paginator: object | None = None,
) -> Page:
    """Construct one virtual listing :class:`Page`."""
    sentinel = Path("__generated__") / "listings" / content_type_name / url.strip("/")
    page = Page(
        source_path=sentinel,
        abs_source_path=Path("/__generated__/listings") / sentinel.relative_to("__generated__"),
        title=content_type_name.title(),
        content_type_name=content_type_name,
        custom_metadata={
            LISTING_KIND_KEY: ListingKind.CONTENT_TYPE,
            "posts": posts,
            "intro_content": intro_content,
        },
    )
    if paginator is not None:
        page.custom_metadata["paginator"] = paginator
    page.output_url = url
    return page


def _url_for_paginator(page_number: int, base_url: str, url_format: str) -> str:
    """Mirror the URL formula used inside :func:`paginate`."""
    if page_number == 1:
        return base_url
    suffix = url_format.replace("{page}", str(page_number))
    return base_url.rstrip("/") + "/" + suffix.strip("/") + "/"
