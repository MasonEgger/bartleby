# ABOUTME: Tests for how both bundled themes render content-type collections.
# Covers undated listing rows, section sidebars on posts and listings, and scoped taxonomy crumbs.

from __future__ import annotations

import datetime
import re
from pathlib import Path

import jinja2
import pytest

from bartleby.build import build
from bartleby.content import Page
from bartleby.listings import LISTING_KIND_KEY, ListingKind
from bartleby.navigation import NavItem
from bartleby.taxonomies import TAXONOMY_KIND_KEY, TaxonomyKind
from bartleby.templates import make_feature_checker
from bartleby.theme_loader import THEME_FEATURES
from tests.theme_helpers import bundled_theme

THEMES = ["material", "scrivener"]


def _page(
    source: str,
    title: str,
    url: str,
    *,
    date: datetime.date | None = None,
    content_type: str | None = None,
) -> Page:
    page = Page(
        source_path=Path(source),
        abs_source_path=Path("/abs") / source,
        title=title,
        date=date,
        content_type_name=content_type,
    )
    page.output_url = url
    return page


def _render(theme_name: str, template_name: str, page: Page, nav: list[NavItem]) -> str:
    """Render ``template_name`` from a bundled theme with a minimal valid context."""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(
            [str(path) for path in bundled_theme(theme_name).templates_dirs()]
        ),
        autoescape=True,
    )
    env.globals["feature"] = make_feature_checker(list(THEME_FEATURES))
    context: dict[str, object] = {
        "site": {"title": "Site", "url": "https://example.com", "description": "Desc"},
        "page": page,
        "nav": nav,
        "pages": [],
        "build": {"date": "2026-05-23", "bartleby_version": "0.1.0"},
        "config": {"theme": {"color_mode": {"toggle": True}}},
        "extra_css": [],
        "extra_js": [],
        "seo": None,
    }
    return env.get_template(template_name).render(**context)


def _listing(posts: list[Page]) -> Page:
    listing = _page("__generated__/listings/reference", "Reference", "/reference/")
    listing.content_type_name = "reference"
    listing.custom_metadata = {
        LISTING_KIND_KEY: ListingKind.CONTENT_TYPE,
        "posts": posts,
        "intro_content": "",
    }
    return listing


def _reference_nav(children: list[Page]) -> list[NavItem]:
    return [
        NavItem(
            title="Reference",
            url="/reference/",
            index_url="/reference/",
            is_section=True,
            children=[
                NavItem(title=child.title, url=child.output_url, page=child) for child in children
            ],
        )
    ]


@pytest.mark.parametrize("theme_name", THEMES)
def test_undated_listing_rows_have_no_date_column(theme_name: str) -> None:
    """A listing row for a page without a date renders no empty date placeholder."""
    undated = _page("reference/pages/cli.md", "CLI", "/reference/pages/cli/")
    html = _render(theme_name, "defaults/list.html", _listing([undated]), [])
    assert "<span></span>" not in html
    assert "<time" not in html
    assert "post-list-item--undated" in html or theme_name == "material"


@pytest.mark.parametrize("theme_name", THEMES)
def test_dated_listing_rows_keep_their_date(theme_name: str) -> None:
    """A dated row still shows its date."""
    dated = _page("guides/posts/a.md", "A", "/guides/posts/a/", date=datetime.date(2026, 3, 1))
    html = _render(theme_name, "defaults/list.html", _listing([dated]), [])
    assert '<time datetime="2026-03-01">' in html


@pytest.mark.parametrize("theme_name", THEMES)
def test_content_type_post_shows_its_section_sidebar(theme_name: str) -> None:
    """A page in a content type gets the section tree when the nav lists its siblings."""
    cli = _page("reference/pages/cli.md", "CLI", "/reference/pages/cli/", content_type="reference")
    config = _page(
        "reference/pages/config.md", "Config", "/reference/pages/config/", content_type="reference"
    )
    html = _render(theme_name, "defaults/post.html", cli, _reference_nav([cli, config]))
    assert 'class="sidebar-nav"' in html
    assert 'href="/reference/pages/config/"' in html
    assert 'aria-current="page"' in html


