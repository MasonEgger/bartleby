# ABOUTME: Tests for search index generation.
# Covers index structure, section-level docs, HTML stripping, and draft exclusion.

from __future__ import annotations

import json
from pathlib import Path

from bartleby.config import (
    AIConfig,
    BartlebyConfig,
    DevServerConfig,
    SiteConfig,
    ThemeConfig,
)
from bartleby.content import Page
from bartleby.search import build_search_index, write_search_index


def _page(
    *,
    source: str,
    title: str,
    html: str = "",
    tags: list[str] | None = None,
    draft: bool = False,
) -> Page:
    page = Page(
        source_path=Path(source),
        abs_source_path=Path("/abs") / source,
        title=title,
        draft=draft,
        taxonomy_values={"tags": tags or []},
    )
    page.output_url = "/" + source.removesuffix(".md") + "/"
    page.rendered_content = html
    return page


def _config() -> BartlebyConfig:
    return BartlebyConfig(
        site=SiteConfig(title="t", url="u"),
        nav=None,
        theme=ThemeConfig(),
        authors_file=".authors.yml",
        content_types={},
        taxonomies={},
        exclude_patterns=[],
        markdown_extensions=[],
        plugins=[],
        extra_css=[],
        extra_js=[],
        ai=AIConfig(),
        dev_server=DevServerConfig(),
        config_dir=Path("/tmp"),
    )


def test_index_structure() -> None:
    """The generated index exposes ``config`` and ``docs`` top-level keys."""
    pages = [_page(source="a.md", title="A", html="<p>hello</p>")]
    index = build_search_index(pages, _config())
    assert "config" in index
    assert "docs" in index
    assert isinstance(index["docs"], list)


def test_config_format() -> None:
    """The ``config`` block exposes the lunr-compatible fields."""
    index = build_search_index([], _config())
    cfg = index["config"]
    assert isinstance(cfg, dict)
    assert "lang" in cfg
    assert "separator" in cfg
    assert "pipeline" in cfg


def test_doc_entry_fields() -> None:
    """Each doc entry carries location, title, text, and tags."""
    pages = [_page(source="a.md", title="A", html="<p>body</p>", tags=["python"])]
    docs = build_search_index(pages, _config())["docs"]
    assert isinstance(docs, list)
    first = docs[0]
    assert isinstance(first, dict)
    assert {"location", "title", "text", "tags"}.issubset(first.keys())


def test_section_level_entries() -> None:
    """Each <h*> heading produces its own doc entry with an anchor in the location."""
    html = (
        '<h1 id="intro">Intro</h1><p>opening</p>'
        '<h2 id="setup">Setup</h2><p>setup body</p>'
        '<h2 id="usage">Usage</h2><p>usage body</p>'
    )
    pages = [_page(source="a.md", title="A", html=html)]
    docs = build_search_index(pages, _config())["docs"]
    assert isinstance(docs, list)
    locations = [doc["location"] for doc in docs if isinstance(doc, dict)]
    assert any(loc.endswith("#setup") for loc in locations)
    assert any(loc.endswith("#usage") for loc in locations)


def test_text_stripped_of_html() -> None:
    """Doc text fields never include HTML tags."""
    pages = [_page(source="a.md", title="A", html="<p>plain <strong>text</strong></p>")]
    docs = build_search_index(pages, _config())["docs"]
    assert isinstance(docs, list)
    for doc in docs:
        assert isinstance(doc, dict)
        text = doc["text"]
        assert isinstance(text, str)
        assert "<" not in text


def test_draft_pages_excluded() -> None:
    """Draft pages do not appear in the search index."""
    pages = [
        _page(source="a.md", title="Live", html="<p>body</p>"),
        _page(source="b.md", title="Draft", html="<p>secret</p>", draft=True),
    ]
    docs = build_search_index(pages, _config())["docs"]
    assert isinstance(docs, list)
    titles = {doc.get("title") for doc in docs if isinstance(doc, dict)}
    assert "Live" in titles
    assert "Draft" not in titles


def test_tags_included() -> None:
    """Tags on the page appear on every doc entry produced for that page."""
    pages = [_page(source="a.md", title="A", html="<p>body</p>", tags=["python", "temporal"])]
    docs = build_search_index(pages, _config())["docs"]
    assert isinstance(docs, list)
    for doc in docs:
        assert isinstance(doc, dict)
        assert doc["tags"] == ["python", "temporal"]


def test_index_is_valid_json(tmp_path: Path) -> None:
    """``write_search_index`` produces a file that parses as JSON."""
    pages = [_page(source="a.md", title="A", html="<p>body</p>")]
    index = build_search_index(pages, _config())
    write_search_index(index, tmp_path)
    parsed = json.loads((tmp_path / "search" / "search_index.json").read_text())
    assert "docs" in parsed
