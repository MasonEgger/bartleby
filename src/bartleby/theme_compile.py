# ABOUTME: Hybrid Tailwind pipeline — resolve the standalone binary and compile theme CSS.
# Resolution order: tailwindcss on PATH -> cached binary -> explicit SHA-256-verified download.

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import stat
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from bartleby.theme_loader import ResolvedTheme

# Pinned Tailwind standalone CLI release. Bump together with the SHA-256 map.
PINNED_TAILWIND_VERSION = "3.4.17"

# SHA-256 digests of each platform asset for PINNED_TAILWIND_VERSION. Recorded
# from the official GitHub release's sha256sums.txt so downloads are verified
# before use. The tests inject their own digest via ``expected_sha256``;
# production callers fall back to this map keyed on the resolved asset name.
_RELEASE_SHA256: dict[str, str] = {
    "tailwindcss-linux-x64": "7d24f7fa191d2193b78cd5f5a42a6093e14409521908529f42d80b11fde1f1d4",
    "tailwindcss-linux-arm64": "69b1378b8133192d7d2feb12a116fa12d035594f58db3eff215879e4ad8cf39b",
    "tailwindcss-macos-x64": "6cbdad74be776c087ffa5e9a057512c54898f9fe8828d3362212dfe32fc933a3",
    "tailwindcss-macos-arm64": "a1d0c7985759accca0bf12e51ac1dcbf0f6cf2fffb62e6e0f62d091c477a10a3",
    "tailwindcss-windows-x64.exe": (
        "67f1c5e3f5a03406a7bf5badf5ada09b79f3ae78ec43450c15f7e983068da346"
    ),
    "tailwindcss-windows-arm64.exe": (
        "76f516476784c00f1562160b5758e3d8f0e6c48957efb26b5b50fbdfd76aa382"
    ),
}

_GITHUB_RELEASE = (
    "https://github.com/tailwindlabs/tailwindcss/releases/download/v{version}/{asset}"
)

# Directory names scanned for user-added utility classes, relative to the project.
_SCAN_SUBDIRS = ("overrides", "partials", "shortcodes", "templates")


# Wrapper input body used when no theme layer ships a tailwind.css. The wrapper
# sits beside the generated tokens.css, which is how the relative import resolves.
_TAILWIND_DIRECTIVES = "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n"


class ThemeCompileError(Exception):
    """A failure resolving the Tailwind binary or compiling theme CSS."""


@dataclass(slots=True)
class ThemeCompileResult:
    """Result of ``bartleby theme compile`` (spec.md JSON output)."""

    css_path: str
    binary: str
    duration_ms: int
    classes_scanned: int

    @property
    def exit_code(self) -> int:
        return 0

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "success",
            "css_path": self.css_path,
            "binary": self.binary,
            "duration_ms": self.duration_ms,
            "classes_scanned": self.classes_scanned,
        }

    def to_text(self) -> str:
        return (
            f"Compiled theme CSS to {self.css_path} "
            f"({self.classes_scanned} classes, {self.binary} binary, {self.duration_ms} ms)"
        )


def tailwind_asset_name() -> str:
    """Name of the Tailwind standalone asset for the current platform.

    :returns: The GitHub release asset filename (e.g. ``tailwindcss-linux-x64``).
    :raises ThemeCompileError: When the platform is not one Tailwind ships for.
    """
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
    if system == "linux":
        return f"tailwindcss-linux-{arch}"
    if system == "darwin":
        return f"tailwindcss-macos-{arch}"
    if system == "windows":
        return f"tailwindcss-windows-{arch}.exe"
    raise ThemeCompileError(f"no Tailwind standalone build for platform {system!r}")


def default_cache_dir() -> Path:
    """Platform cache directory for the downloaded Tailwind binary."""
    base = os.environ.get("XDG_CACHE_HOME")
    root = Path(base) if base else Path.home() / ".cache"
    return root / "bartleby"


def _download(url: str) -> bytes:
    """Fetch ``url`` and return the raw bytes (no caching)."""
    with urllib.request.urlopen(url) as response:  # noqa: S310 - pinned GitHub release URL
        body: bytes = response.read()
    return body


