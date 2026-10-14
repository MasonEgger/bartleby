# ABOUTME: Pins the WCAG contrast ratio of each text-on-color pair in the material palette.
# ABOUTME: Reads the hexes from tailwind.css so a palette change has to update the pins.

from __future__ import annotations

import re
from pathlib import Path

import pytest

MATERIAL_CSS = (
    Path(__file__).parent.parent / "src" / "bartleby" / "themes" / "material" / "tailwind.css"
)

# WCAG 2.1 AA for normal-size text.
AA_TEXT = 4.5

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


def _token(name: str, *, dark: bool = False) -> str:
    """The hex fallback of a ``--bm-*`` variable in the light or dark block of tailwind.css."""
    css = MATERIAL_CSS.read_text(encoding="utf-8")
    root, _, rest = css.partition(":root {")
    light, _, dark_block = rest.partition('[data-theme="dark"] {')
    block = dark_block if dark else light
    match = re.search(rf"--{name}:[^;]*?(#[0-9a-f]{{6}})", block)
    mode = "dark" if dark else "light"
    assert match is not None, f"--{name} has no hex fallback in the {mode} block"
    return match.group(1)


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
