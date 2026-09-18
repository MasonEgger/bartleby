# ABOUTME: Tests for icon pack bundling, resolution, and tree-shaking.
# Covers per-pack resolution, disabled packs, and build-time tree-shaking of unused icons.

from __future__ import annotations

from typing import TYPE_CHECKING

from bartleby.icons import get_icon_path, tree_shake_icons

if TYPE_CHECKING:
    from pathlib import Path


def test_resolve_material_icon() -> None:
    """``:material-account:`` resolves to a bundled SVG path."""
    result = get_icon_path("material-account", {"material": True})
    assert result is not None
    assert result.exists()
    assert result.suffix == ".svg"


def test_resolve_fontawesome_icon() -> None:
    """``:fontawesome-brands-github:`` resolves to a bundled SVG."""
    result = get_icon_path("fontawesome-brands-github", {"fontawesome": True})
    assert result is not None
    assert result.exists()


def test_resolve_octicons_icon() -> None:
    """``:octicons-heart-fill-24:`` resolves to a bundled SVG."""
    result = get_icon_path("octicons-heart-fill-24", {"octicons": True})
    assert result is not None
    assert result.exists()


def test_resolve_simple_icon() -> None:
    """``:simple-python:`` resolves to a bundled SVG."""
    result = get_icon_path("simple-python", {"simple": True})
    assert result is not None
    assert result.exists()


def test_each_pack_vendors_multiple_icons() -> None:
    """Every pack ships more than a single stub icon so it is usable in practice."""
    samples = {
        "material": ["material-account", "material-home", "material-magnify", "material-close"],
        "fontawesome": ["fontawesome-brands-github", "fontawesome-brands-twitter"],
        "octicons": ["octicons-mark-github-16", "octicons-star-16", "octicons-repo-16"],
        "simple": ["simple-python", "simple-github", "simple-rust"],
    }
    for pack, names in samples.items():
        for name in names:
            assert get_icon_path(name, {pack: True}) is not None, name


def test_disabled_pack_not_resolved() -> None:
    """A pack with ``False`` in the icon_packs map returns ``None``."""
    assert get_icon_path("material-account", {"material": False}) is None


def test_unknown_icon_returns_none() -> None:
    """An icon outside the bundled set returns ``None``."""
    assert get_icon_path("material-does-not-exist", {"material": True}) is None


def test_tree_shake_includes_used(tmp_path: Path) -> None:
    """An icon referenced in rendered HTML is copied to the output icons directory."""
    rendered = ['<svg class="icon icon-material-account">…</svg>']
    tree_shake_icons(rendered, {"material": True}, tmp_path)
    assert (tmp_path / "icons" / "material" / "account.svg").exists()


def test_tree_shake_excludes_unused(tmp_path: Path) -> None:
    """Icons not referenced in any page are not copied to the output."""
    rendered = ["<p>no icons here</p>"]
    tree_shake_icons(rendered, {"material": True, "fontawesome": True}, tmp_path)
    assert not (tmp_path / "icons" / "material" / "account.svg").exists()


def test_tree_shake_unreferenced_pack_contributes_zero_files(tmp_path: Path) -> None:
    """A pack with no referenced icons contributes zero files to the output.

    One material icon is referenced; fontawesome is enabled but unreferenced,
    so its output directory must not be created at all.
    """
    rendered = ['<svg class="icon icon-material-account">…</svg>']
    enabled = {"material": True, "fontawesome": True, "octicons": True, "simple": True}
    tree_shake_icons(rendered, enabled, tmp_path)
    assert (tmp_path / "icons" / "material" / "account.svg").exists()
    assert not (tmp_path / "icons" / "fontawesome-brands").exists()
    assert not (tmp_path / "icons" / "octicons").exists()
    assert not (tmp_path / "icons" / "simple").exists()


def test_all_packs_enabled_by_default_can_be_listed() -> None:
    """All four pack names are accepted by ``get_icon_path``."""
    enabled = {"material": True, "fontawesome": True, "octicons": True, "simple": True}
    assert get_icon_path("material-account", enabled) is not None
    assert get_icon_path("fontawesome-brands-github", enabled) is not None
    assert get_icon_path("octicons-heart-fill-24", enabled) is not None
    assert get_icon_path("simple-python", enabled) is not None
