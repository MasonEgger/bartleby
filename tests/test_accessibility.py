# ABOUTME: Pins the accessibility of the HTML both bundled themes build from the scaffold site.
# ABOUTME: Landmarks, names, focus order, heading order, alt text, and the CSS cues behind them.

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import TYPE_CHECKING

import pytest

from bartleby.build import build
from bartleby.cli import main
from bartleby.themes import bundled_theme_root

if TYPE_CHECKING:
    from pathlib import Path

THEMES = ("scrivener", "material")

# The tour page shows every Markdown feature; heading order and alt text are checked there.
TOUR = "tour/index.html"

_FOCUSABLE = {"a", "button", "input", "select", "textarea", "summary"}


class _Page(HTMLParser):
    """The elements of a page in document order, each as (tag, attributes, text)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[tuple[str, dict[str, str | None], str]] = []
        self._open: list[int] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements.append((tag, dict(attrs), ""))
        self._open.append(len(self.elements) - 1)
        if tag in ("input", "img", "meta", "link", "br", "hr"):
            self._open.pop()

    def handle_endtag(self, tag: str) -> None:
        # Walk back to the matching open element so text nested in children still counts.
        for depth in range(len(self._open) - 1, -1, -1):
            if self.elements[self._open[depth]][0] == tag:
                del self._open[depth:]
                return

    def handle_data(self, data: str) -> None:
        for index in self._open:
            tag, attrs, text = self.elements[index]
            self.elements[index] = (tag, attrs, text + data)

    def all(self, tag: str) -> list[tuple[dict[str, str | None], str]]:
        return [(attrs, text) for name, attrs, text in self.elements if name == tag]


def _parse(path: Path) -> _Page:
    page = _Page()
    page.feed(path.read_text(encoding="utf-8"))
    page.close()
    return page


@pytest.fixture(scope="module", params=THEMES)
def built_site(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The scaffold site (with a blog) built once per theme, with every feature on."""
    theme = str(request.param)
    root = tmp_path_factory.mktemp(theme)
    main(["new", "site", str(root / "site"), "--blog", "--quiet"])
    config = root / "site" / "bartleby.yml"
    extra_features = "\n    - nav.tabs\n    - nav.section-index\n    - nav.toc-fold"
    text = config.read_text(encoding="utf-8").replace(
        "theme:\n  features:", f"theme:\n  name: {theme}\n  features:{extra_features}"
    )
    config.write_text(text, encoding="utf-8")
    build(config)
    return root / "site" / "site"


def _accessible_name(attrs: dict[str, str | None], text: str) -> str:
    return (attrs.get("aria-label") or attrs.get("aria-labelledby") or text).strip()


def test_every_page_has_a_lang_one_main_and_the_skip_link_first(built_site: Path) -> None:
    for path in built_site.rglob("*.html"):
        page = _parse(path)
        html_attrs = page.all("html")[0][0]
        assert html_attrs.get("lang") == "en", path
        mains = page.all("main")
        assert len(mains) == 1, path
        assert mains[0][0].get("id") == "main-content", path
        # The first focusable element in the body is the skip link, pointing at main.
        body_seen = False
        for tag, attrs, text in page.elements:
            if tag == "body":
                body_seen = True
            if body_seen and tag in _FOCUSABLE and attrs.get("tabindex") != "-1":
                assert tag == "a" and attrs.get("href") == "#main-content", path
                assert text.strip() == "Skip to content", path
                break


def test_site_language_reaches_the_html_element(tmp_path: Path) -> None:
    """``site.language`` in bartleby.yml becomes the html lang attribute."""
    main(["new", "site", str(tmp_path / "site"), "--quiet"])
    config = tmp_path / "site" / "bartleby.yml"
    text = config.read_text(encoding="utf-8")
    url_line = '  url: "https://example.com"\n'
    config.write_text(text.replace(url_line, url_line + '  language: "de-AT"\n'), encoding="utf-8")
    build(config)
    html = (tmp_path / "site" / "site" / "index.html").read_text(encoding="utf-8")
    assert '<html lang="de-AT"' in html


