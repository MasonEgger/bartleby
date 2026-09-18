# ABOUTME: Content query — list and get discovered pages with curated fields.
# Backs `bartleby content list` and `bartleby content get`; shares published selection with build.

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bartleby.urls import generate_url

# Sentinel for sorting dateless pages last when sorting by date (newest first).
_MIN_DATE = datetime.date.min

if TYPE_CHECKING:
    from bartleby.config import BartlebyConfig
    from bartleby.content import Page


# Default field set for `content list` output (spec.md `bartleby content list`).
_DEFAULT_LIST_FIELDS = ("path", "title", "date", "type", "url")

# Sort keys understood by `content list`.
_SORT_DATE = "date"
_SORT_TITLE = "title"
_SORT_PATH = "path"


class ContentQueryError(Exception):
    """Raised when a content query targets a page that does not exist."""


@dataclass(slots=True)
class ContentList:
    """Result of ``bartleby content list`` (the documented JSON shape)."""

    count: int
    content: list[dict[str, object]]

    @property
    def exit_code(self) -> int:
        return 0

    def to_dict(self) -> dict[str, object]:
        return {"count": self.count, "content": self.content}

    def to_text(self) -> str:
        if not self.content:
            return "no content"
        lines: list[str] = []
        for entry in self.content:
            title = entry.get("title", "")
            path = entry.get("path", "")
            lines.append(f"{title}  {path}")
        return "\n".join(lines)


@dataclass(slots=True)
class ContentGet:
    """Result of ``bartleby content get <path>`` (the documented JSON shape)."""

    path: str
    url: str
    content_type: str | None
    metadata: dict[str, object]
    body: str
    word_count: int

    @property
    def exit_code(self) -> int:
        return 0

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "url": self.url,
            "content_type": self.content_type,
            "metadata": self.metadata,
            "content": self.body,
            "word_count": self.word_count,
        }

    def to_text(self) -> str:
        title = self.metadata.get("title", "")
        return f"{title} ({self.path})\n\n{self.body}"


def select_published(pages: list[Page]) -> list[Page]:
    """Return only the published pages from ``pages`` (drafts excluded).

    "Published" means the same thing here and in the build pipeline: a page whose
    ``draft`` flag is false. Both call sites share this function so the notion of
    a published page never drifts.

    :param pages: Discovered content pages.
    :returns: A new list containing only non-draft pages, order preserved.
    """
    return [page for page in pages if not page.draft]


def list_content(
    pages: list[Page],
    config: BartlebyConfig,
    *,
    content_type: str | None = None,
    sort: str = _SORT_DATE,
    limit: int | None = None,
) -> ContentList:
    """List published pages with curated fields, filtered and sorted.

    :param pages: Discovered content pages.
    :param config: The loaded site configuration.
    :param content_type: When set, only pages of this content type are listed.
    :param sort: Sort key — ``date`` (default, newest first), ``title``, or ``path``.
    :param limit: Maximum number of entries to return.
    :returns: A :class:`ContentList` carrying the curated entries and their count.
    """
    selected = select_published(pages)
    if content_type is not None:
        selected = [page for page in selected if page.content_type_name == content_type]
    selected = _sort_pages(selected, sort)
    if limit is not None:
        selected = selected[:limit]
    entries = [_curated_entry(page, config) for page in selected]
    return ContentList(count=len(entries), content=entries)


def get_content(path: str, pages: list[Page], config: BartlebyConfig) -> ContentGet:
    """Return one page's metadata and body, keyed by its source path.

    :param path: The page's source path (as it appears in ``content list``).
    :param pages: Discovered content pages.
    :param config: The loaded site configuration.
    :returns: A :class:`ContentGet` with the page's metadata, body, and word count.
    :raises ContentQueryError: When no page has the given source path.
    """
    target = normalise_source_path(path)
    for page in pages:
        if normalise_source_path(page.source_path.as_posix()) == target:
            return _build_get(page, config)
    raise ContentQueryError(f"no content page at {path!r}")


def _build_get(page: Page, config: BartlebyConfig) -> ContentGet:
    """Assemble the :class:`ContentGet` result for one page."""
    metadata: dict[str, object] = {"title": page.title}
    if page.date is not None:
        metadata["date"] = page.date.isoformat()
    if page.description is not None:
        metadata["description"] = page.description
    if page.author_keys:
        metadata["authors"] = list(page.author_keys)
    for taxonomy_name, terms in page.taxonomy_values.items():
        metadata[taxonomy_name] = list(terms)
    metadata["draft"] = page.draft
    return ContentGet(
        path=page.source_path.as_posix(),
        url=_url_for(page, config),
        content_type=page.content_type_name,
        metadata=metadata,
        body=page.raw_content,
        word_count=len(page.raw_content.split()),
    )


def _curated_entry(page: Page, config: BartlebyConfig) -> dict[str, object]:
    """Build the default curated field map for one page in a list."""
    return {
        "path": page.source_path.as_posix(),
        "title": page.title,
        "date": page.date.isoformat() if page.date is not None else None,
        "type": page.content_type_name,
        "url": _url_for(page, config),
        "draft": page.draft,
    }


def _url_for(page: Page, config: BartlebyConfig) -> str:
    """Compute a page's output URL without mutating the page."""
    content_type = (
        config.content_types.get(page.content_type_name) if page.content_type_name else None
    )
    return generate_url(page, content_type)


def _sort_pages(pages: list[Page], sort: str) -> list[Page]:
    """Sort pages by the requested key; date sorts newest first."""
    if sort == _SORT_TITLE:
        return sorted(pages, key=lambda page: page.title)
    if sort == _SORT_PATH:
        return sorted(pages, key=lambda page: page.source_path.as_posix())
    return sorted(
        pages,
        key=lambda page: page.date or _MIN_DATE,
        reverse=True,
    )


def normalise_source_path(path: str) -> str:
    """Normalise a source path for comparison (strip a leading ``content/``)."""
    cleaned = path.replace("\\", "/").lstrip("/")
    return cleaned[len("content/") :] if cleaned.startswith("content/") else cleaned
