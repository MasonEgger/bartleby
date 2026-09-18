# ABOUTME: Tests for content type listing page generation.
# Covers listing creation, sort order, intro content from index.md, and pagination.

from __future__ import annotations

import datetime
from pathlib import Path

import jinja2
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
from bartleby.listings import generate_listing_pages
from bartleby.theme import get_theme_templates_dir


def _render(page: Page, template_name: str) -> str:
    """Render a generated listing/taxonomy page through the real theme template.

    Builds a minimal but valid base context so the template's chrome renders, then
    returns the HTML so tests can grep the actual output rather than only checking
    the virtual :class:`Page` dataclass shape.
    """
    from bartleby.config import KNOWN_FEATURES
    from bartleby.templates import make_feature_checker

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader([str(get_theme_templates_dir())]),
        autoescape=True,
    )
    env.globals["feature"] = make_feature_checker(list(KNOWN_FEATURES))
    context: dict[str, object] = {
        "site": {"title": "Site", "url": "https://example.com", "description": "Desc"},
        "page": page,
        "nav": [],
        "pages": [],
        "build": {"date": "2026-05-23", "bartleby_version": "0.1.0"},
        "config": {"theme": {"color_mode": {"toggle": True}}},
        "extra_css": [],
        "extra_js": [],
        "seo": None,
    }
    return env.get_template(template_name).render(**context)


def _post(*, source: str, title: str, date: datetime.date, draft: bool = False) -> Page:
    return Page(
        source_path=Path(source),
        abs_source_path=Path("/abs") / source,
        title=title,
        date=date,
        draft=draft,
        content_type_name="blog",
    )


def _config(*, paginated: bool = False, per_page: int = 10) -> BartlebyConfig:
    return BartlebyConfig(
        site=SiteConfig(title="t", url="u"),
        nav=None,
        theme=ThemeConfig(),
        authors_file=".authors.yml",
        content_types={
            "blog": ContentTypeConfig(
                name="blog",
                path="blog/posts",
                pagination=PaginationConfig(enabled=paginated, per_page=per_page),
            ),
        },
        taxonomies={"tags": TaxonomyConfig(name="tags", slug_format="{slug}")},
        exclude_patterns=[],
        markdown_extensions=[],
        plugins=[],
        extra_css=[],
        extra_js=[],
        ai=AIConfig(),
        dev_server=DevServerConfig(),
        config_dir=Path("/tmp"),
    )


@pytest.fixture
def content_dir(tmp_path: Path) -> Path:
    """A bare ``content/`` directory the tests can populate per-case."""
    target = tmp_path / "content"
    target.mkdir()
    return target


def test_listing_page_generated(content_dir: Path) -> None:
    """Each content type gets at least one listing page at its base URL."""
    posts = [_post(source="blog/posts/a.md", title="A", date=datetime.date(2026, 3, 1))]
    listings = generate_listing_pages(posts, _config(), content_dir)
    urls = {page.output_url for page in listings}
    assert "/blog/" in urls


def test_listing_posts_reverse_chronological(content_dir: Path) -> None:
    """``intro_content`` aside, the listed posts are newest first."""
    older = _post(source="blog/posts/o.md", title="Older", date=datetime.date(2026, 1, 1))
    newer = _post(source="blog/posts/n.md", title="Newer", date=datetime.date(2026, 4, 1))
    listings = generate_listing_pages([older, newer], _config(), content_dir)
    listing = next(page for page in listings if page.output_url == "/blog/")
    posts_in_context = listing.custom_metadata["posts"]
    assert isinstance(posts_in_context, list)
    assert posts_in_context[0] is newer
    assert posts_in_context[1] is older


def test_listing_includes_index_md_content(content_dir: Path) -> None:
    """A ``content/{type}/index.md`` provides the listing's intro content, rendered as HTML."""
    (content_dir / "blog").mkdir()
    (content_dir / "blog" / "index.md").write_text(
        "---\ntitle: Blog\n---\n## Welcome\n\nThis is **bold** text.\n"
    )
    posts = [_post(source="blog/posts/a.md", title="A", date=datetime.date(2026, 3, 1))]
    listings = generate_listing_pages(posts, _config(), content_dir)
    listing = next(page for page in listings if page.output_url == "/blog/")
    intro_content = str(listing.custom_metadata.get("intro_content", ""))
    # The toc extension adds an id attribute to headings, so check the tag and
    # text rather than the exact opening tag (matches test_markdown_pipeline.py's
    # convention for asserting rendered heading output).
    assert "<h2" in intro_content
    assert "Welcome</h2>" in intro_content
    assert "<strong>bold</strong>" in intro_content
    assert "## Welcome" not in intro_content