def resolve_tailwind_binary(
    *,
    cache_dir: Path,
    allow_download: bool = False,
    refresh: bool = False,
    expected_sha256: str | None = None,
    fetch: Callable[[str], bytes] | None = None,
) -> tuple[Path, str]:
    """Resolve the Tailwind standalone binary.

    Resolution order: a ``tailwindcss`` on ``PATH`` wins; otherwise a cached
    binary at ``<cache_dir>/tailwindcss-<version>``; otherwise, only when
    ``allow_download`` is set, an explicit download verified against
    ``expected_sha256``. The download is atomic: bytes are written to a temp
    file, checksummed, then moved into place, so a checksum mismatch never
    leaves a partial binary behind.

    :param cache_dir: Directory holding the cached binary.
    :param allow_download: When ``False``, a cache miss raises instead of fetching.
    :param refresh: When ``True``, skip both PATH and cache and force a download.
    :param expected_sha256: Hex digest the downloaded bytes must match.
    :param fetch: Override for the network fetch (the tests inject a stub).
    :returns: ``(binary_path, origin)`` where origin is ``"path"``,
        ``"cached"``, or ``"downloaded"``.
    :raises ThemeCompileError: On a cache miss with downloads disabled, or a
        checksum mismatch, or an unsupported platform.
    """
    if not refresh:
        on_path = shutil.which("tailwindcss")
        if on_path is not None:
            return Path(on_path), "path"

        cached = cache_dir / f"tailwindcss-{PINNED_TAILWIND_VERSION}"
        if cached.exists():
            return cached, "cached"

    if not allow_download:
        raise ThemeCompileError(
            "no tailwindcss on PATH and none cached; run "
            "`bartleby theme compile` to download the standalone binary"
        )

    return _download_binary(
        cache_dir=cache_dir,
        expected_sha256=expected_sha256,
        fetch=fetch or _download,
    )


