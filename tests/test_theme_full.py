# ABOUTME: Tests for the full Material theme styling and interactive components.
# Covers admonition styling, code blocks, tabs, search modal, TOC sidebar, back-to-top.

from __future__ import annotations

import jinja2

from bartleby.theme import get_theme_templates_dir


def _env() -> jinja2.Environment:
    from bartleby.config import KNOWN_FEATURES
    from bartleby.templates import make_feature_checker

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader([str(get_theme_templates_dir())]),
        autoescape=True,
    )
    env.globals["feature"] = make_feature_checker(list(KNOWN_FEATURES))
    return env


def _ctx(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "site": {"title": "Site", "url": "https://example.com", "description": "Desc"},
        "page": {
            "title": "Home",
            "content": "",
            "url": "/",
            "description": "",
            "previous": None,
            "next": None,
            "toc": [],
            "custom_metadata": {"posts": [], "intro_content": "", "paginator": None},
        },
        "nav": [],
        "pages": [],
        "build": {"date": "2026-05-23", "bartleby_version": "0.1.0"},
        "config": {"theme": {"color_mode": {"toggle": True}}},
        "extra_css": [],
        "extra_js": [],
        "seo": None,
    }
    base.update(overrides)
    return base


def test_search_modal_markup_present() -> None:
    """The base template includes the search modal partial with Alpine x-data."""
    rendered = _env().get_template("base.html").render(**_ctx())
    assert "search-modal" in rendered
    assert "x-data" in rendered


def test_back_to_top_button_present() -> None:
    """The base template includes the back-to-top button with x-show wiring."""
    rendered = _env().get_template("base.html").render(**_ctx())
    assert "back-to-top" in rendered
    assert "scrollTo" in rendered


def test_search_partial_uses_input() -> None:
    """The search partial wires an input bound to an Alpine ``query`` model."""
    rendered = _env().get_template("partials/search.html").render(**_ctx())
    assert "<input" in rendered
    assert "x-model" in rendered


def test_toc_partial_renders_entries() -> None:
    """The TOC partial iterates ``page.toc`` entries when available."""
    page_ctx = _ctx()["page"]
    assert isinstance(page_ctx, dict)
    page_ctx["toc"] = [{"id": "intro", "name": "Intro"}]
    rendered = _env().get_template("partials/toc.html").render(**_ctx(page=page_ctx))
    assert "Intro" in rendered
    assert "#intro" in rendered


def test_css_has_admonition_styles() -> None:
    """The base stylesheet has rules for ``.admonition`` variants."""
    css_path = get_theme_templates_dir().parent / "static" / "css" / "main.css"
    text = css_path.read_text()
    assert ".admonition" in text
    assert ".admonition.note" in text
    assert ".admonition.warning" in text


def test_css_has_responsive_media_query() -> None:
    """The base stylesheet has at least one mobile-first media query."""
    css_path = get_theme_templates_dir().parent / "static" / "css" / "main.css"
    assert "@media" in css_path.read_text()


def test_css_has_grid_cards_layout() -> None:
    """The ``.grid.cards`` layout from mkdocs-material is supported."""
    css_path = get_theme_templates_dir().parent / "static" / "css" / "main.css"
    text = css_path.read_text()
    assert ".grid.cards" in text
    assert "grid-template-columns" in text


def test_css_has_md_button_compatibility() -> None:
    """The ``.md-button`` class is styled for mkdocs-material compatibility."""
    css_path = get_theme_templates_dir().parent / "static" / "css" / "main.css"
    assert ".md-button" in css_path.read_text()
