# ABOUTME: Tests for async build pipeline correctness and concurrency.
# Verifies async build produces the same output as sync build for the fixture site.

from __future__ import annotations

import asyncio
import shutil
from typing import TYPE_CHECKING

import pytest

from bartleby.build import async_build, build

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def sync_project(tmp_path: Path) -> Path:
    """A copy of the fixture site for the sync build."""
    from pathlib import Path as _Path

    source = _Path(__file__).parent / "fixtures" / "site"
    destination = tmp_path / "sync_project"
    shutil.copytree(source, destination)
    return destination


@pytest.fixture
def async_project(tmp_path: Path) -> Path:
    """A second copy of the fixture site for the async build."""
    from pathlib import Path as _Path

    source = _Path(__file__).parent / "fixtures" / "site"
    destination = tmp_path / "async_project"
    shutil.copytree(source, destination)
    return destination


def test_async_build_produces_output(async_project: Path) -> None:
    """``async_build`` produces a complete ``site/`` directory."""
    result = asyncio.run(async_build(async_project / "bartleby.yml"))
    assert result.page_count > 0
    assert (async_project / "site" / "index.html").exists()


def test_async_build_includes_post(async_project: Path) -> None:
    """Blog posts land at the expected URL path under ``site/``."""
    asyncio.run(async_build(async_project / "bartleby.yml"))
    assert (async_project / "site" / "blog" / "posts" / "first-post" / "index.html").exists()


def test_async_build_returns_build_result(async_project: Path) -> None:
    """``async_build`` returns a :class:`BuildResult` with positive page count."""
    result = asyncio.run(async_build(async_project / "bartleby.yml"))
    assert result.page_count > 0
    assert result.duration_seconds >= 0.0


def test_async_build_same_output(sync_project: Path, async_project: Path) -> None:
    """Async and sync builds produce identical HTML for the same fixture."""
    build(sync_project / "bartleby.yml")
    asyncio.run(async_build(async_project / "bartleby.yml"))
    sync_index = (sync_project / "site" / "index.html").read_text()
    async_index = (async_project / "site" / "index.html").read_text()
    assert sync_index == async_index


def test_async_build_writes_search_index(async_project: Path) -> None:
    """The post-render concurrent outputs include the search index."""
    asyncio.run(async_build(async_project / "bartleby.yml"))
    assert (async_project / "site" / "search" / "search_index.json").exists()


def test_async_build_writes_sitemap(async_project: Path) -> None:
    """The post-render concurrent outputs include the sitemap."""
    asyncio.run(async_build(async_project / "bartleby.yml"))
    assert (async_project / "site" / "sitemap.xml").exists()


def test_async_build_with_timeout(async_project: Path) -> None:
    """The async build completes within a reasonable timeout (no deadlocks)."""

    async def run_with_timeout() -> int:
        result = await asyncio.wait_for(async_build(async_project / "bartleby.yml"), timeout=15.0)
        return result.page_count

    page_count = asyncio.run(run_with_timeout())
    assert page_count > 0
