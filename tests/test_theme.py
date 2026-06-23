# ABOUTME: Tests for the built-in Material theme templates.
# Verifies HTML5 structure, asset references, and partial composition.

from __future__ import annotations

from pathlib import Path

import jinja2
import pytest

from bartleby.assets import copy_static_files
from bartleby.theme import get_theme_static_dir, get_theme_templates_dir

# Pinned vendored bundle versions. Keep these in sync with THIRD-PARTY-NOTICES.
VENDORED_BUNDLES = {
    "alpine.min.js": {"min_size": 20_000, "signature": "Alpine"},
    "htmx.min.js": {"min_size": 20_000, "signature": "htmx"},
    "lunr.min.js": {"min_size": 20_000, "signature": "lunr"},
}


def _env() -> jinja2.Environment:
    loader = jinja2.FileSystemLoader([str(get_theme_templates_dir())])
    return jinja2.Environment(loader=loader, autoescape=True)


def _notices_path() -> Path:
    """Absolute path to the THIRD-PARTY-NOTICES file shipped in the package."""
    import bartleby

    return Path(bartleby.__file__).parent / "THIRD-PARTY-NOTICES"


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


@pytest.mark.parametrize("filename", sorted(VENDORED_BUNDLES))
def test_vendored_bundle_is_real(filename: str) -> None:
    """Each vendored JS bundle is the real library, not a stub.

    Real minified bundles are tens of kilobytes and contain a known signature
    string from the library; the old placeholder stubs were ~200 bytes.
    """
    expected = VENDORED_BUNDLES[filename]
    bundle = get_theme_static_dir() / "js" / filename
    assert bundle.exists(), f"missing vendored bundle: {filename}"
    text = bundle.read_text(encoding="utf-8")
    assert len(text.encode("utf-8")) >= expected["min_size"], (
        f"{filename} is smaller than a real bundle — still a stub?"
    )
    assert expected["signature"] in text, (
        f"{filename} lacks the {expected['signature']!r} signature string"
    )


def test_vendored_bundles_have_no_stub_comment() -> None:
    """The old placeholder stub markers must be gone from every bundle.

    Match the exact stub strings, not the bare word "placeholder": real
    minified bundles legitimately use tokens like ``__placeholder`` internally.
    """
    stub_markers = ("ABOUTME: Vendored", "console.debug && console.debug")
    for filename in VENDORED_BUNDLES:
        text = (get_theme_static_dir() / "js" / filename).read_text(encoding="utf-8")
        for marker in stub_markers:
            assert marker not in text, f"{filename} still contains a stub comment ({marker!r})"


def test_third_party_notices_lists_vendored_libraries() -> None:
    """THIRD-PARTY-NOTICES records each JS library with its license and pinned version."""
    notices = _notices_path()
    assert notices.exists(), "THIRD-PARTY-NOTICES is missing from the package"
    text = notices.read_text(encoding="utf-8")
    for library, license_name in (
        ("Alpine.js", "MIT"),
        ("HTMX", "BSD 2-Clause"),
        ("lunr.js", "MIT"),
    ):
        assert library in text, f"{library} not listed in THIRD-PARTY-NOTICES"
        assert license_name in text, f"{license_name} license not recorded for {library}"
    # Pinned versions must be present (semver-ish strings).
    for version in ("3.14.1", "2.0.4", "2.3.9"):
        assert version in text, f"pinned version {version} not recorded in THIRD-PARTY-NOTICES"


def test_build_copies_real_bundles_into_site_js(tmp_path: Path) -> None:
    """copy_static_files places the real bundles under site/js/."""
    output_dir = tmp_path / "site"
    copy_static_files(get_theme_static_dir(), output_dir)
    for filename in VENDORED_BUNDLES:
        copied = output_dir / "js" / filename
        assert copied.exists(), f"{filename} was not copied into site/js/"
        assert len(copied.read_bytes()) >= VENDORED_BUNDLES[filename]["min_size"]


def test_base_html_wires_search_and_dark_mode_to_bundles() -> None:
    """Rendered HTML references the real bundles and wires the Alpine markup."""
    rendered = _env().get_template("base.html").render(**_base_context())
    # Bundle references.
    assert "/js/alpine.min.js" in rendered
    assert "/js/htmx.min.js" in rendered
    assert "/js/lunr.min.js" in rendered
    # Search container wired to Alpine + the lunr-backed search hook.
    assert "search-modal" in rendered
    assert 'x-on:click="open = true"' in rendered
    assert "__bartlebySearch" in rendered
    # Dark-mode toggle wired to Alpine.
    assert "theme-toggle" in rendered
    assert "document.documentElement.dataset.theme" in rendered