@pytest.mark.parametrize("theme_name", THEMES)
def test_content_type_listing_shows_its_section_sidebar(theme_name: str) -> None:
    """The listing page itself carries the section tree too."""
    cli = _page("reference/pages/cli.md", "CLI", "/reference/pages/cli/", content_type="reference")
    html = _render(theme_name, "defaults/list.html", _listing([cli]), _reference_nav([cli]))
    assert 'class="sidebar-nav"' in html
    assert 'href="/reference/pages/cli/"' in html


@pytest.mark.parametrize("theme_name", THEMES)
def test_post_outside_any_section_has_no_sidebar(theme_name: str) -> None:
    """A post whose nav entry has no children keeps the single reading column."""
    post = _page("blog/posts/a.md", "A", "/blog/posts/a/", content_type="blog")
    nav = [NavItem(title="Blog", url="/blog/")]
    html = _render(theme_name, "defaults/post.html", post, nav)
    assert 'class="sidebar-nav"' not in html


@pytest.mark.parametrize("theme_name", THEMES)
def test_scoped_term_page_crumb_names_its_scope(theme_name: str) -> None:
    """The back link on a per-content-type term page says which scope it returns to."""
    term_page = _page(
        "__generated__/taxonomy/guides/tags/ai", "Tags in Guides: ai", "/guides/tags/ai/"
    )
    term_page.content_type_name = "guides"
    term_page.custom_metadata = {
        "taxonomy_name": "tags",
        TAXONOMY_KIND_KEY: TaxonomyKind.TERM,
        "taxonomy_term": "ai",
        "posts": [],
    }
    html = _render(theme_name, "taxonomy.html", term_page, [])
    assert "All tags in guides" in html


@pytest.mark.parametrize("theme_name", THEMES)
def test_post_without_date_authors_or_readtime_has_no_empty_meta_line(theme_name: str) -> None:
    """A post with nothing to put in the meta line leaves out the line, not an empty paragraph."""
    post = _page(
        "reference/pages/cli.md", "CLI", "/reference/pages/cli/", content_type="reference"
    )
    html = _render(theme_name, "defaults/post.html", post, [])
    assert "post-meta" not in html


@pytest.mark.parametrize("theme_name", THEMES)
def test_dated_post_keeps_its_meta_line(theme_name: str) -> None:
    """A dated post still renders its meta line."""
    post = _page(
        "blog/posts/a.md",
        "A",
        "/blog/posts/a/",
        date=datetime.date(2026, 3, 1),
        content_type="blog",
    )
    html = _render(theme_name, "defaults/post.html", post, [])
    assert '<time datetime="2026-03-01">' in html


def _tagged_project(root: Path, theme_name: str) -> Path:
    """Write a tiny site whose blog posts carry tags, with a non-default slug format."""
    (root / "content" / "blog").mkdir(parents=True)
    (root / "bartleby.yml").write_text(
        "site:\n  title: T\n  url: https://example.com\n"
        f"theme:\n  name: {theme_name}\n"
        "content_types:\n  blog:\n    path: blog\n    taxonomies: [tags]\n"
        'taxonomies:\n  tags:\n    slug_format: "t-{slug}"\n',
        encoding="utf-8",
    )
    (root / "content" / "index.md").write_text("---\ntitle: Home\n---\nHi\n", encoding="utf-8")
    for name in ("one", "two"):
        (root / "content" / "blog" / f"{name}.md").write_text(
            f"---\ntitle: Post {name}\ndate: 2026-01-0{1 if name == 'one' else 2}\n"
            "tags: [Hello World]\n---\nBody\n",
            encoding="utf-8",
        )
    return root


@pytest.mark.parametrize("theme_name", THEMES)
def test_post_tag_chips_link_to_scoped_pages(theme_name: str, tmp_path: Path) -> None:
    project = _tagged_project(tmp_path, theme_name)
    build(project / "bartleby.yml")
    site = project / "site"
    html = (site / "blog" / "one" / "index.html").read_text(encoding="utf-8")
    foot = html[html.index('class="tag-list"') :]
    hrefs = re.findall(r'<a href="([^"]+)"[^>]*>\s*Hello World\s*</a>', foot)
    assert hrefs == ["/blog/tags/t-hello-world/"]
    assert (site / hrefs[0].strip("/") / "index.html").is_file()
