# ABOUTME: Built-in Material theme package for Bartleby.
# Exposes the on-disk path of the bundled template directory.

from pathlib import Path


def get_theme_templates_dir() -> Path:
    """Absolute path to the directory containing the built-in theme templates."""
    return Path(__file__).parent / "templates"
