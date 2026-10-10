# ABOUTME: Theme manifest parsing and extends-chain resolution for all theme sources.
# Produces a ResolvedTheme with layers ordered leaf-first for template, static, and icon lookup.

"""Theme manifests and the theme resolver.

A theme is a directory holding a ``theme.yml`` manifest plus optional
``templates/``, ``static/``, and ``icons/`` subdirectories.

Manifest schema (``theme.yml``):

* ``name`` (required, string): the theme's identifier.
* ``version`` (optional, string): the theme's version.
* ``description`` (optional, string): one-line summary.
* ``extends`` (optional, string): the name of a parent theme.
* ``features`` (optional, list of strings): native feature names the theme implements.

A theme root comes from one of three sources:

* ``name``: a bundled theme under ``bartleby/themes/`` (``base``, ``material``, ``scrivener``).
* ``path``: a directory in the project, relative to the project directory or absolute.
* ``package``: an entry point in the ``bartleby.themes`` group, whose loaded value is the
  theme directory as a ``Path`` or ``str``.

An ``extends`` value is looked up as a bundled theme name first, then as a sibling
directory of the extending theme, then as a ``bartleby.themes`` entry point.

The resolved chain is leaf-first: the requested theme comes first and each parent
follows, so a lookup that takes the first hit lets a child override its parent.
"""

from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from bartleby.themes import BUNDLED_THEME_NAMES, bundled_theme_root

THEME_ENTRY_POINT_GROUP = "bartleby.themes"
MANIFEST_FILENAME = "theme.yml"


class ThemeError(Exception):
    """Raised when a theme manifest is invalid or a theme cannot be resolved."""


@dataclass(slots=True)
class ThemeManifest:
    """The parsed contents of a ``theme.yml`` file.

    Attributes:
        name: The theme's identifier.
        version: Optional version string.
        description: Optional one-line summary.
        extends: Optional name of the parent theme.
        features: Native feature names the theme implements.
    """

    name: str
    version: str | None = None
    description: str | None = None
    extends: str | None = None
    features: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ThemeLayer:
    """One theme in a resolved chain.

    Attributes:
        name: The manifest name.
        root: The theme's directory.
        manifest: The parsed manifest.
    """

    name: str
    root: Path
    manifest: ThemeManifest


@dataclass(slots=True)
class ResolvedTheme:
    """A theme and its ancestors, ordered leaf-first.

    Attributes:
        chain: Layers with the requested theme first and the root ancestor last.
    """

    chain: list[ThemeLayer]

    def templates_dirs(self) -> list[Path]:
        """Existing ``templates/`` directories, leaf-first."""
        return self._existing_dirs("templates")

    def static_dirs(self) -> list[Path]:
        """Existing ``static/`` directories, leaf-first."""
        return self._existing_dirs("static")

    def icons_dirs(self) -> list[Path]:
        """Existing ``icons/`` directories, leaf-first."""
        return self._existing_dirs("icons")

    def _existing_dirs(self, subdirectory: str) -> list[Path]:
        candidates = (layer.root / subdirectory for layer in self.chain)
        return [candidate for candidate in candidates if candidate.is_dir()]


def load_manifest(root: Path) -> ThemeManifest:
    """Parse ``theme.yml`` in the theme directory ``root``.

    Args:
        root: The theme directory.

    Returns:
        The parsed manifest.

    Raises:
        ThemeError: If the file is missing, is not a mapping, lacks ``name``, or has a
            field of the wrong type.
    """
    manifest_path = root / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise ThemeError(f"{root}: missing {MANIFEST_FILENAME}")
    parsed: Any = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ThemeError(f"{root}: {MANIFEST_FILENAME} must be a YAML mapping")
    return ThemeManifest(
        name=_parse_name(parsed.get("name"), root),
        version=_parse_optional_str(parsed.get("version"), "version", root),
        description=_parse_optional_str(parsed.get("description"), "description", root),
        extends=_parse_optional_str(parsed.get("extends"), "extends", root),
        features=_parse_features(parsed.get("features"), root),
    )


def resolve_theme(
    *,
    project_dir: Path,
    name: str | None = None,
    path: str | None = None,
    package: str | None = None,
) -> ResolvedTheme:
    """Resolve a theme and its ``extends`` ancestors into a leaf-first chain.

    Exactly one of ``name``, ``path``, or ``package`` must be given.

    Args:
        project_dir: The project directory that relative ``path`` values resolve against.
        name: A bundled theme name.
        path: A theme directory, absolute or relative to ``project_dir``.
        package: A ``bartleby.themes`` entry point name.

    Returns:
        The resolved chain.

    Raises:
        ThemeError: If the source selection is ambiguous, a theme cannot be found,
            a manifest is invalid, or the ``extends`` chain is cyclic.
    """
    sources = [value for value in (name, path, package) if value is not None]
    if len(sources) > 1:
        raise ThemeError("specify exactly one of name, path, or package")

    if name is not None:
        root = _bundled_root(name)
    elif path is not None:
        root = _path_root(path, project_dir)
    elif package is not None:
        root = _package_root(package)
    else:
        raise ThemeError("specify exactly one of name, path, or package")

    chain: list[ThemeLayer] = []
    while True:
        manifest = load_manifest(root)
        if any(layer.name == manifest.name for layer in chain):
            names = [layer.name for layer in chain] + [manifest.name]
            raise ThemeError(f"cyclic theme extends: {' -> '.join(names)}")
        chain.append(ThemeLayer(name=manifest.name, root=root, manifest=manifest))
        if manifest.extends is None:
            return ResolvedTheme(chain=chain)
        root = _extends_root(manifest.extends, root)


def _parse_name(value: Any, root: Path) -> str:
    if not isinstance(value, str) or not value:
        raise ThemeError(f"{root}: {MANIFEST_FILENAME} is missing required key 'name'")
    return value


def _parse_optional_str(value: Any, key: str, root: Path) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ThemeError(f"{root}: '{key}' must be a string")
    return value


def _parse_features(value: Any, root: Path) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ThemeError(f"{root}: 'features' must be a list of strings")
    return list(value)


def _bundled_root(name: str) -> Path:
    if name not in BUNDLED_THEME_NAMES:
        known = ", ".join(BUNDLED_THEME_NAMES)
        raise ThemeError(f"unknown bundled theme {name!r} (bundled themes: {known})")
    root = bundled_theme_root(name)
    if not root.is_dir():
        raise ThemeError(f"bundled theme {name!r} not found at {root}")
    return root


def _path_root(path: str, project_dir: Path) -> Path:
    root = Path(path)
    if not root.is_absolute():
        root = project_dir / root
    if not root.is_dir():
        raise ThemeError(f"theme path does not exist: {root}")
    return root


def _package_root(package: str) -> Path:
    for entry_point in importlib.metadata.entry_points(group=THEME_ENTRY_POINT_GROUP):
        if entry_point.name != package:
            continue
        loaded: Any = entry_point.load()
        if not isinstance(loaded, str | Path):
            raise ThemeError(f"theme package {package!r} must load to a directory path")
        root = Path(loaded)
        if not root.is_dir():
            raise ThemeError(f"theme package {package!r} points at a missing directory: {root}")
        return root
    raise ThemeError(
        f"theme package {package!r} not found in entry-point group {THEME_ENTRY_POINT_GROUP!r}"
    )


def _extends_root(extends: str, child_root: Path) -> Path:
    if extends in BUNDLED_THEME_NAMES:
        return _bundled_root(extends)
    sibling = child_root.parent / extends
    if sibling.is_dir():
        return sibling
    return _package_root(extends)
