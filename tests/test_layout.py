# ABOUTME: Render tests for the docs layout flags (nav.sidebar, nav.toc-fold) in bundled themes.
# Each test builds a small site and inspects the HTML a reader would get.

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from bartleby.build import build

if TYPE_CHECKING:
    from pathlib import Path

PAGE_BODY = "---\ntitle: {title}\n---\n\n## {title} Heading\n\nText.\n"


def _build_site(root: Path, theme_name: str, features: list[str]) -> Path:
    """Write a three-page site (one page outside the nav) and build it.

    Args:
        root: Empty directory that becomes the project.
        theme_name: Bundled theme to build with.
        features: Feature names to enable.

    Returns:
        The build output directory.
    """
    content = root / "content"
    (content / "guide").mkdir(parents=True)
    (content / "index.md").write_text(PAGE_BODY.format(title="Home"), encoding="utf-8")
    (content / "guide" / "install.md").write_text(
        PAGE_BODY.format(title="Install"), encoding="utf-8"
    )
    (content / "orphan.md").write_text(PAGE_BODY.format(title="Orphan"), encoding="utf-8")
    feature_lines = "".join(f"    - {name}\n" for name in features)
    (root / "bartleby.yml").write_text(
        'site:\n  title: "Layout Site"\n  url: "https://layout.example.com"\n'
        "nav:\n  - Home: index.md\n  - Guide:\n      - Install: guide/install.md\n"
        f"theme:\n  name: {theme_name}\n  features:\n{feature_lines}",
        encoding="utf-8",
    )
    build(root / "bartleby.yml")
    return root / "site"


@pytest.fixture(params=["material", "scrivener"])
def folded_site(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    """A built site with the sidebar and the TOC fold on, once per bundled theme."""
    return _build_site(tmp_path, str(request.param), ["nav.sidebar", "nav.toc-fold"])


def test_fold_moves_headings_under_the_current_sidebar_entry(folded_site: Path) -> None:
    """A page in the sidebar tree gets .nav-toc and loses the right column."""
    html = (folded_site / "guide" / "install" / "index.html").read_text(encoding="utf-8")
    assert 'class="nav-toc"' in html
    assert "layout-docs--no-toc" in html
    assert "toc-sidebar" not in html


def test_fold_keeps_the_right_toc_for_a_page_outside_the_sidebar_tree(
    folded_site: Path,
) -> None:
    """A page the sidebar does not list keeps its right-hand table of contents."""
    html = (folded_site / "orphan" / "index.html").read_text(encoding="utf-8")
    assert "toc-sidebar" in html
    assert 'class="nav-toc"' not in html
    assert "layout-docs--no-toc" not in html


@pytest.mark.parametrize("theme_name", ["material", "scrivener"])
def test_header_nav_section_without_url_links_to_its_first_page(
    tmp_path: Path, theme_name: str
) -> None:
    """A section item with no index page of its own links to its first child."""
    site = _build_site(tmp_path, theme_name, ["nav.sidebar"])
    html = (site / "index.html").read_text(encoding="utf-8")
    header = re.search(r"<header.*?</header>", html, re.DOTALL)
    assert header is not None
    assert re.search(r'<a [^>]*href="/guide/install/"[^>]*>\s*Guide\s*</a>', header.group(0))


SECTION_INDEX_BODY = "---\ntitle: Guide\n---\n\n## Overview\n\nText.\n\n## Setup\n\nMore.\n"


def _build_tabbed_section_site(root: Path, theme_name: str) -> Path:
    """Build a site whose Guide section has an index page, under all four nav features.

    Args:
        root: Empty directory that becomes the project.
        theme_name: Bundled theme to build with.

    Returns:
        The build output directory.
    """
    content = root / "content"
    (content / "guide").mkdir(parents=True)
    (content / "index.md").write_text(PAGE_BODY.format(title="Home"), encoding="utf-8")
    (content / "guide" / "index.md").write_text(SECTION_INDEX_BODY, encoding="utf-8")
    (content / "guide" / "install.md").write_text(
        PAGE_BODY.format(title="Install"), encoding="utf-8"
    )
    (root / "bartleby.yml").write_text(
        'site:\n  title: "Layout Site"\n  url: "https://layout.example.com"\n'
        "nav:\n  - Home: index.md\n  - Guide: guide/\n"
        f"theme:\n  name: {theme_name}\n  features:\n"
        "    - nav.tabs\n    - nav.sidebar\n    - nav.section-index\n    - nav.toc-fold\n",
        encoding="utf-8",
    )
    build(root / "bartleby.yml")
    return root / "site"


@pytest.mark.parametrize("theme_name", ["material", "scrivener"])
def test_section_index_page_keeps_its_folded_toc_under_tabs(
    tmp_path: Path, theme_name: str
) -> None:
    """With tabs, section-index, and toc-fold, the index page's headings print exactly once."""
    site = _build_tabbed_section_site(tmp_path, theme_name)
    html = (site / "guide" / "index.html").read_text(encoding="utf-8")
    assert 'class="nav-toc"' in html
    assert "toc-sidebar" not in html
    assert html.count('href="#overview"') == 1
    assert html.count('href="#setup"') == 1


@pytest.mark.parametrize("theme_name", ["material", "scrivener"])
def test_section_child_page_keeps_its_folded_toc_under_tabs(
    tmp_path: Path, theme_name: str
) -> None:
    """A non-index page in the same section folds its headings under its own entry."""
    site = _build_tabbed_section_site(tmp_path, theme_name)
    html = (site / "guide" / "install" / "index.html").read_text(encoding="utf-8")
    assert 'class="nav-toc"' in html
    assert "toc-sidebar" not in html
    assert html.count('href="#install-heading"') == 1
