# ABOUTME: Tests for theme manifest parsing and extends-chain resolution.
# Covers path, bundled, and entry-point sources plus cycle and error paths using fixture themes.

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from bartleby import theme_loader
from bartleby.theme_loader import ThemeError, load_manifest, resolve_theme
from bartleby.themes import bundled_theme_root

if TYPE_CHECKING:
    from collections.abc import Iterable

THEMES = Path(__file__).parent / "fixtures" / "themes"


class FakeEntryPoint:
    """Stand-in for importlib.metadata.EntryPoint."""

    def __init__(self, name: str, value: Path | str | int) -> None:
        self.name = name
        self._value = value

    def load(self) -> Path | str | int:
        return self._value


def _patch_entry_points(
    monkeypatch: pytest.MonkeyPatch, entry_points: Iterable[FakeEntryPoint]
) -> list[str]:
    requested_groups: list[str] = []

    def fake_entry_points(*, group: str) -> list[FakeEntryPoint]:
        requested_groups.append(group)
        return list(entry_points)

    monkeypatch.setattr("importlib.metadata.entry_points", fake_entry_points)
    return requested_groups


def test_load_manifest_parses_all_fields() -> None:
    manifest = load_manifest(THEMES / "parent")

    assert manifest.name == "parent"
    assert manifest.version == "1.0.0"
    assert manifest.description == "Fixture parent theme."
    assert manifest.extends is None
    assert manifest.features == ["search"]


def test_load_manifest_defaults_optional_fields() -> None:
    manifest = load_manifest(THEMES / "child")

    assert manifest.extends == "parent"
    assert manifest.version is None
    assert manifest.description is None
    assert manifest.features == []


def test_missing_manifest_names_directory(tmp_path: Path) -> None:
    with pytest.raises(ThemeError, match=str(tmp_path)):
        load_manifest(tmp_path)


def test_manifest_without_name_names_directory_and_key(tmp_path: Path) -> None:
    (tmp_path / "theme.yml").write_text("version: '1'\n", encoding="utf-8")

    with pytest.raises(ThemeError, match=rf"{tmp_path}.*'name'"):
        load_manifest(tmp_path)


def test_manifest_that_is_not_a_mapping_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "theme.yml").write_text("- just\n- a list\n", encoding="utf-8")

    with pytest.raises(ThemeError, match="mapping"):
        load_manifest(tmp_path)


def test_manifest_features_must_be_a_list_of_strings(tmp_path: Path) -> None:
    (tmp_path / "theme.yml").write_text("name: x\nfeatures: search\n", encoding="utf-8")

    with pytest.raises(ThemeError, match="features"):
        load_manifest(tmp_path)


def test_manifest_rejects_feature_outside_native_vocabulary(tmp_path: Path) -> None:
    (tmp_path / "theme.yml").write_text(
        "name: x\nfeatures:\n  - navigation.tabs\n", encoding="utf-8"
    )

    with pytest.raises(ThemeError, match=r"navigation\.tabs"):
        load_manifest(tmp_path)


def test_default_theme_declares_the_features_its_templates_honor() -> None:
    resolved = theme_loader.default_theme()
    assert [layer.name for layer in resolved.chain] == ["material", "base"]
    manifest = resolved.chain[0].manifest

    assert set(manifest.features) == {
        "search",
        "nav.tabs",
        "nav.sidebar",
        "nav.section-index",
        "nav.back-to-top",
        "content.code.copy",
        "color-mode.toggle",
    }
    assert set(manifest.features) <= theme_loader.THEME_FEATURES


def test_manifest_scalar_fields_must_be_strings(tmp_path: Path) -> None:
    (tmp_path / "theme.yml").write_text("name: x\nextends: [a, b]\n", encoding="utf-8")

    with pytest.raises(ThemeError, match="extends"):
        load_manifest(tmp_path)


def test_resolve_child_yields_leaf_first_chain() -> None:
    resolved = resolve_theme(path=str(THEMES / "child"), project_dir=Path("/unused"))

    assert [layer.name for layer in resolved.chain] == ["child", "parent"]
    assert [layer.root for layer in resolved.chain] == [THEMES / "child", THEMES / "parent"]


def test_resolve_relative_path_uses_project_dir() -> None:
    resolved = resolve_theme(path="child", project_dir=THEMES)

    assert resolved.chain[0].root == THEMES / "child"


