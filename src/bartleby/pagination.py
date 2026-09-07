# ABOUTME: Pagination logic for splitting content into pages.
# Produces PaginatorPage objects with navigation context (prev/next/range).

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bartleby.content import Page


@dataclass(slots=True)
class PaginatorPage:
    """One paginated chunk of items with navigation context."""

    items: list[Page]
    page_number: int
    total_pages: int
    has_next: bool = False
    has_prev: bool = False
    next_url: str | None = None
    prev_url: str | None = None
    page_range: list[int] = field(default_factory=list)


def paginate(
    items: list[Page],
    per_page: int,
    base_url: str,
    url_format: str,
) -> list[PaginatorPage]:
    """Split ``items`` into paginator pages.

    :param items: Source items to paginate.
    :param per_page: Maximum items per page.
    :param base_url: URL of the first page (e.g. ``/blog/``). Subsequent
        pages are placed under ``base_url + url_format.format(page=N)``.
    :param url_format: Template for subsequent page URLs. May reference
        ``{page}``.
    :returns: At least one :class:`PaginatorPage`. An empty input produces
        a single empty paginator page rather than an empty list — callers
        can always render "page 1 of 1".
    """
    if not items:
        return [
            PaginatorPage(
                items=[],
                page_number=1,
                total_pages=1,
                has_next=False,
                has_prev=False,
                page_range=[1],
            )
        ]

    total_pages = (len(items) + per_page - 1) // per_page
    page_range = list(range(1, total_pages + 1))
    pages: list[PaginatorPage] = []
    for index in range(total_pages):
        start = index * per_page
        end = start + per_page
        page_number = index + 1
        pages.append(
            PaginatorPage(
                items=items[start:end],
                page_number=page_number,
                total_pages=total_pages,
                has_prev=page_number > 1,
                has_next=page_number < total_pages,
                prev_url=_url_for_page(page_number - 1, base_url, url_format)
                if page_number > 1
                else None,
                next_url=_url_for_page(page_number + 1, base_url, url_format)
                if page_number < total_pages
                else None,
                page_range=page_range,
            )
        )
    return pages


def _url_for_page(page_number: int, base_url: str, url_format: str) -> str:
    """Build the URL for paginator page ``page_number`` (1-indexed)."""
    if page_number == 1:
        return base_url
    suffix = url_format.replace("{page}", str(page_number))
    return base_url.rstrip("/") + "/" + suffix.strip("/") + "/"
