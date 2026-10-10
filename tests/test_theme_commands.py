# ABOUTME: Tests for the `bartleby theme eject` and `bartleby theme inspect` commands.
# Covers flattening, overwrite protection, shadow marking, JSON stability, and eject-edit-build.

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from bartleby.cli import main
from bartleby.theme_loader import (
    ThemeError,
    flatten_chain,
    inspect_chain,
    resolve_theme,
)
from bartleby.themes import bundled_theme_root
from tests.theme_helpers import material_theme

THEMES = Path(__file__).parent / "fixtures" / "themes"


def _project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, theme_path: Path | None) -> Path:
    """Scaffold a site, point its theme at ``theme_path`` (if given), and chdir into it."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    project = tmp_path / "mysite"
    if theme_path is not None:
        config = project / "bartleby.yml"
        config.write_text(
            config.read_text(encoding="utf-8") + f"\ntheme:\n  path: {theme_path}\n",
            encoding="utf-8",
        )
    monkeypatch.chdir(project)
    return project


def _json_out(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    line = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()][-1]
    parsed: dict[str, object] = json.loads(line)
    return parsed


class TestEject:
    def test_flattens_chain_leaf_wins(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        project = _project(tmp_path, monkeypatch, THEMES / "child")
        main(["theme", "eject"])

        target = project / "themes" / "child"
        assert (target / "templates" / "parent_only.html").read_text() == (
            THEMES / "parent" / "templates" / "parent_only.html"
        ).read_text()
        assert (target / "templates" / "child_only.html").is_file()
        assert (target / "templates" / "shared.html").read_text() == "child shared template\n"
        assert (target / "static" / "parent.txt").is_file()
        assert (target / "icons" / "material" / "parent-icon.svg").is_file()
        assert (target / "tailwind.css").is_file()
        assert (target / "tailwind.config.js").is_file()

        manifest = yaml.safe_load((target / "theme.yml").read_text(encoding="utf-8"))
        assert manifest["name"] == "child"
        assert "extends" not in manifest
        assert manifest["features"] == ["search"]
        out = capsys.readouterr().out
        assert "theme:\n  path: themes/child" in out

    def test_refuses_existing_target_without_force(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        project = _project(tmp_path, monkeypatch, THEMES / "child")
        (project / "themes" / "child").mkdir(parents=True)

        with pytest.raises(SystemExit) as exc:
            main(["theme", "eject"])
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "themes/child" in err
        assert "theme_error" in err
        assert "Traceback" not in err

        main(["theme", "eject", "--force"])
        assert (project / "themes" / "child" / "theme.yml").is_file()

    def test_to_honors_destination(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        project = _project(tmp_path, monkeypatch, THEMES / "child")
        main(["theme", "eject", "--to", "custom/place", "--output", "json"])

        assert (project / "custom" / "place" / "theme.yml").is_file()
        assert not (project / "themes").exists()
        payload = _json_out(capsys)
        assert payload["target"] == "custom/place"
        assert payload["config"] == "theme:\n  path: custom/place"

    def test_ejects_default_theme_flattened(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = _project(tmp_path, monkeypatch, None)
        main(["theme", "eject"])

        target = project / "themes" / "scrivener"
        manifest = yaml.safe_load((target / "theme.yml").read_text(encoding="utf-8"))
        assert manifest["name"] == "scrivener"
        assert "extends" not in manifest
        assert "search" in manifest["features"]
        assert (target / "templates" / "base.html").is_file()
        assert (target / "templates" / "partials" / "header.html").is_file()

    @pytest.fixture
    def themes_copy(self, tmp_path: Path) -> Path:
        """A throwaway copy of the fixture themes, so the guard tests never write into tests/."""
        copy = tmp_path / "themes-copy"
        shutil.copytree(THEMES, copy)
        return copy

    def test_refuses_to_eject_onto_a_chain_layer(self, tmp_path: Path, themes_copy: Path) -> None:
        resolved = resolve_theme(project_dir=tmp_path, path=str(themes_copy / "child"))
        with pytest.raises(ThemeError, match="part of the theme"):
            flatten_chain(resolved, themes_copy / "parent", project_dir=tmp_path, force=True)

    def test_refuses_destination_nested_in_a_layer_root(
        self, tmp_path: Path, themes_copy: Path
    ) -> None:
        resolved = resolve_theme(project_dir=tmp_path, path=str(themes_copy / "child"))
        nested = themes_copy / "child" / "templates" / "out"
        with pytest.raises(ThemeError, match="inside") as exc:
            flatten_chain(resolved, nested, project_dir=tmp_path)
        assert str(nested) in str(exc.value)
        assert str(themes_copy / "child") in str(exc.value)
        assert not nested.exists()

    def test_refuses_layer_root_nested_in_destination(
        self, tmp_path: Path, themes_copy: Path
    ) -> None:
        resolved = resolve_theme(project_dir=tmp_path, path=str(themes_copy / "child"))
        with pytest.raises(ThemeError, match="inside") as exc:
            flatten_chain(resolved, themes_copy, project_dir=tmp_path, force=True)
        assert str(themes_copy) in str(exc.value)

    def test_flatten_unions_features_across_chain(self, tmp_path: Path) -> None:
        theme_root = tmp_path / "kid"
        (theme_root / "templates").mkdir(parents=True)
        shutil.copytree(THEMES / "parent", tmp_path / "parent")
        (theme_root / "theme.yml").write_text(
            "name: kid\nextends: parent\nfeatures: [nav.tabs]\n", encoding="utf-8"
        )
        resolved = resolve_theme(project_dir=tmp_path, path=str(theme_root))

        result = flatten_chain(resolved, tmp_path / "out", project_dir=tmp_path)

        manifest = yaml.safe_load((tmp_path / "out" / "theme.yml").read_text(encoding="utf-8"))
        assert manifest["features"] == ["nav.tabs", "search"]
        assert result.to_dict()["theme"] == "kid"
        assert "Ejected theme 'kid'" in result.to_text()


class TestInspect:
    def test_text_lists_files_with_layers_and_shadowing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        project = _project(tmp_path, monkeypatch, THEMES / "child")
        (project / "overrides").mkdir()
        (project / "overrides" / "shared.html").write_text("mine", encoding="utf-8")
        main(["theme", "inspect"])

        lines = capsys.readouterr().out.splitlines()
        assert "templates/parent_only.html  (parent)" in lines
        assert "templates/child_only.html  (child)" in lines
        assert "templates/shared.html  (child)  [shadowed by overrides/shared.html]" in lines
        assert "tailwind.css  (parent)" in lines

    def test_json_is_sorted_and_stable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        project = _project(tmp_path, monkeypatch, THEMES / "child")
        (project / "overrides").mkdir()
        (project / "overrides" / "shared.html").write_text("mine", encoding="utf-8")

        main(["theme", "inspect", "--output", "json"])
        first = _json_out(capsys)
        main(["theme", "inspect", "--output", "json"])
        second = _json_out(capsys)

        assert first == second
        assert first["chain"] == ["child", "parent"]
        files = first["files"]
        assert isinstance(files, list)
        paths = [entry["path"] for entry in files]
        assert paths == sorted(paths)
        by_path = {entry["path"]: entry for entry in files}
        assert by_path["templates/shared.html"] == {
            "path": "templates/shared.html",
            "kind": "template",
            "layer": "child",
            "shadowed_by": "overrides/shared.html",
        }
        assert by_path["static/parent.txt"]["kind"] == "static"
        assert by_path["static/parent.txt"]["shadowed_by"] is None
        assert by_path["icons/material/parent-icon.svg"]["kind"] == "icon"
        assert by_path["tailwind.config.js"]["kind"] == "tailwind"

    @staticmethod
    def _shadow_of(project: Path, template: str) -> str | None:
        result = inspect_chain(material_theme(), project)
        return next(item.shadowed_by for item in result.files if item.path == template)

    def test_templates_dir_shadows_theme_template(self, tmp_path: Path) -> None:
        (tmp_path / "templates").mkdir()
        (tmp_path / "templates" / "base.html").write_text("x", encoding="utf-8")
        assert self._shadow_of(tmp_path, "templates/base.html") == "templates/base.html"

    def test_project_root_shadows_theme_template(self, tmp_path: Path) -> None:
        (tmp_path / "base.html").write_text("x", encoding="utf-8")
        assert self._shadow_of(tmp_path, "templates/base.html") == "base.html"

    def test_overrides_win_over_templates_dir(self, tmp_path: Path) -> None:
        for directory in ("overrides", "templates"):
            (tmp_path / directory).mkdir()
            (tmp_path / directory / "base.html").write_text("x", encoding="utf-8")
        assert self._shadow_of(tmp_path, "templates/base.html") == "overrides/base.html"

    def test_inspect_material_theme_reports_material_over_base(self, tmp_path: Path) -> None:
        result = inspect_chain(material_theme(), tmp_path)
        assert result.chain == ["material", "base"]
        assert {item.layer for item in result.files} == {"material", "base"}

    def test_theme_error_is_a_clean_cli_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _project(tmp_path, monkeypatch, tmp_path / "no-such-theme")

        with pytest.raises(SystemExit) as exc:
            main(["theme", "inspect"])
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "theme_error" in err
        assert "no-such-theme" in err
        assert "Traceback" not in err


class TestEjectEditBuild:
    @staticmethod
    def _eject_edit_build(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, theme_path: Path | None
    ) -> str:
        project = _project(tmp_path, monkeypatch, theme_path)
        main(["theme", "eject"])
        ejected = next((project / "themes").iterdir())

        config = project / "bartleby.yml"
        text = config.read_text(encoding="utf-8")
        text = text.split("\ntheme:\n")[0]
        config.write_text(f"{text}\ntheme:\n  path: themes/{ejected.name}\n", encoding="utf-8")
        page = ejected / "templates" / "page.html"
        page.write_text(
            page.read_text(encoding="utf-8").replace("<p>", "<p>EJECTED-EDIT-MARKER "),
            encoding="utf-8",
        )

        main(["build"])
        return (project / "site" / "index.html").read_text(encoding="utf-8")

    def test_edit_to_ejected_fixture_theme_shows_in_build(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        html = self._eject_edit_build(tmp_path, monkeypatch, THEMES / "child")
        assert "EJECTED-EDIT-MARKER CHILD-PAGE-TEMPLATE" in html

    def test_edit_to_ejected_material_shows_in_build(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        main(["new", "site", "mysite"])
        project = tmp_path / "mysite"
        config = project / "bartleby.yml"
        config.write_text(
            config.read_text(encoding="utf-8") + "\ntheme:\n  name: material\n", encoding="utf-8"
        )
        monkeypatch.chdir(project)
        main(["theme", "eject"])
        ejected = project / "themes" / "material"
        config.write_text(
            config.read_text(encoding="utf-8").replace("name: material", "path: themes/material"),
            encoding="utf-8",
        )
        header = ejected / "templates" / "partials" / "header.html"
        header.write_text(
            header.read_text(encoding="utf-8") + "\nEJECTED-EDIT-MARKER\n", encoding="utf-8"
        )

        main(["build"])

        assert "EJECTED-EDIT-MARKER" in (project / "site" / "index.html").read_text(
            encoding="utf-8"
        )


class TestEjectSafelist:
    @pytest.mark.parametrize("theme_name", ["material", "scrivener"])
    def test_eject_copies_the_bundled_safelist(self, theme_name: str, tmp_path: Path) -> None:
        resolved = resolve_theme(name=theme_name, project_dir=tmp_path)

        flatten_chain(resolved, tmp_path / "out", project_dir=tmp_path)

        ejected = tmp_path / "out" / "safelist.txt"
        source = bundled_theme_root(theme_name) / "safelist.txt"
        assert ejected.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")

    def test_child_safelist_wins_over_parent(self, tmp_path: Path) -> None:
        parent = tmp_path / "parent"
        child = tmp_path / "child"
        for root in (parent, child):
            (root / "templates").mkdir(parents=True)
        (parent / "theme.yml").write_text("name: parent\n", encoding="utf-8")
        (parent / "safelist.txt").write_text("from-parent\n", encoding="utf-8")
        (child / "theme.yml").write_text(f"name: child\nextends: {parent}\n", encoding="utf-8")
        (child / "safelist.txt").write_text("from-child\n", encoding="utf-8")
        resolved = resolve_theme(project_dir=tmp_path, path=str(child))

        flatten_chain(resolved, tmp_path / "out", project_dir=tmp_path)

        assert (tmp_path / "out" / "safelist.txt").read_text(encoding="utf-8") == "from-child\n"

    def test_inspect_lists_the_safelist_with_its_layer(self, tmp_path: Path) -> None:
        result = inspect_chain(material_theme(), tmp_path)

        by_path = {entry.path: entry for entry in result.files}
        assert by_path["safelist.txt"].layer == "material"
        assert by_path["safelist.txt"].kind == "tailwind"
