# ABOUTME: Bundled theme data package (base, material, scrivener) shipped inside bartleby.
# Exposes the on-disk root of each bundled theme directory.

from __future__ import annotations

from pathlib import Path

BUNDLED_THEME_NAMES: tuple[str, ...] = ("base", "material", "scrivener")


def bundled_theme_root(name: str) -> Path:
    """Return the directory of the bundled theme ``name``.

    The directory is not checked for existence; callers decide how to report a
    bundled theme that has not been created yet.

    Args:
        name: A bundled theme name such as ``"base"``.

    Returns:
        Absolute path to ``src/bartleby/themes/<name>``.
    """
    return Path(__file__).parent / name
