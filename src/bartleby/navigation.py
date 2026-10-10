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
    index_url: str | None = None


@dataclass(slots=True)
class Navigation:
    """Resolved navigation for a build — tree of NavItems plus a flat page order."""

    items: list[NavItem]
    pages_flat: list[Page]


def build_navigation(config: BartlebyConfig, pages: list[Page]) -> Navigation:
    """Build navigation from explicit config or auto-generate from ``pages``."""
    listing_paths = tuple(
        content_type.path.strip("/") for content_type in config.content_types.values()
    )
    if config.nav is not None:
        items = _build_explicit_nav(config.nav, pages, listing_paths)
    else:
        items = _auto_generate_nav(pages, listing_paths)
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
    listing_paths: tuple[str, ...],
) -> list[NavItem]:
    """Build NavItems from the explicit ``nav`` config block."""
    pages_by_source = {str(page.source_path): page for page in pages}
    pages_by_url = {page.output_url: page for page in pages}
    items: list[NavItem] = []
    for entry in nav_config:
        for title, target in entry.items():
            items.append(
                _build_explicit_item(
                    title, target, pages_by_source, pages_by_url, pages, listing_paths
                )
            )
    return items


def _build_explicit_item(
    title: str,
    target: object,
    pages_by_source: dict[str, Page],
    pages_by_url: dict[str, Page],
    pages: list[Page],
    listing_paths: tuple[str, ...],
) -> NavItem:
    """Resolve a single explicit-nav entry into a NavItem (with children)."""
    if isinstance(target, list):
        children = [
            _build_explicit_item(
                child_title, child_target, pages_by_source, pages_by_url, pages, listing_paths
            )
            for child_entry in target
            if isinstance(child_entry, dict)
            for child_title, child_target in child_entry.items()
        ]
        index_url = next(
            (
                child.url
                for child in children
                if child.page is not None and child.page.source_path.name == "index.md"
            ),
            None,
        )
        return NavItem(title=title, children=children, is_section=True, index_url=index_url)
    if not isinstance(target, str):
        return NavItem(title=title)
    page = pages_by_source.get(target)
    if page is None and target.endswith("/") and not _is_listing_dir(target, listing_paths):
        return _directory_section(title, target.strip("/"), pages, listing_paths)
    if page is None:
        return NavItem(title=title, url=_target_to_url(target))
    return NavItem(title=title, url=page.output_url, page=page)


def _auto_generate_nav(pages: list[Page], listing_paths: tuple[str, ...]) -> list[NavItem]:
    """Synthesize a nav from the page set, expanding each top-level directory."""
    items: list[NavItem] = []
    section_dirs: set[str] = set()
    for page in pages:
        parts = page.source_path.parts
        if len(parts) == 1:
            items.append(NavItem(title=page.title, url=page.output_url, page=page))
        else:
            section_dirs.add(parts[0])
    for name in section_dirs:
        title = name.replace("-", " ").replace("_", " ").title()
        if _is_listing_dir(name, listing_paths):
            items.append(NavItem(title=title, url=_target_to_url(name + "/")))
        else:
            items.append(_directory_section(title, name, pages, listing_paths))
    items.sort(key=lambda item: item.title.lower())
    return items


def _is_listing_dir(directory: str, listing_paths: tuple[str, ...]) -> bool:
    """True when ``directory`` is a content-type path or contains one.

    Those directories are rendered as a generated listing, so their posts stay out
    of the sidebar tree.
    """
    directory = directory.strip("/")
    return any(path == directory or path.startswith(directory + "/") for path in listing_paths)


def _directory_section(
    title: str,
    directory: str,
    pages: list[Page],
    listing_paths: tuple[str, ...],
) -> NavItem:
    """Expand ``directory`` into a section: its index, its pages, and nested sections."""
    prefix = directory + "/"
    index_page: Page | None = None
    children: list[NavItem] = []
    subdirectories: set[str] = set()
    for page in pages:
        source = page.source_path.as_posix()
        if not source.startswith(prefix):
            continue
        relative_parts = source[len(prefix) :].split("/")
        if len(relative_parts) > 1:
            subdirectories.add(relative_parts[0])
        elif relative_parts[0] == "index.md":
            index_page = page
        else:
            children.append(NavItem(title=page.title, url=page.output_url, page=page))
    for name in subdirectories:
        nested = prefix + name
        nested_title = name.replace("-", " ").replace("_", " ").title()
        if _is_listing_dir(nested, listing_paths):
            children.append(NavItem(title=nested_title, url=_target_to_url(nested + "/")))
        else:
            children.append(_directory_section(nested_title, nested, pages, listing_paths))
    children.sort(key=lambda item: item.title.lower())
    if index_page is None:
        return NavItem(title=title, children=children, is_section=True)
    index_item = NavItem(title=index_page.title, url=index_page.output_url, page=index_page)
    return NavItem(
        title=title,
        url=index_page.output_url,
        children=[index_item, *children],
        is_section=True,
        index_url=index_page.output_url,
    )


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
