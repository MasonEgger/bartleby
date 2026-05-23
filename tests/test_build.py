# ABOUTME: Integration tests for the build pipeline orchestrator.
# Drives the sample fixture site through build() and inspects the output.

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from bartleby.build import BuildResult, build, calculate_readtime, extract_excerpt


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Copy the sample fixture site into a temp dir so build can mutate ``site/``."""
    source = Path(__file__).parent / "fixtures" / "site"
    destination = tmp_path / "site_project"
    shutil.copytree(source, destination)
    return destination


def test_build_produces_output_directory(project: Path) -> None:
    """``build`` writes a ``site/`` directory next to ``bartleby.yml``."""
    build(project / "bartleby.yml")
    assert (project / "site").is_dir()


def test_build_renders_index_page(project: Path) -> None:
    """The top-level ``index.md`` becomes ``site/index.html``."""
    build(project / "bartleby.yml")
    rendered = (project / "site" / "index.html").read_text(encoding="utf-8")
    assert "Welcome" in rendered


def test_build_renders_blog_post(project: Path) -> None:
    """Blog posts land at their generated URL path under ``site/``."""
    build(project / "bartleby.yml")
    rendered_dir = project / "site" / "blog" / "posts" / "first-post"
    assert (rendered_dir / "index.html").exists()


def test_build_html_is_valid_structure(project: Path) -> None:
    """Rendered pages include the standard HTML5 scaffolding."""
    build(project / "bartleby.yml")
    rendered = (project / "site" / "index.html").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in rendered
    assert "<html" in rendered
    assert "<head>" in rendered
    assert "<body>" in rendered


def test_build_page_title_in_output(project: Path) -> None:
    """The page's front-matter title appears inside ``<title>``."""
    build(project / "bartleby.yml")
    rendered = (project / "site" / "index.html").read_text(encoding="utf-8")
    assert "<title>Home" in rendered


def test_build_excludes_drafts(project: Path) -> None:
    """Draft posts are not written to ``site/`` by default."""
    build(project / "bartleby.yml")
    draft_dir = project / "site" / "blog" / "posts" / "draft-post"
    assert not draft_dir.exists()


def test_build_includes_drafts_when_requested(project: Path) -> None:
    """``include_drafts=True`` writes draft posts alongside published ones."""
    build(project / "bartleby.yml", include_drafts=True)
    draft_dir = project / "site" / "blog" / "posts" / "draft-post"
    assert draft_dir.exists()


def test_build_cleans_output_dir(project: Path) -> None:
    """``site/`` is cleaned at the start of each build — stale files vanish."""
    site_dir = project / "site"
    site_dir.mkdir()
    (site_dir / "stale.html").write_text("stale")
    build(project / "bartleby.yml")
    assert not (site_dir / "stale.html").exists()


def test_build_returns_result(project: Path) -> None:
    """``build`` returns a :class:`BuildResult` with positive page count and duration."""
    result = build(project / "bartleby.yml")
    assert isinstance(result, BuildResult)
    assert result.page_count > 0
    assert result.duration_seconds >= 0.0


def test_extract_excerpt_with_separator() -> None:
    """When a separator is present, the excerpt is the content above it rendered to HTML."""
    source = "Intro paragraph.\n\n<!-- more -->\n\nRest of post.\n"
    excerpt = extract_excerpt(source, "<!-- more -->")
    assert "Intro paragraph" in excerpt
    assert "Rest of post" not in excerpt


def test_extract_excerpt_first_paragraph() -> None:
    """Without a separator, the first paragraph of source is returned."""
    source = "First paragraph.\n\nSecond paragraph.\n"
    excerpt = extract_excerpt(source, None)
    assert "First paragraph" in excerpt
    assert "Second paragraph" not in excerpt


def test_calculate_readtime() -> None:
    """``calculate_readtime`` returns ~1 minute per 265 words (rounded up)."""
    text = "word " * 1000
    assert calculate_readtime(text) in {3, 4, 5}


def test_calculate_readtime_short_text() -> None:
    """Very short text still returns at least 1 minute."""
    assert calculate_readtime("hello world") == 1