def test_every_button_has_an_accessible_name(built_site: Path) -> None:
    for path in built_site.rglob("*.html"):
        for attrs, text in _parse(path).all("button"):
            assert _accessible_name(attrs, text), f"{path}: unnamed button {attrs}"


def test_every_nav_landmark_is_labeled_and_labels_are_unique_per_page(built_site: Path) -> None:
    for path in built_site.rglob("*.html"):
        labels = [_accessible_name(attrs, "") for attrs, _text in _parse(path).all("nav")]
        assert all(labels), f"{path}: a nav has no label"
        assert len(labels) == len(set(labels)), f"{path}: repeated nav labels {labels}"


def test_tour_headings_never_skip_a_level(built_site: Path) -> None:
    page = _parse(built_site / TOUR)
    levels = [int(tag[1]) for tag, _attrs, _text in page.elements if re.fullmatch(r"h[1-6]", tag)]
    assert levels[0] == 1
    for previous, current in zip(levels, levels[1:], strict=False):
        assert current <= previous + 1, f"h{previous} is followed by h{current}"


def test_tour_images_have_alt_text(built_site: Path) -> None:
    images = _parse(built_site / TOUR).all("img")
    assert images, "the tour shows no image"
    for attrs, _text in images:
        assert attrs.get("alt") is not None, attrs


def test_color_mode_toggle_is_a_switch_with_state(built_site: Path) -> None:
    buttons = [attrs for attrs, _text in _parse(built_site / "index.html").all("button")]
    toggles = [attrs for attrs in buttons if "theme-toggle" in (attrs.get("class") or "")]
    assert len(toggles) == 1
    assert toggles[0].get("role") == "switch"
    assert toggles[0].get("x-bind:aria-checked"), "the switch does not expose aria-checked"


def test_search_dialog_is_a_modal_dialog(built_site: Path) -> None:
    dialogs = [
        attrs
        for tag, attrs, _text in _parse(built_site / "index.html").elements
        if attrs.get("role") == "dialog"
    ]
    assert len(dialogs) == 1
    assert dialogs[0].get("aria-modal") == "true"
    assert _accessible_name(dialogs[0], "")


def test_admonition_and_environment_cues_reach_the_tour_page(built_site: Path) -> None:
    html = (built_site / TOUR).read_text(encoding="utf-8")
    assert 'class="admonition-icon"' in html
    assert '<span class="visually-hidden">Warning: </span>Check Before You Deploy' in html
    assert '<span class="visually-hidden">Environment local. </span>' in html


def test_search_script_traps_focus_inside_the_dialog() -> None:
    script = (bundled_theme_root("base") / "static" / "js" / "search.js").read_text("utf-8")
    assert "trap: function (event)" in script
    assert 'event.key !== "Tab"' in script


@pytest.mark.parametrize("theme", THEMES)
def test_theme_css_carries_the_keyboard_and_motion_rules(theme: str) -> None:
    """Reduced motion is honored, focus is visible, tabs stay reachable, the cues are styled."""
    root = bundled_theme_root(theme)
    source = (root / "tailwind.css").read_text("utf-8")
    compiled = (root / "static" / "css" / "main.css").read_text("utf-8")
    assert "@media (prefers-reduced-motion: reduce)" in source
    assert re.search(r"^  :focus-visible \{\n    outline: 2px solid", source, re.MULTILINE)
    tab_inputs = re.search(r"\.tabbed-set > input \{([^}]*)\}", source)
    assert tab_inputs is not None
    assert "display: none" not in tab_inputs.group(1), "a display:none radio cannot take focus"
    cues = (".admonition-icon", ".skip-link:focus-visible", "pre.environment-local:before")
    for selector in cues:
        assert selector in compiled, f"{theme} main.css lacks {selector}"


def test_material_prose_links_are_underlined() -> None:
    """Material's link green is under 3:1 against its text, so the underline is always on."""
    compiled = (bundled_theme_root("material") / "static" / "css" / "main.css").read_text("utf-8")
    rule = re.search(r"\.prose :where\(a\):not\([^{]*\{([^}]*)\}", compiled)
    assert rule is not None, "the typography plugin emitted no .prose a rule"
    assert "text-decoration:underline" in rule.group(1)
    assert "text-decoration-thickness:1px" in rule.group(1)
