# ABOUTME: Static file copying and co-located asset handling.
# Copies static/ → site root and co-located assets to each page's output URL directory.

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from bartleby.content import ColocatedAsset, Page


class AssetCollisionError(Exception):
    """Raised when a co-located asset's directory holds more than one page.

    The v1 spec assumes one page per bundle directory (the Hugo leaf-bundle
    model) and leaves the shared-directory case undefined. Rather than guess
    which page an asset belongs to, the build fails loudly and names the
    directory and every page sharing it, so the user restructures into one
    bundle directory per page.

    :ivar directory: The shared source directory, relative to ``content/``.
    :ivar page_paths: Source paths (relative to ``content/``) of every page
        sharing ``directory``.
    """

    def __init__(self, directory: str, page_paths: list[str]) -> None:
        self.directory = directory
        self.page_paths = page_paths
        pages = ", ".join(page_paths)
        super().__init__(
            f"directory {directory!r} holds a co-located asset and more than one "
            f"page ({pages}); split it into one bundle directory per page"
        )


def copy_static_files(static_dir: Path, output_dir: Path) -> int:
    """Recursively copy ``static_dir`` into ``output_dir``.

    Missing or empty ``static_dir`` is a no-op so callers don't need a
    pre-check.

    :returns: The number of files copied.
    """
    if not static_dir.exists():
        return 0
    copied = 0
    for source in static_dir.rglob("*"):
        if source.is_dir():
            continue
        relative = source.relative_to(static_dir)
        destination = output_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied += 1
    return copied


def copy_colocated_assets(
    assets: list[ColocatedAsset],
    pages: list[Page],
    content_dir: Path,
    output_dir: Path,
) -> int:
    """Copy each co-located asset to follow its associated page's output URL.

    :param assets: Assets discovered alongside content (e.g. images, PDFs).
    :param pages: All published pages (used to map assets to URL prefixes).
    :param content_dir: The site's ``content/`` directory (only used for
        parity with the spec; kept for future page-by-source-path lookups).
    :param output_dir: The build's ``site/`` directory.
    :returns: The number of assets copied.
    :raises AssetCollisionError: When an asset's directory holds more than
        one page (see :class:`AssetCollisionError`).
    """
    del content_dir  # currently unused — kept to match spec signature
    pages_by_dir: dict[str, list[Page]] = {}
    for page in pages:
        pages_by_dir.setdefault(page.source_path.parent.as_posix(), []).append(page)
    copied = 0
    for asset in assets:
        associated_page = _find_associated_page(asset, pages_by_dir)
        destination = _destination_for(asset, associated_page, output_dir)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset.abs_source_path, destination)
        copied += 1
    return copied


def drop_draft_only_assets(
    assets: list[ColocatedAsset], all_pages: list[Page], published_pages: list[Page]
) -> list[ColocatedAsset]:
    """Drop assets whose directory held only pages that draft filtering removed.

    An asset survives when its directory still contains a published page, or
    when it never had any associated page to begin with (a genuine orphan,
    unaffected by draft filtering — see the fallback in
    :func:`copy_colocated_assets`). Without this, a draft's co-located asset
    falls through that same orphan fallback and leaks into the output at its
    source path once the draft page itself is filtered out.

    :param assets: Every discovered co-located asset, before draft filtering.
    :param all_pages: Every discovered page, drafts included.
    :param published_pages: The subset of ``all_pages`` surviving draft filtering.
    :returns: The assets whose directory still has a published page, or never
        had a page at all.
    """
    published_dirs = {page.source_path.parent.as_posix() for page in published_pages}
    all_dirs = {page.source_path.parent.as_posix() for page in all_pages}
    draft_only_dirs = all_dirs - published_dirs
    return [
        asset for asset in assets if asset.source_path.parent.as_posix() not in draft_only_dirs
    ]


def _find_associated_page(
    asset: ColocatedAsset, pages_by_dir: dict[str, list[Page]]
) -> Page | None:
    """Return the page that lives in the same directory as ``asset``, if any.

    The collision check fires here, at the point an asset actually resolves
    to a directory, rather than up front over every directory two pages
    happen to share: a shared directory with no assets is legal, so nothing
    should be checked until an asset needs an association.

    :raises AssetCollisionError: When ``asset``'s directory holds more than
        one page.
    """
    asset_dir = asset.source_path.parent.as_posix()
    directory_pages = pages_by_dir.get(asset_dir, [])
    if len(directory_pages) > 1:
        raise AssetCollisionError(asset_dir, [str(page.source_path) for page in directory_pages])
    return directory_pages[0] if directory_pages else None


def _destination_for(
    asset: ColocatedAsset, associated_page: Page | None, output_dir: Path
) -> Path:
    """Compute the asset's output path, following the page URL when available."""
    if associated_page is None:
        return output_dir / asset.source_path
    url = associated_page.output_url.strip("/")
    if url:
        return output_dir / url / asset.source_path.name
    return output_dir / asset.source_path.name
