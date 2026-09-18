# ABOUTME: Navigation building from config or auto-generation from directory structure.
# Produces NavItems for templates and links pages with previous/next references.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bartleby.config import BartlebyConfig
    from bartleby.content import Page


@dataclass(slots=True)
class NavItem:
    """One entry in the rendered site navigation."""

    title: str
    url: str | None = None
    children: list[NavItem] = field(default_factory=list)
    page: Page | None = None
    is_section: bool = False


@dataclass(slots=True)
class Navigation:
    """Resolved navigation for a build — tree of NavItems plus a flat page order."""

    items: list[NavItem]
    pages_flat: list[Page]


def build_navigation(config: BartlebyConfig, pages: list[Page]) -> Navigation:
    """Build navigation from explicit config or auto-generate from ``pages``."""
    if config.nav is not None:
        items = _build_explicit_nav(config.nav, pages)
    else:
        items = _auto_generate_nav(pages)
    return Navigation(items=items, pages_flat=_flatten(items))


def link_pages(nav: Navigation) -> None:
    """Walk ``nav.pages_flat`` and set ``previous``/``next`` on each page."""
    flat = nav.pages_flat
    for index, page in enumerate(flat):
        page.previous = flat[index - 1] if index > 0 else None
        page.next = flat[index + 1] if index < len(flat) - 1 else None


def _build_explicit_nav(
    nav_config: list[dict[str, object]],
    pages: list[Page],
) -> list[NavItem]:
    """Build NavItems from the explicit ``nav`` config block."""
    pages_by_source = {str(page.source_path): page for page in pages}
    pages_by_url = {page.output_url: page for page in pages}
    items: list[NavItem] = []
    for entry in nav_config:
        for title, target in entry.items():
            items.append(_build_explicit_item(title, target, pages_by_source, pages_by_url))
    return items


def _build_explicit_item(
    title: str,
    target: object,
    pages_by_source: dict[str, Page],
    pages_by_url: dict[str, Page],
) -> NavItem:
    """Resolve a single explicit-nav entry into a NavItem (with children)."""
    if isinstance(target, list):
        children = [
            _build_explicit_item(child_title, child_target, pages_by_source, pages_by_url)
            for child_entry in target
            if isinstance(child_entry, dict)
            for child_title, child_target in child_entry.items()
        ]
        return NavItem(title=title, children=children, is_section=True)
    if not isinstance(target, str):
        return NavItem(title=title)
    page = pages_by_source.get(target)
    if page is None:
        return NavItem(title=title, url=_target_to_url(target))
    return NavItem(title=title, url=page.output_url, page=page)


def _auto_generate_nav(pages: list[Page]) -> list[NavItem]:
    """Synthesize a flat nav from the page set, grouping by top-level directory."""
    top_level_pages: list[NavItem] = []
    section_titles: set[str] = set()
    for page in pages:
        parts = page.source_path.parts
        if len(parts) == 1:
            if parts[0] == "index.md":
                top_level_pages.append(NavItem(title=page.title, url=page.output_url, page=page))
                continue
            top_level_pages.append(NavItem(title=page.title, url=page.output_url, page=page))
        else:
            section_titles.add(parts[0])
    sections = [
        NavItem(title=name.replace("-", " ").replace("_", " ").title(), is_section=True)
        for name in section_titles
    ]
    items = top_level_pages + sections
    items.sort(key=lambda item: item.title.lower())
    return items


def _flatten(items: list[NavItem]) -> list[Page]:
    """Depth-first walk producing the ordered list of pages referenced in the nav."""
    flat: list[Page] = []
    for item in items:
        if item.page is not None:
            flat.append(item.page)
        flat.extend(_flatten(item.children))
    return flat


def _target_to_url(target: str) -> str:
    """Convert a nav target string like ``blog/`` or ``index.md`` into a URL."""
    if target.endswith(".md"):
        stem = target[: -len(".md")]
        return "/" + stem.rstrip("/") + "/"
    if target.endswith("/"):
        return "/" + target.lstrip("/")
    return "/" + target.strip("/") + "/"
