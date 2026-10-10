# ABOUTME: Tests for the interactive partials and error page shared by material and scrivener.
# Covers the search modal binding, back-to-top link, and the 404 page's absolute links.

from __future__ import annotations

import re
from pathlib import Path

import jinja2
import pytest

from bartleby.templates import make_feature_checker
from bartleby.theme_loader import THEME_FEATURES
from tests.theme_helpers import bundled_theme

THEMES = ["material", "scrivener"]


ENGINE_SOURCE = (
    Path(__file__).resolve().parents[1] / "src/bartleby/themes/base/static/js/search.js"
)


def _render(
    theme_name: str,
    template: str,
    nav: list[dict[str, str]] | None = None,
    override_dir: Path | None = None,
    page_url: str = "/404.html",
) -> str:
    template_dirs = list(bundled_theme(theme_name).templates_dirs())
    if override_dir is not None:
        template_dirs.insert(0, override_dir)
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader([str(path) for path in template_dirs]),
        autoescape=True,
    )
    env.globals["feature"] = make_feature_checker(list(THEME_FEATURES))
    context: dict[str, object] = {
        "site": {"title": "Site", "url": "https://example.com", "description": "Desc"},
        "page": {
            "title": "Not found",
            "content": "",
            "url": page_url,
            "description": "",
            "previous": None,
            "next": None,
            "toc": [],
            "custom_metadata": {},
        },
        "nav": nav or [],
        "pages": [],
        "build": {"date": "2026-05-23", "bartleby_version": "0.1.0"},
        "config": {"theme": {"color_mode": {"toggle": True}}},
        "extra_css": [],
        "extra_js": [],
        "seo": None,
    }
    return env.get_template(template).render(**context)


@pytest.mark.parametrize("theme_name", THEMES)
def test_search_modal_binds_the_base_engine(theme_name: str) -> None:
    """The modal root binds bartlebySearch and is x-cloak, so JS-off pages show no dead trigger."""
    rendered = _render(theme_name, "base.html")
    root = re.search(r'<div class="search-modal"[^>]*>', rendered)
    assert root is not None
    assert 'x-data="bartlebySearch()"' in root.group(0)
    assert "x-cloak" in root.group(0)
    assert 'x-ref="input"' in rendered


@pytest.mark.parametrize("theme_name", THEMES)
def test_search_modal_renders_exactly_once(theme_name: str) -> None:
    """A page carries one modal, no matter how many partials sit around it."""
    assert _render(theme_name, "base.html").count('class="search-modal"') == 1


@pytest.mark.parametrize("theme_name", THEMES)
def test_header_renders_the_search_trigger(theme_name: str) -> None:
    """The header carries the trigger, which opens the modal through the window event."""
    rendered = _render(theme_name, "base.html")
    assert 'class="search-trigger"' in rendered
    assert "bartleby:search-open" in rendered


def test_scrivener_keeps_the_modal_when_an_override_drops_the_trigger(tmp_path: Path) -> None:
    """A project header.html without the trigger still leaves exactly one bound modal."""
    partials = tmp_path / "partials"
    partials.mkdir()
    (partials / "header.html").write_text("<header>Bare header</header>")
    rendered = _render("scrivener", "base.html", override_dir=tmp_path)
    assert "Bare header" in rendered
    assert 'class="search-trigger"' not in rendered
    assert rendered.count('class="search-modal"') == 1
    assert rendered.count('x-data="bartlebySearch()"') == 1


def test_engine_listens_for_the_open_event_and_shortcuts() -> None:
    """The base engine opens on the window event, on "/", and on Ctrl/Cmd+K."""
    source = ENGINE_SOURCE.read_text()
    assert 'addEventListener("bartleby:search-open"' in source
    assert 'event.key === "/"' in source
    assert "event.ctrlKey || event.metaKey" in source
    assert "isContentEditable" in source


