# ABOUTME: Pins the WCAG contrast ratio of each text-on-color pair in the bundled palettes.
# ABOUTME: Reads the hexes and mixes from each tailwind.css, so a palette change updates the pins.

from __future__ import annotations

import re
from pathlib import Path

import pytest

THEMES = Path(__file__).parent.parent / "src" / "bartleby" / "themes"
MATERIAL_CSS = THEMES / "material" / "tailwind.css"
SCRIVENER_CSS = THEMES / "scrivener" / "tailwind.css"

# WCAG 2.1 AA for normal-size text, and the floor for focus rings and other non-text cues.
AA_TEXT = 4.5
AA_NON_TEXT = 3.0

WHITE = "#ffffff"
BLACK = "#000000"


def _channel(value: int) -> float:
    """Linearize one sRGB channel (WCAG 2.1 relative luminance, step 1)."""
    c = value / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _rgb(hex_color: str) -> tuple[int, int, int]:
    digits = hex_color.lstrip("#")
    return int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)


def _luminance(hex_color: str) -> float:
    r, g, b = _rgb(hex_color)
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    """The WCAG contrast ratio between two hex colors, from 1.0 to 21.0."""
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def mix(a: str, b: str, share_of_a: float) -> str:
    """``color-mix(in srgb, a <share>%, b)``: a per-channel blend in sRGB space."""
    pairs = zip(_rgb(a), _rgb(b), strict=True)
    blended = (round(ca * share_of_a + cb * (1 - share_of_a)) for ca, cb in pairs)
    return "#" + "".join(f"{v:02x}" for v in blended)


def _block(css_path: Path, *, dark: bool) -> str:
    """The light or dark variable block of a theme's tailwind.css."""
    css = css_path.read_text(encoding="utf-8")
    _root, _, rest = css.partition(":root {")
    light, _, dark_block = rest.partition('[data-theme="dark"] {')
    return dark_block if dark else light


def _token(name: str, *, dark: bool = False, css_path: Path = MATERIAL_CSS) -> str:
    """The hex fallback of a theme variable in the light or dark block of its tailwind.css."""
    match = re.search(rf"--{name}:[^;]*?(#[0-9a-f]{{6}})", _block(css_path, dark=dark))
    mode = "dark" if dark else "light"
    assert match is not None, f"--{name} has no hex fallback in the {mode} block"
    return match.group(1)


def _mix_share(name: str, *, dark: bool = False, css_path: Path = MATERIAL_CSS) -> float:
    """The share (0 to 1) a ``color-mix`` variable gives its first color."""
    match = re.search(
        rf"--{name}: color-mix\(in srgb, var\([^)]*\) (\d+)%", _block(css_path, dark=dark)
    )
    assert match is not None, (
        f"--{name} is not a color-mix in the {'dark' if dark else 'light'} block"
    )
    return int(match.group(1)) / 100


def _palette() -> dict[str, str]:
    primary = _token("bm-primary")
    return {
        "primary": primary,
        "primary_dark": mix(primary, BLACK, 0.8),
        "accent": _token("bm-accent"),
        "bg": _token("bm-bg"),
        "surface": mix(_token("bm-bg"), BLACK, 0.96),
        "dark_bg": _token("bm-bg", dark=True),
        "dark_surface": mix(_token("bm-bg", dark=True), WHITE, 0.94),
        "dark_link": _token("bm-link", dark=True),
        "dark_accent": _token("bm-accent", dark=True),
    }


def test_material_primary_is_forest_green() -> None:
    """The primary keeps forestgreen's hue (equal red and blue, green well above both)."""
    r, g, b = _rgb(_token("bm-primary"))
    assert r == b
    assert g > 3 * r


# Each entry: (foreground token, background token, the ratio the palette produces).
# The ratio is the computed value rounded to two places, so a palette edit that
# moves a pair shows up here and the AA floor stays visible beside it.
PAIRS = [
    ("white_on_primary", "primary", 5.04),
    ("white_on_primary_dark", "primary_dark", 7.10),
    ("link_on_bg", "bg", 7.10),
    ("link_on_surface", "surface", 6.52),
    ("primary_on_bg", "bg", 5.04),
    ("accent_on_bg", "bg", 5.13),
    ("accent_on_surface", "surface", 4.70),
    ("dark_link_on_dark_bg", "dark_bg", 7.17),
    ("dark_link_on_dark_surface", "dark_surface", 6.03),
    ("dark_accent_on_dark_bg", "dark_bg", 9.18),
    ("dark_accent_on_dark_surface", "dark_surface", 7.72),
]

