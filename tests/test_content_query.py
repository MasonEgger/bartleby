# ABOUTME: Tests for content query — `bartleby content list` and `content get`.
# Covers curated-field listing, type filtering, date sorting, draft exclusion, and single-page get.

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

from bartleby.config import (
    AIConfig,
    BartlebyConfig,
    ContentTypeConfig,
    DevServerConfig,
    PaginationConfig,
    SiteConfig,
    TaxonomyConfig,
    ThemeConfig,
)
from bartleby.content import Page
from bartleby.content_query import (
    ContentGet,
    ContentList,
    ContentQueryError,
    get_content,
    list_content,
    select_published,
)
from bartleby.output import render


def _config() -> BartlebyConfig:
    """A config with a blog content type and two taxonomies."""
    blog = ContentTypeConfig(
        name="blog",
        path="blog/posts",
        url_base="blog",
        url_format="{date:%Y/%m/%d}/{slug}",
        pagination=PaginationConfig(enabled=True, per_page=10),
        taxonomies=["tags", "categories"],
        feeds=["rss", "atom"],
        readtime=True,
        excerpt_separator="<!-- more -->",
        metadata={},
    )
    page = ContentTypeConfig(
        name="page",
        path="pages",
        url_base=None,
        url_format=None,
        pagination=PaginationConfig(enabled=False, per_page=10),
        taxonomies=[],
        feeds=[],
        readtime=False,
        excerpt_separator=None,
        metadata={},
    )
    return BartlebyConfig(
        site=SiteConfig(title="Test", url="https://example.com"),
        nav=None,
        theme=ThemeConfig(),
        authors_file=".authors.yml",
        content_types={"blog": blog, "page": page},
        taxonomies={
            "tags": TaxonomyConfig(name="tags", slug_format="tag:{slug}"),
            "categories": TaxonomyConfig(name="categories", slug_format="category:{slug}"),
        },
        exclude_patterns=[],
        markdown_extensions=[],
        plugins=[],
        extra_css=[],
        extra_js=[],
        ai=AIConfig(),
        dev_server=DevServerConfig(),
        config_dir=Path("/tmp/site"),
    )


def _page(
    *,
    rel: str,
    title: str,
    date: datetime.date | None,
    content_type: str | None,
    draft: bool = False,
    authors: list[str] | None = None,
    tags: list[str] | None = None,
    body: str = "Body text here.",
) -> Page:
    """Build a discovered Page with the given metadata."""
    return Page(
        source_path=Path(rel),
        abs_source_path=Path("/tmp/site") / rel,
        title=title,
        date=date,
        draft=draft,
        content_type_name=content_type,
        author_keys=authors or [],
        taxonomy_values={"tags": tags} if tags else {},
        raw_content=body,
    )


def _pages() -> list[Page]:
    return [
        _page(
            rel="content/blog/posts/old.md",
            title="Old Post",
            date=datetime.date(2026, 1, 1),
            content_type="blog",
            authors=["mason"],
            tags=["python"],
        ),
        _page(
            rel="content/blog/posts/new.md",
            title="New Post",
            date=datetime.date(2026, 5, 1),
            content_type="blog",
            authors=["mason"],
            tags=["temporal"],
        ),
        _page(
            rel="content/blog/posts/secret.md",
            title="Secret Draft",
            date=datetime.date(2026, 6, 1),
            content_type="blog",
            draft=True,
        ),
        _page(
            rel="content/pages/about.md",
            title="About",
            date=None,
            content_type="page",
        ),
    ]


def test_select_published_excludes_drafts() -> None:
    published = select_published(_pages())
    titles = {page.title for page in published}
    assert "Secret Draft" not in titles
    assert {"Old Post", "New Post", "About"} <= titles


def test_list_content_returns_curated_fields() -> None:
    result = list_content(_pages(), _config())
    by_path = {entry["path"]: entry for entry in result.content}
    new = by_path["content/blog/posts/new.md"]
    assert new["title"] == "New Post"
    assert new["date"] == "2026-05-01"
    assert new["type"] == "blog"
    assert new["url"] == "/blog/2026/05/01/new/"
    assert new["draft"] is False


def test_list_content_excludes_drafts_by_default() -> None:
    result = list_content(_pages(), _config())
    titles = {entry["title"] for entry in result.content}
    assert "Secret Draft" not in titles
    assert result.count == 3


def test_list_content_filter_by_type() -> None:
    result = list_content(_pages(), _config(), content_type="blog")
    types = {entry["type"] for entry in result.content}
    assert types == {"blog"}
    assert result.count == 2


def test_list_content_sorted_by_date_descending() -> None:
    result = list_content(_pages(), _config(), sort="date")
    dates = [entry["date"] for entry in result.content if entry["date"] is not None]
    assert dates == sorted(dates, reverse=True)
    assert result.content[0]["title"] == "New Post"


def test_get_content_returns_metadata_and_body() -> None:
    result = get_content("content/blog/posts/new.md", _pages(), _config())
    assert result.path == "content/blog/posts/new.md"
    assert result.url == "/blog/2026/05/01/new/"
    assert result.content_type == "blog"
    assert result.metadata["title"] == "New Post"
    assert result.metadata["date"] == "2026-05-01"
    assert result.body == "Body text here."
    assert result.word_count == 3


def test_get_content_unknown_path_raises() -> None:
    with pytest.raises(ContentQueryError):
        get_content("content/blog/posts/missing.md", _pages(), _config())


def test_list_content_renders_json_through_formatter() -> None:
    result = list_content(_pages(), _config())
    payload = json.loads(render(result, "json"))
    assert payload["count"] == 3
    assert isinstance(payload["content"], list)


def test_get_content_renders_json_through_formatter() -> None:
    result = get_content("content/blog/posts/new.md", _pages(), _config())
    payload = json.loads(render(result, "json"))
    assert payload["path"] == "content/blog/posts/new.md"
    assert payload["metadata"]["title"] == "New Post"
    assert payload["content"] == "Body text here."


def test_results_render_human_text() -> None:
    list_result = list_content(_pages(), _config())
    assert "New Post" in render(list_result, "text")
    get_result = get_content("content/blog/posts/new.md", _pages(), _config())
    assert "New Post" in render(get_result, "text")


def test_content_list_and_get_have_exit_code_zero() -> None:
    assert ContentList(count=0, content=[]).exit_code == 0
    assert (
        ContentGet(
            path="x",
            url="/x/",
            content_type=None,
            metadata={},
            body="",
            word_count=0,
        ).exit_code
        == 0
    )
