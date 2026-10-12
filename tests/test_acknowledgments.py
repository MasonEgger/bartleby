# ABOUTME: Pins ACKNOWLEDGMENTS.md so a vendored script or icon pack cannot land uncredited.
# Each vendored *.min.js and each bundled icon pack needs an entry that names its license.

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


def test_acknowledgments_ships_in_the_wheel() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "ACKNOWLEDGMENTS.md" in pyproject
