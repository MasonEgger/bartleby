# ABOUTME: Build-level tests for the `markwright:` section of bartleby.yml.
# Covers the ignored markwright.toml / [tool.markwright] warning and per-site extension toggles.

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from bartleby.build import build

if TYPE_CHECKING:
    from collections.abc import Callable

    ProjectFactory = Callable[..., Path]

_TWEET = "[twitter someone/status/1234567890]"
_EMBED_PAGE = f"---\ntitle: Embeds\ndescription: An embed page\n---\n\n{_TWEET}\n"


@pytest.fixture
def make_project(tmp_path: Path) -> ProjectFactory:
    """Factory: copy the sample site to a fresh directory with an embed page and extra config."""
    counter = 0

    def _make(extra_config: str = "") -> Path:
        nonlocal counter
        counter += 1
        project = tmp_path / f"project-{counter}"
        shutil.copytree(Path(__file__).parent / "fixtures" / "site", project)
        (project / "content" / "embeds.md").write_text(_EMBED_PAGE, encoding="utf-8")
        config_path = project / "bartleby.yml"
        config_path.write_text(
            config_path.read_text(encoding="utf-8") + "\n" + extra_config, encoding="utf-8"
        )
        return project

    return _make


def _ignored_warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.levelname == "WARNING" and "ignored" in record.getMessage()
    ]


def _embed_html(project: Path) -> str:
    return (project / "site" / "embeds" / "index.html").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("file_name", "body", "named"),
    [
        ("markwright.toml", 'disable = ["twitter"]\n', "markwright.toml"),
        ("pyproject.toml", '[tool.markwright]\ndisable = ["twitter"]\n', "pyproject.toml"),
    ],
)
def test_ignored_markwright_config_warns_once_and_changes_nothing(
    make_project: ProjectFactory,
    file_name: str,
    body: str,
    named: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A stray markwright config beside bartleby.yml warns once and does not affect rendering."""
    baseline = make_project()
    build(baseline / "bartleby.yml")

    stray = make_project()
    (stray / file_name).write_text(body, encoding="utf-8")
    with caplog.at_level("WARNING", logger="bartleby"):
        build(stray / "bartleby.yml")

    warnings = _ignored_warnings(caplog)
    assert len(warnings) == 1
    assert named in warnings[0]
    assert "bartleby.yml" in warnings[0]
    assert _embed_html(stray) == _embed_html(baseline)
    assert "twitter-tweet" in _embed_html(stray)


def test_pyproject_without_a_markwright_table_does_not_warn(
    make_project: ProjectFactory, caplog: pytest.LogCaptureFixture
) -> None:
    """A pyproject.toml with no [tool.markwright] table is not a markwright config."""
    project = make_project()
    (project / "pyproject.toml").write_text('[project]\nname = "site"\n', encoding="utf-8")
    with caplog.at_level("WARNING", logger="bartleby"):
        build(project / "bartleby.yml")
    assert _ignored_warnings(caplog) == []


@pytest.mark.parametrize("tool_value", ["5", '"markwright"'])
def test_non_table_tool_key_neither_crashes_nor_warns(
    make_project: ProjectFactory, tool_value: str, caplog: pytest.LogCaptureFixture
) -> None:
    """A pyproject.toml whose `tool` is not a table is not a markwright config."""
    project = make_project()
    (project / "pyproject.toml").write_text(f"tool = {tool_value}\n", encoding="utf-8")
    with caplog.at_level("WARNING", logger="bartleby"):
        build(project / "bartleby.yml")
    assert _ignored_warnings(caplog) == []


def test_no_stray_config_means_no_warning(
    make_project: ProjectFactory, caplog: pytest.LogCaptureFixture
) -> None:
    """A plain project builds with no ignored-config warning."""
    project = make_project()
    with caplog.at_level("WARNING", logger="bartleby"):
        build(project / "bartleby.yml")
    assert _ignored_warnings(caplog) == []


def test_disabled_twitter_leaves_the_raw_fence_and_stray_file_warns(
    make_project: ProjectFactory, caplog: pytest.LogCaptureFixture
) -> None:
    """`markwright: {disable: [twitter]}` renders the directive as text, beside the warning."""
    project = make_project("markwright:\n  disable: [twitter]\n")
    (project / "markwright.toml").write_text('disable = ["youtube"]\n', encoding="utf-8")

    with caplog.at_level("WARNING", logger="bartleby"):
        build(project / "bartleby.yml")

    html = _embed_html(project)
    assert _TWEET in html
    assert "twitter-tweet" not in html
    assert len(_ignored_warnings(caplog)) == 1