_FOREGROUNDS = {
    "white_on_primary": WHITE,
    "white_on_primary_dark": WHITE,
    "link_on_bg": "primary_dark",
    "link_on_surface": "primary_dark",
    "primary_on_bg": "primary",
    "accent_on_bg": "accent",
    "accent_on_surface": "accent",
    "dark_link_on_dark_bg": "dark_link",
    "dark_link_on_dark_surface": "dark_link",
    "dark_accent_on_dark_bg": "dark_accent",
    "dark_accent_on_dark_surface": "dark_accent",
}


@pytest.mark.parametrize(("pair", "background", "expected"), PAIRS, ids=[p[0] for p in PAIRS])
def test_material_text_pairs_meet_aa(pair: str, background: str, expected: float) -> None:
    """Every text-on-color pair in the material palette clears 4.5:1 at the pinned ratio."""
    palette = _palette()
    foreground = _FOREGROUNDS[pair]
    fg = palette.get(foreground, foreground)
    ratio = contrast(fg, palette[background])
    assert ratio >= AA_TEXT, f"{pair} is {ratio:.2f}:1"
    assert round(ratio, 2) == pytest.approx(expected, abs=0.005), f"{pair} is {ratio:.2f}:1"


def test_light_link_is_the_dark_primary() -> None:
    """Links in light mode use ``--bm-primary-dark`` so they sit darker than the header bar."""
    css = MATERIAL_CSS.read_text(encoding="utf-8")
    assert "--bm-link: var(--bm-primary-dark);" in css


def test_no_indigo_remains() -> None:
    """The old indigo hexes are gone from the theme source and its config note."""
    theme_dir = MATERIAL_CSS.parent
    for path in (MATERIAL_CSS, theme_dir / "tailwind.config.js"):
        text = path.read_text(encoding="utf-8").lower()
        assert "3f51b5" not in text, path
        assert "536dfe" not in text, path
        assert "indigo" not in text, path


# Muted and faint text: the mixes of text into page that both themes use for secondary
# copy (labels, counters, the environment tag, line-number prefixes) and for bullets.
# Each is checked on the page, the surface, the code background, and every environment tint.

_MATERIAL_ENVIRONMENTS = ("local", "second", "third", "fourth", "fifth")


def _material_mode(*, dark: bool) -> dict[str, str]:
    text = _token("bm-text", dark=dark)
    bg = _token("bm-bg", dark=dark)
    surface = mix(bg, WHITE if dark else BLACK, 0.94 if dark else 0.96)
    code_bg = mix(text, bg, 0.07 if dark else 0.05)
    backgrounds = {"bg": bg, "surface": surface, "code_bg": code_bg}
    for name in _MATERIAL_ENVIRONMENTS:
        backgrounds[f"env_{name}"] = mix(_token(f"bm-env-{name}", dark=dark), bg, 0.12)
    return {
        "muted": mix(text, bg, _mix_share("bm-text-muted")),
        "faint": mix(text, bg, _mix_share("bm-text-faint")),
        **backgrounds,
    }


@pytest.mark.parametrize("dark", [False, True], ids=["light", "dark"])
def test_material_muted_text_meets_aa_on_every_surface(dark: bool) -> None:
    mode = _material_mode(dark=dark)
    for background in (
        "bg",
        "surface",
        "code_bg",
        *(f"env_{name}" for name in _MATERIAL_ENVIRONMENTS),
    ):
        ratio = contrast(mode["muted"], mode[background])
        assert ratio >= AA_TEXT, f"muted on {background} is {ratio:.2f}:1"


@pytest.mark.parametrize("dark", [False, True], ids=["light", "dark"])
def test_material_faint_meets_the_non_text_floor(dark: bool) -> None:
    """Faint is for bullets and rules, never text, so it holds the 3:1 non-text floor."""
    mode = _material_mode(dark=dark)
    ratio = contrast(mode["faint"], mode["bg"])
    assert ratio >= AA_NON_TEXT, f"faint on bg is {ratio:.2f}:1"


