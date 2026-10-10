# ABOUTME: Tests for taxonomy term collection, page mapping, and page generation.
# Covers global and per-content-type taxonomies, slug formats, and sorted page lists.

from __future__ import annotations

import datetime
from pathlib import Path

import jinja2

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
    taxonomy_links_for,
    term_url,
)
from tests.theme_helpers import material_theme


def _render(page: Page, template_name: str) -> str:
    """Render a generated taxonomy page through the real theme template.

    Returns the HTML so tests can grep the actual output rather than only checking
    the virtual :class:`Page` dataclass shape.
    """
    from bartleby.templates import make_feature_checker
    from bartleby.theme_loader import THEME_FEATURES

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader([str(path) for path in material_theme().templates_dirs()]),
        autoescape=True,
    )
    env.globals["feature"] = make_feature_checker(list(THEME_FEATURES))
    context: dict[str, object] = {
        "site": {"title": "Site", "url": "https://example.com", "description": "Desc"},
        "page": page,
        "nav": [],
        "pages": [],
        "build": {"date": "2026-05-23", "bartleby_version": "0.1.0"},
        "config": {"theme": {"color_mode": {}}},
        "extra_css": [],
        "extra_js": [],
        "seo": None,
    }
    return env.get_template(template_name).render(**context)


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


def test_rendered_taxonomy_term_html_links_tagged_posts() -> None:
    """Rendering the taxonomy template emits a link + title for each tagged post.

    Grep the real HTML, not just the ``custom_metadata`` dataclass: a term page
    can carry the right pages while the template still fails to list them.
    """
    first = _page(source="blog/posts/a.md", title="First Tagged", tags=["python"])
    second = _page(source="blog/posts/b.md", title="Second Tagged", tags=["python"])
    first.output_url = "/blog/posts/a/"
    second.output_url = "/blog/posts/b/"
    result = build_taxonomies([first, second], _config(blog_taxonomies=["tags"]))
    generated = generate_taxonomy_pages(result, _config(blog_taxonomies=["tags"]))
    term_page = next(page for page in generated if page.output_url == "/tags/python/")

    html = _render(term_page, "taxonomy.html")
    assert 'href="/blog/posts/a/"' in html
    assert 'href="/blog/posts/b/"' in html
    assert "First Tagged" in html
    assert "Second Tagged" in html


def test_rendered_taxonomy_index_html_shows_taxonomy_title() -> None:
    """The taxonomy index template renders the taxonomy's heading."""
    page = _page(source="blog/posts/a.md", title="A", tags=["python"])
    result = build_taxonomies([page], _config(blog_taxonomies=["tags"]))
    generated = generate_taxonomy_pages(result, _config(blog_taxonomies=["tags"]))
    index_page = next(page for page in generated if page.output_url == "/tags/")

    html = _render(index_page, "taxonomy_index.html")
    assert "Tags" in html


def test_scoped_taxonomy_pages_are_titled_by_their_content_type() -> None:
    """Global and per-content-type pages at the same taxonomy get distinct titles.

    The scoped pages are intended (one opt-in yields both scopes), so they must
    not read as duplicates of the global ones in search results, tabs, or feeds.
    """
    page = _page(source="blog/posts/a.md", title="A", tags=["python"])
    config = _config(blog_taxonomies=["tags"])
    generated = generate_taxonomy_pages(build_taxonomies([page], config), config)
    titles = {generated_page.output_url: generated_page.title for generated_page in generated}
    assert titles["/tags/"] == "Tags"
    assert titles["/blog/tags/"] == "Tags in Blog"
    assert titles["/tags/python/"] == "Tags: python"
    assert titles["/blog/tags/python/"] == "Tags in Blog: python"
    assert len(set(titles.values())) == len(titles)


def test_rendered_scoped_term_page_crumb_names_its_scope() -> None:
    """The back link on a scoped term page says which scope it returns to."""
    page = _page(source="blog/posts/a.md", title="A", tags=["python"])
    page.output_url = "/blog/posts/a/"
    config = _config(blog_taxonomies=["tags"])
    generated = generate_taxonomy_pages(build_taxonomies([page], config), config)
    scoped = next(item for item in generated if item.output_url == "/blog/tags/python/")
    html = _render(scoped, "taxonomy.html")
    assert "All tags in blog" in html


def _config_with_slug_format(slug_format: str) -> BartlebyConfig:
    config = _config(blog_taxonomies=["tags"])
    config.taxonomies["tags"] = TaxonomyConfig(name="tags", slug_format=slug_format)
    return config


def test_term_url_matches_generated_page_urls_for_both_scopes() -> None:
    """``term_url`` and the page generator share one URL scheme, so links cannot drift."""
    page = _page(source="blog/posts/a.md", title="A", tags=["Hello World"])
    config = _config_with_slug_format("t-{slug}")
    result = build_taxonomies([page], config)
    urls = {generated.output_url for generated in generate_taxonomy_pages(result, config)}
    assert term_url("tags", "t-hello-world") in urls
    assert term_url("tags", "t-hello-world", "blog") in urls
    assert term_url("tags", "t-hello-world", "blog") == "/blog/tags/t-hello-world/"


def test_taxonomy_links_point_at_the_pages_content_type_scope() -> None:
    """A post links to its own content type's term page, where its siblings are listed."""
    page = _page(source="blog/posts/a.md", title="A", tags=["Hello World", "python"])
    config = _config_with_slug_format("t-{slug}")
    result = build_taxonomies([page], config)
    links = taxonomy_links_for(page, result.global_taxonomies, result.content_type_taxonomies)
    assert [(link.term, link.url) for link in links["tags"]] == [
        ("Hello World", "/blog/tags/t-hello-world/"),
        ("python", "/blog/tags/t-python/"),
    ]
    urls = {generated.output_url for generated in generate_taxonomy_pages(result, config)}
    assert all(link.url in urls for link in links["tags"])


def test_taxonomy_links_fall_back_to_global_without_a_content_type() -> None:
    """A page outside any content type links to the global term page when the term exists."""
    tagged = _page(source="blog/posts/a.md", title="A", tags=["python"])
    config = _config_with_slug_format("{slug}")
    result = build_taxonomies([tagged], config)
    loose = _page(source="about.md", title="About", tags=["python"])
    loose.content_type_name = None
    links = taxonomy_links_for(loose, result.global_taxonomies, result.content_type_taxonomies)
    assert [link.url for link in links["tags"]] == ["/tags/python/"]


def test_taxonomy_links_have_no_url_for_unlisted_terms() -> None:
    """A value in a taxonomy the page's type did not opt into stays as plain text."""
    page = _page(source="blog/posts/a.md", title="A", tags=["python"], categories=["news"])
    config = _config(blog_taxonomies=["tags"])
    result = build_taxonomies([page], config)
    links = taxonomy_links_for(page, result.global_taxonomies, result.content_type_taxonomies)
    assert [(link.term, link.url) for link in links["categories"]] == [("news", None)]
