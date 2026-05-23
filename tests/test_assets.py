# ABOUTME: Tests for static file copying and co-located asset handling.
# Covers static/ tree, co-located asset URL following, and missing-static edge case.

from __future__ import annotations

from pathlib import Path

from bartleby.assets import copy_colocated_assets, copy_static_files
from bartleby.content import ColocatedAsset, Page


def test_copy_static_to_root(tmp_path: Path) -> None:
    """A file at ``static/logo.png`` is copied to ``site/logo.png``."""
    static = tmp_path / "static"
    static.mkdir()
    (static / "logo.png").write_bytes(b"stub-png")
    output = tmp_path / "site"
    output.mkdir()
    copy_static_files(static, output)
    assert (output / "logo.png").read_bytes() == b"stub-png"


def test_copy_static_preserves_subdirs(tmp_path: Path) -> None:
    """Subdirectories under ``static/`` are preserved verbatim."""
    static = tmp_path / "static"
    (static / "css").mkdir(parents=True)
    (static / "css" / "custom.css").write_text("body{}")
    output = tmp_path / "site"
    output.mkdir()
    copy_static_files(static, output)
    assert (output / "css" / "custom.css").read_text() == "body{}"


def test_colocated_asset_path_based(tmp_path: Path) -> None:
    """When the associated page's URL matches its source, the asset stays in place."""
    content_dir = tmp_path / "content"
    (content_dir / "blog" / "posts").mkdir(parents=True)
    asset_src = content_dir / "blog" / "posts" / "diagram.png"
    asset_src.write_bytes(b"png-bytes")

    page = Page(
        source_path=Path("blog/posts/my-post.md"),
        abs_source_path=content_dir / "blog/posts/my-post.md",
        title="My Post",
    )
    page.output_url = "/blog/posts/my-post/"
    asset = ColocatedAsset(
        source_path=Path("blog/posts/diagram.png"),
        abs_source_path=asset_src,
    )
    output = tmp_path / "site"
    output.mkdir()

    copy_colocated_assets([asset], [page], content_dir, output)
    assert (output / "blog" / "posts" / "my-post" / "diagram.png").read_bytes() == b"png-bytes"


def test_colocated_asset_follows_url_format(tmp_path: Path) -> None:
    """When a content type's url_format relocates the page, the asset follows."""
    content_dir = tmp_path / "content"
    (content_dir / "blog" / "posts").mkdir(parents=True)
    asset_src = content_dir / "blog" / "posts" / "diagram.png"
    asset_src.write_bytes(b"png")

    page = Page(
        source_path=Path("blog/posts/my-post.md"),
        abs_source_path=content_dir / "blog/posts/my-post.md",
        title="My Post",
    )
    page.output_url = "/blog/2026/03/01/my-post/"
    asset = ColocatedAsset(
        source_path=Path("blog/posts/diagram.png"),
        abs_source_path=asset_src,
    )
    output = tmp_path / "site"
    output.mkdir()

    copy_colocated_assets([asset], [page], content_dir, output)
    assert (output / "blog" / "2026" / "03" / "01" / "my-post" / "diagram.png").exists()


def test_binary_files_copied_unchanged(tmp_path: Path) -> None:
    """Binary file contents are preserved byte-for-byte across the copy."""
    static = tmp_path / "static"
    static.mkdir()
    payload = bytes(range(256))
    (static / "blob.bin").write_bytes(payload)
    output = tmp_path / "site"
    output.mkdir()
    copy_static_files(static, output)
    assert (output / "blob.bin").read_bytes() == payload


def test_empty_static_dir_ok(tmp_path: Path) -> None:
    """A missing ``static/`` directory is not an error."""
    output = tmp_path / "site"
    output.mkdir()
    copy_static_files(tmp_path / "missing", output)  # No exception expected.


def test_orphan_asset_lands_at_source_path(tmp_path: Path) -> None:
    """An asset with no associated page is copied to its source-relative path."""
    content_dir = tmp_path / "content"
    (content_dir / "loose").mkdir(parents=True)
    asset_src = content_dir / "loose" / "unused.png"
    asset_src.write_bytes(b"x")
    asset = ColocatedAsset(
        source_path=Path("loose/unused.png"),
        abs_source_path=asset_src,
    )
    output = tmp_path / "site"
    output.mkdir()
    copy_colocated_assets([asset], [], content_dir, output)
    assert (output / "loose" / "unused.png").exists()
