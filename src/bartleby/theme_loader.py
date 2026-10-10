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

Error-message contract: a :class:`ThemeError` renders as
``<theme directory or manifest>: <message> (fix: <hint>)`` (see
:func:`bartleby.errors.format_error`). It names the directory or ``theme.yml`` at fault,
says what a theme directory needs when the manifest is missing or invalid, lists the
bundled theme names for an unknown ``theme.name``, and points a missing ``theme.path``
at ``bartleby theme eject`` as the way to start a theme.
"""

from __future__ import annotations

import importlib.metadata
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from bartleby.errors import format_error
from bartleby.themes import BUNDLED_THEME_NAMES, bundled_theme_root

if TYPE_CHECKING:
    from bartleby.config import ThemeConfig

THEME_ENTRY_POINT_GROUP = "bartleby.themes"
MANIFEST_FILENAME = "theme.yml"
THEME_ASSET_DIRS: tuple[str, ...] = ("templates", "static", "icons")
TAILWIND_SOURCES: tuple[str, ...] = ("tailwind.css", "tailwind.config.js", "safelist.txt")

THEME_FEATURES: frozenset[str] = frozenset(
    {
        "search",
        "search.highlight",
        "nav.tabs",
        "nav.sidebar",
        "nav.section-index",
        "nav.back-to-top",
        "content.code.copy",
        "color-mode.toggle",
    }
)
"""The native feature vocabulary, the single source of truth for feature names.

Both ``theme.features`` in ``bartleby.yml`` and ``features`` in a theme manifest are
checked against this set, and the ``feature()`` template helper reports membership in
the enabled subset. Each name means:

* ``search``: the search box and the client-side search index.
* ``search.highlight``: highlight the search terms on the page a result opens.
* ``nav.tabs``: top-level sections render as tabs in the header.
* ``nav.sidebar``: the section tree renders as a sidebar.
* ``nav.section-index``: a section's index page is the section's own nav entry.
* ``nav.back-to-top``: a back-to-top button appears after scrolling.
* ``content.code.copy``: code blocks get a copy button.
* ``color-mode.toggle``: the header shows a light/dark toggle.