def test_material_muted_and_faint_pins() -> None:
    """The two mixes, so a change to either shows up here beside its reason."""
    assert _mix_share("bm-text-muted") == 0.68
    assert _mix_share("bm-text-faint") == 0.50
    light = _material_mode(dark=False)
    assert round(contrast(light["muted"], light["bg"]), 2) == pytest.approx(5.57, abs=0.005)
    assert round(contrast(light["muted"], light["code_bg"]), 2) == pytest.approx(5.07, abs=0.005)


def test_material_focus_ring_meets_the_non_text_floor() -> None:
    """The accent draws the focus ring on the page; white draws it on the header bar."""
    assert contrast(_token("bm-accent"), _token("bm-bg")) >= AA_NON_TEXT
    assert contrast(_token("bm-accent", dark=True), _token("bm-bg", dark=True)) >= AA_NON_TEXT
    assert contrast(WHITE, _token("bm-primary")) >= AA_NON_TEXT


def test_material_header_links_are_the_on_primary_color() -> None:
    """Header nav links are not faded: white at 80% on the green was 3.83:1."""
    css = MATERIAL_CSS.read_text(encoding="utf-8")
    nav = re.search(r"\.site-nav a,\n  \.nav-tabs a \{([^}]*)\}", css)
    assert nav is not None
    assert "opacity" not in nav.group(1)


_SCRIVENER_ENVIRONMENTS = ("local", "second", "third", "fourth", "fifth")


def _scrivener_mode(*, dark: bool) -> dict[str, str]:
    ink = _token("sc-ink", dark=dark, css_path=SCRIVENER_CSS)
    paper = _token("sc-paper", dark=dark, css_path=SCRIVENER_CSS)
    backgrounds = {
        "paper": paper,
        "surface": mix(ink, paper, _mix_share("sc-surface", dark=dark, css_path=SCRIVENER_CSS)),
        "wash": mix(ink, paper, _mix_share("sc-wash", dark=dark, css_path=SCRIVENER_CSS)),
    }
    for name in _SCRIVENER_ENVIRONMENTS:
        backgrounds[f"env_{name}"] = mix(
            _token(f"sc-env-{name}", dark=dark, css_path=SCRIVENER_CSS), paper, 0.10
        )
    return {
        "muted": mix(ink, paper, _mix_share("sc-muted", dark=dark, css_path=SCRIVENER_CSS)),
        **backgrounds,
    }


@pytest.mark.parametrize("dark", [False, True], ids=["light", "dark"])
def test_scrivener_muted_text_meets_aa_on_every_surface(dark: bool) -> None:
    mode = _scrivener_mode(dark=dark)
    for background in (
        "paper",
        "surface",
        "wash",
        *(f"env_{name}" for name in _SCRIVENER_ENVIRONMENTS),
    ):
        ratio = contrast(mode["muted"], mode[background])
        assert ratio >= AA_TEXT, f"muted on {background} is {ratio:.2f}:1"


def test_scrivener_muted_pins() -> None:
    assert _mix_share("sc-muted", css_path=SCRIVENER_CSS) == 0.72
    assert _mix_share("sc-muted", dark=True, css_path=SCRIVENER_CSS) == 0.68
    light = _scrivener_mode(dark=False)
    dark = _scrivener_mode(dark=True)
    assert round(contrast(light["muted"], light["paper"]), 2) == pytest.approx(6.14, abs=0.005)
    assert round(contrast(dark["muted"], dark["paper"]), 2) == pytest.approx(7.11, abs=0.005)


def test_scrivener_focus_ring_meets_the_non_text_floor() -> None:
    """The margin accent draws the focus ring; in dark mode it is mixed 40% toward #c2d6ff."""
    light_ring = _token("sc-margin", css_path=SCRIVENER_CSS)
    dark_ring = mix(_token("sc-margin", dark=True, css_path=SCRIVENER_CSS), "#c2d6ff", 0.4)
    assert contrast(light_ring, _token("sc-paper", css_path=SCRIVENER_CSS)) >= AA_NON_TEXT
    assert (
        contrast(dark_ring, _token("sc-paper", dark=True, css_path=SCRIVENER_CSS)) >= AA_NON_TEXT
    )
