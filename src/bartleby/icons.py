# ABOUTME: Icon pack management, resolution, and build-time tree-shaking.
# Maps icon names to bundled SVGs and copies only referenced icons to site output.

from __future__ import annotations

import re
import shutil
from pathlib import Path

_PACK_PREFIXES: dict[str, tuple[str, str]] = {
    # pack key: (prefix used in `:name:` references, on-disk directory name)
    "material": ("material-", "material"),
    "fontawesome": ("fontawesome-", "fontawesome-brands"),
    "octicons": ("octicons-", "octicons"),
    "simple": ("simple-", "simple"),
}

DEFAULT_ICON_PACKS: dict[str, bool] = dict.fromkeys(_PACK_PREFIXES, True)
"""All bundled icon packs, enabled. The base that config overrides are merged onto."""

_ICON_CLASS_RE = re.compile(r"icon-([a-z0-9-]+)")


def get_icon_path(icon_name: str, icon_packs: dict[str, bool]) -> Path | None:
    """Resolve an icon name like ``material-account`` to a bundled SVG path.

    :param icon_name: The icon name (without leading ``:``), e.g. ``"material-account"``.
    :param icon_packs: Mapping of pack key to enabled flag. A pack with
        ``False`` is treated as if it didn't exist.
    :returns: An absolute path to the SVG file when found, else ``None``.
    """
    base = _icons_root()
    for pack_key, (prefix, dirname) in _PACK_PREFIXES.items():
        if not icon_packs.get(pack_key, False):
            continue
        if not icon_name.startswith(prefix):
            continue
        rest = icon_name[len(prefix) :]
        # FontAwesome lives under "fontawesome-brands/" — strip the leading
        # "brands-" from the rest if present, since the prefix already
        # consumed "fontawesome-".
        if pack_key == "fontawesome" and rest.startswith("brands-"):
            rest = rest[len("brands-") :]
        candidate = base / dirname / f"{rest}.svg"
        if candidate.exists():
            return candidate
    return None


def tree_shake_icons(
    rendered_pages: list[str], icon_packs: dict[str, bool], output_dir: Path
) -> None:
    """Copy only the icons referenced in ``rendered_pages`` to ``output_dir/icons/``.

    :param rendered_pages: Iterable of rendered HTML strings to scan for
        ``class="icon-…"`` references.
    :param icon_packs: Mapping of pack name to enabled flag.
    :param output_dir: The build output directory (``site/``).
    """
    referenced: set[str] = set()
    for html in rendered_pages:
        referenced.update(_ICON_CLASS_RE.findall(html))

    for icon_name in referenced:
        source = get_icon_path(icon_name, icon_packs)
        if source is None:
            continue
        pack_dir = source.parent.name
        destination = output_dir / "icons" / pack_dir / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _icons_root() -> Path:
    """Absolute path to the bundled icon directory inside the theme package."""
    return Path(__file__).parent / "theme" / "icons"