def test_layer_dirs_are_leaf_first_and_only_existing() -> None:
    resolved = resolve_theme(path="child", project_dir=THEMES)

    assert resolved.templates_dirs() == [
        THEMES / "child" / "templates",
        THEMES / "parent" / "templates",
    ]
    assert resolved.static_dirs() == [
        THEMES / "child" / "static",
        THEMES / "parent" / "static",
    ]
    assert resolved.icons_dirs() == [
        THEMES / "child" / "icons",
        THEMES / "parent" / "icons",
    ]


def test_cyclic_extends_names_both_themes() -> None:
    with pytest.raises(ThemeError, match=r"cyclic-a.*cyclic-b"):
        resolve_theme(path="cyclic-a", project_dir=THEMES)


def test_extends_bundled_name_resolves_to_bundled_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundled_base = tmp_path / "bundled" / "base"
    bundled_base.mkdir(parents=True)
    (bundled_base / "theme.yml").write_text("name: base\n", encoding="utf-8")
    monkeypatch.setattr(
        theme_loader, "bundled_theme_root", lambda name: tmp_path / "bundled" / name
    )
    own = tmp_path / "own"
    own.mkdir()
    (own / "theme.yml").write_text("name: own\nextends: base\n", encoding="utf-8")

    resolved = resolve_theme(path="own", project_dir=tmp_path)

    assert [layer.root for layer in resolved.chain] == [own, bundled_base]


def test_bundled_theme_root_points_inside_the_package() -> None:
    root = bundled_theme_root("base")

    assert root.name == "base"
    assert root.parent.name == "themes"
    assert root.parent.parent.name == "bartleby"


def test_unknown_bundled_name_is_rejected() -> None:
    with pytest.raises(ThemeError, match="nonesuch"):
        resolve_theme(name="nonesuch", project_dir=THEMES)


def test_nonexistent_path_names_the_path(tmp_path: Path) -> None:
    with pytest.raises(ThemeError, match="no-such-theme"):
        resolve_theme(path="no-such-theme", project_dir=tmp_path)


def test_package_source_consults_entry_point_group(monkeypatch: pytest.MonkeyPatch) -> None:
    groups = _patch_entry_points(monkeypatch, [FakeEntryPoint("acme-theme", THEMES / "child")])

    resolved = resolve_theme(package="acme-theme", project_dir=THEMES)

    assert groups == ["bartleby.themes"]
    assert [layer.name for layer in resolved.chain] == ["child", "parent"]


def test_missing_package_names_the_package(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_entry_points(monkeypatch, [])

    with pytest.raises(ThemeError, match="acme-theme"):
        resolve_theme(package="acme-theme", project_dir=THEMES)


def test_package_entry_point_must_load_to_a_path(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_entry_points(monkeypatch, [FakeEntryPoint("acme-theme", 42)])

    with pytest.raises(ThemeError, match="acme-theme"):
        resolve_theme(package="acme-theme", project_dir=THEMES)


def test_package_entry_point_with_missing_directory_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_entry_points(monkeypatch, [FakeEntryPoint("acme-theme", tmp_path / "gone")])

    with pytest.raises(ThemeError, match="gone"):
        resolve_theme(package="acme-theme", project_dir=THEMES)


def test_extends_falls_back_to_entry_point_package(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "own").mkdir()
    (tmp_path / "own" / "theme.yml").write_text(
        "name: own\nextends: acme-theme\n", encoding="utf-8"
    )
    _patch_entry_points(monkeypatch, [FakeEntryPoint("acme-theme", THEMES / "parent")])

    resolved = resolve_theme(path="own", project_dir=tmp_path)

    assert [layer.name for layer in resolved.chain] == ["own", "parent"]


def test_selecting_multiple_sources_is_rejected() -> None:
    with pytest.raises(ThemeError, match="exactly one"):
        resolve_theme(name="base", path="child", project_dir=THEMES)


def test_selecting_no_source_is_rejected() -> None:
    with pytest.raises(ThemeError, match="exactly one"):
        resolve_theme(project_dir=THEMES)


def test_bundled_base_resolves() -> None:
    resolved = resolve_theme(name="base", project_dir=THEMES)

    assert [layer.name for layer in resolved.chain] == ["base"]


def test_bundled_material_resolves_with_base_parent() -> None:
    resolved = resolve_theme(name="material", project_dir=THEMES)

    assert [layer.name for layer in resolved.chain] == ["material", "base"]


@pytest.mark.xfail(reason="bundled scrivener theme lands in Step 11", strict=True)
def test_bundled_scrivener_resolves() -> None:
    resolved = resolve_theme(name="scrivener", project_dir=THEMES)

    assert resolved.chain[0].name == "scrivener"