A feature enabled in config but missing from the active theme's manifest is a build
warning, not an error. Keep this set and :func:`_parse_features` together.
"""

DEFAULT_THEME_NAME = "scrivener"
"""The bundled theme selected when ``theme:`` sets none of ``name``, ``path``, ``package``."""


class ThemeError(Exception):
    """Raised when a theme manifest is invalid or a theme cannot be resolved.

    :ivar message: What is wrong.
    :ivar source: The theme directory or manifest at fault, when there is one.
    :ivar hint: A concrete fix.
    """

    def __init__(
        self, message: str, *, source: Path | str | None = None, hint: str | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.source = source
        self.hint = hint

    def __str__(self) -> str:
        return format_error(self.message, source=self.source, hint=self.hint)


_THEME_DIR_NEEDS = (
    "a theme directory needs a theme.yml with `name: my-theme`, "
    "plus optional templates/, static/, and icons/ folders"
)
_THEME_SOURCES_HINT = (
    "set exactly one of `name`, `path`, or `package` under `theme:` in bartleby.yml"
)


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

    def implemented_features(self) -> list[str]:
        """The sorted union of feature names declared by every manifest in the chain."""
        return sorted({name for layer in self.chain for name in layer.manifest.features})

    def templates_dirs(self) -> list[Path]:
        """Existing ``templates/`` directories, leaf-first."""
        return self._existing_dirs("templates")

    def static_dirs(self) -> list[Path]:
        """Existing ``static/`` directories, leaf-first."""
        return self._existing_dirs("static")

    def icons_dirs(self) -> list[Path]:
        """Existing ``icons/`` directories, leaf-first."""
        return self._existing_dirs("icons")

    def find_provider(self, relative_path: str) -> ThemeLayer | None:
        """The nearest layer that holds a file at ``relative_path``.

        This is the one per-file layer walk. :meth:`find_file`, :meth:`file_providers`,
        and so ``theme eject`` and ``theme inspect`` all resolve through it, so they
        cannot disagree about which layer wins.

        Args:
            relative_path: A path relative to a theme root, such as ``tailwind.css``.

        Returns:
            The first (leaf-most) layer holding the file, or ``None``.
        """
        for layer in self.chain:
            if (layer.root / relative_path).is_file():
                return layer
        return None

    def find_file(self, relative_path: str) -> Path | None:
        """The file at ``relative_path`` in the nearest layer that provides it.

        Args:
            relative_path: A path relative to a theme root, such as ``tailwind.css``.

        Returns:
            The file in the first (leaf-most) layer holding it, or ``None``.
        """
        layer = self.find_provider(relative_path)
        return None if layer is None else layer.root / relative_path

    def file_providers(self) -> dict[str, ThemeLayer]:
        """Every theme file mapped to the layer that provides it.

        Covers everything under ``templates/``, ``static/``, and ``icons/`` plus the
        Tailwind sources. Keys are theme-root-relative POSIX paths, sorted.

        Returns:
            Relative path to the leaf-most providing layer.
        """
        relative_paths: set[str] = set()
        for layer in self.chain:
            for subdirectory in THEME_ASSET_DIRS:
                base = layer.root / subdirectory
                relative_paths.update(
                    path.relative_to(layer.root).as_posix()
                    for path in base.rglob("*")
                    if path.is_file()
                )
            relative_paths.update(
                name for name in TAILWIND_SOURCES if (layer.root / name).is_file()
            )
        providers: dict[str, ThemeLayer] = {}
        for relative_path in sorted(relative_paths):
            provider = self.find_provider(relative_path)
            if provider is not None:
                providers[relative_path] = provider
        return providers

    def _existing_dirs(self, subdirectory: str) -> list[Path]:
        candidates = (layer.root / subdirectory for layer in self.chain)
        return [candidate for candidate in candidates if candidate.is_dir()]


def default_theme() -> ResolvedTheme:
    """The theme used when no theme is selected: the bundled default theme chain.

    Returns:
        The resolved chain for :data:`DEFAULT_THEME_NAME`.
    """
    return resolve_theme(
        project_dir=bundled_theme_root(DEFAULT_THEME_NAME).parent, name=DEFAULT_THEME_NAME
    )


def select_theme(theme_config: ThemeConfig, project_dir: Path) -> ResolvedTheme:
    """Resolve the theme that a ``theme:`` config section selects.

    Args:
        theme_config: The parsed ``theme:`` section.
        project_dir: The project directory that relative ``path`` values resolve against.

    Returns:
        The resolved chain.

    Raises:
        ThemeError: If the selected theme cannot be resolved.
    """
    uses_name = theme_config.path is None and theme_config.package is None
    return resolve_theme(
        project_dir=project_dir,
        name=theme_config.name if uses_name else None,
        path=theme_config.path,
        package=theme_config.package,
    )


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
        raise ThemeError(f"missing {MANIFEST_FILENAME}", source=root, hint=_THEME_DIR_NEEDS)
    try:
        parsed: Any = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f" at line {mark.line + 1}" if mark is not None else ""
        raise ThemeError(
            f"invalid YAML{where}",
            source=manifest_path,
            hint="fix the syntax at that line (check indentation, quotes, and brackets)",
        ) from exc
    if not isinstance(parsed, dict):
        raise ThemeError(
            "the manifest must be a YAML mapping",
            source=manifest_path,
            hint=_THEME_DIR_NEEDS,
        )
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
        raise ThemeError(
            "more than one of name, path, and package is set", hint=_THEME_SOURCES_HINT
        )

    if name is not None:
        root = _bundled_root(name)
    elif path is not None:
        root = _path_root(path, project_dir)
    elif package is not None:
        root = _package_root(package)
    else:
        raise ThemeError("none of name, path, or package is set", hint=_THEME_SOURCES_HINT)

    chain: list[ThemeLayer] = []
    while True:
        manifest = load_manifest(root)
        if any(layer.name == manifest.name for layer in chain):
            names = [layer.name for layer in chain] + [manifest.name]
            raise ThemeError(
                f"cyclic theme extends: {' -> '.join(names)}",
                source=root,
                hint="remove `extends:` from one theme.yml in that chain",
            )
        chain.append(ThemeLayer(name=manifest.name, root=root, manifest=manifest))
        if manifest.extends is None:
            return ResolvedTheme(chain=chain)
        root = _extends_root(manifest.extends, root)


def _parse_name(value: Any, root: Path) -> str:
    if not isinstance(value, str) or not value:
        raise ThemeError(
            "missing required key 'name'",
            source=root / MANIFEST_FILENAME,
            hint="add a line such as `name: my-theme`",
        )
    return value


def _parse_optional_str(value: Any, key: str, root: Path) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ThemeError(
            f"'{key}' must be a string",
            source=root / MANIFEST_FILENAME,
            hint=f'write it as `{key}: "text"`',
        )
    return value


def _parse_features(value: Any, root: Path) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ThemeError(
            "'features' must be a list of strings",
            source=root / MANIFEST_FILENAME,
            hint="write one `- feature.name` line per feature",
        )
    unknown = [item for item in value if item not in THEME_FEATURES]
    if unknown:
        known = ", ".join(sorted(THEME_FEATURES))
        raise ThemeError(
            f"unknown feature {unknown[0]!r} in 'features'",
            source=root / MANIFEST_FILENAME,
            hint=f"use native features only: {known}",
        )
    return list(value)


def _bundled_root(name: str) -> Path:
    if name not in BUNDLED_THEME_NAMES:
        known = ", ".join(BUNDLED_THEME_NAMES)
        raise ThemeError(
            f"unknown bundled theme {name!r}",
            hint=(
                f"set theme.name to one of the bundled themes ({known}), "
                "or use theme.path for a theme directory in your project"
            ),
        )
    root = bundled_theme_root(name)
    if not root.is_dir():
        raise ThemeError(
            f"bundled theme {name!r} is missing from the install",
            source=root,
            hint="reinstall bartleby-ssg",
        )
    return root


def _path_root(path: str, project_dir: Path) -> Path:
    root = Path(path)
    if not root.is_absolute():
        root = project_dir / root
    if not root.is_dir():
        raise ThemeError(
            "theme path does not exist",
            source=root,
            hint=(
                "set theme.path to an existing directory, relative to the project, "
                "or create one with `bartleby theme eject`"
            ),
        )
    return root


def _package_root(package: str) -> Path:
    for entry_point in importlib.metadata.entry_points(group=THEME_ENTRY_POINT_GROUP):
        if entry_point.name != package:
            continue
        loaded: Any = entry_point.load()
        if not isinstance(loaded, str | Path):
            raise ThemeError(
                f"theme package {package!r} must load to a directory path",
                hint="make the entry point return a Path or str naming the theme directory",
            )
        root = Path(loaded)
        if not root.is_dir():
            raise ThemeError(
                f"theme package {package!r} points at a missing directory",
                source=root,
                hint="reinstall the package, or fix the directory its entry point returns",
            )
        return root
    raise ThemeError(
        f"theme package {package!r} not found in entry-point group {THEME_ENTRY_POINT_GROUP!r}",
        hint="install the package that provides it, or check theme.package for a typo",
    )


def _extends_root(extends: str, child_root: Path) -> Path:
    if extends in BUNDLED_THEME_NAMES:
        return _bundled_root(extends)
    sibling = child_root.parent / extends
    if sibling.is_dir():
        return sibling
    return _package_root(extends)


def _file_kind(relative_path: str) -> str:
    """Classify a theme-relative path as template, static, icon, or tailwind.

    The safelist belongs to the Tailwind sources, so it classifies as ``tailwind``.
    """
    top = relative_path.split("/", 1)[0]
    return {"templates": "template", "static": "static", "icons": "icon"}.get(top, "tailwind")


@dataclass(slots=True)
class EjectResult:
    """Result of ``bartleby theme eject``.

    Attributes:
        theme: The ejected theme's name.
        target: The directory written, as shown to the user.
        files: Theme-relative paths copied, sorted.
        config_line: The ``theme:`` snippet to put in ``bartleby.yml``.
    """

    theme: str
    target: str
    files: list[str]
    config_line: str

    @property
    def exit_code(self) -> int:
        return 0

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "success",
            "theme": self.theme,
            "target": self.target,
            "files": self.files,
            "config": self.config_line,
        }

    def to_text(self) -> str:
        return (
            f"Ejected theme {self.theme!r} ({len(self.files)} files) to {self.target}\n"
            f"Add this to bartleby.yml:\n{self.config_line}"
        )


@dataclass(slots=True)
class InspectedFile:
    """One file in a resolved theme.

    Attributes:
        path: Theme-relative POSIX path.
        kind: ``template``, ``static``, ``icon``, or ``tailwind``.
        layer: Name of the layer that provides the file.
        shadowed_by: Project-relative path of the ``overrides/`` file that shadows
            this template, or ``None``.
    """

    path: str
    kind: str
    layer: str
    shadowed_by: str | None


@dataclass(slots=True)
class InspectResult:
    """Result of ``bartleby theme inspect``.

    Attributes:
        theme: The requested theme's name.
        chain: Layer names, leaf-first.
        files: Every theme file, sorted by path.
    """

    theme: str
    chain: list[str]
    files: list[InspectedFile]

    @property
    def exit_code(self) -> int:
        return 0

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "success",
            "theme": self.theme,
            "chain": self.chain,
            "files": [
                {
                    "path": item.path,
                    "kind": item.kind,
                    "layer": item.layer,
                    "shadowed_by": item.shadowed_by,
                }
                for item in self.files
            ],
        }

    def to_text(self) -> str:
        lines = [f"Theme {self.theme} (chain: {' -> '.join(self.chain)})"]
        for item in self.files:
            suffix = f"  [shadowed by {item.shadowed_by}]" if item.shadowed_by else ""
            lines.append(f"{item.path}  ({item.layer}){suffix}")
        return "\n".join(lines)


def flatten_chain(
    resolved: ResolvedTheme, destination: Path, *, project_dir: Path, force: bool = False
) -> EjectResult:
    """Copy a resolved theme chain, flattened leaf-wins, into one directory.

    The directory gets every template, static, icon, and Tailwind source file the
    chain provides (the leaf's version wins a shared path) and a ``theme.yml`` with
    the leaf's name, version, and description, the union of features across the chain,
    and no ``extends``.

    Args:
        resolved: The theme chain to flatten.
        destination: The directory to write.
        project_dir: The project directory, used to show ``destination`` relative to it.
        force: Overwrite files in an existing destination.

    Returns:
        The files written and the ``theme:`` config snippet.

    Raises:
        ThemeError: If the destination exists and ``force`` is false, or is a theme
            directory in the chain being flattened, inside one, or contains one.
    """
    if destination.exists() and not force:
        raise ThemeError(
            "destination already exists",
            source=destination,
            hint="pass --force to overwrite it, or choose another --to",
        )
    resolved_destination = destination.resolve()
    for layer in resolved.chain:
        layer_root = layer.root.resolve()
        if resolved_destination == layer_root:
            raise ThemeError(
                "destination is part of the theme being ejected",
                source=destination,
                hint="choose another --to",
            )
        if resolved_destination.is_relative_to(layer_root) or layer_root.is_relative_to(
            resolved_destination
        ):
            raise ThemeError(
                f"destination and theme directory {layer.root} are inside one another",
                source=destination,
                hint="choose another --to",
            )

    # Copy each file from its winning layer
    providers = resolved.file_providers()
    for relative_path, layer in providers.items():
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(layer.root / relative_path, target)

    # Write a manifest that stands alone
    leaf = resolved.chain[0].manifest
    features = resolved.implemented_features()
    manifest: dict[str, object] = {"name": leaf.name}
    if leaf.version is not None:
        manifest["version"] = leaf.version
    if leaf.description is not None:
        manifest["description"] = leaf.description
    manifest["features"] = features
    destination.mkdir(parents=True, exist_ok=True)
    (destination / MANIFEST_FILENAME).write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )

    # Report where it landed, relative to the project when it sits inside it
    shown = destination.resolve()
    if shown.is_relative_to(project_dir.resolve()):
        shown = shown.relative_to(project_dir.resolve())
    return EjectResult(
        theme=leaf.name,
        target=shown.as_posix(),
        files=sorted([*providers, MANIFEST_FILENAME]),
        config_line=f"theme:\n  path: {shown.as_posix()}",
    )


def inspect_chain(resolved: ResolvedTheme, project_dir: Path) -> InspectResult:
    """List every file in a resolved theme with its providing layer.

    A template is marked shadowed when a file at the same template path exists in
    one of the project-level search bases that precede the theme layers (``overrides/``,
    ``templates/``, the project root). Those bases come from
    :func:`bartleby.templates.template_search_bases`, so this report follows the real
    Jinja cascade; ``shadowed_by`` names the first one that wins.

    Args:
        resolved: The theme chain to inspect.
        project_dir: The project directory holding the shadowing files.

    Returns:
        Files sorted by path.
    """
    # templates.py imports this module at load time, so import it lazily here
    from bartleby.templates import template_search_bases  # noqa: PLC0415

    bases = template_search_bases(project_dir, resolved)
    project_bases = bases[: len(bases) - len(resolved.templates_dirs())]
    files: list[InspectedFile] = []
    for relative_path, layer in resolved.file_providers().items():
        kind = _file_kind(relative_path)
        shadowed_by: str | None = None
        if kind == "template":
            template_name = relative_path.removeprefix("templates/")
            for base in project_bases:
                if (base / template_name).is_file():
                    shadowed_by = (base / template_name).relative_to(project_dir).as_posix()
                    break
        files.append(
            InspectedFile(path=relative_path, kind=kind, layer=layer.name, shadowed_by=shadowed_by)
        )
    return InspectResult(
        theme=resolved.chain[0].name, chain=[layer.name for layer in resolved.chain], files=files
    )
