# ABOUTME: Pins ACKNOWLEDGMENTS.md so no vendored script, icon pack, or inline SVG goes uncredited.
# Each vendored *.min.js, icon pack, and template that inlines an SVG path needs an entry.

from __future__ import annotations

import re
from pathlib import Path

from bartleby.themes import bundled_theme_root

ROOT = Path(__file__).resolve().parent.parent
ACK = ROOT / "ACKNOWLEDGMENTS.md"

_LIBRARY_FOR_FILE = {
    "alpine.min.js": ("Alpine.js", "MIT"),
    "htmx.min.js": ("htmx", "Zero-Clause BSD"),
    "lunr.min.js": ("lunr.js", "MIT"),
}

_PACK_ENTRIES = {
    "material": ("Material Design Icons", "Apache"),
    "fontawesome-brands": ("Font Awesome", "CC BY 4.0"),
    "octicons": ("Octicons", "MIT"),
    "simple": ("Simple Icons", "CC0"),
}

# Every project whose code or artwork ships in the wheel; dropping any entry fails.
_REQUIRED_ENTRIES = (
    "Alpine.js",
    "htmx",
    "lunr.js",
    "Tailwind CSS",
    "modern-normalize",
    "Octicons",
    "Lucide",
    "Material Design Icons",
    "Font Awesome",
)

# Templates whose inline <path> is Bartleby's own drawing, so no entry credits them.
_ORIGINAL_INLINE_SVGS = {
    # A two-segment line arrow on a 16-unit grid, drawn for scrivener; it is no icon set's glyph.
    "scrivener/templates/partials/back_to_top.html",
}

_INLINE_PATH_RE = re.compile(r"<svg\b[^>]*>.*?<path d=", re.DOTALL)


def _entries() -> list[str]:
    """Each top-level bullet in the acknowledgments file, joined into one string."""
    text = ACK.read_text(encoding="utf-8")
    return re.split(r"\n(?=- )", text)


def test_every_vendored_script_is_credited_with_its_license() -> None:
    entries = _entries()
    vendored = sorted(
        script_path.name for script_path in bundled_theme_root("base").glob("**/*.min.js")
    )
    assert vendored, "no vendored scripts found"
    for name in vendored:
        assert name in _LIBRARY_FOR_FILE, f"{name} is vendored but this test does not know it"
        library, license_name = _LIBRARY_FOR_FILE[name]
        matching = [
            entry
            for entry in entries
            if entry.lstrip("- ").startswith(f"**{library}") and name in entry
        ]
        assert matching, f"{name} has no entry in ACKNOWLEDGMENTS.md"
        assert license_name in matching[0], f"{name} entry does not name {license_name}"


def test_every_bundled_icon_pack_is_credited_with_its_license() -> None:
    entries = _entries()
    icons = bundled_theme_root("base") / "icons"
    for pack_dir in sorted(candidate for candidate in icons.iterdir() if candidate.is_dir()):
        assert pack_dir.name in _PACK_ENTRIES, f"icon pack {pack_dir.name} is not credited"
        library, license_name = _PACK_ENTRIES[pack_dir.name]
        matching = [
            entry
            for entry in entries
            if library in entry.split("\n")[0] and pack_dir.name in entry
        ]
        assert matching, f"icon pack {pack_dir.name} has no entry"
        assert license_name in matching[0].split("\n")[1], (
            f"{library} license line is not {license_name}"
        )


def test_every_required_project_has_an_entry() -> None:
    """Each project the wheel ships code or artwork from is named in a bullet entry.

    modern-normalize is credited inside the Tailwind CSS entry (its preflight reset
    derives from it), so the check is a mention within an entry, not a bullet of its own.
    """
    entries = _entries()[1:]
    for library in _REQUIRED_ENTRIES:
        assert any(library in entry for entry in entries), (
            f"{library} has no entry in ACKNOWLEDGMENTS.md"
        )


def test_every_template_with_an_inline_path_is_credited_or_original() -> None:
    """A template that inlines an <svg> with a <path d=...> is credited, or listed as original."""
    themes_dir = bundled_theme_root("base").parent
    text = ACK.read_text(encoding="utf-8")
    inlined = sorted(
        template.relative_to(themes_dir).as_posix()
        for template in themes_dir.glob("*/templates/**/*.html")
        if _INLINE_PATH_RE.search(template.read_text(encoding="utf-8"))
    )
    assert inlined, "no template inlines an SVG path, so the scan found nothing to check"
    for relative in inlined:
        if relative in _ORIGINAL_INLINE_SVGS:
            continue
        assert f"themes/{relative}" in text, (
            f"{relative} inlines an SVG path and ACKNOWLEDGMENTS.md does not name it"
        )


def test_acknowledgments_ships_in_the_wheel() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "ACKNOWLEDGMENTS.md" in pyproject
