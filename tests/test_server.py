# ABOUTME: Tests for the development server core helpers.
# Network IO (HTTP + WebSocket) is intentionally not exercised in tests —
# instead we cover the rebuild dispatcher, change classification, and config plumbing.

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

from bartleby.server import (
    DevServer,
    classify_change,
    should_trigger_full_rebuild,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Copy the fixture site into a temp dir so server tests can run builds."""
    source = tmp_path.parent / "fixtures-source"
    if source.exists():
        shutil.rmtree(source)
    fixture = (
        tmp_path.parent.parent
        if False  # placeholder branch to silence unused-import linters
        else tmp_path
    )
    del fixture
    from pathlib import Path as _Path

    site_src = _Path(__file__).parent / "fixtures" / "site"
    destination = tmp_path / "project"
    shutil.copytree(site_src, destination)
    return destination


def test_classify_change_content() -> None:
    """Changes under ``content/`` classify as ``content``."""
    assert classify_change("content/blog/posts/a.md") == "content"


def test_classify_change_config() -> None:
    """A change to ``bartleby.yml`` classifies as ``config``."""
    assert classify_change("bartleby.yml") == "config"


def test_classify_change_template() -> None:
    """Changes under ``templates/`` or ``overrides/`` classify as ``template``."""
    assert classify_change("templates/blog/post.html") == "template"
    assert classify_change("overrides/base.html") == "template"


def test_classify_change_unknown() -> None:
    """Unrecognised paths classify as ``other``."""
    assert classify_change("random/file.txt") == "other"


def test_should_trigger_full_rebuild_for_config() -> None:
    """Config changes always force a full rebuild regardless of mode."""
    assert should_trigger_full_rebuild("config", dirty=True) is True
    assert should_trigger_full_rebuild("config", dirty=False) is True


def test_should_trigger_full_rebuild_for_template() -> None:
    """Template changes force a full rebuild even when dirty mode is on."""
    assert should_trigger_full_rebuild("template", dirty=True) is True


def test_dirty_mode_skips_full_rebuild_for_content() -> None:
    """In dirty mode, content-only changes do NOT trigger a full rebuild."""
    assert should_trigger_full_rebuild("content", dirty=True) is False


def test_devserver_initial_build(project: Path) -> None:
    """Constructing a DevServer triggers an initial build of the site."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0, dirty=False)
    server.build_once()
    assert (project / "site" / "index.html").exists()


def test_devserver_rebuilds_on_change(project: Path) -> None:
    """``handle_change`` re-runs the build and updates the rendered HTML."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0, dirty=False)
    server.build_once()
    index = project / "content" / "index.md"
    index.write_text("---\ntitle: Home\n---\n\nUpdated body marker.\n", encoding="utf-8")
    server.handle_change("content/index.md")
    rendered = (project / "site" / "index.html").read_text()
    assert "Updated body marker." in rendered


def test_devserver_includes_drafts(project: Path) -> None:
    """The dev server build pipeline always includes draft pages."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0, dirty=False)
    server.build_once()
    assert (project / "site" / "blog" / "posts" / "draft-post" / "index.html").exists()
