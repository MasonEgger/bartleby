# ABOUTME: Tests for pagination logic.
# Covers exact-fit, overflow, multi-page, empty, and per-page paginator context.

from __future__ import annotations

from pathlib import Path

from bartleby.content import Page
from bartleby.pagination import paginate


def _pages(count: int) -> list[Page]:
    return [
        Page(
            source_path=Path(f"item-{index}.md"),
            abs_source_path=Path(f"/abs/item-{index}.md"),
            title=f"Item {index}",
        )
        for index in range(count)
    ]


def test_paginate_exact_fit() -> None:
    """10 items into pages of 10 → 1 page with all items."""
    pages = paginate(_pages(10), per_page=10, base_url="/blog/", url_format="page/{page}")
    assert len(pages) == 1
    assert len(pages[0].items) == 10


def test_paginate_overflow() -> None:
    """11 items into pages of 10 → 2 pages (10 + 1)."""
    pages = paginate(_pages(11), per_page=10, base_url="/blog/", url_format="page/{page}")
    assert len(pages) == 2
    assert len(pages[0].items) == 10
    assert len(pages[1].items) == 1


def test_paginate_multiple_pages() -> None:
    """25 items into pages of 10 → 3 pages."""
    pages = paginate(_pages(25), per_page=10, base_url="/blog/", url_format="page/{page}")
    assert len(pages) == 3
    assert [len(page.items) for page in pages] == [10, 10, 5]


def test_paginate_empty() -> None:
    """An empty input still produces one empty paginator page."""
    pages = paginate([], per_page=10, base_url="/blog/", url_format="page/{page}")
    assert len(pages) == 1
    assert pages[0].items == []


def test_paginator_context() -> None:
    """A middle page exposes prev/next URLs and the full page_range."""
    pages = paginate(_pages(25), per_page=10, base_url="/blog/", url_format="page/{page}")
    middle = pages[1]
    assert middle.page_number == 2
    assert middle.total_pages == 3
    assert middle.has_prev is True
    assert middle.has_next is True
    assert middle.prev_url == "/blog/"
    assert middle.next_url == "/blog/page/3/"
    assert middle.page_range == [1, 2, 3]


def test_paginator_first_page() -> None:
    """The first page has ``has_prev=False`` and ``prev_url=None``."""
    pages = paginate(_pages(25), per_page=10, base_url="/blog/", url_format="page/{page}")
    first = pages[0]
    assert first.has_prev is False
    assert first.prev_url is None
    assert first.has_next is True


def test_paginator_last_page() -> None:
    """The last page has ``has_next=False`` and ``next_url=None``."""
    pages = paginate(_pages(25), per_page=10, base_url="/blog/", url_format="page/{page}")
    last = pages[-1]
    assert last.has_next is False
    assert last.next_url is None
    assert last.has_prev is True
