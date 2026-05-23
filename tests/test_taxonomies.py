# ABOUTME: Tests for taxonomy term collection, page mapping, and page generation.
# Covers global and per-content-type taxonomies, slug formats, and sorted page lists.

from __future__ import annotations

import datetime
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
from bartleby.taxonomies import (
    AllTaxonomies,
    TaxonomyData,
    TaxonomyTerm,
    build_taxonomies,
    generate_taxonomy_pages,
)


def _page(
    *,
    source: str,
    title: str,
    content_type_name: str = "blog",
    tags: list[str] | None = None,
    categories: list[str] | None = None,
    date: datetime.date | None = None,
) -> Page:
    taxonomy_values: dict[str, list[str]] = {}
    if tags is not None:
        taxonomy_values["tags"] = tags
    if categories is not None:
        taxonomy_values["categories"] = categories
    return Page(
        source_path=Path(source),
        abs_source_path=Path("/abs") / source,
        title=title,
        date=date,
        content_type_name=content_type_name,
        taxonomy_values=taxonomy_values,
    )


def _config(*, blog_taxonomies: list[str] | None = None) -> BartlebyConfig:
    return BartlebyConfig(
        site=SiteConfig(title="t", url="u"),
        nav=None,
        theme=ThemeConfig(),
        authors_file=".authors.yml",
        content_types={
            "blog": ContentTypeConfig(
                name="blog",
                path="blog/posts",
                pagination=PaginationConfig(),
                taxonomies=blog_taxonomies
                if blog_taxonomies is not None
                else ["tags", "categories"],
            ),
        },
        taxonomies={
            "tags": TaxonomyConfig(name="tags", slug_format="{slug}"),
            "categories": TaxonomyConfig(name="categories", slug_format="{slug}"),
        },
        exclude_patterns=[],
        markdown_extensions=[],
        plugins=[],
        extra_css=[],
        extra_js=[],
        ai=AIConfig(),
        dev_server=DevServerConfig(),
        config_dir=Path("/tmp"),
    )


def test_collect_terms_from_pages() -> None:
    """Pages with overlapping tags collect into a single TaxonomyTerm with both pages listed."""
    pages = [
        _page(source="blog/posts/a.md", title="A", tags=["python", "temporal"]),
        _page(source="blog/posts/b.md", title="B", tags=["python", "devops"]),
    ]
    result = build_taxonomies(pages, _config())
    tags_data = result.global_taxonomies["tags"]
    assert set(tags_data.terms.keys()) == {"python", "temporal", "devops"}
    python_pages = {str(page.source_path) for page in tags_data.terms["python"].pages}
    assert python_pages == {"blog/posts/a.md", "blog/posts/b.md"}


def test_term_counts() -> None:
    """``TaxonomyTerm.count`` matches the number of pages tagged with that term."""
    pages = [
        _page(source="blog/posts/a.md", title="A", tags=["python", "temporal"]),
        _page(source="blog/posts/b.md", title="B", tags=["python", "devops"]),
    ]
    result = build_taxonomies(pages, _config())
    terms = result.global_taxonomies["tags"].terms
    assert terms["python"].count == 2
    assert terms["temporal"].count == 1
    assert terms["devops"].count == 1


def test_ignores_non_opted_in_taxonomy() -> None:
    """Content types that don't opt into a taxonomy don't contribute terms to it."""
    pages = [
        _page(source="blog/posts/a.md", title="A", tags=["python"], categories=["devops"]),
    ]
    result = build_taxonomies(pages, _config(blog_taxonomies=["tags"]))
    assert "categories" not in result.global_taxonomies
    assert "tags" in result.global_taxonomies


def test_slug_format_applied() -> None:
    """A term's slug obeys the taxonomy's ``slug_format`` template."""
    config = _config()
    config.taxonomies["tags"] = TaxonomyConfig(name="tags", slug_format="tag:{slug}")
    pages = [_page(source="blog/posts/a.md", title="A", tags=["Temporal Workflows"])]
    result = build_taxonomies(pages, config)
    term = result.global_taxonomies["tags"].terms["Temporal Workflows"]
    assert term.slug == "tag:temporal-workflows"


def test_global_taxonomy_pages_generated() -> None:
    """``generate_taxonomy_pages`` produces an index page for each taxonomy and a page per term."""
    pages = [
        _page(source="blog/posts/a.md", title="A", tags=["python"]),
        _page(source="blog/posts/b.md", title="B", tags=["python", "devops"]),
    ]
    result = build_taxonomies(pages, _config(blog_taxonomies=["tags"]))
    generated = generate_taxonomy_pages(result, _config(blog_taxonomies=["tags"]))
    urls = {page.output_url for page in generated}
    assert "/tags/" in urls
    assert "/tags/python/" in urls


def test_per_content_type_pages_generated() -> None:
    """Per-content-type taxonomy pages live under ``/{type}/{taxonomy}/``."""
    pages = [
        _page(source="blog/posts/a.md", title="A", tags=["python"]),
    ]
    result = build_taxonomies(pages, _config(blog_taxonomies=["tags"]))
    generated = generate_taxonomy_pages(result, _config(blog_taxonomies=["tags"]))
    urls = {page.output_url for page in generated}
    assert "/blog/tags/" in urls
    assert "/blog/tags/python/" in urls


def test_taxonomy_page_has_correct_context() -> None:
    """Generated taxonomy pages carry name/term/pages info in ``custom_metadata``."""
    pages = [_page(source="blog/posts/a.md", title="A", tags=["python"])]
    result = build_taxonomies(pages, _config(blog_taxonomies=["tags"]))
    generated = generate_taxonomy_pages(result, _config(blog_taxonomies=["tags"]))
    term_page = next(page for page in generated if page.output_url == "/tags/python/")
    assert term_page.custom_metadata["taxonomy_name"] == "tags"
    assert term_page.custom_metadata["taxonomy_term"] == "python"


def test_pages_sorted_by_date_within_term() -> None:
    """Pages within a term are ordered newest-first by ``page.date``."""
    older = _page(
        source="blog/posts/old.md", title="Old", tags=["python"], date=datetime.date(2026, 1, 1)
    )
    newer = _page(
        source="blog/posts/new.md", title="New", tags=["python"], date=datetime.date(2026, 4, 1)
    )
    result = build_taxonomies([older, newer], _config(blog_taxonomies=["tags"]))
    pages_for_python = result.global_taxonomies["tags"].terms["python"].pages
    assert pages_for_python[0] is newer
    assert pages_for_python[1] is older


def test_no_pages_for_term_no_page_generated() -> None:
    """A taxonomy with zero pages still produces the index page but no term pages."""
    result = build_taxonomies([], _config(blog_taxonomies=["tags"]))
    generated = generate_taxonomy_pages(result, _config(blog_taxonomies=["tags"]))
    urls = {page.output_url for page in generated}
    # Index pages still exist so the user can link to /tags/ etc.
    assert "/tags/" in urls
    # But no individual term pages exist.
    assert not any("/python" in url for url in urls)


def test_alltaxonomies_dataclass_shapes() -> None:
    """Verify the public dataclass shapes match the typed returns."""
    pages = [_page(source="blog/posts/a.md", title="A", tags=["python"])]
    result = build_taxonomies(pages, _config(blog_taxonomies=["tags"]))
    assert isinstance(result, AllTaxonomies)
    assert isinstance(result.global_taxonomies["tags"], TaxonomyData)
    assert isinstance(result.global_taxonomies["tags"].terms["python"], TaxonomyTerm)
