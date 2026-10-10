# ABOUTME: Test helper that resolves the bundled material theme by name.
# ABOUTME: Material-specific tests use it so they do not depend on the default theme.

from __future__ import annotations

from bartleby.theme_loader import ResolvedTheme, resolve_theme
from bartleby.themes import bundled_theme_root


def material_theme() -> ResolvedTheme:
    """Resolve the bundled ``material`` theme chain (material over base).

    Returns:
        The resolved material chain, independent of ``DEFAULT_THEME_NAME``.
    """
    return resolve_theme(name="material", project_dir=bundled_theme_root("material").parent)
