# ABOUTME: Tests for content export — JSONL, JSON, and CSV of published content.
# Covers curated fields, content-type filtering, optional body/HTML, and the export formats.

from __future__ import annotations

import csv
import datetime
import io
import json
from pathlib import Path

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
from bartleby.export import export_content


def _config() -> BartlebyConfig:
    """A config with a blog and a page content type."""
    blog = ContentTypeConfig(
        name="blog",
        path="blog/posts",
        url_base="blog",
        url_format="{date:%Y/%m/%d}/{slug}",
        pagination=PaginationConfig(enabled=True, per_page=10),
        taxonomies=["tags"],
        feeds=["rss"],
        readtime=True,
        excerpt_separator=None,
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
        taxonomies={"tags": TaxonomyConfig(name="tags", slug_format="{slug}")},
        exclude_patterns=[],
        markdown_extensions=[],
        plugins=[],
        extra_css=[],
        extra_js=[],
        ai=AIConfig(),
        dev_server=DevServerConfig(),
        config_dir=Path("/tmp/site"),
    )


def _pages() -> list[Page]:
    """Two published blog posts, one page, and one draft (excluded)."""
    first = Page(
        source_path=Path("blog/posts/first.md"),
        abs_source_path=Path("/tmp/site/content/blog/posts/first.md"),
        title="First",
        description="The first post.",
        date=datetime.date(2026, 3, 1),
        content_type_name="blog",
        author_keys=["mason"],
        taxonomy_values={"tags": ["python"]},
        raw_content="## Intro\n\nBody words here.",
    )
    first.rendered_content = "<h2>Intro</h2>\n<p>Body words here.</p>"
    second = Page(
        source_path=Path("blog/posts/second.md"),
        abs_source_path=Path("/tmp/site/content/blog/posts/second.md"),
        title="Second",
        date=datetime.date(2026, 4, 1),
        content_type_name="blog",
        raw_content="Just a body.",
    )
    about = Page(
        source_path=Path("pages/about.md"),
        abs_source_path=Path("/tmp/site/content/pages/about.md"),
        title="About",
        content_type_name="page",
        raw_content="About us.",
    )
    draft = Page(
        source_path=Path("blog/posts/draft.md"),
        abs_source_path=Path("/tmp/site/content/blog/posts/draft.md"),
        title="Draft",
        content_type_name="blog",
        draft=True,
        raw_content="secret",
    )
    return [first, second, about, draft]


def test_jsonl_export_one_object_per_published_page() -> None:
    """JSONL export emits one JSON object per line, drafts excluded."""
    output = export_content(_pages(), _config(), fmt="jsonl")
    lines = [line for line in output.splitlines() if line]
    assert len(lines) == 3  # first, second, about — not the draft
    records = [json.loads(line) for line in lines]
    titles = {record["title"] for record in records}
    assert titles == {"First", "Second", "About"}
    assert "Draft" not in titles


def test_jsonl_export_curated_fields() -> None:
    """Each record carries the documented curated fields."""
    output = export_content(_pages(), _config(), fmt="jsonl")
    first = next(json.loads(line) for line in output.splitlines() if line and "First" in line)
    assert first["path"] == "blog/posts/first.md"
    assert first["type"] == "blog"
    assert first["title"] == "First"
    assert first["date"] == "2026-03-01"
    assert first["url"] == "/blog/2026/03/01/first/"
    assert first["tags"] == ["python"]
    assert first["authors"] == ["mason"]
    # "## Intro\n\nBody words here." splits into 5 whitespace tokens.
    assert first["word_count"] == 5


def test_jsonl_metadata_only_omits_content_by_default() -> None:
    """Without --include-content, the markdown body is not emitted."""
    output = export_content(_pages(), _config(), fmt="jsonl")
    first = next(json.loads(line) for line in output.splitlines() if line and "First" in line)
    assert "content" not in first
    assert "html" not in first


def test_jsonl_include_content_adds_markdown_body() -> None:
    """--include-content embeds the raw markdown body verbatim."""
    output = export_content(_pages(), _config(), fmt="jsonl", include_content=True)
    first = next(json.loads(line) for line in output.splitlines() if line and "First" in line)
    assert first["content"] == "## Intro\n\nBody words here."


def test_jsonl_include_html_adds_rendered_html() -> None:
    """--include-html embeds the rendered HTML body."""
    output = export_content(_pages(), _config(), fmt="jsonl", include_html=True)
    first = next(json.loads(line) for line in output.splitlines() if line and "First" in line)
    assert first["html"] == "<h2>Intro</h2>\n<p>Body words here.</p>"


def test_json_export_is_a_single_array() -> None:
    """JSON export is a single array of records, not newline-delimited."""
    output = export_content(_pages(), _config(), fmt="json")
    records = json.loads(output)
    assert isinstance(records, list)
    assert len(records) == 3
    assert {record["title"] for record in records} == {"First", "Second", "About"}


def test_csv_export_has_header_and_rows() -> None:
    """CSV export has a header row plus one row per published page."""
    output = export_content(_pages(), _config(), fmt="csv")
    reader = csv.DictReader(io.StringIO(output))
    rows = list(reader)
    assert len(rows) == 3
    assert reader.fieldnames is not None
    assert "title" in reader.fieldnames
    assert "url" in reader.fieldnames
    first = next(row for row in rows if row["title"] == "First")
    assert first["type"] == "blog"
    # List-valued fields serialise as comma-joined strings in CSV.
    assert first["tags"] == "python"


def test_export_filters_by_content_type() -> None:
    """The content_type filter restricts export to one type."""
    output = export_content(_pages(), _config(), fmt="jsonl", content_type="page")
    lines = [line for line in output.splitlines() if line]
    records = [json.loads(line) for line in lines]
    assert len(records) == 1
    assert records[0]["title"] == "About"