def _download_binary(
    *,
    cache_dir: Path,
    expected_sha256: str | None,
    fetch: Callable[[str], bytes],
) -> tuple[Path, str]:
    """Download, verify, and atomically install the Tailwind binary.

    :raises ThemeCompileError: When the checksum does not match.
    """
    asset = tailwind_asset_name()
    url = _GITHUB_RELEASE.format(version=PINNED_TAILWIND_VERSION, asset=asset)
    expected = expected_sha256 or _RELEASE_SHA256.get(asset)
    if expected is None:
        raise ThemeCompileError(f"no recorded SHA-256 for asset {asset!r}")

    payload = fetch(url)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected:
        raise ThemeCompileError(
            f"Tailwind binary checksum mismatch: expected {expected}, got {digest}"
        )

    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"tailwindcss-{PINNED_TAILWIND_VERSION}"
    temp = cache_dir / f"tailwindcss-{PINNED_TAILWIND_VERSION}.tmp"
    temp.write_bytes(payload)
    temp.chmod(temp.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    temp.replace(target)
    return target, "downloaded"


def active_theme_css(project_dir: Path, theme: ResolvedTheme | None = None) -> Path | None:
    """Return the project's compiled theme CSS when it should be preferred.

    ``<project>/.bartleby/theme.css`` is preferred over the shipped CSS only
    when it exists and is at least as new as every file in the project
    ``templates/`` tree and in the ``templates/`` of every project-local theme
    layer (a ``theme.path`` directory is a project file the user edits). A
    compiled CSS older than any of those is stale and ignored so the build
    falls back to the shipped CSS. Bundled and package layers are not checked.

    :param project_dir: The project root directory.
    :param theme: The resolved theme whose project-local layers are checked.
    :returns: The compiled CSS path when it should win, else ``None``.
    """
    compiled = project_dir / ".bartleby" / "theme.css"
    if not compiled.exists():
        return None

    compiled_mtime = compiled.stat().st_mtime
    watched = [project_dir / "templates"]
    if theme is not None:
        project_root = project_dir.resolve()
        watched.extend(
            layer.root / "templates"
            for layer in theme.chain
            if layer.root.resolve().is_relative_to(project_root)
        )
    for templates_dir in watched:
        if not templates_dir.exists():
            continue
        for source in templates_dir.rglob("*"):
            if source.is_file() and source.stat().st_mtime > compiled_mtime:
                return None
    return compiled


def css_import_line(path: PurePath) -> str:
    """Build a CSS ``@import`` line for an absolute file path.

    Forward slashes are used on every platform because CSS reads a backslash in
    a string as an escape sequence.

    :param path: The file to import.
    :returns: The ``@import`` statement, newline-terminated.
    :raises ThemeCompileError: When the path contains a double quote, which
        would end the CSS string early.
    """
    posix = path.as_posix()
    if '"' in posix:
        raise ThemeCompileError(f"cannot import a path containing a double quote: {posix}")
    return f'@import "{posix}";\n'


def format_tokens_css(tokens: Mapping[str, str]) -> str:
    """Render design tokens as a ``:root`` block of ``--bb-*`` custom properties.

    A dotted token name becomes a dashed property: ``color.primary`` is
    ``--bb-color-primary``. An empty map renders an empty string.
    """
    if not tokens:
        return ""
    lines = [f"  --bb-{name.replace('.', '-')}: {value};" for name, value in tokens.items()]
    return ":root {\n" + "\n".join(lines) + "\n}\n"


def compile_theme_css(
    project_dir: Path,
    theme: ResolvedTheme,
    tokens: Mapping[str, str],
    *,
    refresh: bool = False,
    cache_dir: Path | None = None,
) -> ThemeCompileResult:
    """Compile the resolved theme's CSS, including tokens and project overrides.

    Resolves the binary (PATH -> cache -> download), then writes
    ``<project>/.bartleby/tokens.css`` from ``tokens`` (always, even when
    empty, so an ``@import`` of it never fails). ``--config`` comes from the
    nearest layer (leaf-first) with a ``tailwind.config.js``. ``--input`` is
    always the generated wrapper ``.bartleby/input.css``, which sits beside
    ``tokens.css`` (postcss-import resolves relative imports from the input's
    own directory) and imports ``tokens.css`` first, then the absolute path of
    the nearest layer's ``tailwind.css``. When no layer has a ``tailwind.css``
    the wrapper carries the three ``@tailwind`` directives instead. Tokens
    therefore reach every theme's CSS without the theme importing them.
    ``--content`` covers
    every layer's ``templates/`` plus the project ``overrides/``,
    ``partials/``, ``shortcodes/``, and ``templates/`` directories. The result
    is written to ``<project>/.bartleby/theme.css``.

    :param project_dir: The project root directory.
    :param theme: The resolved theme chain, leaf-first.
    :param tokens: The ``theme.tokens`` map of dotted names to CSS values.
    :param refresh: Force a re-download of the Tailwind binary.
    :param cache_dir: Override the binary cache location (defaults to the
        platform cache dir).
    :returns: A :class:`ThemeCompileResult` describing the compile.
    :raises ThemeCompileError: When the binary cannot be resolved or Tailwind
        exits non-zero.
    """
    started = time.perf_counter()
    resolved_cache = cache_dir or default_cache_dir()
    binary, origin = resolve_tailwind_binary(
        cache_dir=resolved_cache,
        allow_download=True,
        refresh=refresh,
    )

    output_dir = project_dir / ".bartleby"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "tokens.css").write_text(format_tokens_css(tokens), encoding="utf-8")

    # Both @imports lead the file so postcss-import accepts them.
    theme_input = theme.find_file("tailwind.css")
    theme_body = (
        _TAILWIND_DIRECTIVES if theme_input is None else css_import_line(theme_input.resolve())
    )
    tailwind_input = output_dir / "input.css"
    tailwind_input.write_text(f'@import "tokens.css";\n{theme_body}', encoding="utf-8")
    tailwind_config = theme.find_file("tailwind.config.js")

    output = output_dir / "theme.css"
    command = [str(binary)]
    if tailwind_config is not None:
        command += ["--config", str(tailwind_config)]
    command += [
        "--input",
        str(tailwind_input),
        "--content",
        ",".join(_content_globs(project_dir, theme)),
        "--output",
        str(output),
    ]
    completed = subprocess.run(  # noqa: S603 - resolved binary, fixed arg list
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ThemeCompileError(f"tailwindcss failed: {completed.stderr.strip()}")

    duration_ms = round((time.perf_counter() - started) * 1000)
    classes_scanned = _count_classes(output)
    return ThemeCompileResult(
        css_path=str(output.relative_to(project_dir)),
        binary=origin,
        duration_ms=duration_ms,
        classes_scanned=classes_scanned,
    )


def _content_globs(project_dir: Path, theme: ResolvedTheme) -> list[str]:
    """Build the list of template globs Tailwind scans for utility classes."""
    globs = [str(templates_dir / "**" / "*.html") for templates_dir in theme.templates_dirs()]
    for subdir in _SCAN_SUBDIRS:
        candidate = project_dir / subdir
        if candidate.exists():
            globs.append(str(candidate / "**" / "*.html"))
    return globs


def _count_classes(css_path: Path) -> int:
    """Count CSS rule selectors in the compiled output as a classes-scanned proxy."""
    if not css_path.exists():
        return 0
    text = css_path.read_text(encoding="utf-8")
    return text.count("{")
