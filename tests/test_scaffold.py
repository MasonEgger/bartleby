# ABOUTME: Tests for what `bartleby new site` emits: layout, theme, and a clean first build.
# Builds the real scaffold so a green suite means a newcomer's first run renders well.

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from bartleby.cli import main
from bartleby.config import load_config
from bartleby.theme_loader import select_theme

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def scaffold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Scaffold `mysite` in a temp dir and make it the working directory."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    project = tmp_path / "mysite"
    monkeypatch.chdir(project)
    return project


def test_scaffold_has_a_content_type_and_a_published_sample_post(scaffold: Path) -> None:
    """The scaffold ships a home page and one published, authored sample post."""
    assert (scaffold / "content" / "index.md").is_file()
    posts = list((scaffold / "content" / "blog" / "posts").glob("*.md"))
    assert len(posts) == 1
    body = posts[0].read_text(encoding="utf-8")
    assert "\ndraft: false\n" in body
    assert "authors: [default]" in body


def test_scaffold_selects_scrivener_with_features_its_manifest_declares(scaffold: Path) -> None:
    """The scaffold names scrivener and enables only features the theme implements."""
    config = load_config(scaffold / "bartleby.yml")
    assert config.theme.name == "scrivener"
    assert "color-mode.toggle" in config.theme.features
    theme = select_theme(config.theme, scaffold)
    declared = {feature for layer in theme.chain for feature in layer.manifest.features}
    assert set(config.theme.features) <= declared


def test_scaffold_config_references_only_existing_paths(scaffold: Path) -> None:
    """Every content type path in the scaffold exists on disk."""
    config = load_config(scaffold / "bartleby.yml")
    for content_type in config.content_types.values():
        assert (scaffold / "content" / content_type.path).is_dir()
    assert (scaffold / config.authors_file).is_file()


def test_scaffold_builds_home_listing_and_post_without_warnings(
    scaffold: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The first build emits home, listing, and post pages and logs no warnings."""
    with caplog.at_level(logging.WARNING):
        main(["build"])
    assert [record.getMessage() for record in caplog.records] == []
    site = scaffold / "site"
    assert (site / "index.html").is_file()
    assert (site / "blog" / "index.html").is_file()
    post_pages = list((site / "blog" / "posts").glob("*/index.html"))
    assert len(post_pages) == 1


def test_scaffold_home_page_carries_scrivener_layout_classes(scaffold: Path) -> None:
    """The home page uses scrivener's container and prose classes, with no template error."""
    main(["build"])
    html = (scaffold / "site" / "index.html").read_text(encoding="utf-8")
    assert "UndefinedError" not in html
    assert "layout-prose" in html or "layout-docs" in html
    # layout-docs wraps the reading column in docs-content; layout-prose uses prose-column.
    assert "prose-column" in html or "docs-content" in html
    assert 'class="prose ' in html


def test_scaffold_home_links_to_the_blog_listing(scaffold: Path) -> None:
    """A newcomer can reach the listing and the sample post from the home page."""
    main(["build"])
    home = (scaffold / "site" / "index.html").read_text(encoding="utf-8")
    assert 'href="/blog/"' in home
    listing = (scaffold / "site" / "blog" / "index.html").read_text(encoding="utf-8")
    assert "/blog/posts/" in listing


def test_scaffold_new_post_fits_the_scaffolded_content_type(scaffold: Path) -> None:
    """`new post` writes into the scaffold's blog path and the result still builds."""
    main(["new", "post", "Second Post", "--type", "blog"])
    assert (scaffold / "content" / "blog" / "posts" / "second-post.md").is_file()
    main(["build"])
