# ABOUTME: Tests for navigation building, auto-generation, and prev/next linking.
# Covers explicit config nav, auto-generated nav from pages, and page linking.

from __future__ import annotations

from pathlib import Path

from bartleby.config import (
    AIConfig,
    BartlebyConfig,
    ContentTypeConfig,
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


def _config(
    *,
    nav: list[dict[str, object]] | None = None,
    content_type_paths: tuple[str, ...] = (),
) -> BartlebyConfig:
    return BartlebyConfig(
        site=SiteConfig(title="t", url="u"),
        nav=nav,
        theme=ThemeConfig(),
        authors_file=".authors.yml",
        content_types={
            f"type{position}": ContentTypeConfig(name=f"type{position}", path=path)
            for position, path in enumerate(content_type_paths)
        },
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


def test_section_index_url_points_at_the_sections_index_page() -> None:
    """A section whose children include an ``index.md`` exposes that page's URL."""
    pages = [
        _page("concepts/index.md", "Overview", "/concepts/"),
        _page("concepts/urls.md", "URLs", "/concepts/urls/"),
    ]
    nav_config = [
        {"Concepts": [{"Overview": "concepts/index.md"}, {"URLs": "concepts/urls.md"}]},
    ]
    nav = build_navigation(_config(nav=nav_config), pages)
    assert nav.items[0].index_url == "/concepts/"


def test_section_index_url_is_none_without_an_index_page() -> None:
    """A section with no ``index.md`` child has no index URL, and a plain page has none."""
    pages = [
        _page("docs/intro.md", "Intro", "/docs/intro/"),
        _page("about.md", "About", "/about/"),
    ]
    nav_config = [{"Docs": [{"Intro": "docs/intro.md"}]}, {"About": "about.md"}]
    nav = build_navigation(_config(nav=nav_config), pages)
    assert [item.index_url for item in nav.items] == [None, None]


def _concepts_pages() -> list[Page]:
    return [
        _page("concepts/index.md", "Overview", "/concepts/"),
        _page("concepts/urls.md", "URLs", "/concepts/urls/"),
        _page("concepts/front-matter.md", "front matter", "/concepts/front-matter/"),
        _page("concepts/advanced/tuning.md", "Tuning", "/concepts/advanced/tuning/"),
        _page("concepts/advanced/index.md", "Advanced", "/concepts/advanced/"),
        _page("about.md", "About", "/about/"),
    ]


def test_directory_target_expands_into_a_section_with_children() -> None:
    """A ``dir/`` nav target becomes a section holding the pages in that directory."""
    nav = build_navigation(_config(nav=[{"Concepts": "concepts/"}]), _concepts_pages())
    concepts = nav.items[0]
    assert concepts.is_section
    assert concepts.index_url == "/concepts/"
    assert concepts.url == "/concepts/"
    assert [child.title for child in concepts.children] == [
        "Overview",
        "Advanced",
        "front matter",
        "URLs",
    ]


def test_directory_target_nests_subdirectories_as_sections() -> None:
    """A subdirectory becomes a nested section with its own index_url and children."""
    nav = build_navigation(_config(nav=[{"Concepts": "concepts/"}]), _concepts_pages())
    advanced = next(child for child in nav.items[0].children if child.title == "Advanced")
    assert advanced.is_section
    assert advanced.index_url == "/concepts/advanced/"
    assert [child.title for child in advanced.children] == ["Advanced", "Tuning"]


def test_directory_target_children_order_is_deterministic() -> None:
    """Input page order does not change the expanded children order."""
    pages = _concepts_pages()
    forward = build_navigation(_config(nav=[{"Concepts": "concepts/"}]), pages)
    backward = build_navigation(_config(nav=[{"Concepts": "concepts/"}]), pages[::-1])
    assert [c.title for c in forward.items[0].children] == [
        c.title for c in backward.items[0].children
    ]
    assert [p.title for p in forward.pages_flat] == [p.title for p in backward.pages_flat]


def test_directory_target_flattens_index_first_then_children() -> None:
    """Prev/next order walks the section index, then its children."""
    nav = build_navigation(_config(nav=[{"Concepts": "concepts/"}]), _concepts_pages())
    assert [page.title for page in nav.pages_flat] == [
        "Overview",
        "Advanced",
        "Tuning",
        "front matter",
        "URLs",
    ]


def test_directory_without_index_has_no_index_url() -> None:
    """A directory with no index.md expands but carries no index_url or url."""
    pages = [_page("docs/a.md", "A", "/docs/a/")]
    nav = build_navigation(_config(nav=[{"Docs": "docs/"}]), pages)
    assert nav.items[0].index_url is None
    assert nav.items[0].url is None
    assert [child.title for child in nav.items[0].children] == ["A"]


def test_content_type_directory_target_stays_a_listing_link() -> None:
    """A content-type directory is a link to its generated listing, not a tree."""
    pages = [
        _page("guides/index.md", "Guides", "/guides/"),
        _page("guides/posts/one.md", "One", "/guides/posts/one/"),
    ]
    config = _config(nav=[{"Posts": "guides/posts/"}], content_type_paths=("guides/posts",))
    item = build_navigation(config, pages).items[0]
    assert item.children == []
    assert item.url == "/guides/posts/"


def test_directory_containing_a_content_type_stays_a_listing_link() -> None:
    """A parent of a content-type directory is not expanded either."""
    pages = [
        _page("guides/index.md", "Guides", "/guides/"),
        _page("guides/posts/one.md", "One", "/guides/posts/one/"),
    ]
    config = _config(nav=[{"Guides": "guides/"}], content_type_paths=("guides/posts",))
    item = build_navigation(config, pages).items[0]
    assert item.children == []
    assert item.url == "/guides/"


def test_auto_nav_sections_carry_children() -> None:
    """Auto-generated top-level sections expand their directory like explicit nav."""
    nav = build_navigation(_config(), _concepts_pages())
    concepts = next(item for item in nav.items if item.title == "Concepts")
    assert concepts.is_section
    assert concepts.index_url == "/concepts/"
    assert [child.title for child in concepts.children][0] == "Overview"
    assert "Advanced" in [child.title for child in concepts.children]