@pytest.mark.parametrize("theme_name", THEMES)
def test_back_to_top_is_a_real_link(theme_name: str) -> None:
    """Back-to-top is <a href="#"> with a label and no x-cloak, so it works with JS off."""
    rendered = _render(theme_name, "base.html")
    link = re.search(r'<a\b(?:[^>"]|"[^"]*")*class="back-to-top"(?:[^>"]|"[^"]*")*>', rendered)
    assert link is not None
    assert 'href="#"' in link.group(0)
    assert 'aria-label="Back to top"' in link.group(0)
    assert "x-cloak" not in link.group(0)
    assert "prefers-reduced-motion" in link.group(0)


@pytest.mark.parametrize("theme_name", THEMES)
def test_404_uses_absolute_links(theme_name: str) -> None:
    """Every internal link on the 404 starts with a slash so it works from any URL depth."""
    rendered = _render(theme_name, "404.html", nav=[{"title": "Guides", "url": "/guides/"}])
    article = rendered[rendered.index('<article class="not-found"') : rendered.index("</article>")]
    hrefs = re.findall(r'href="([^"]*)"', article)
    assert "/" in hrefs
    assert "/guides/" in hrefs
    assert all(href.startswith("/") for href in hrefs)


@pytest.mark.parametrize("theme_name", THEMES)
def test_404_links_a_section_that_has_no_page_of_its_own(theme_name: str) -> None:
    """A group with no url of its own links to the first page inside it."""
    nav = [{"title": "Docs", "url": None, "children": [{"title": "Intro", "url": "/docs/intro/"}]}]
    rendered = _render(theme_name, "404.html", nav=nav)
    article = rendered[rendered.index('<article class="not-found"') : rendered.index("</article>")]
    assert 'href="/docs/intro/">Docs</a>' in article


@pytest.mark.parametrize("theme_name", THEMES)
def test_sidebar_folds_behind_a_toggle_that_needs_javascript_to_appear(theme_name: str) -> None:
    """The toggle button is in the markup, and only Alpine marks the sidebar collapsible."""
    nav = [
        {
            "title": "Docs",
            "url": None,
            "index_url": None,
            "children": [{"title": "Intro", "url": "/docs/intro/", "children": []}],
        }
    ]
    rendered = _render(theme_name, "page.html", nav=nav, page_url="/docs/intro/")
    sidebar = rendered[rendered.index('<nav class="sidebar-nav"') :]
    assert 'class="sidebar-toggle"' in sidebar
    assert 'class="sidebar-tree"' in sidebar
    assert "classList.add('js-collapsible')" in sidebar
    assert 'class="sidebar-nav js-collapsible' not in sidebar


@pytest.mark.parametrize("theme_name", THEMES)
def test_sidebar_toggle_controls_the_tree(theme_name: str) -> None:
    """The toggle names the tree it folds through aria-controls."""
    nav = [
        {
            "title": "Docs",
            "url": None,
            "index_url": None,
            "children": [{"title": "Intro", "url": "/docs/intro/", "children": []}],
        }
    ]
    rendered = _render(theme_name, "page.html", nav=nav, page_url="/docs/intro/")
    toggle = re.search(r'<button[^>]*class="sidebar-toggle"[^>]*>', rendered)
    tree = re.search(r'<div class="sidebar-tree" id="([^"]+)"', rendered)
    assert toggle is not None
    assert tree is not None
    assert f'aria-controls="{tree.group(1)}"' in toggle.group(0)


@pytest.mark.parametrize("theme_name", THEMES)
@pytest.mark.parametrize("template", ["page.html", "defaults/post.html"])
def test_reading_column_is_the_search_highlight_root(theme_name: str, template: str) -> None:
    """Page and post templates mark their article, so ?h= marks never touch navigation."""
    rendered = _render(theme_name, template, page_url="/docs/intro/")
    article = re.search(r"<article[^>]*>", rendered)
    assert article is not None
    assert "data-search-highlight-root" in article.group(0)


def test_search_engine_scopes_highlight_to_the_reading_column() -> None:
    """The engine prefers the marked column, then the article, and only then main."""
    source = ENGINE_SOURCE.read_text(encoding="utf-8")
    assert "[data-search-highlight-root]" in source
    assert source.index("[data-search-highlight-root]") < source.index('"main article"')
    assert source.index('"main article"') < source.index('querySelector("main")')
