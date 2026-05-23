# ABOUTME: Static file copying and co-located asset handling.
# Copies static/ → site root and co-located assets to each page's output URL directory.

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from bartleby.content import ColocatedAsset, Page


def copy_static_files(static_dir: Path, output_dir: Path) -> None:
    """Recursively copy ``static_dir`` into ``output_dir``.

    Missing or empty ``static_dir`` is a no-op so callers don't need a
    pre-check.
    """
    if not static_dir.exists():
        return
    for source in static_dir.rglob("*"):
        if source.is_dir():
            continue
        relative = source.relative_to(static_dir)
        destination = output_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def copy_colocated_assets(
    assets: list[ColocatedAsset],
    pages: list[Page],
    content_dir: Path,
    output_dir: Path,
) -> None:
    """Copy each co-located asset to follow its associated page's output URL.

    :param assets: Assets discovered alongside content (e.g. images, PDFs).
    :param pages: All published pages (used to map assets to URL prefixes).
    :param content_dir: The site's ``content/`` directory (only used for
        parity with the spec; kept for future page-by-source-path lookups).
    :param output_dir: The build's ``site/`` directory.
    """
    del content_dir  # currently unused — kept to match spec signature
    page_by_dir = {page.source_path.parent.as_posix(): page for page in pages}
    for asset in assets:
        associated_page = _find_associated_page(asset, page_by_dir)
        destination = _destination_for(asset, associated_page, output_dir)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset.abs_source_path, destination)


def _find_associated_page(asset: ColocatedAsset, page_by_dir: dict[str, Page]) -> Page | None:
    """Return the page that lives in the same directory as ``asset``, if any."""
    asset_dir = asset.source_path.parent.as_posix()
    return page_by_dir.get(asset_dir)


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
