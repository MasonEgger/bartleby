# ABOUTME: Tests for content discovery, front matter parsing, and file exclusion.
# Covers parse_front_matter, should_exclude, and discover_content end-to-end.

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from bartleby.content import (
    ColocatedAsset,
    Page,
    discover_content,
    parse_front_matter,
    should_exclude,
)

if TYPE_CHECKING:
    from pathlib import Path

    from bartleby.config import BartlebyConfig


def test_parse_front_matter_basic() -> None:
    """A document with YAML front matter splits into metadata and body."""
    text = "---\ntitle: Hello\ndraft: false\n---\nBody text here.\n"
    metadata, body = parse_front_matter(text)
    assert metadata == {"title": "Hello", "draft": False}
    assert body.strip() == "Body text here."


def test_parse_front_matter_no_front_matter() -> None:
    """A document without front matter returns an empty dict and full body."""
    text = "Just body, no front matter.\n"
    metadata, body = parse_front_matter(text)
    assert metadata == {}
    assert body == text


def test_parse_front_matter_empty_front_matter() -> None:
    """An empty ``--- / ---`` block returns an empty dict and empty body."""
    text = "---\n---\n"
    metadata, body = parse_front_matter(text)
    assert metadata == {}
    assert body.strip() == ""


def test_discover_content_finds_markdown_files(
    sample_site_path: Path, sample_config: BartlebyConfig
) -> None:
    """All markdown files under content/ are discovered as Page objects."""
    pages, _ = discover_content(sample_config, sample_site_path / "content")
    source_paths = {str(page.source_path) for page in pages}
    assert "index.md" in source_paths
    assert "about.md" in source_paths
    assert "blog/index.md" in source_paths
    assert "blog/posts/first-post.md" in source_paths
    assert "blog/posts/second-post.md" in source_paths


def test_discover_content_associates_content_type(
    sample_site_path: Path, sample_config: BartlebyConfig
) -> None:
    """Pages under a content type's path get ``content_type_name`` set."""
    pages, _ = discover_content(sample_config, sample_site_path / "content")
    by_source = {str(page.source_path): page for page in pages}
    assert by_source["blog/posts/first-post.md"].content_type_name == "blog"
    assert by_source["about.md"].content_type_name is None
    assert by_source["index.md"].content_type_name is None


def test_discover_content_excludes_patterns(
    sample_site_path: Path, sample_config: BartlebyConfig
) -> None:
    """Files matching ``exclude_patterns`` are skipped entirely."""
    pages, _ = discover_content(sample_config, sample_site_path / "content")
    source_paths = {str(page.source_path) for page in pages}
    assert "_drafts/wip.md" not in source_paths


def test_discover_content_identifies_colocated_assets(
    sample_site_path: Path, sample_config: BartlebyConfig
) -> None:
    """Non-markdown files are returned as :class:`ColocatedAsset` objects."""
    pages, assets = discover_content(sample_config, sample_site_path / "content")
    asset_sources = {str(asset.source_path) for asset in assets}
    page_sources = {str(page.source_path) for page in pages}
    assert "blog/posts/diagram.png" in asset_sources
    assert "blog/posts/diagram.png" not in page_sources


def test_discover_drafts_found_but_marked(
    sample_site_path: Path, sample_config: BartlebyConfig
) -> None:
    """Drafts are discovered but flagged via ``Page.draft``."""
    pages, _ = discover_content(sample_config, sample_site_path / "content")
    drafts = [page for page in pages if str(page.source_path) == "blog/posts/draft-post.md"]
    assert len(drafts) == 1
    assert drafts[0].draft is True


def test_page_fields_from_front_matter(
    sample_site_path: Path, sample_config: BartlebyConfig
) -> None:
    """Standard front matter fields map onto the :class:`Page` dataclass."""
    pages, _ = discover_content(sample_config, sample_site_path / "content")
    first = next(page for page in pages if str(page.source_path) == "blog/posts/first-post.md")
    assert first.title == "First Post"
    assert first.description == "The first sample blog post"
    assert first.date == datetime.date(2026, 3, 1)
    assert first.draft is False
    assert first.author_keys == ["mason"]
    assert first.taxonomy_values["tags"] == ["python", "temporal"]
    assert first.taxonomy_values["categories"] == ["devops"]


def test_should_exclude_matches_patterns() -> None:
    """``should_exclude`` matches each documented default pattern."""
    patterns = ["_drafts/**", "_*.md", ".git/**"]
    assert should_exclude("_drafts/wip.md", patterns) is True
    assert should_exclude("_secret.md", patterns) is True
    assert should_exclude(".git/config", patterns) is True


def test_should_exclude_no_match() -> None:
    """Regular content paths are not excluded by the defaults."""
    patterns = ["_drafts/**", "_*.md", ".git/**"]
    assert should_exclude("blog/posts/good.md", patterns) is False
    assert should_exclude("about.md", patterns) is False


def test_discover_content_returns_colocated_assets_list(
    sample_site_path: Path, sample_config: BartlebyConfig
) -> None:
    """``discover_content`` always returns both pages and an assets list."""
    pages, assets = discover_content(sample_config, sample_site_path / "content")
    assert isinstance(pages, list)
    assert isinstance(assets, list)
    assert all(isinstance(page, Page) for page in pages)
    assert all(isinstance(asset, ColocatedAsset) for asset in assets)
