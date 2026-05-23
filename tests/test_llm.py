# ABOUTME: Tests for LLM-friendly output generation.
# Covers llms.txt, llms-full.txt, .md variants, and JSON-LD structured data.

from __future__ import annotations

import datetime
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
from bartleby.llm import (
    generate_jsonld,
    generate_llms_full_txt,
    generate_llms_txt,
    write_markdown_variant,
)


def _page(
    *,
    source: str,
    title: str,
    content_type_name: str | None = "blog",
    date: datetime.date | None = None,
    raw: str = "Body content.\n",
    description: str | None = None,
) -> Page:
    page = Page(
        source_path=Path(source),
        abs_source_path=Path("/abs") / source,
        title=title,
        content_type_name=content_type_name,
        date=date,
        description=description,
        raw_content=raw,
    )
    page.output_url = "/" + source.removesuffix(".md") + "/"
    return page


def _config(*, ai: AIConfig | None = None) -> BartlebyConfig:
    return BartlebyConfig(
        site=SiteConfig(title="Site", url="https://example.com", description="Site desc"),
        nav=None,
        theme=ThemeConfig(),
        authors_file=".authors.yml",
        content_types={
            "blog": ContentTypeConfig(
                name="blog", path="blog/posts", pagination=PaginationConfig()
            ),
        },
        taxonomies={"tags": TaxonomyConfig(name="tags", slug_format="{slug}")},
        exclude_patterns=[],
        markdown_extensions=[],
        plugins=[],
        extra_css=[],
        extra_js=[],
        ai=ai if ai is not None else AIConfig(),
        dev_server=DevServerConfig(),
        config_dir=Path("/tmp"),
    )


def test_llms_txt_format() -> None:
    """``llms.txt`` opens with the site title and lists posts by content type."""
    pages = [_page(source="blog/posts/a.md", title="A")]
    text = generate_llms_txt(pages, _config())
    assert text.startswith("# Site")
    assert "Site desc" in text
    assert "## Blog" in text
    assert "A" in text


def test_llms_txt_links_to_md_variants() -> None:
    """The links in ``llms.txt`` resolve to ``.md`` variants of each page."""
    pages = [_page(source="blog/posts/a.md", title="A")]
    text = generate_llms_txt(pages, _config())
    assert "/blog/posts/a/index.md" in text


def test_llms_full_txt_includes_content() -> None:
    """``llms-full.txt`` embeds each page's raw markdown body."""
    pages = [
        _page(source="blog/posts/a.md", title="A", raw="First body."),
        _page(source="blog/posts/b.md", title="B", raw="Second body."),
    ]
    text = generate_llms_full_txt(pages, _config())
    assert "First body." in text
    assert "Second body." in text
    assert "---" in text


def test_markdown_variant_written(tmp_path: Path) -> None:
    """A page at ``/blog/posts/a/`` produces ``/blog/posts/a/index.md`` next to the HTML."""
    page = _page(source="blog/posts/a.md", title="A", raw="Body content.\n")
    write_markdown_variant(page, tmp_path)
    assert (tmp_path / "blog" / "posts" / "a" / "index.md").exists()


def test_markdown_variant_strips_front_matter(tmp_path: Path) -> None:
    """The ``.md`` variant contains only the body — no YAML front matter."""
    page = _page(source="blog/posts/a.md", title="A", raw="Body only.")
    write_markdown_variant(page, tmp_path)
    contents = (tmp_path / "blog" / "posts" / "a" / "index.md").read_text()
    assert "Body only." in contents
    assert "---" not in contents


def test_jsonld_article_for_post() -> None:
    """Pages with a content type get ``@type=Article`` in JSON-LD."""
    page = _page(
        source="blog/posts/a.md",
        title="A",
        date=datetime.date(2026, 3, 1),
        description="A desc",
    )
    payload = json.loads(generate_jsonld(page, _config().site))
    assert payload["@type"] == "Article"
    assert payload["headline"] == "A"
    assert payload["datePublished"] == "2026-03-01"


def test_jsonld_webpage_for_static() -> None:
    """Pages without a content type get ``@type=WebPage``."""
    page = _page(source="about.md", title="About", content_type_name=None)
    payload = json.loads(generate_jsonld(page, _config().site))
    assert payload["@type"] == "WebPage"


def test_jsonld_fields_populated() -> None:
    """JSON-LD carries headline, description, url, and (for articles) datePublished."""
    page = _page(
        source="blog/posts/a.md",
        title="A",
        date=datetime.date(2026, 3, 1),
        description="A desc",
    )
    payload = json.loads(generate_jsonld(page, _config().site))
    assert payload["headline"] == "A"
    assert payload["description"] == "A desc"
    assert payload["url"] == "https://example.com/blog/posts/a/"
