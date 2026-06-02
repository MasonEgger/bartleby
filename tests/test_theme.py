# ABOUTME: Tests for the built-in Material theme templates.
# Verifies HTML5 structure, asset references, and partial composition.

from __future__ import annotations

import jinja2

from bartleby.theme import get_theme_templates_dir


def _env() -> jinja2.Environment:
    loader = jinja2.FileSystemLoader([str(get_theme_templates_dir())])
    return jinja2.Environment(loader=loader, autoescape=True)


def _base_context(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "site": {"title": "Site", "url": "https://example.com", "description": "Desc"},
        "page": {
            "title": "Home",
            "content": "<p>body</p>",
            "url": "/",
            "description": "Page desc",
            "previous": None,
            "next": None,
            "custom_metadata": {"posts": [], "intro_content": "", "paginator": None},
        },
        "nav": [{"title": "Home", "url": "/"}, {"title": "Blog", "url": "/blog/"}],
        "pages": [],
        "build": {"date": "2026-05-23", "bartleby_version": "0.1.0"},
        "config": {"theme": {"color_mode": {"toggle": True}}},
        "extra_css": [],
        "extra_js": [],
        "seo": None,
    }
    base.update(overrides)
    return base


def test_base_template_valid_html5() -> None:
    """The base template emits a complete HTML5 document."""
    env = _env()
    rendered = env.get_template("base.html").render(**_base_context())
    assert rendered.startswith("<!DOCTYPE html>")
    assert "<html" in rendered
    assert "<head>" in rendered
    assert "<body>" in rendered


def test_base_template_has_meta_viewport() -> None:
    """The responsive viewport meta tag is present."""
    rendered = _env().get_template("base.html").render(**_base_context())
    assert 'name="viewport"' in rendered


def test_base_template_includes_css() -> None:
    """The base CSS file is referenced."""
    rendered = _env().get_template("base.html").render(**_base_context())
    assert "/css/main.css" in rendered


def test_base_template_includes_alpine() -> None:
    """Alpine.js (and the other vendor scripts) are referenced."""
    rendered = _env().get_template("base.html").render(**_base_context())
    assert "/js/alpine.min.js" in rendered
    assert "/js/htmx.min.js" in rendered
    assert "/js/lunr.min.js" in rendered


def test_header_has_site_title() -> None:
    """The header partial renders the site title."""
    rendered = _env().get_template("base.html").render(**_base_context())
    assert "Site" in rendered


def test_dark_mode_toggle() -> None:
    """The theme toggle button is present when color_mode.toggle is true."""
    rendered = _env().get_template("base.html").render(**_base_context())
    assert "theme-toggle" in rendered
    assert "x-data" in rendered


def test_404_template_renders() -> None:
    """The 404 template renders without error."""
    page = {
        "title": "Not Found",
        "content": "",
        "url": "/404.html",
        "description": "",
        "previous": None,
        "next": None,
    }
    rendered = _env().get_template("404.html").render(**_base_context(page=page))
    assert "404" in rendered


def test_post_template_renders_metadata() -> None:
    """The default post template shows date and tags when present."""
    page = {
        "title": "My Post",
        "content": "<p>body</p>",
        "url": "/blog/posts/my-post/",
        "date": "2026-03-01",
        "authors": [{"name": "Mason"}],
        "readtime": 3,
        "taxonomies": {"tags": ["python"]},
        "description": "",
        "previous": None,
        "next": None,
    }
    rendered = _env().get_template("defaults/post.html").render(**_base_context(page=page))
    assert "My Post" in rendered
    assert "2026-03-01" in rendered
    assert "Mason" in rendered


def test_footer_shows_prev_next() -> None:
    """The footer renders previous/next links when set on the page."""
    page = {
        "title": "Current",
        "content": "<p>body</p>",
        "url": "/current/",
        "description": "",
        "previous": {"title": "Earlier", "url": "/earlier/"},
        "next": {"title": "Later", "url": "/later/"},
    }
    rendered = _env().get_template("base.html").render(**_base_context(page=page))
    assert "Earlier" in rendered
    assert "Later" in rendered


def test_all_templates_render() -> None:
    """Every theme template renders without raising."""
    env = _env()
    for template_name in (
        "base.html",
        "page.html",
        "defaults/post.html",
        "defaults/list.html",
        "taxonomy.html",
        "taxonomy_index.html",
        "404.html",
    ):
        env.get_template(template_name).render(**_base_context(paginator=None))