def test_listing_without_index_md(content_dir: Path) -> None:
    """Without a content/{type}/index.md the intro content is empty."""
    posts = [_post(source="blog/posts/a.md", title="A", date=datetime.date(2026, 3, 1))]
    listings = generate_listing_pages(posts, _config(), content_dir)
    listing = next(page for page in listings if page.output_url == "/blog/")
    assert listing.custom_metadata.get("intro_content", "") == ""


def test_listing_with_pagination(content_dir: Path) -> None:
    """Pagination splits the listing into /blog/, /blog/page/2/, /blog/page/3/."""
    posts = [
        _post(
            source=f"blog/posts/post-{i}.md", title=f"Post {i}", date=datetime.date(2026, 1, i + 1)
        )
        for i in range(25)
    ]
    listings = generate_listing_pages(posts, _config(paginated=True, per_page=10), content_dir)
    urls = {page.output_url for page in listings}
    assert "/blog/" in urls
    assert "/blog/page/2/" in urls
    assert "/blog/page/3/" in urls


def test_listing_pagination_disabled(content_dir: Path) -> None:
    """Without pagination, a single listing page contains every post."""
    posts = [
        _post(
            source=f"blog/posts/post-{i}.md", title=f"Post {i}", date=datetime.date(2026, 1, i + 1)
        )
        for i in range(25)
    ]
    listings = generate_listing_pages(posts, _config(paginated=False), content_dir)
    blog_listings = [page for page in listings if page.output_url == "/blog/"]
    assert len(blog_listings) == 1
    posts_in_context = blog_listings[0].custom_metadata["posts"]
    assert isinstance(posts_in_context, list)
    assert len(posts_in_context) == 25


def test_listing_excludes_drafts(content_dir: Path) -> None:
    """Draft posts are not included in listing pages."""
    posts = [
        _post(source="blog/posts/published.md", title="Published", date=datetime.date(2026, 3, 1)),
        _post(
            source="blog/posts/draft.md",
            title="Draft",
            date=datetime.date(2026, 3, 2),
            draft=True,
        ),
    ]
    listings = generate_listing_pages(posts, _config(), content_dir)
    listing = next(page for page in listings if page.output_url == "/blog/")
    titles = {post.title for post in listing.custom_metadata["posts"] if isinstance(post, Page)}
    assert "Published" in titles
    assert "Draft" not in titles


def test_rendered_listing_html_links_each_post(content_dir: Path) -> None:
    """Rendering the list template emits a link and title for every listed post.

    This is the regression guard the audit was missing: the dataclass can carry
    the right ``posts`` while the template still fails to render them. Grep the
    actual HTML.
    """
    older = _post(source="blog/posts/o.md", title="Older Post", date=datetime.date(2026, 1, 1))
    newer = _post(source="blog/posts/n.md", title="Newer Post", date=datetime.date(2026, 4, 1))
    older.output_url = "/blog/posts/o/"
    newer.output_url = "/blog/posts/n/"
    listings = generate_listing_pages([older, newer], _config(), content_dir)
    listing = next(page for page in listings if page.output_url == "/blog/")

    html = _render(listing, "defaults/list.html")
    assert 'href="/blog/posts/n/"' in html
    assert 'href="/blog/posts/o/"' in html
    assert "Newer Post" in html
    assert "Older Post" in html
    # Newest-first order is preserved in the rendered markup, not just the data.
    assert html.index("Newer Post") < html.index("Older Post")


def test_rendered_listing_html_omits_drafts(content_dir: Path) -> None:
    """A draft post never appears in the rendered listing HTML."""
    published = _post(
        source="blog/posts/pub.md", title="Published Post", date=datetime.date(2026, 3, 1)
    )
    published.output_url = "/blog/posts/pub/"
    draft = _post(
        source="blog/posts/draft.md",
        title="Draft Post",
        date=datetime.date(2026, 3, 2),
        draft=True,
    )
    draft.output_url = "/blog/posts/draft/"
    listings = generate_listing_pages([published, draft], _config(), content_dir)
    listing = next(page for page in listings if page.output_url == "/blog/")

    html = _render(listing, "defaults/list.html")
    assert "Published Post" in html
    assert "Draft Post" not in html
