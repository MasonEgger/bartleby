# ABOUTME: Tests for navigation building, auto-generation, and prev/next linking.
# Covers explicit config nav, auto-generated nav from pages, and page linking.

from __future__ import annotations

from pathlib import Path

from bartleby.config import (
    AIConfig,
    BartlebyConfig,
    DevServerConfig,
    SiteConfig,
    ThemeConfig,
)
from bartleby.content import Page
from bartleby.navigation import (
    Navigation,
    NavItem,
    build_navigation,
    link_pages,
)


def _page(source: str, title: str, output_url: str) -> Page:
    page = Page(
        source_path=Path(source),
        abs_source_path=Path("/abs") / source,
        title=title,
    )
    page.output_url = output_url
    return page


def _config(*, nav: list[dict[str, object]] | None = None) -> BartlebyConfig:
    return BartlebyConfig(
        site=SiteConfig(title="t", url="u"),
        nav=nav,
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


def test_explicit_nav_from_config() -> None:
    """An explicit nav config builds NavItems with title/URL from the listed pages."""
    pages = [
        _page("index.md", "Home", "/"),
        _page("blog/index.md", "Blog", "/blog/"),
        _page("about.md", "About", "/about/"),
    ]
    nav_config: list[dict[str, object]] = [
        {"Home": "index.md"},
        {"Blog": "blog/"},
        {"About": "about.md"},
    ]
    nav = build_navigation(_config(nav=nav_config), pages)
    assert [item.title for item in nav.items] == ["Home", "Blog", "About"]
    assert nav.items[0].url == "/"
    assert nav.items[1].url == "/blog/"


def test_explicit_nav_nested() -> None:
    """Nested ``children`` lists in nav config produce nested NavItems."""
    pages = [
        _page("docs/intro.md", "Intro", "/docs/intro/"),
        _page("docs/guide.md", "Guide", "/docs/guide/"),
    ]
    nav_config = [
        {"Docs": [{"Intro": "docs/intro.md"}, {"Guide": "docs/guide.md"}]},
    ]
    nav = build_navigation(_config(nav=nav_config), pages)
    assert len(nav.items) == 1
    docs = nav.items[0]
    assert docs.title == "Docs"
    assert docs.is_section is True
    assert len(docs.children) == 2
    assert [child.title for child in docs.children] == ["Intro", "Guide"]


def test_auto_generate_nav() -> None:
    """Without a nav config, top-level pages and directories become nav items."""
    pages = [
        _page("index.md", "Home", "/"),
        _page("about.md", "About", "/about/"),
        _page("blog/index.md", "Blog", "/blog/"),
        _page("blog/posts/first.md", "First", "/blog/posts/first/"),
    ]
    nav = build_navigation(_config(), pages)
    titles = [item.title for item in nav.items]
    assert "Home" in titles
    assert "About" in titles
    assert "Blog" in titles


def test_auto_nav_alphabetical() -> None:
    """Auto-generated items appear in alphabetical order by title."""
    pages = [
        _page("zebra.md", "Zebra", "/zebra/"),
        _page("apple.md", "Apple", "/apple/"),
        _page("mango.md", "Mango", "/mango/"),
    ]
    nav = build_navigation(_config(), pages)
    titles = [item.title for item in nav.items]
    assert titles == sorted(titles)


def test_auto_nav_directory_names_as_sections() -> None:
    """A directory without an ``index.md`` still becomes a title-cased section."""
    pages = [
        _page("blog/posts/first.md", "First", "/blog/posts/first/"),
    ]
    nav = build_navigation(_config(), pages)
    titles = [item.title for item in nav.items]
    assert "Blog" in titles


def test_auto_nav_uses_page_title() -> None:
    """Auto-generated nav titles come from front matter, not filenames."""
    pages = [
        _page("about-us.md", "About Our Company", "/about-us/"),
    ]
    nav = build_navigation(_config(), pages)
    assert nav.items[0].title == "About Our Company"


def test_prev_next_linking() -> None:
    """``link_pages`` walks ``pages_flat`` and wires previous/next on each Page."""
    pages = [
        _page("a.md", "A", "/a/"),
        _page("b.md", "B", "/b/"),
        _page("c.md", "C", "/c/"),
    ]
    nav = Navigation(
        items=[
            NavItem(title="A", url="/a/", page=pages[0]),
            NavItem(title="B", url="/b/", page=pages[1]),
            NavItem(title="C", url="/c/", page=pages[2]),
        ],
        pages_flat=pages,
    )
    link_pages(nav)
    assert pages[0].next is pages[1]
    assert pages[1].previous is pages[0]
    assert pages[1].next is pages[2]


def test_prev_next_none_at_edges() -> None:
    """The first page's ``previous`` and the last page's ``next`` are ``None``."""
    pages = [_page("a.md", "A", "/a/"), _page("b.md", "B", "/b/")]
    nav = Navigation(
        items=[
            NavItem(title="A", url="/a/", page=pages[0]),
            NavItem(title="B", url="/b/", page=pages[1]),
        ],
        pages_flat=pages,
    )
    link_pages(nav)
    assert pages[0].previous is None
    assert pages[1].next is None


def test_pages_not_in_nav_no_prev_next() -> None:
    """Pages absent from ``pages_flat`` keep ``previous``/``next`` as ``None``."""
    in_nav = _page("a.md", "A", "/a/")
    outside = _page("hidden.md", "Hidden", "/hidden/")
    nav = Navigation(
        items=[NavItem(title="A", url="/a/", page=in_nav)],
        pages_flat=[in_nav],
    )
    link_pages(nav)
    assert outside.previous is None
    assert outside.next is None
