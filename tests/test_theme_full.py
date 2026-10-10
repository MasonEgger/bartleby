# ABOUTME: Tests for the full Material theme styling and interactive components.
# Covers admonition styling, code blocks, tabs, search modal, TOC sidebar, back-to-top.

from __future__ import annotations

import re

import jinja2

from bartleby.themes import bundled_theme_root
from tests.theme_helpers import material_theme


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
    css_path = bundled_theme_root("material") / "static" / "css" / "main.css"
    text = css_path.read_text()
    pattern = re.escape(selector) + r"[^{}]*\{"
    return re.search(pattern, text) is not None


def _admonition_variant_defined(kind: str) -> bool:
    """Return whether the shipped stylesheet styles ``.admonition`` of this ``kind``.

    The compiled CSS groups the selectors (``:is(.admonition,.prose details).note``),
    so a literal ``.admonition.note`` never appears.
    """
    css_path = bundled_theme_root("material") / "static" / "css" / "main.css"
    text = css_path.read_text()
    pattern = rf"(?::is\(\.admonition[^)]*\)|\.admonition)\.{kind}[^{{}}]*\{{"
    return re.search(pattern, text) is not None


def _env() -> jinja2.Environment:
    from bartleby.templates import make_feature_checker
    from bartleby.theme_loader import THEME_FEATURES

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader([str(path) for path in material_theme().templates_dirs()]),
        autoescape=True,
    )
    env.globals["feature"] = make_feature_checker(list(THEME_FEATURES))
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
    assert _admonition_variant_defined("note")
    assert _admonition_variant_defined("warning")


def test_stylesheet_has_responsive_media_query() -> None:
    """The base stylesheet has at least one media query for responsive layout."""
    css_path = bundled_theme_root("material") / "static" / "css" / "main.css"
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
    css_text = (bundled_theme_root("material") / "static" / "css" / "main.css").read_text()
    assert "grid-template-columns" in css_text


def test_rendered_md_button_html_uses_styled_class() -> None:
    """An attr-list ``.md-button`` link renders the styled class for compatibility."""
    html = _render_markdown("[Get started](/start/){ .md-button }\n")
    assert 'class="md-button"' in html
    assert _stylesheet_defines(".md-button")


def _color_mode_ctx(color_mode: dict[str, object]) -> dict[str, object]:
    return _ctx(config={"theme": {"color_mode": color_mode}})


def test_configured_dark_default_sets_static_data_theme_without_toggle() -> None:
    """With the toggle off, color_mode.default still picks the static data-theme."""
    rendered = _env().get_template("base.html").render(**_color_mode_ctx({"default": "dark"}))
    assert '<html lang="en" data-theme="dark">' in rendered
    assert "bartleby-color-mode" not in rendered


def test_configured_dark_default_reaches_pre_paint_script_with_toggle() -> None:
    """With the toggle on, the script falls back to the configured default before the OS."""
    rendered = (
        _env()
        .get_template("base.html")
        .render(**_color_mode_ctx({"default": "dark", "toggle": True}))
    )
    assert '<html lang="en" data-theme="dark">' in rendered
    assert 'var configured = "dark";' in rendered
    assert rendered.index("mode = configured;") < rendered.index("prefers-color-scheme")


def test_missing_or_unknown_default_keeps_light_and_script_falls_through() -> None:
    """No default, or an unrecognised one, leaves data-theme light and configured null."""
    template = _env().get_template("base.html")
    for color_mode in ({"toggle": True}, {"default": "sepia", "toggle": True}):
        rendered = template.render(**_color_mode_ctx(color_mode))
        assert '<html lang="en" data-theme="light">' in rendered
        assert "var configured = null;" in rendered


def _base_page(features: list[str]) -> str:
    from bartleby.templates import make_feature_checker

    env = _env()
    env.globals["feature"] = make_feature_checker(features)
    return env.get_template("base.html").render(**_ctx())


def test_search_highlight_gated_by_feature() -> None:
    """The ``search.highlight`` flag rides on the script tag as a JSON data attribute."""
    on = _base_page(["search", "search.highlight"])
    off = _base_page(["search"])
    assert '<script defer src="/js/search.js" data-highlight="true">' in on
    assert '<script defer src="/js/search.js" data-highlight="false">' in off
    assert "/js/search.js" not in _base_page([])


def test_search_engine_reads_highlight_flag_from_data_attribute() -> None:
    """The engine takes the flag from its script tag, never from templated source."""
    engine = _search_engine()
    assert "script.dataset.highlight" in engine
    assert "{{" not in engine


def test_search_highlight_never_injects_html() -> None:
    """Marks are built from DOM text nodes; neither engine nor modal assigns innerHTML."""
    rendered = _base_page(["search", "search.highlight"])
    for source in (_search_engine(), rendered):
        assert "innerHTML" not in source
        assert "x-html" not in source


def test_search_engine_uses_straight_quotes() -> None:
    """The no-results message keeps straight quotes, per the project's quote rule."""
    assert all(ord(char) < 128 for char in _search_engine())


def _search_engine() -> str:
    return (bundled_theme_root("base") / "static" / "js" / "search.js").read_text()
