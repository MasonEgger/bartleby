# ABOUTME: Tests for the full Material theme styling and interactive components.
# Covers admonition styling, code blocks, tabs, search modal, TOC sidebar, back-to-top.

from __future__ import annotations

import re

import jinja2

from bartleby.theme import get_theme_templates_dir


def _render_markdown(source: str) -> str:
    """Render a markdown snippet through the real pipeline and return the HTML."""
    from pathlib import Path

    from bartleby.config import (
        AIConfig,
        BartlebyConfig,
        DevServerConfig,
        SiteConfig,
        ThemeConfig,
    )
    from bartleby.markdown_pipeline import create_markdown_renderer, render_markdown

    config = BartlebyConfig(
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
    return render_markdown(source, create_markdown_renderer(config)).html


def _stylesheet_defines(selector: str) -> bool:
    """Return whether the shipped stylesheet has a rule block for ``selector``.

    Matches ``selector`` followed by optional combinators/pseudo-classes and an
    opening brace, so a bare substring inside an unrelated rule does not count as
    a definition.
    """
    css_path = get_theme_templates_dir().parent / "static" / "css" / "main.css"
    text = css_path.read_text()
    pattern = re.escape(selector) + r"[^{}]*\{"
    return re.search(pattern, text) is not None


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


def test_rendered_admonition_html_carries_styled_classes() -> None:
    """A rendered admonition emits the exact classes the stylesheet styles.

    Inspect the real rendered HTML (not just the CSS source): the markdown
    pipeline must emit ``class="admonition note"`` / ``warning`` so the
    stylesheet's ``.admonition.note`` / ``.admonition.warning`` rules match
    something real.
    """
    note_html = _render_markdown('!!! note "Heads up"\n    Body.\n')
    warning_html = _render_markdown('!!! warning "Careful"\n    Body.\n')
    assert 'class="admonition note"' in note_html
    assert 'class="admonition warning"' in warning_html
    # The stylesheet defines rules for the classes the HTML actually produces.
    assert _stylesheet_defines(".admonition")
    assert _stylesheet_defines(".admonition.note")
    assert _stylesheet_defines(".admonition.warning")


def test_stylesheet_has_responsive_media_query() -> None:
    """The base stylesheet has at least one media query for responsive layout."""
    css_path = get_theme_templates_dir().parent / "static" / "css" / "main.css"
    assert "@media" in css_path.read_text()


def test_rendered_grid_cards_html_uses_styled_class() -> None:
    """A mkdocs-material grid-cards block renders the ``.grid.cards`` markup.

    Render the authoring syntax through the pipeline and inspect the HTML so the
    stylesheet's grid rule is verified against output that can actually exist.
    """
    source = '<div class="grid cards" markdown>\n\n- First card\n- Second card\n\n</div>\n'
    html = _render_markdown(source)
    assert 'class="grid cards"' in html
    assert _stylesheet_defines(".grid.cards")
    css_text = (get_theme_templates_dir().parent / "static" / "css" / "main.css").read_text()
    assert "grid-template-columns" in css_text


def test_rendered_md_button_html_uses_styled_class() -> None:
    """An attr-list ``.md-button`` link renders the styled class for compatibility."""
    html = _render_markdown("[Get started](/start/){ .md-button }\n")
    assert 'class="md-button"' in html
    assert _stylesheet_defines(".md-button")
